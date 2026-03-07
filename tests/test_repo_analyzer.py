from __future__ import annotations

from pathlib import Path

import pytest

from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput, analyze_repository, run


def test_repo_analyzer_inspects_local_repo(sample_repo: Path) -> None:
    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo))
    assert analysis.total_files >= 3
    assert analysis.has_git_dir is True
    assert "Python" in analysis.language_breakdown
    assert any(item.path.endswith("src/main.py") for item in analysis.largest_files)


def test_repo_analyzer_no_silent_overwrite(sample_repo: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "generated"
    run(
        RepoAnalyzerInput(repo_path=sample_repo),
        output_dir=output_dir,
        output_name="report",
        overwrite=False,
    )
    with pytest.raises(FileExistsError):
        run(
            RepoAnalyzerInput(repo_path=sample_repo),
            output_dir=output_dir,
            output_name="report",
            overwrite=False,
        )


def test_repo_analyzer_excludes_hidden_files_by_default(sample_repo: Path) -> None:
    hidden_file = sample_repo / ".env"
    hidden_file.write_text("KEY=value\n", encoding="utf-8")
    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo, include_hidden=False))
    assert not any(stat.path == ".env" for stat in analysis.largest_files)
