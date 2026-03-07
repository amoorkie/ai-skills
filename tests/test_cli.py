from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.cli import main


def test_cli_repo_analyzer_smoke(sample_repo: Path, tmp_path: Path) -> None:
    rc = main(
        [
            "repo-analyzer",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "repo-smoke",
        ]
    )
    assert rc == 0


def test_cli_prompt_debugger_smoke(tmp_path: Path) -> None:
    rc = main(
        [
            "prompt-debugger",
            "--prompt",
            "Design an API for incident tracking.",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "prompt-smoke",
        ]
    )
    assert rc == 0


def test_cli_repo_analyzer_overwrite_error(sample_repo: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "generated"
    first = main(
        [
            "repo-analyzer",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(output_dir),
            "--output-name",
            "same-name",
        ]
    )
    second = main(
        [
            "repo-analyzer",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(output_dir),
            "--output-name",
            "same-name",
        ]
    )
    assert first == 0
    assert second == 2


def test_cli_validation_error_returns_non_zero(tmp_path: Path) -> None:
    rc = main(
        [
            "prompt-debugger",
            "--prompt",
            "short",
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "invalid-prompt",
        ]
    )
    assert rc == 1


def test_cli_test_generator_smoke(sample_repo: Path, tmp_path: Path) -> None:
    rc = main(
        [
            "test-generator",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "test-plan",
        ]
    )
    assert rc == 0


def test_cli_code_reviewer_smoke(sample_repo: Path, tmp_path: Path) -> None:
    rc = main(
        [
            "code-reviewer",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "review",
        ]
    )
    assert rc == 0


def test_cli_deploy_helper_smoke(sample_repo: Path, tmp_path: Path) -> None:
    rc = main(
        [
            "deploy-helper",
            "--repo-path",
            str(sample_repo),
            "--output-dir",
            str(tmp_path / "generated"),
            "--output-name",
            "deploy",
        ]
    )
    assert rc == 0
