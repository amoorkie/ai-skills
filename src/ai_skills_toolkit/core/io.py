"""Filesystem helpers for skill outputs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import unicodedata


def slugify(value: str) -> str:
    """Convert arbitrary text into a filesystem-safe ASCII slug."""
    original = value.strip()
    if not original:
        return "output"

    normalized = unicodedata.normalize("NFKD", original).encode("ascii", "ignore").decode("ascii").lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")

    contains_non_ascii = any(ord(char) > 127 for char in original)
    if normalized and not contains_non_ascii:
        return normalized

    digest = hashlib.sha1(original.encode("utf-8")).hexdigest()[:8]
    stem = normalized or "output"
    return f"{stem}-{digest}"


def utc_timestamp() -> str:
    """Return current UTC timestamp suitable for output file names."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def ensure_output_dir(output_dir: Path) -> Path:
    """Create output directory if it does not exist and return it."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_output_path(
    output_dir: Path,
    skill_name: str,
    file_stem: str,
    extension: str = "md",
) -> Path:
    """Build normalized output path under generated/<skill_name>/<file_stem>.<ext>."""
    root = ensure_output_dir(output_dir)
    skill_dir = ensure_output_dir(root / skill_name)
    safe_stem = slugify(file_stem)
    safe_extension = extension.lstrip(".")
    return skill_dir / f"{safe_stem}.{safe_extension}"


def safe_write_text(path: Path, content: str, *, overwrite: bool = False) -> Path:
    """Write text to disk and block silent overwrite unless explicitly enabled."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")
    return path
