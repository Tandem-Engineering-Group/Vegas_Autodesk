"""Manifest CSV and per-class markdown notes for the AU harvester. File I/O only."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

MANIFEST_COLUMNS = ["class_id", "title", "url", "kind", "file_name", "bytes", "status", "note"]


@dataclass
class MaterialRow:
    class_id: str
    title: str
    url: str
    kind: str
    file_name: str = ""
    bytes: int = 0
    status: str = "pending"  # pending | saved | skipped | failed | stream
    note: str = ""


@dataclass
class ClassMeta:
    class_id: str
    title: str
    url: str
    speakers: list[str] = field(default_factory=list)
    description: str = ""
    materials: list[MaterialRow] = field(default_factory=list)
    embeds: list[str] = field(default_factory=list)


def write_manifest(rows: list[MaterialRow], path: Path) -> None:
    """Write (or overwrite) the manifest CSV. One row per material."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def read_manifest(path: Path) -> list[MaterialRow]:
    """Read an existing manifest so a re-run can skip what is already saved."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [
            MaterialRow(**{**r, "bytes": int(r.get("bytes") or 0)})
            for r in csv.DictReader(fh)
        ]


def write_class_meta(meta: ClassMeta, path: Path) -> None:
    """meta.json beside the downloaded files — the machine-readable record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(meta)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def class_note_markdown(meta: ClassMeta, files_dir: str) -> str:
    """Inbox-style note for one class. Plain markdown, no frontmatter required at capture."""
    lines = [f"# AU 2026 — {meta.title}", ""]
    lines.append(f"- Source: {meta.url}")
    if meta.speakers:
        lines.append(f"- Speakers: {', '.join(meta.speakers)}")
    lines.append(f"- Files: `{files_dir}`")
    lines.append("")
    if meta.description:
        lines += ["## Description", "", meta.description.strip(), ""]
    lines += ["## Materials", ""]
    if not meta.materials and not meta.embeds:
        lines.append("_None found on the class page at harvest time._")
    for m in meta.materials:
        size = f" ({m.bytes // 1024} KB)" if m.bytes else ""
        lines.append(f"- [{m.status}] {m.kind}: {m.file_name or m.url}{size}")
    for e in meta.embeds:
        lines.append(f"- [stream] video: {e}")
    lines += ["", "## Takeaways for TEG", "", "_(fill in after review)_", ""]
    return "\n".join(lines)


def write_class_note(meta: ClassMeta, files_dir: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(class_note_markdown(meta, files_dir), encoding="utf-8")
