from __future__ import annotations

import re
from pathlib import Path


INVALID_FILENAME_CHARS = r'<>:"/\|?*'


def safe_filename(value: str, fallback: str = "youtube-video") -> str:
    cleaned = "".join("_" if char in INVALID_FILENAME_CHARS else char for char in value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.strip(".")
    return cleaned[:140] or fallback


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

