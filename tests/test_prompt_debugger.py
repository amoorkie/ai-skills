from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.prompt_debugger import PromptDebuggerInput, debug_prompt, run


def test_prompt_debugger_produces_diagnosis_and_variants() -> None:
    output = debug_prompt(PromptDebuggerInput(prompt="Write docs."))
    assert len(output.diagnosis) >= 1
    assert len(output.improved_variants) >= 3


def test_prompt_debugger_writes_markdown(tmp_path: Path) -> None:
    result = run(
        PromptDebuggerInput(prompt="Build a reliable deployment checklist for staging and production."),
        output_dir=tmp_path / "generated",
        output_name="prompt-report",
    )
    content = result.output_path.read_text(encoding="utf-8")
    assert "## Diagnosis" in content
    assert "## Improved Prompt Variants" in content


def test_prompt_debugger_can_report_no_critical_issues() -> None:
    output = debug_prompt(
        PromptDebuggerInput(
            prompt=(
                "You must produce a deployment checklist for staging and production. Include output format in markdown, "
                "do not invent environment details, provide rollback steps with clear constraints, and describe validation "
                "gates, owners, and post-release verification steps."
            )
        )
    )
    assert any(issue.title == "No critical issues detected" for issue in output.diagnosis)
