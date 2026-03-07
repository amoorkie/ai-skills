"""Implementation for prompt_debugger."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult
from ai_skills_toolkit.skills.prompt_debugger.schema import (
    PromptDebuggerInput,
    PromptDebuggerOutput,
    PromptIssue,
    PromptVariant,
)


def _build_diagnosis(data: PromptDebuggerInput) -> list[PromptIssue]:
    prompt = data.prompt.strip()
    words = prompt.split()
    issues: list[PromptIssue] = []

    if len(words) < 25:
        issues.append(
            PromptIssue(
                severity="high",
                title="Prompt is underspecified",
                rationale="The request is short and likely missing constraints, acceptance criteria, or context.",
            )
        )
    if "output" not in prompt.lower() and "format" not in prompt.lower():
        issues.append(
            PromptIssue(
                severity="high",
                title="No explicit output format",
                rationale="Without a format contract, responses may be inconsistent and harder to verify automatically.",
            )
        )
    if not any(token in prompt.lower() for token in ["must", "should", "avoid", "do not", "constraint"]):
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
    goal = data.goal or "Deliver a complete and correct result."
    context = data.context or "No additional context provided."
    model_line = f"Target model: {data.target_model}" if data.target_model else "Target model: unspecified"

    base_sections = (
        f"Goal:\n{goal}\n\n"
        f"Context:\n{context}\n\n"
        f"{model_line}\n\n"
        "Hard constraints:\n"
        "- Do not invent missing facts.\n"
        "- State assumptions explicitly.\n"
        "- Return actionable output.\n"
    )

    strict = (
        "You are a senior execution agent.\n"
        f"{base_sections}\n"
        "Task:\n"
        f"{data.prompt.strip()}\n\n"
        "Output format:\n"
        "1. Assumptions\n"
        "2. Plan\n"
        "3. Result\n"
        "4. Risks/Limitations\n"
    )
    concise = (
        "Execute the task below with minimal prose and maximum correctness.\n\n"
        f"Task:\n{data.prompt.strip()}\n\n"
        "Required output:\n"
        "- Summary (3 lines max)\n"
        "- Final deliverable\n"
        "- Known limitations\n"
    )
    evaluative = (
        "Act as both implementer and reviewer.\n"
        f"{base_sections}\n"
        f"Task:\n{data.prompt.strip()}\n\n"
        "Before finalizing, score your output (1-5) on:\n"
        "- Correctness\n"
        "- Completeness\n"
        "- Clarity\n"
        "If any score < 4, revise once before returning final output.\n"
    )

    return [
        PromptVariant(name="Structured Strict", why="Adds explicit constraints and a fixed response schema.", prompt=strict),
        PromptVariant(name="Concise Execution", why="Optimized for shorter deterministic responses.", prompt=concise),
        PromptVariant(name="Self-Evaluating", why="Adds a lightweight quality gate before final response.", prompt=evaluative),
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
        metadata={"diagnosis_count": len(report.diagnosis), "variant_count": len(report.improved_variants)},
    )
