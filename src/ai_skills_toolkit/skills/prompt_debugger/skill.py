"""Implementation for prompt_debugger."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.prompt_debugger.schema import (
    PromptDebuggerInput,
    PromptDebuggerOutput,
    PromptIssue,
    PromptVariant,
)

OUTPUT_FORMAT_HINTS = (
    "output",
    "format",
    "response format",
    "markdown",
    "json",
    "yaml",
    "\\u0442\\u0430\\u0431\\u043b\\u0438\\u0446\\u0430",
    "\\u0444\\u043e\\u0440\\u043c\\u0430\\u0442",
    "\\u0444\\u043e\\u0440\\u043c\\u0430\\u0442 \\u043e\\u0442\\u0432\\u0435\\u0442\\u0430",
    "\\u0444\\u043e\\u0440\\u043c\\u0430\\u0442 \\u0432\\u044b\\u0432\\u043e\\u0434\\u0430",
    "\\u0432\\u044b\\u0432\\u043e\\u0434",
    "\\u043e\\u0442\\u0432\\u0435\\u0442 \\u0432 \\u0432\\u0438\\u0434\\u0435",
)

GUARDRAIL_HINTS = (
    "must",
    "should",
    "avoid",
    "do not",
    "constraint",
    "required",
    "only",
    "exactly",
    "\\u0434\\u043e\\u043b\\u0436\\u0435\\u043d",
    "\\u0434\\u043e\\u043b\\u0436\\u043d\\u044b",
    "\\u043d\\u0443\\u0436\\u043d\\u043e",
    "\\u043d\\u0435 ",
    "\\u043d\\u0435\\n",
    "\\u043d\\u0435 \\u0434\\u043e\\u043b\\u0436\\u0435\\u043d",
    "\\u043d\\u0435 \\u0434\\u043e\\u043b\\u0436\\u043d\\u044b",
    "\\u0438\\u0437\\u0431\\u0435\\u0433\\u0430\\u0439",
    "\\u043e\\u0433\\u0440\\u0430\\u043d\\u0438\\u0447",
    "\\u0442\\u043e\\u043b\\u044c\\u043a\\u043e",
    "\\u0437\\u0430\\u043f\\u0440\\u0435\\u0449",
)

LANGUAGE_LABELS = {
    "en": {
        "goal": "Goal",
        "context": "Context",
        "model": "Target model",
        "model_unspecified": "unspecified",
        "constraints": "Hard constraints",
        "task": "Task",
        "output_format": "Output format",
        "required_output": "Required output",
        "reason_strict": "Adds explicit constraints and a fixed response schema.",
        "reason_concise": "Optimized for shorter deterministic responses.",
        "reason_eval": "Adds a lightweight quality gate before final response.",
        "strict_intro": "You are a senior execution agent.",
        "concise_intro": "Execute the task below with minimal prose and maximum correctness.",
        "eval_intro": "Act as both implementer and reviewer.",
        "summary": "Summary (3 lines max)",
        "deliverable": "Final deliverable",
        "limitations": "Known limitations",
        "assumptions": "Assumptions",
        "plan": "Plan",
        "result": "Result",
        "risks": "Risks/Limitations",
        "score_intro": "Before finalizing, score your output (1-5) on:",
        "score_fix": "If any score < 4, revise once before returning final output.",
        "do_not_invent": "Do not invent missing facts.",
        "state_assumptions": "State assumptions explicitly.",
        "actionable": "Return actionable output.",
        "task_requirements": {
            "deployment": "Include rollout steps, validation checks, rollback criteria, and required owners.",
            "documentation": "Structure the answer into clear sections, audience notes, assumptions, and follow-up docs.",
            "design": "Include user flows, screen states, edge cases, and explicit handoff notes.",
            "implementation": "Name the files or modules to change, the test strategy, and the main regression risks.",
            "general": "State acceptance criteria, assumptions, and how success will be verified.",
        },
    },
    "ru": {
        "goal": "\u0426\u0435\u043b\u044c",
        "context": "\u041a\u043e\u043d\u0442\u0435\u043a\u0441\u0442",
        "model": "\u0426\u0435\u043b\u0435\u0432\u0430\u044f \u043c\u043e\u0434\u0435\u043b\u044c",
        "model_unspecified": "\u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430",
        "constraints": "\u0416\u0435\u0441\u0442\u043a\u0438\u0435 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f",
        "task": "\u0417\u0430\u0434\u0430\u0447\u0430",
        "output_format": "\u0424\u043e\u0440\u043c\u0430\u0442 \u043e\u0442\u0432\u0435\u0442\u0430",
        "required_output": "\u041e\u0436\u0438\u0434\u0430\u0435\u043c\u044b\u0439 \u0432\u044b\u0432\u043e\u0434",
        "reason_strict": "\u0414\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u044f\u0432\u043d\u044b\u0435 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f \u0438 \u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u0443\u044e \u0441\u0445\u0435\u043c\u0443 \u043e\u0442\u0432\u0435\u0442\u0430.",
        "reason_concise": "\u041e\u043f\u0442\u0438\u043c\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u043d \u043f\u043e\u0434 \u043a\u043e\u0440\u043e\u0442\u043a\u0438\u0439 \u0438 \u0434\u0435\u0442\u0435\u0440\u043c\u0438\u043d\u0438\u0441\u0442\u0438\u0447\u043d\u044b\u0439 \u043e\u0442\u0432\u0435\u0442.",
        "reason_eval": "\u0414\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u043b\u0435\u0433\u043a\u0438\u0439 \u044d\u0442\u0430\u043f \u0441\u0430\u043c\u043e\u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u043f\u0435\u0440\u0435\u0434 \u0444\u0438\u043d\u0430\u043b\u044c\u043d\u044b\u043c \u043e\u0442\u0432\u0435\u0442\u043e\u043c.",
        "strict_intro": "\u0422\u044b \u0441\u0442\u0430\u0440\u0448\u0438\u0439 \u0430\u0433\u0435\u043d\u0442 \u0438\u0441\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f.",
        "concise_intro": "\u0412\u044b\u043f\u043e\u043b\u043d\u0438 \u0437\u0430\u0434\u0430\u0447\u0443 \u043d\u0438\u0436\u0435 \u043c\u0438\u043d\u0438\u043c\u0443\u043c\u043e\u043c \u0432\u043e\u0434\u044b \u0438 \u043c\u0430\u043a\u0441\u0438\u043c\u0443\u043c\u043e\u043c \u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u043e\u0441\u0442\u0438.",
        "eval_intro": "\u0412\u044b\u0441\u0442\u0443\u043f\u0438 \u0438 \u043a\u0430\u043a \u0438\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c, \u0438 \u043a\u0430\u043a \u0440\u0435\u0432\u044c\u044e\u0435\u0440.",
        "summary": "\u0420\u0435\u0437\u044e\u043c\u0435 (\u043d\u0435 \u0431\u043e\u043b\u0435\u0435 3 \u0441\u0442\u0440\u043e\u043a)",
        "deliverable": "\u0424\u0438\u043d\u0430\u043b\u044c\u043d\u044b\u0439 \u0430\u0440\u0442\u0435\u0444\u0430\u043a\u0442",
        "limitations": "\u0418\u0437\u0432\u0435\u0441\u0442\u043d\u044b\u0435 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f",
        "assumptions": "\u0414\u043e\u043f\u0443\u0449\u0435\u043d\u0438\u044f",
        "plan": "\u041f\u043b\u0430\u043d",
        "result": "\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442",
        "risks": "\u0420\u0438\u0441\u043a\u0438/\u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f",
        "score_intro": "\u041f\u0435\u0440\u0435\u0434 \u0444\u0438\u043d\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u0435\u0439 \u043e\u0446\u0435\u043d\u0438 \u043e\u0442\u0432\u0435\u0442 \u043f\u043e \u0448\u043a\u0430\u043b\u0435 1-5 \u043f\u043e:",
        "score_fix": "\u0415\u0441\u043b\u0438 \u0445\u043e\u0442\u044f \u0431\u044b \u043e\u0434\u043d\u0430 \u043e\u0446\u0435\u043d\u043a\u0430 < 4, \u043f\u0435\u0440\u0435\u0441\u043e\u0431\u0435\u0440\u0438 \u043e\u0442\u0432\u0435\u0442 \u043e\u0434\u0438\u043d \u0440\u0430\u0437 \u043f\u0435\u0440\u0435\u0434 \u0432\u044b\u0432\u043e\u0434\u043e\u043c.",
        "do_not_invent": "\u041d\u0435 \u0432\u044b\u0434\u0443\u043c\u044b\u0432\u0430\u0439 \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0435 \u0444\u0430\u043a\u0442\u044b.",
        "state_assumptions": "\u042f\u0432\u043d\u043e \u043e\u0442\u043c\u0435\u0447\u0430\u0439 \u0434\u043e\u043f\u0443\u0449\u0435\u043d\u0438\u044f.",
        "actionable": "\u0412\u0435\u0440\u043d\u0438 \u043f\u0440\u0438\u043c\u0435\u043d\u0438\u043c\u044b\u0439 \u043a \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044e \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442.",
        "task_requirements": {
            "deployment": "\u0412\u043a\u043b\u044e\u0447\u0438 \u0448\u0430\u0433\u0438 \u0432\u044b\u043a\u0430\u0442\u0430, \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438, \u043a\u0440\u0438\u0442\u0435\u0440\u0438\u0438 \u043e\u0442\u043a\u0430\u0442\u0430 \u0438 \u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0445.",
            "documentation": "\u0421\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0438\u0440\u0443\u0439 \u043e\u0442\u0432\u0435\u0442 \u043f\u043e \u0440\u0430\u0437\u0434\u0435\u043b\u0430\u043c, \u0430\u0443\u0434\u0438\u0442\u043e\u0440\u0438\u0438, \u0434\u043e\u043f\u0443\u0449\u0435\u043d\u0438\u044f\u043c \u0438 \u0441\u0432\u044f\u0437\u0430\u043d\u043d\u044b\u043c \u0434\u043e\u043a\u0430\u043c.",
            "design": "\u041e\u043f\u0438\u0448\u0438 user flows, \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f \u044d\u043a\u0440\u0430\u043d\u043e\u0432, edge cases \u0438 handoff notes.",
            "implementation": "\u0423\u043a\u0430\u0436\u0438 \u0444\u0430\u0439\u043b\u044b/\u043c\u043e\u0434\u0443\u043b\u0438 \u0434\u043b\u044f \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f, \u0442\u0435\u0441\u0442-\u0441\u0442\u0440\u0430\u0442\u0435\u0433\u0438\u044e \u0438 \u043e\u0441\u043d\u043e\u0432\u043d\u044b\u0435 \u0440\u0438\u0441\u043a\u0438 \u0440\u0435\u0433\u0440\u0435\u0441\u0441\u0438\u0438.",
            "general": "\u042f\u0432\u043d\u043e \u0437\u0430\u0444\u0438\u043a\u0441\u0438\u0440\u0443\u0439 acceptance criteria, \u0434\u043e\u043f\u0443\u0449\u0435\u043d\u0438\u044f \u0438 \u0441\u043f\u043e\u0441\u043e\u0431 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u0443\u0441\u043f\u0435\u0445\u0430.",
        },
    },
}


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(_decode_escaped_text(hint) in text for hint in hints)


def _decode_escaped_text(value: str) -> str:
    return value.encode("utf-8").decode("unicode_escape") if "\\u" in value else value


def _decode_localized_map(value: object) -> object:
    if isinstance(value, str):
        return _decode_escaped_text(value)
    if isinstance(value, dict):
        return {key: _decode_localized_map(item) for key, item in value.items()}
    return value


def _detect_language(prompt: str) -> str:
    return "ru" if any("\u0400" <= char <= "\u04FF" for char in prompt) else "en"


def _detect_task_type(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if any(
        token in prompt_lower
        for token in (
            "deploy",
            "rollout",
            "rollback",
            "release",
            "\u0434\u0435\u043f\u043b\u043e\u0439",
            "\u0440\u0435\u043b\u0438\u0437",
            "\u043e\u0442\u043a\u0430\u0442",
        )
    ):
        return "deployment"
    if any(
        token in prompt_lower
        for token in (
            "design",
            "figma",
            "ux",
            "ui",
            "screen",
            "\u0434\u0438\u0437\u0430\u0439\u043d",
            "\u044d\u043a\u0440\u0430\u043d",
            "flow",
        )
    ):
        return "design"
    if any(
        token in prompt_lower
        for token in (
            "doc",
            "readme",
            "runbook",
            "guide",
            "\u0434\u043e\u043a",
            "\u0438\u043d\u0441\u0442\u0440\u0443\u043a",
            "\u0440\u0430\u043d\u0431\u0443\u043a",
        )
    ):
        return "documentation"
    if any(
        token in prompt_lower
        for token in (
            "implement",
            "code",
            "refactor",
            "test",
            "fix",
            "\u043a\u043e\u0434",
            "\u0440\u0435\u0444\u0430\u043a\u0442",
            "\u0442\u0435\u0441\u0442",
            "\u0438\u0441\u043f\u0440\u0430\u0432",
        )
    ):
        return "implementation"
    return "general"


def _build_diagnosis(data: PromptDebuggerInput) -> list[PromptIssue]:
    prompt = data.prompt.strip()
    words = prompt.split()
    prompt_lower = prompt.lower()
    issues: list[PromptIssue] = []

    if len(words) < 25:
        issues.append(
            PromptIssue(
                severity="high",
                title="Prompt is underspecified",
                rationale="The request is short and likely missing constraints, acceptance criteria, or context.",
            )
        )
    if not _contains_any(prompt_lower, OUTPUT_FORMAT_HINTS):
        issues.append(
            PromptIssue(
                severity="high",
                title="No explicit output format",
                rationale="Without a format contract, responses may be inconsistent and harder to verify automatically.",
            )
        )
    if not _contains_any(prompt_lower, GUARDRAIL_HINTS):
        issues.append(
            PromptIssue(
                severity="medium",
                title="Weak guardrails",
                rationale="The prompt lacks explicit constraints and negative requirements.",
            )
        )
    if len(prompt) > 500 and "\n" not in prompt:
        issues.append(
            PromptIssue(
                severity="low",
                title="Low readability",
                rationale="Long single-block prompts are harder for humans and models to maintain.",
            )
        )
    if not issues:
        issues.append(
            PromptIssue(
                severity="low",
                title="No critical issues detected",
                rationale="The prompt already includes core intent; refinements are optional.",
            )
        )
    return issues


def _build_variants(data: PromptDebuggerInput) -> list[PromptVariant]:
    language = _detect_language(data.prompt)
    task_type = _detect_task_type(data.prompt)
    labels = _decode_localized_map(LANGUAGE_LABELS[language])

    goal = data.goal or (
        "Deliver a complete and correct result."
        if language == "en"
        else "\u0414\u0430\u0439 \u043f\u043e\u043b\u043d\u044b\u0439 \u0438 \u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0439 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442."
    )
    context = data.context or (
        "No additional context provided."
        if language == "en"
        else "\u0414\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442 \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d."
    )
    model_line = (
        f"{labels['model']}: {data.target_model}"
        if data.target_model
        else f"{labels['model']}: {labels['model_unspecified']}"
    )
    task_requirement = labels["task_requirements"][task_type]

    base_sections = (
        f"{labels['goal']}:\n{goal}\n\n"
        f"{labels['context']}:\n{context}\n\n"
        f"{model_line}\n\n"
        f"{labels['constraints']}:\n"
        f"- {labels['do_not_invent']}\n"
        f"- {labels['state_assumptions']}\n"
        f"- {labels['actionable']}\n"
        f"- {task_requirement}\n"
    )

    strict = (
        f"{labels['strict_intro']}\n"
        f"{base_sections}\n"
        f"{labels['task']}:\n"
        f"{data.prompt.strip()}\n\n"
        f"{labels['output_format']}:\n"
        f"1. {labels['assumptions']}\n"
        f"2. {labels['plan']}\n"
        f"3. {labels['result']}\n"
        f"4. {labels['risks']}\n"
    )
    concise = (
        f"{labels['concise_intro']}\n\n"
        f"{labels['task']}:\n{data.prompt.strip()}\n\n"
        f"{labels['required_output']}:\n"
        f"- {labels['summary']}\n"
        f"- {labels['deliverable']}\n"
        f"- {labels['limitations']}\n"
    )
    evaluative = (
        f"{labels['eval_intro']}\n"
        f"{base_sections}\n"
        f"{labels['task']}:\n{data.prompt.strip()}\n\n"
        f"{labels['score_intro']}\n"
        "- Correctness\n"
        "- Completeness\n"
        "- Clarity\n"
        f"{labels['score_fix']}\n"
    )

    return [
        PromptVariant(name="Structured Strict", why=labels["reason_strict"], prompt=strict),
        PromptVariant(name="Concise Execution", why=labels["reason_concise"], prompt=concise),
        PromptVariant(name="Self-Evaluating", why=labels["reason_eval"], prompt=evaluative),
    ]


def debug_prompt(data: PromptDebuggerInput) -> PromptDebuggerOutput:
    """Analyze prompt quality and build improved prompt variants."""
    return PromptDebuggerOutput(
        diagnosis=_build_diagnosis(data),
        improved_variants=_build_variants(data),
    )


def render_markdown(report: PromptDebuggerOutput, original_prompt: str) -> str:
    """Render prompt diagnosis/variants into a markdown report."""
    lines: list[str] = []
    lines.append("# Prompt Debugger Report")
    lines.append("")
    lines.append("## Original Prompt")
    lines.append("")
    lines.append("```text")
    lines.append(original_prompt.strip())
    lines.append("```")
    lines.append("")
    lines.append("## Diagnosis")
    lines.append("")
    for issue in report.diagnosis:
        lines.append(f"- **[{issue.severity.upper()}] {issue.title}**: {issue.rationale}")
    lines.append("")
    lines.append("## Improved Prompt Variants")
    lines.append("")
    for index, variant in enumerate(report.improved_variants, start=1):
        lines.append(f"### {index}. {variant.name}")
        lines.append("")
        lines.append(f"Reason: {variant.why}")
        lines.append("")
        lines.append("```text")
        lines.append(variant.prompt.strip())
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def run(
    data: PromptDebuggerInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "prompt-debugger-report",
    overwrite: bool = False,
) -> SkillRunResult:
    """Execute prompt_debugger and persist a markdown report."""
    report = debug_prompt(data)
    markdown = render_markdown(report, data.prompt)
    output_path = build_output_path(output_dir, "prompt_debugger", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="prompt_debugger",
        output_path=output_path,
        summary=f"Prompt diagnosis created with {len(report.diagnosis)} findings and {len(report.improved_variants)} variants.",
        metadata=build_run_metadata(
            artifact_type="prompt_debug_report",
            subject=data.prompt[:120],
            subject_type="prompt",
            warning_count=len(report.diagnosis),
            extra={
                "diagnosis_count": len(report.diagnosis),
                "variant_count": len(report.improved_variants),
                "language": _detect_language(data.prompt),
                "task_type": _detect_task_type(data.prompt),
            },
        ),
    )
