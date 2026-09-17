"""AU 2026 harvester — run this on YOUR PC, not in the cloud.

The Autodesk University site sits behind your Autodesk login, so this opens a
real Chromium window with a persistent profile, lets you sign in once, then
walks the catalog and downloads every deck, handout, dataset and recording it
can find. Nothing runs headless and nothing stores your password: the browser
profile on disk holds the session cookie, exactly like your normal browser.

Typical run (PowerShell, from the repo root):

    pip install -r au2026/harvest/requirements.txt
    playwright install chromium
    python tools/au_harvest/au_harvest.py --out "C:\\Users\\<you>\\Tandem\\AU2026" ^
        --from-catalog au2026/data/au2026_catalog.json

Status: AMBER. Written blind — the build environment could not reach any
Autodesk host, so selectors are pattern-based and the start URLs are best
guesses. Use --start-url to point it at whatever page shows the class list on
your screen. Expect to iterate once against the live site.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from links import (  # noqa: E402
    classify_link,
    extract_embed_urls,
    is_class_url,
    safe_filename,
    slugify,
)
from catalog import load_catalog, parse_code_list, select_sessions  # noqa: E402
from manifest import (  # noqa: E402
    ClassMeta,
    MaterialRow,
    read_manifest,
    write_class_meta,
    write_class_note,
    write_manifest,
)

START_URLS: dict[str, str] = {
    # RainFocus session catalog — the list the Events app mirrors (in-person tab).
    "catalog": "https://conferences.autodesk.com/flow/autodesk/au2026/sessioncatalog/page/inperson?tab.inpersontabs=inPersonTab_All",
    # Your saved sessions only.
    "myschedule": "https://conferences.autodesk.com/flow/autodesk/au2026/myschedule/page/inperson",
    # Post-event class library, where recordings + handouts get published.
    "library": "https://www.autodesk.com/autodesk-university/conference/overview",
}

POLITE_DELAY_S = 1.5
SCROLL_ROUNDS_MAX = 60


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def wait_for_operator(prompt: str) -> None:
    input(f"\n>>> {prompt}\n>>> Press Enter here when ready... ")


def scroll_to_load_all(page) -> None:
    """Infinite-scroll the catalog until the page height stops growing."""
    last_height = -1
    for _ in range(SCROLL_ROUNDS_MAX):
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(900)
        # Some catalogs use a "Load more" button instead of infinite scroll.
        for label in ("Load more", "Show more", "More results"):
            btn = page.get_by_role("button", name=re.compile(label, re.I))
            if btn.count() and btn.first.is_visible():
                btn.first.click()
                page.wait_for_timeout(1200)
        height = page.evaluate("document.body.scrollHeight")
        if height == last_height:
            break
        last_height = height


def collect_class_links(page) -> list[tuple[str, str]]:
    """(href, text) for every anchor on the page that looks like a class detail."""
    anchors = page.evaluate(
        "Array.from(document.querySelectorAll('a[href]')).map(a => [a.href, a.innerText.trim()])"
    )
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for href, text in anchors:
        if is_class_url(href) and href not in seen:
            seen.add(href)
            out.append((href, text))
    return out


def read_class_page(page, url: str) -> ClassMeta:
    """Open a class page and pull title, speakers, description, download links, embeds."""
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    title = (page.title() or "").split("|")[0].strip()
    h1 = page.locator("h1")
    if h1.count():
        title = h1.first.inner_text().strip() or title
    class_id = slugify(re.sub(r".*/(session|class)/", "", url).split("?")[0]) or slugify(title)

    speakers: list[str] = []
    for sel in ("[class*=speaker] [class*=name]", "[data-testid*=speaker]", "[class*=Speaker]"):
        loc = page.locator(sel)
        for i in range(min(loc.count(), 12)):
            name = loc.nth(i).inner_text().strip()
            if name and name not in speakers and len(name) < 80:
                speakers.append(name)
        if speakers:
            break

    description = ""
    for sel in ("[class*=description]", "[class*=abstract]", "section p", "main p"):
        loc = page.locator(sel)
        if loc.count():
            description = "\n\n".join(
                loc.nth(i).inner_text().strip() for i in range(min(loc.count(), 6))
            ).strip()
            if description:
                break

    anchors = page.evaluate(
        "Array.from(document.querySelectorAll('a[href], button')).map(e => [e.href || '', e.innerText.trim()])"
    )
    materials: list[MaterialRow] = []
    seen: set[str] = set()
    for href, text in anchors:
        kind = classify_link(href, text)
        key = href or text
        if kind and key and key not in seen:
            seen.add(key)
            materials.append(MaterialRow(class_id, title, href or url, kind, note=text[:120]))

    embeds = extract_embed_urls(page.content())
    return ClassMeta(class_id, title, url, speakers, description, materials, embeds)


def download_material(page, row: MaterialRow, dest_dir: Path) -> None:
    """Click / fetch one material into dest_dir, updating the row in place."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        if row.url and row.url != page.url and classify_link(row.url):
            # Direct file link: let the browser download it so cookies apply.
            with page.expect_download(timeout=120_000) as dl:
                page.evaluate(
                    "url => { const a = document.createElement('a'); a.href = url; a.download = ''; document.body.appendChild(a); a.click(); a.remove(); }",
                    row.url,
                )
            download = dl.value
        else:
            # Button with no href: click it by its text.
            with page.expect_download(timeout=120_000) as dl:
                page.get_by_text(row.note, exact=False).first.click()
            download = dl.value
        name = safe_filename(download.suggested_filename, fallback=f"{row.kind}.bin")
        target = dest_dir / name
        if target.exists():
            row.file_name, row.bytes, row.status = name, target.stat().st_size, "skipped"
            return
        download.save_as(target)
        row.file_name, row.bytes, row.status = name, target.stat().st_size, "saved"
    except Exception as exc:  # noqa: BLE001 — one bad link must not stop the run
        row.status, row.note = "failed", f"{row.note} | {type(exc).__name__}: {exc}"[:240]


