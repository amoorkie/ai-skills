"""Shared validation helpers for pydantic input models."""

from __future__ import annotations

from pathlib import Path


def validate_repo_dir(value: Path) -> Path:
    """Resolve and validate that a path points to an existing directory."""
    resolved = value.resolve()
    if not resolved.exists():
        raise ValueError(f"Path does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"Path is not a directory: {resolved}")
    return resolved
