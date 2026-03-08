"""Evaluation helpers for prompt_debugger."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.prompt_debugger.eval_corpus import build_builtin_eval_cases
from ai_skills_toolkit.skills.prompt_debugger.eval_types import EvaluationCase, EvaluationCaseResult, EvaluationSummary
from ai_skills_toolkit.skills.prompt_debugger.schema import PromptDebuggerInput
from ai_skills_toolkit.skills.prompt_debugger.skill import _detect_language, _detect_task_type, debug_prompt


def evaluate_cases(cases: list[EvaluationCase]) -> EvaluationSummary:
    """Run a batch of evaluation cases against the prompt debugger."""
    results: list[EvaluationCaseResult] = []
    total_cases = len(cases) or 1
    language_hits = 0
    task_hits = 0
    total_expected_items = 0
    total_found_expected_items = 0
    total_noise = 0.0

    for case in cases:
        input_data = PromptDebuggerInput(
            prompt=case.prompt,
            goal=case.goal,
            context=case.context,
            target_model=case.target_model,
        )
        output = debug_prompt(input_data)
        issue_titles = {issue.title for issue in output.diagnosis}
        variant_text = "\n".join(variant.prompt for variant in output.improved_variants)

        detected_language = _detect_language(case.prompt)
        detected_task_type = _detect_task_type(case.prompt)
        language_correct = case.expected_language is None or detected_language == case.expected_language
        task_type_correct = case.expected_task_type is None or detected_task_type == case.expected_task_type
        missing_issue_titles = case.expected_issue_titles - issue_titles
        forbidden_issue_hits = issue_titles & case.forbidden_issue_titles
        missing_variant_fragments = {fragment for fragment in case.expected_variant_fragments if fragment not in variant_text}

        expected_item_count = len(case.expected_issue_titles) + len(case.expected_variant_fragments)
        found_expected_items = expected_item_count - len(missing_issue_titles) - len(missing_variant_fragments)
        recall = 1.0 if expected_item_count == 0 else found_expected_items / expected_item_count
        denominator = max(expected_item_count + len(case.forbidden_issue_titles), 1)
        noise_rate = len(forbidden_issue_hits) / denominator
        passed = language_correct and task_type_correct and not missing_issue_titles and not forbidden_issue_hits and not missing_variant_fragments

        results.append(
            EvaluationCaseResult(
                name=case.name,
                language_correct=language_correct,
                task_type_correct=task_type_correct,
                missing_issue_titles=missing_issue_titles,
                forbidden_issue_hits=forbidden_issue_hits,
                missing_variant_fragments=missing_variant_fragments,
                recall=recall,
                noise_rate=noise_rate,
                passed=passed,
            )
        )

        language_hits += 1 if language_correct else 0
        task_hits += 1 if task_type_correct else 0
        total_expected_items += expected_item_count
        total_found_expected_items += found_expected_items
        total_noise += noise_rate

    overall_language_accuracy = language_hits / total_cases
    overall_task_accuracy = task_hits / total_cases
    overall_recall = 1.0 if total_expected_items == 0 else total_found_expected_items / total_expected_items
    average_noise_rate = total_noise / total_cases
    pass_rate = sum(1 for result in results if result.passed) / total_cases

    return EvaluationSummary(
        case_results=results,
        overall_language_accuracy=overall_language_accuracy,
        overall_task_accuracy=overall_task_accuracy,
        overall_recall=overall_recall,
        average_noise_rate=average_noise_rate,
        pass_rate=pass_rate,
    )


def render_evaluation_markdown(summary: EvaluationSummary) -> str:
    """Render evaluation metrics into markdown."""
    lines: list[str] = []
    lines.append("# Prompt Debugger Evaluation")
    lines.append("")
    lines.append(f"- **Overall language accuracy:** {summary.overall_language_accuracy:.2f}")
    lines.append(f"- **Overall task accuracy:** {summary.overall_task_accuracy:.2f}")
    lines.append(f"- **Overall recall:** {summary.overall_recall:.2f}")
    lines.append(f"- **Average noise rate:** {summary.average_noise_rate:.2f}")
    lines.append(f"- **Pass rate:** {summary.pass_rate:.2f}")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for result in summary.case_results:
        lines.append(f"- **{result.name}**")
        lines.append(f"  - Passed: `{result.passed}`")
        lines.append(f"  - Language correct: `{result.language_correct}`")
        lines.append(f"  - Task correct: `{result.task_type_correct}`")
        lines.append(f"  - Recall: {result.recall:.2f}")
        lines.append(f"  - Noise rate: {result.noise_rate:.2f}")
        if result.missing_issue_titles:
            lines.append(f"  - Missing issues: {', '.join(f'`{item}`' for item in sorted(result.missing_issue_titles))}")
        if result.forbidden_issue_hits:
            lines.append(f"  - Forbidden issues: {', '.join(f'`{item}`' for item in sorted(result.forbidden_issue_hits))}")
        if result.missing_variant_fragments:
            lines.append(
                f"  - Missing variant fragments: {', '.join(f'`{item}`' for item in sorted(result.missing_variant_fragments))}"
            )
    lines.append("")
    return "\n".join(lines)


def run_builtin_evaluation(
    *,
    output_dir: Path,
    output_name: str = "prompt-debugger-eval",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run the built-in evaluation corpus and persist a markdown report."""
    summary = evaluate_cases(build_builtin_eval_cases())
    markdown = render_evaluation_markdown(summary)
    output_path = build_output_path(output_dir, "prompt_debugger_eval", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="prompt_debugger_eval",
        output_path=output_path,
        summary=(
            f"Prompt debugger evaluation completed: "
            f"language accuracy {summary.overall_language_accuracy:.2f}, "
            f"task accuracy {summary.overall_task_accuracy:.2f}, "
            f"pass rate {summary.pass_rate:.2f}."
        ),
        metadata=build_run_metadata(
            artifact_type="evaluation_report",
            subject="prompt_debugger",
            subject_type="skill",
            warning_count=sum(1 for result in summary.case_results if not result.passed),
            extra={
                "case_count": len(summary.case_results),
                "overall_language_accuracy": summary.overall_language_accuracy,
                "overall_task_accuracy": summary.overall_task_accuracy,
                "overall_recall": summary.overall_recall,
                "average_noise_rate": summary.average_noise_rate,
                "pass_rate": summary.pass_rate,
            },
        ),
    )
