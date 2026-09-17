"""Pure link-classification helpers for the AU harvester. No I/O, no browser."""

from __future__ import annotations

import re
from urllib.parse import urlparse, unquote

# Which file extensions we treat as which kind of material.
_EXT_KIND: dict[str, str] = {
    ".pptx": "presentation",
    ".ppt": "presentation",
    ".key": "presentation",
    ".pdf": "document",
    ".docx": "document",
    ".doc": "document",
    ".xlsx": "dataset",
    ".xls": "dataset",
    ".csv": "dataset",
    ".zip": "dataset",
    ".7z": "dataset",
    ".dwg": "dataset",
    ".rvt": "dataset",
    ".mp4": "video",
    ".mov": "video",
    ".m4v": "video",
    ".webm": "video",
    ".m3u8": "video",
    ".mpd": "video",
}

_TEXT_KIND: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(presentation|slides?|deck|powerpoint)\b", re.I), "presentation"),
    (re.compile(r"\b(handout|class handout|notes)\b", re.I), "document"),
    (re.compile(r"\b(video|recording|watch|replay|on[- ]demand)\b", re.I), "video"),
    (re.compile(r"\b(dataset|sample files?|exercise files?|download files?)\b", re.I), "dataset"),
    (re.compile(r"\bdownload\b", re.I), "document"),
]

# Session / class detail URLs on the two Autodesk hosts we know about.
_CLASS_URL = re.compile(
    r"(/session/[A-Za-z0-9]{6,}|/class/[a-z0-9][a-z0-9\-]+|sessionDetail)",
    re.I,
)

# Streaming embeds worth handing to yt-dlp later.
_EMBED_HOSTS = (
    "players.brightcove.net",
    "player.vimeo.com",
    "vimeo.com",
    "fast.wistia.net",
    "youtube.com",
    "youtu.be",
    "video.autodesk.com",
    "cloudfront.net",
)

_SRC_ATTR = re.compile(r"""<(?:iframe|video|source)[^>]+src=["']([^"']+)["']""", re.I)


def file_extension(href: str) -> str:
    """Lower-cased extension of the URL path (query string ignored), or ''."""
    path = unquote(urlparse(href).path)
    match = re.search(r"(\.[a-z0-9]{2,5})$", path, re.I)
    return match.group(1).lower() if match else ""


def classify_link(href: str, text: str = "") -> str | None:
    """Return the material kind for an anchor, or None if it is not a download.

    Extension wins over link text. Link text alone is enough for buttons such as
    "Download presentation" whose href is an opaque signed URL.
    """
    ext = file_extension(href)
    if ext in _EXT_KIND:
        return _EXT_KIND[ext]
    for pattern, kind in _TEXT_KIND:
        if pattern.search(text or ""):
            return kind
    return None


def is_class_url(href: str) -> bool:
    """True when the URL looks like a session/class detail page, not a nav link."""
    if not href or href.startswith(("mailto:", "javascript:", "#")):
        return False
    return bool(_CLASS_URL.search(href))


def extract_embed_urls(html: str) -> list[str]:
    """Streaming player URLs (iframe/video/source src) found in a page's HTML."""
    found: list[str] = []
    for src in _SRC_ATTR.findall(html or ""):
        if any(host in src for host in _EMBED_HOSTS) or file_extension(src) in (".m3u8", ".mpd", ".mp4"):
            if src not in found:
                found.append(src)
    return found


def slugify(text: str, max_len: int = 80) -> str:
    """Lower-case, non-alphanumerics collapsed to hyphens, trimmed to max_len."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:max_len].rstrip("-") or "untitled"


def safe_filename(name: str, fallback: str = "file") -> str:
    """Strip path separators and characters Windows rejects; keep the extension."""
    name = unquote(name or "").split("?")[0].split("/")[-1].split("\\")[-1]
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name).strip(" .")
    return name or fallback
