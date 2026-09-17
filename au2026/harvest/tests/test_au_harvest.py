"""AU harvester tests — stdlib unittest only (no new deps).

Run from the repo root:  python -m unittest tests.test_au_harvest -v
Covers the pure logic (link classification, slugs, filenames, embeds) and the
manifest/notes writers. The Playwright driver is exercised on the operator's PC.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import links  # noqa: E402
import manifest  # noqa: E402


class LinkClassification(unittest.TestCase):
    def test_extension_wins(self):
        self.assertEqual(links.classify_link("https://x/y/deck.PPTX?sig=1", "open"), "presentation")
        self.assertEqual(links.classify_link("https://x/handout.pdf", ""), "document")
        self.assertEqual(links.classify_link("https://cdn/x/master.m3u8", ""), "video")
        self.assertEqual(links.classify_link("https://x/files.zip", ""), "dataset")

    def test_text_fallback_for_opaque_urls(self):
        self.assertEqual(links.classify_link("https://x/dl/abc123", "Download presentation"), "presentation")
        self.assertEqual(links.classify_link("https://x/dl/abc123", "Class handout"), "document")
        self.assertEqual(links.classify_link("", "Watch recording"), "video")
        self.assertEqual(links.classify_link("https://x/dl/1", "Download"), "document")

    def test_non_downloads_are_none(self):
        self.assertIsNone(links.classify_link("https://x/agenda", "Agenda"))
        self.assertIsNone(links.classify_link("https://x/speaker/jane", "Jane Doe"))

    def test_class_url_patterns(self):
        self.assertTrue(links.is_class_url("https://conferences.autodesk.com/flow/autodesk/au2026/sessioncatalog/page/sessioncatalog/session/1783105132417001PTZE"))
        self.assertTrue(links.is_class_url("https://conferences.autodesk.com/flow/autodesk/au2026/web/page/agenda/session/1712345678"))
        self.assertTrue(links.is_class_url("https://www.autodesk.com/autodesk-university/class/seven-deadly-sins-civil-3d-2026"))
        self.assertFalse(links.is_class_url("https://conferences.autodesk.com/flow/autodesk/au2026/web/page/agenda"))
        self.assertFalse(links.is_class_url("mailto:au.info@autodeskuniversity.com"))
        self.assertFalse(links.is_class_url("#top"))

    def test_extract_embeds(self):
        html = """
        <iframe src="https://players.brightcove.net/123/default_default/index.html?videoId=456"></iframe>
        <video><source src="https://d1.cloudfront.net/rec/master.m3u8"></video>
        <iframe src="https://www.google.com/maps/embed"></iframe>
        <iframe src="https://players.brightcove.net/123/default_default/index.html?videoId=456"></iframe>
        """
        found = links.extract_embed_urls(html)
        self.assertEqual(len(found), 2)
        self.assertTrue(found[0].startswith("https://players.brightcove.net"))

    def test_slug_and_filename(self):
        self.assertEqual(links.slugify("Seven Deadly Sins of Civil 3D: Project Performance!"), "seven-deadly-sins-of-civil-3d-project-performance")
        self.assertEqual(links.slugify(""), "untitled")
        self.assertEqual(links.safe_filename('https://x/a/b/AU2026%20Deck:v2.pptx?sig=1'), "AU2026 Deck_v2.pptx")
        self.assertEqual(links.safe_filename("", fallback="f.bin"), "f.bin")


class ManifestAndNotes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _meta(self):
        rows = [
            manifest.MaterialRow("c1", "Forma Roadmap", "https://x/deck.pdf", "document", "deck.pdf", 2048, "saved"),
            manifest.MaterialRow("c1", "Forma Roadmap", "https://x/v.m3u8", "video", status="stream"),
        ]
        return manifest.ClassMeta("c1", "Forma Roadmap", "https://x/class/forma-roadmap-2026",
                                  ["A. Speaker"], "What is coming.", rows, ["https://players.brightcove.net/1/x"])

    def test_manifest_roundtrip(self):
        meta = self._meta()
        path = self.root / "manifest.csv"
        manifest.write_manifest(meta.materials, path)
        back = manifest.read_manifest(path)
        self.assertEqual(len(back), 2)
        self.assertEqual(back[0].bytes, 2048)
        self.assertEqual(back[1].status, "stream")
        self.assertEqual(manifest.read_manifest(self.root / "missing.csv"), [])

    def test_meta_and_note(self):
        meta = self._meta()
        manifest.write_class_meta(meta, self.root / "c1" / "meta.json")
        self.assertIn('"speakers"', (self.root / "c1" / "meta.json").read_text(encoding="utf-8"))
        note = manifest.class_note_markdown(meta, "C:/AU2026/forma-roadmap")
        self.assertIn("# AU 2026 — Forma Roadmap", note)
        self.assertIn("- Speakers: A. Speaker", note)
        self.assertIn("[saved] document: deck.pdf (2 KB)", note)
        self.assertIn("[stream] video: https://players.brightcove.net/1/x", note)
        self.assertIn("## Takeaways for TEG", note)
        empty = manifest.ClassMeta("c2", "Empty", "https://x")
        self.assertIn("_None found", manifest.class_note_markdown(empty, "x"))


if __name__ == "__main__":
    unittest.main()


class CatalogSelection(unittest.TestCase):
    def setUp(self):
        import catalog  # noqa: F401
        self.catalog = catalog
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "cat.json"
        self.path.write_text(json.dumps([
            {"code": "AS2183", "title": "Using MCP", "type": "Technical Deep Dive", "url": "https://x/session/1783A", "times": [{"date": "2026-09-16", "s": 540, "e": 600}]},
            {"code": "5034", "title": "AU Merch Store", "type": "Activity", "url": "https://x/session/1783B", "times": [{"date": "2026-09-15", "s": 540, "e": 600}]},
            {"code": "CS1316", "title": "Claude MCP", "type": "Strategy Talk", "url": "https://x/session/1783C", "times": []},
            {"code": "NOURL", "title": "Broken", "type": "Strategy Talk", "url": "", "times": []},
        ]), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_and_default_selection_drops_logistics_and_urlless(self):
        rows = self.catalog.load_catalog(self.path)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0].date, "2026-09-16")
        self.assertEqual(rows[2].date, "")
        picked = self.catalog.select_sessions(rows)
        self.assertEqual([s.code for s in picked], ["AS2183", "CS1316"])
        self.assertEqual([s.code for s in self.catalog.select_sessions(rows, include_logistics=True)], ["AS2183", "5034", "CS1316"])

    def test_code_and_date_filters(self):
        rows = self.catalog.load_catalog(self.path)
        self.assertEqual([s.code for s in self.catalog.select_sessions(rows, codes={"CS1316"})], ["CS1316"])
        self.assertEqual([s.code for s in self.catalog.select_sessions(rows, dates={"2026-09-16"})], ["AS2183"])
        self.assertEqual(self.catalog.parse_code_list("as2183, cs1316  bes4067"), {"AS2183", "CS1316", "BES4067"})

    def test_real_catalog_file_loads(self):
        real = Path(__file__).resolve().parent.parent.parent / "data" / "au2026_catalog.json"
        rows = self.catalog.select_sessions(self.catalog.load_catalog(real))
        self.assertGreater(len(rows), 600)
        self.assertTrue(all(links.is_class_url(s.url) for s in rows))
