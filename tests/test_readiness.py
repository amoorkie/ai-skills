from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.readiness import run_all_evaluations


def test_run_all_evaluations_writes_consolidated_report(tmp_path: Path) -> None:
    result = run_all_evaluations(output_dir=tmp_path / "generated", output_name="readiness")
    text = result.output_path.read_text(encoding="utf-8")

    assert result.metadata["artifact_type"] == "readiness_report"
    assert result.metadata["skill_count"] >= 8
    assert result.metadata["warning_count"] == 0
    assert "# Skills Readiness Report" in text
    assert "## Skill Evaluations" in text
    assert "`code_reviewer_eval`" in text
    assert "`prompt_debugger_eval`" in text
