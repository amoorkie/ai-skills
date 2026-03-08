"""Evaluation helpers for architecture_designer."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.architecture_designer.eval_corpus import build_builtin_eval_cases
from ai_skills_toolkit.skills.architecture_designer.eval_types import EvaluationCase, EvaluationCaseResult, EvaluationSummary
from ai_skills_toolkit.skills.architecture_designer.skill import design_architecture


def _contains_fragment(items: list[str], fragment: str) -> bool:
    return any(fragment in item for item in items)


def evaluate_cases(cases: list[EvaluationCase]) -> EvaluationSummary:
    """Run a batch of evaluation cases against the architecture designer."""
    results: list[EvaluationCaseResult] = []
    total_expected = 0
    total_found = 0

    for case in cases:
        spec = design_architecture(case.input_data)
        missing_components = case.expected_components - set(spec.components)
        missing_entities = case.expected_entities - set(spec.data_entities)
        missing_endpoints = case.expected_endpoints - set(spec.api_endpoints)
        missing_risk_fragments = {item for item in case.expected_risks if not _contains_fragment(spec.risks, item)}
        missing_question_fragments = {
            item for item in case.expected_questions if not _contains_fragment(spec.open_questions, item)
        }
        expected_count = (
            len(case.expected_components)
            + len(case.expected_entities)
            + len(case.expected_endpoints)
            + len(case.expected_risks)
            + len(case.expected_questions)
        )
        missing_count = (
            len(missing_components)
            + len(missing_entities)
            + len(missing_endpoints)
            + len(missing_risk_fragments)
            + len(missing_question_fragments)
        )
        recall = 1.0 if expected_count == 0 else (expected_count - missing_count) / expected_count
        passed = missing_count == 0

        results.append(
            EvaluationCaseResult(
                name=case.name,
                missing_components=missing_components,
                missing_entities=missing_entities,
                missing_endpoints=missing_endpoints,
                missing_risk_fragments=missing_risk_fragments,
                missing_question_fragments=missing_question_fragments,
                recall=recall,
                passed=passed,
            )
        )
        total_expected += expected_count
        total_found += expected_count - missing_count

    overall_recall = 1.0 if total_expected == 0 else total_found / total_expected
    pass_rate = sum(1 for result in results if result.passed) / (len(results) or 1)
    return EvaluationSummary(case_results=results, overall_recall=overall_recall, pass_rate=pass_rate)


def render_evaluation_markdown(summary: EvaluationSummary) -> str:
    """Render evaluation metrics into markdown."""
    lines: list[str] = []
    lines.append("# Architecture Designer Evaluation")
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
        if result.missing_components:
            lines.append(f"  - Missing components: {', '.join(f'`{item}`' for item in sorted(result.missing_components))}")
        if result.missing_entities:
            lines.append(f"  - Missing entities: {', '.join(f'`{item}`' for item in sorted(result.missing_entities))}")
        if result.missing_endpoints:
            lines.append(f"  - Missing endpoints: {', '.join(f'`{item}`' for item in sorted(result.missing_endpoints))}")
        if result.missing_risk_fragments:
            lines.append(
                f"  - Missing risks: {', '.join(f'`{item}`' for item in sorted(result.missing_risk_fragments))}"
            )
        if result.missing_question_fragments:
            lines.append(
                f"  - Missing questions: {', '.join(f'`{item}`' for item in sorted(result.missing_question_fragments))}"
            )
    lines.append("")
    return "\n".join(lines)


def run_builtin_evaluation(
    *,
    output_dir: Path,
    output_name: str = "architecture-designer-eval",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run the built-in evaluation corpus and persist a markdown report."""
    summary = evaluate_cases(build_builtin_eval_cases())
    markdown = render_evaluation_markdown(summary)
    output_path = build_output_path(output_dir, "architecture_designer_eval", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="architecture_designer_eval",
        output_path=output_path,
        summary=f"Architecture designer evaluation completed: recall {summary.overall_recall:.2f}, pass rate {summary.pass_rate:.2f}.",
        metadata=build_run_metadata(
            artifact_type="evaluation_report",
            subject="architecture_designer",
            subject_type="skill",
            warning_count=sum(1 for result in summary.case_results if not result.passed),
            extra={
                "case_count": len(summary.case_results),
                "overall_recall": summary.overall_recall,
                "pass_rate": summary.pass_rate,
            },
        ),
    )
