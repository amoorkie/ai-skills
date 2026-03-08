from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.architecture_designer import ArchitectureDesignerInput
from ai_skills_toolkit.skills.architecture_designer import run as run_architecture_designer
from ai_skills_toolkit.skills.code_reviewer import CodeReviewerInput
from ai_skills_toolkit.skills.code_reviewer import run as run_code_reviewer
from ai_skills_toolkit.skills.deploy_helper import DeployHelperInput
from ai_skills_toolkit.skills.deploy_helper import run as run_deploy_helper
from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput
from ai_skills_toolkit.skills.repo_analyzer import run as run_repo_analyzer


def _assert_common_metadata(metadata: dict[str, object]) -> None:
    assert metadata["artifact_type"]
    assert metadata["subject"]
    assert metadata["subject_type"]
    assert metadata["output_format"] == "markdown"
    assert "warning_count" in metadata


def test_repository_skills_expose_stable_metadata(sample_repo: Path, tmp_path: Path) -> None:
    repo_result = run_repo_analyzer(
        RepoAnalyzerInput(repo_path=sample_repo),
        output_dir=tmp_path / "generated",
        output_name="repo-metadata",
    )
    review_result = run_code_reviewer(
        CodeReviewerInput(repo_path=sample_repo),
        output_dir=tmp_path / "generated",
        output_name="review-metadata",
    )
    deploy_result = run_deploy_helper(
        DeployHelperInput(repo_path=sample_repo),
        output_dir=tmp_path / "generated",
        output_name="deploy-metadata",
    )

    for result in (repo_result, review_result, deploy_result):
        _assert_common_metadata(result.metadata)
        assert result.metadata["subject_type"] == "repository"


def test_product_skills_expose_stable_metadata(tmp_path: Path) -> None:
    result = run_architecture_designer(
        ArchitectureDesignerInput(
            product_name="Ops Console",
            product_goal="Help operations teams monitor incidents and coordinate remediation safely.",
        ),
        output_dir=tmp_path / "generated",
        output_name="arch-metadata",
    )

    _assert_common_metadata(result.metadata)
    assert result.metadata["subject_type"] == "product"
    assert result.metadata["artifact_type"] == "architecture_spec"
