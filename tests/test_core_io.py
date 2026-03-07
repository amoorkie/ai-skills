from __future__ import annotations

from pathlib import Path

import pytest

from ai_skills_toolkit.core.io import build_output_path, safe_write_text, slugify


def test_slugify_normalizes_to_ascii_slug() -> None:
    assert slugify("  My Report v1  ") == "my-report-v1"
    assert slugify("!!!") == "output"


def test_build_output_path_uses_skill_subfolder(tmp_path: Path) -> None:
    path = build_output_path(tmp_path / "generated", "repo_analyzer", "My Scan", "md")
    assert path.name == "my-scan.md"
    assert path.parent.name == "repo_analyzer"


def test_safe_write_text_blocks_silent_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "generated" / "file.md"
    safe_write_text(path, "first", overwrite=False)
    with pytest.raises(FileExistsError):
        safe_write_text(path, "second", overwrite=False)

