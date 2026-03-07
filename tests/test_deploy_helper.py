from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.deploy_helper import DeployHelperInput, generate_deploy_plan, run


def test_deploy_helper_auto_detects_platform(sample_repo: Path) -> None:
    (sample_repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    plan = generate_deploy_plan(DeployHelperInput(repo_path=sample_repo, platform="auto"))
    assert plan.platform == "docker"
    assert any("Dockerfile" in item for item in plan.detected_files)


def test_deploy_helper_writes_output(sample_repo: Path, tmp_path: Path) -> None:
    output = run(
        DeployHelperInput(repo_path=sample_repo, platform="generic", app_name="sample-app"),
        output_dir=tmp_path / "generated",
        output_name="deploy-plan",
    )
    text = output.output_path.read_text(encoding="utf-8")
    assert "# Deployment Helper Plan" in text
    assert "## Suggested Commands" in text

