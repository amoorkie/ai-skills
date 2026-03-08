from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.design_chain import DesignChainInput, run_design_chain


def test_design_chain_writes_linked_artifacts(sample_repo: Path, tmp_path: Path) -> None:
    result = run_design_chain(
        DesignChainInput(
            repo_path=sample_repo,
            product_name="Ops Console",
            product_goal="Help operators review workflows and integrations safely.",
            users=["Operator"],
            jtbds=["When reviewing queue health, I want actionable status so I can resolve issues quickly."],
            constraints=["Desktop-first", "WCAG 2.1 AA"],
        ),
        output_dir=tmp_path / "generated",
        output_name="design-chain",
        overwrite=True,
    )

    summary_text = result.output_path.read_text(encoding="utf-8")
    repo_artifact = Path(result.metadata["repo_artifact"])
    architecture_artifact = Path(result.metadata["architecture_artifact"])
    figma_artifact = Path(result.metadata["figma_artifact"])

    assert result.metadata["artifact_type"] == "design_chain_report"
    assert repo_artifact.exists()
    assert architecture_artifact.exists()
    assert figma_artifact.exists()
    assert "# Design Chain Report" in summary_text
    assert "`repo_analyzer` established runtime, service, and hotspot context." in summary_text
