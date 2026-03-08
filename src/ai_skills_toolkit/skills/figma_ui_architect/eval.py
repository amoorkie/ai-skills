"""Evaluation helpers for figma_ui_architect."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.figma_ui_architect.eval_corpus import build_builtin_eval_cases
from ai_skills_toolkit.skills.figma_ui_architect.eval_types import EvaluationCase, EvaluationCaseResult, EvaluationSummary
from ai_skills_toolkit.skills.figma_ui_architect.skill import generate_ui_spec


def evaluate_cases(cases: list[EvaluationCase]) -> EvaluationSummary:
    """Run a batch of evaluation cases against the UI architect."""
    results: list[EvaluationCaseResult] = []
    total_expected = 0
    total_found = 0

    for case in cases:
        spec = generate_ui_spec(case.input_data)
        missing_fragments = {fragment for fragment in case.expected_fragments if fragment not in spec}
        forbidden_fragments_found = {fragment for fragment in case.forbidden_fragments if fragment in spec}
        expected_count = len(case.expected_fragments)
        recall = 1.0 if expected_count == 0 else (expected_count - len(missing_fragments)) / expected_count
        passed = not missing_fragments and not forbidden_fragments_found
        results.append(
            EvaluationCaseResult(
                name=case.name,
                missing_fragments=missing_fragments,
                forbidden_fragments_found=forbidden_fragments_found,
                recall=recall,
                passed=passed,
            )
        )
        total_expected += expected_count
        total_found += expected_count - len(missing_fragments)

    overall_recall = 1.0 if total_expected == 0 else total_found / total_expected
    pass_rate = sum(1 for result in results if result.passed) / (len(results) or 1)
    return EvaluationSummary(case_results=results, overall_recall=overall_recall, pass_rate=pass_rate)


def render_evaluation_markdown(summary: EvaluationSummary) -> str:
    """Render evaluation metrics into markdown."""
    lines: list[str] = []
    lines.append("# Figma UI Architect Evaluation")
    lines.append("")
    lines.append(f"- **Overall recall:** {summary.overall_recall:.2f}")
    lines.append(f"- **Pass rate:** {summary.pass_rate:.2f}")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for result in summary.case_results:
        lines.append(f"- **{result.name}**")
        lines.append(f"  - Passed: `{result.passed}`")
        lines.append(f"  - Recall: {result.recall:.2f}")
        if result.missing_fragments:
            lines.append(f"  - Missing fragments: {', '.join(f'`{item}`' for item in sorted(result.missing_fragments))}")
        if result.forbidden_fragments_found:
            lines.append(
                f"  - Forbidden fragments: {', '.join(f'`{item}`' for item in sorted(result.forbidden_fragments_found))}"
            )
    lines.append("")
    return "\n".join(lines)


def run_builtin_evaluation(
    *,
    output_dir: Path,
    output_name: str = "figma-ui-architect-eval",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run the built-in evaluation corpus and persist a markdown report."""
    summary = evaluate_cases(build_builtin_eval_cases())
    markdown = render_evaluation_markdown(summary)
    output_path = build_output_path(output_dir, "figma_ui_architect_eval", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="figma_ui_architect_eval",
        output_path=output_path,
        summary=f"Figma UI architect evaluation completed: recall {summary.overall_recall:.2f}, pass rate {summary.pass_rate:.2f}.",
        metadata=build_run_metadata(
            artifact_type="evaluation_report",
            subject="figma_ui_architect",
            subject_type="skill",
            warning_count=sum(1 for result in summary.case_results if not result.passed),
            extra={
                "case_count": len(summary.case_results),
                "overall_recall": summary.overall_recall,
                "pass_rate": summary.pass_rate,
            },
        ),
    )
