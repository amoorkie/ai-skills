from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.full_suite import FullSuiteInput, run_full_suite


def test_full_suite_writes_release_pack(sample_repo: Path, tmp_path: Path) -> None:
    result = run_full_suite(
        FullSuiteInput(
            repo_path=sample_repo,
            product_name="Ops Console",
            product_goal="Help operators review workflows and integrations safely.",
            jtbds=["When reviewing queue health, I want actionable status so I can resolve issues quickly."],
            test_focus_paths=["src/main.py"],
        ),
        output_dir=tmp_path / "generated",
        output_name="release-pack",
        overwrite=True,
    )

    text = result.output_path.read_text(encoding="utf-8")
    readiness_artifact = Path(result.metadata["readiness_artifact"])
    design_artifact = Path(result.metadata["design_artifact"])
    engineering_artifact = Path(result.metadata["engineering_artifact"])

    assert result.metadata["artifact_type"] == "full_suite_report"
    assert readiness_artifact.exists()
    assert design_artifact.exists()
    assert engineering_artifact.exists()
    assert "# Full Workflow Suite Report" in text
    assert "`benchmark-all`" in text