def fetch_streams_with_ytdlp(embeds: list[str], dest_dir: Path, profile_dir: Path) -> list[str]:
    """Hand streaming embeds to yt-dlp using the same browser profile's cookies."""
    notes: list[str] = []
    for url in embeds:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--cookies-from-browser", f"chromium:{profile_dir}",
            "-o", str(dest_dir / "%(title)s.%(ext)s"),
            "--no-overwrites", url,
        ]
        log(f"yt-dlp {url}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        notes.append(f"{'ok' if result.returncode == 0 else 'failed'}: {url}")
        if result.returncode != 0:
            log(result.stderr[-400:])
    return notes


def run(args: argparse.Namespace) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed: pip install -r au2026/harvest/requirements.txt && playwright install chromium")
        return 2

    out_dir = Path(args.out).expanduser().resolve()
    notes_dir = Path(args.notes_dir).expanduser().resolve() if args.notes_dir else out_dir / "_notes"
    profile_dir = Path(args.profile).expanduser().resolve()
    manifest_path = out_dir / "manifest.csv"
    rows = read_manifest(manifest_path)
    done_files = {(r.class_id, r.file_name) for r in rows if r.status in ("saved", "skipped")}
    start_url = args.start_url or START_URLS[args.start]

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(profile_dir), headless=False, accept_downloads=True,
            viewport={"width": 1400, "height": 950},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(start_url, wait_until="domcontentloaded")
        wait_for_operator("Sign in to Autodesk if asked (the catalog page is fine to leave open).")

        if args.from_catalog:
            sessions = select_sessions(
                load_catalog(Path(args.from_catalog)),
                codes=parse_code_list(args.codes) if args.codes else None,
                dates=set(args.dates.split(",")) if args.dates else None,
            )
            classes = [(s.url, s.title) for s in sessions]
            log(f"catalog mode: {len(classes)} sessions selected from {args.from_catalog}")
        else:
            wait_for_operator("Make sure the CLASS LIST is showing in the browser.")
            scroll_to_load_all(page)
            classes = collect_class_links(page)
            log(f"found {len(classes)} class links")
        if not classes:
            log("No sessions to visit. Use --from-catalog au2026/data/au2026_catalog.json, or open a class in the browser, copy its URL, and pass --start-url.")
            ctx.close()
            return 1
        if args.max:
            classes = classes[: args.max]

        for i, (href, _text) in enumerate(classes, 1):
            time.sleep(POLITE_DELAY_S)
            try:
                meta = read_class_page(page, href)
            except Exception as exc:  # noqa: BLE001
                log(f"[{i}/{len(classes)}] failed to read {href}: {exc}")
                continue
            log(f"[{i}/{len(classes)}] {meta.title} — {len(meta.materials)} links, {len(meta.embeds)} streams")
            class_dir = out_dir / slugify(meta.title)
            for row in meta.materials:
                if args.skip_video and row.kind == "video":
                    row.status = "skipped"
                    continue
                if (row.class_id, row.file_name) in done_files and row.file_name:
                    row.status = "skipped"
                    continue
                download_material(page, row, class_dir)
                rows.append(row)
            if meta.embeds and not args.skip_video:
                for e in meta.embeds:
                    rows.append(MaterialRow(meta.class_id, meta.title, e, "video", status="stream"))
                if args.ytdlp:
                    fetch_streams_with_ytdlp(meta.embeds, class_dir, profile_dir)
            write_class_meta(meta, class_dir / "meta.json")
            write_class_note(meta, str(class_dir), notes_dir / f"au2026-{slugify(meta.title)}.md")
            write_manifest(rows, manifest_path)  # checkpoint after every class

        ctx.close()

    saved = sum(1 for r in rows if r.status == "saved")
    failed = sum(1 for r in rows if r.status == "failed")
    streams = sum(1 for r in rows if r.status == "stream")
    log(f"done: {saved} files saved, {failed} failed, {streams} streams recorded -> {manifest_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, help="Folder to save into (a SharePoint-synced folder works well)")
    p.add_argument("--start", choices=sorted(START_URLS), default="library", help="Which AU page to start from")
    p.add_argument("--start-url", help="Override the start page entirely")
    p.add_argument("--profile", default=str(Path.home() / ".au_harvest_profile"), help="Persistent browser profile dir")
    p.add_argument("--notes-dir", help="Where to write per-class markdown notes (default <out>/_notes; point at the org-brain inbox to file them)")
    p.add_argument("--from-catalog", help="Session catalog JSON (tools/au_harvest/data/au2026_catalog.json): visit every session URL directly instead of scraping the list page")
    p.add_argument("--codes", help="Only these session codes, comma/space separated (with --from-catalog)")
    p.add_argument("--dates", help="Only these dates, e.g. 2026-09-15,2026-09-16 (with --from-catalog)")
    p.add_argument("--max", type=int, default=0, help="Stop after N classes (smoke test)")
    p.add_argument("--skip-video", action="store_true", help="Decks and handouts only")
    p.add_argument("--ytdlp", action="store_true", help="Also pull streaming embeds with yt-dlp")
    return p


if __name__ == "__main__":
    sys.exit(run(build_parser().parse_args()))
