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
    assert result.metadata["artifact_type"] == "prompt_debug_report"
    assert result.metadata["subject_type"] == "prompt"
    assert result.metadata["output_format"] == "markdown"


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


def test_prompt_debugger_recognizes_russian_format_and_guardrails() -> None:
    output = debug_prompt(
        PromptDebuggerInput(
            prompt=(
                "\u0421\u043e\u0441\u0442\u0430\u0432\u044c \u043f\u043b\u0430\u043d \u0434\u0435\u043f\u043b\u043e\u044f \u0434\u043b\u044f staging \u0438 production. "
                "\u0424\u043e\u0440\u043c\u0430\u0442 \u043e\u0442\u0432\u0435\u0442\u0430: markdown \u0441 \u0440\u0430\u0437\u0434\u0435\u043b\u0430\u043c\u0438 \u00ab\u041f\u0440\u0435\u0434\u043f\u043e\u0441\u044b\u043b\u043a\u0438\u00bb, \u00ab\u0428\u0430\u0433\u0438\u00bb, \u00ab\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0438\u00bb, \u00ab\u041e\u0442\u043a\u0430\u0442\u00bb. "
                "\u041d\u0435 \u0432\u044b\u0434\u0443\u043c\u044b\u0432\u0430\u0439 \u0434\u0435\u0442\u0430\u043b\u0438 \u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\u044f, \u0443\u043a\u0430\u0436\u0438 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f \u044f\u0432\u043d\u043e \u0438 \u0434\u043e\u043b\u0436\u0435\u043d \u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0448\u0430\u0433\u0438 \u0432\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u0438 \u043f\u043e\u0441\u043b\u0435 \u0440\u0435\u043b\u0438\u0437\u0430."
            )
        )
    )

    titles = {issue.title for issue in output.diagnosis}
    assert "No explicit output format" not in titles
    assert "Weak guardrails" not in titles


def test_prompt_debugger_localizes_and_specializes_variants_for_russian_deployment_prompt() -> None:
    output = debug_prompt(
        PromptDebuggerInput(
            prompt=(
                "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u044c \u043f\u043b\u0430\u043d \u0434\u0435\u043f\u043b\u043e\u044f \u0441 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430\u043c\u0438 \u0438 \u043e\u0442\u043a\u0430\u0442\u043e\u043c. "
                "\u0424\u043e\u0440\u043c\u0430\u0442 \u043e\u0442\u0432\u0435\u0442\u0430: markdown."
            )
        )
    )

    strict = output.improved_variants[0].prompt
    assert "\u0417\u0430\u0434\u0430\u0447\u0430:" in strict
    assert "\u0424\u043e\u0440\u043c\u0430\u0442 \u043e\u0442\u0432\u0435\u0442\u0430:" in strict
    assert "\u043e\u0442\u043a\u0430\u0442" in strict.lower()


def test_prompt_debugger_specializes_variants_for_design_prompts() -> None:
    output = debug_prompt(
        PromptDebuggerInput(
            prompt="Design a Figma handoff spec for a dashboard with edge cases, states, and user flows."
        )
    )

    strict = output.improved_variants[0].prompt.lower()
    assert "user flows" in strict
    assert "states" in strict
