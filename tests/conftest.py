from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample_repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (repo / "README.md").write_text("# sample\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    (repo / "package.json").write_text('{"name":"sample"}\n', encoding="utf-8")
    return repo

