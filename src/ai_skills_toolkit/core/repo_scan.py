"""Shared repository traversal helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    "dist",
    "build",
}


def is_hidden_relative(path: Path) -> bool:
    """Return whether a relative path contains hidden segments."""
    return any(part.startswith(".") for part in path.parts)


def iter_repo_files(
    repo_path: Path,
    *,
    scan_root: Path | None = None,
    include_hidden: bool = False,
    excluded_dirs: set[str] | None = None,
    file_filter: Callable[[Path], bool] | None = None,
) -> tuple[list[Path], int]:
    """Walk a repository with shared exclusion and hidden-file handling."""
    root_path = repo_path.resolve()
    walk_root = (scan_root or root_path).resolve()
    excluded = set(DEFAULT_EXCLUDED_DIRS if excluded_dirs is None else excluded_dirs)

    file_paths: list[Path] = []
    total_dirs = 0

    for root, dirs, files in os.walk(walk_root):
        current = Path(root)
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in excluded and (include_hidden or not directory.startswith("."))
        ]
        total_dirs += len(dirs)

        for filename in files:
            if filename in {".DS_Store"}:
                continue
            file_path = current / filename
            rel_path = file_path.relative_to(root_path)
            if not include_hidden and is_hidden_relative(rel_path):
                continue
            if file_filter is not None and not file_filter(file_path):
                continue
            file_paths.append(file_path)

    return sorted(file_paths), total_dirs
