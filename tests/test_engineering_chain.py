from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.engineering_chain import EngineeringChainInput, run_engineering_chain


def test_engineering_chain_writes_linked_artifacts(sample_repo: Path, tmp_path: Path) -> None:
    result = run_engineering_chain(
        EngineeringChainInput(
            repo_path=sample_repo,
            test_focus_paths=["src/main.py"],
        ),
        output_dir=tmp_path / "generated",
        output_name="engineering-chain",
        overwrite=True,
    )

    summary_text = result.output_path.read_text(encoding="utf-8")
    repo_artifact = Path(result.metadata["repo_artifact"])
    review_artifact = Path(result.metadata["review_artifact"])
    test_artifact = Path(result.metadata["test_artifact"])
    doc_artifact = Path(result.metadata["doc_artifact"])

    assert result.metadata["artifact_type"] == "engineering_chain_report"
    assert repo_artifact.exists()
    assert review_artifact.exists()
    assert test_artifact.exists()
    assert doc_artifact.exists()
    assert "# Engineering Chain Report" in summary_text
    assert "`code_reviewer` identified prioritized implementation risks" in summary_text
