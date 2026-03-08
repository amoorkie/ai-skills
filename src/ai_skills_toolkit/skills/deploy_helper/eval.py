"""Evaluation helpers for deploy_helper."""

from __future__ import annotations

from pathlib import Path
import tempfile

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.deploy_helper.eval_corpus import build_builtin_eval_cases
from ai_skills_toolkit.skills.deploy_helper.eval_types import EvaluationCase, EvaluationCaseResult, EvaluationSummary
from ai_skills_toolkit.skills.deploy_helper.schema import DeployHelperInput
from ai_skills_toolkit.skills.deploy_helper.skill import generate_deploy_plan


def _contains_fragment(items: list[str], fragment: str) -> bool:
    return any(fragment in item for item in items)


def evaluate_cases(cases: list[EvaluationCase]) -> EvaluationSummary:
    """Run a batch of evaluation cases against the deploy helper."""
    results: list[EvaluationCaseResult] = []
    total_cases = len(cases) or 1
    total_platform_hits = 0
    total_expected_items = 0
    total_found_expected_items = 0
    total_noise = 0.0

    for case in cases:
        plan = generate_deploy_plan(DeployHelperInput(repo_path=case.repo_path, **case.input_overrides))
        platform_correct = case.expected_platform is None or plan.platform == case.expected_platform
        missing_detected_files = {item for item in case.expected_detected_files if item not in set(plan.detected_files)}
        missing_commands = {item for item in case.expected_commands if item not in set(plan.commands)}
        missing_notes = {item for item in case.expected_notes if not _contains_fragment(plan.notes, item)}
        missing_manifest_signals = {
            item for item in case.expected_manifest_signals if item not in set(plan.manifest_signals)
        }
        forbidden_command_hits = {item for item in case.forbidden_commands if item in set(plan.commands)}

        expected_item_count = (
            len(case.expected_detected_files)
            + len(case.expected_commands)
            + len(case.expected_notes)
            + len(case.expected_manifest_signals)
        )
        found_expected_items = (
            expected_item_count
            - len(missing_detected_files)
            - len(missing_commands)
            - len(missing_notes)
            - len(missing_manifest_signals)
        )
        recall = 1.0 if expected_item_count == 0 else found_expected_items / expected_item_count
        denominator = max(expected_item_count + len(case.forbidden_commands), 1)
        noise_rate = len(forbidden_command_hits) / denominator
        passed = (
            platform_correct
            and not missing_detected_files
            and not missing_commands
            and not missing_notes
            and not missing_manifest_signals
            and not forbidden_command_hits
        )

        results.append(
            EvaluationCaseResult(
                name=case.name,
                platform_correct=platform_correct,
                missing_detected_files=missing_detected_files,
                missing_commands=missing_commands,
                missing_notes=missing_notes,
                missing_manifest_signals=missing_manifest_signals,
                forbidden_command_hits=forbidden_command_hits,
                recall=recall,
                noise_rate=noise_rate,
                passed=passed,
            )
        )

        total_platform_hits += 1 if platform_correct else 0
        total_expected_items += expected_item_count
        total_found_expected_items += found_expected_items
        total_noise += noise_rate

    overall_platform_accuracy = total_platform_hits / total_cases
    overall_recall = 1.0 if total_expected_items == 0 else total_found_expected_items / total_expected_items
    average_noise_rate = total_noise / total_cases
    pass_rate = sum(1 for result in results if result.passed) / total_cases

    return EvaluationSummary(
        case_results=results,
        overall_platform_accuracy=overall_platform_accuracy,
        overall_recall=overall_recall,
        average_noise_rate=average_noise_rate,
        pass_rate=pass_rate,
    )


def render_evaluation_markdown(summary: EvaluationSummary) -> str:
    """Render evaluation metrics into markdown."""
    lines: list[str] = []
    lines.append("# Deploy Helper Evaluation")
    lines.append("")
    lines.append(f"- **Overall platform accuracy:** {summary.overall_platform_accuracy:.2f}")
    lines.append(f"- **Overall recall:** {summary.overall_recall:.2f}")
    lines.append(f"- **Average noise rate:** {summary.average_noise_rate:.2f}")
    lines.append(f"- **Pass rate:** {summary.pass_rate:.2f}")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for result in summary.case_results:
        lines.append(f"- **{result.name}**")
        lines.append(f"  - Passed: `{result.passed}`")
        lines.append(f"  - Platform correct: `{result.platform_correct}`")
        lines.append(f"  - Recall: {result.recall:.2f}")
        lines.append(f"  - Noise rate: {result.noise_rate:.2f}")
        if result.missing_detected_files:
            lines.append(
                f"  - Missing detected files: {', '.join(f'`{item}`' for item in sorted(result.missing_detected_files))}"
            )
        if result.missing_commands:
            lines.append(f"  - Missing commands: {', '.join(f'`{item}`' for item in sorted(result.missing_commands))}")
        if result.missing_notes:
            lines.append(f"  - Missing notes: {', '.join(f'`{item}`' for item in sorted(result.missing_notes))}")
        if result.missing_manifest_signals:
            lines.append(
                f"  - Missing manifest signals: {', '.join(f'`{item}`' for item in sorted(result.missing_manifest_signals))}"
            )
        if result.forbidden_command_hits:
            lines.append(
                f"  - Forbidden command hits: {', '.join(f'`{item}`' for item in sorted(result.forbidden_command_hits))}"
            )
    lines.append("")
    return "\n".join(lines)


def run_builtin_evaluation(
    *,
    output_dir: Path,
    output_name: str = "deploy-helper-eval",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run the built-in evaluation corpus and persist a markdown report."""
    with tempfile.TemporaryDirectory(prefix="deploy-helper-eval-") as temp_dir:
        cases = build_builtin_eval_cases(Path(temp_dir))
        summary = evaluate_cases(cases)
    markdown = render_evaluation_markdown(summary)
    output_path = build_output_path(output_dir, "deploy_helper_eval", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="deploy_helper_eval",
        output_path=output_path,
        summary=(
            f"Deploy helper evaluation completed: "
            f"platform accuracy {summary.overall_platform_accuracy:.2f}, "
            f"recall {summary.overall_recall:.2f}, "
            f"pass rate {summary.pass_rate:.2f}."
        ),
        metadata=build_run_metadata(
            artifact_type="evaluation_report",
            subject="deploy_helper",
            subject_type="skill",
            warning_count=sum(1 for result in summary.case_results if not result.passed),
            extra={
                "case_count": len(summary.case_results),
                "overall_platform_accuracy": summary.overall_platform_accuracy,
                "overall_recall": summary.overall_recall,
                "average_noise_rate": summary.average_noise_rate,
                "pass_rate": summary.pass_rate,
            },
        ),
    )
