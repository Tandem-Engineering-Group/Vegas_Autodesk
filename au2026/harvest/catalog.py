"""Load the AU session catalog and select which sessions the harvester visits. No I/O beyond one JSON read."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Catalog "type" values that are logistics, not learning content.
LOGISTICS_TYPES: frozenset[str] = frozenset(
    {"Activity", "Meal", "Reception", "Watch Party", "Certification", "Braindate", "Lunch and Learn"}
)


@dataclass(frozen=True)
class CatalogSession:
    code: str
    title: str
    url: str
    type: str
    date: str


def load_catalog(path: Path) -> list[CatalogSession]:
    """Read the compact catalog JSON (list of session dicts) into CatalogSession rows."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: list[CatalogSession] = []
    for s in data:
        times = s.get("times") or []
        date = times[0].get("date", "") if times else ""
        out.append(CatalogSession(s.get("code", ""), s.get("title", ""), s.get("url", ""), s.get("type", ""), date))
    return out


def select_sessions(
    sessions: list[CatalogSession],
    codes: set[str] | None = None,
    dates: set[str] | None = None,
    include_logistics: bool = False,
) -> list[CatalogSession]:
    """Filter by explicit codes and/or dates; drop logistics rows unless asked. Order preserved."""
    wanted = []
    for s in sessions:
        if not s.url:
            continue
        if not include_logistics and s.type in LOGISTICS_TYPES:
            continue
        if codes and s.code not in codes:
            continue
        if dates and s.date not in dates:
            continue
        wanted.append(s)
    return wanted


def parse_code_list(text: str) -> set[str]:
    """'AS2183, cs1316 bes4067' -> {'AS2183','CS1316','BES4067'}."""
    return {c.strip().upper() for c in text.replace(",", " ").split() if c.strip()}
