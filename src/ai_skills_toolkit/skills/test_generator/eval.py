"""Evaluation helpers for test_generator."""

from __future__ import annotations

from pathlib import Path
import tempfile

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.test_generator.eval_corpus import build_builtin_eval_cases
from ai_skills_toolkit.skills.test_generator.eval_types import EvaluationCase, EvaluationCaseResult, EvaluationSummary
from ai_skills_toolkit.skills.test_generator.schema import TestGeneratorInput
from ai_skills_toolkit.skills.test_generator.skill import generate_test_plan


def evaluate_cases(cases: list[EvaluationCase]) -> EvaluationSummary:
    """Run a batch of evaluation cases against the test generator."""
    results: list[EvaluationCaseResult] = []
    total_expected_targets = 0
    total_found_expected_targets = 0
    total_expected_test_types = 0
    total_found_expected_test_types = 0
    top_hits = 0
    total_noise = 0.0

    for case in cases:
        plan = generate_test_plan(TestGeneratorInput(repo_path=case.repo_path, **case.input_overrides))
        found_target_paths = [target.path for target in plan.targets]
        found_target_set = set(found_target_paths)
        missing_target_paths = case.expected_target_paths - found_target_set
        top_slice_size = max(len(case.expected_target_paths), 1)
        top_slice = found_target_paths[:top_slice_size]
        forbidden_target_hits = set(top_slice) & case.forbidden_target_paths
        top_path = found_target_paths[0] if found_target_paths else None
        top_path_correct = case.expected_top_path is None or top_path == case.expected_top_path

        missing_test_types_by_target: dict[str, set[str]] = {}
        for target_path, expected_types in case.expected_test_types_by_target.items():
            matching_target = next((target for target in plan.targets if target.path == target_path), None)
            found_types = set(matching_target.suggested_test_types) if matching_target else set()
            missing = expected_types - found_types
            if missing:
                missing_test_types_by_target[target_path] = missing

        expected_target_count = len(case.expected_target_paths)
        expected_test_type_count = sum(len(items) for items in case.expected_test_types_by_target.values())
        target_recall = (
            1.0 if expected_target_count == 0 else (expected_target_count - len(missing_target_paths)) / expected_target_count
        )
        missing_test_type_count = sum(len(items) for items in missing_test_types_by_target.values())
        test_type_recall = (
            1.0
            if expected_test_type_count == 0
            else (expected_test_type_count - missing_test_type_count) / expected_test_type_count
        )

        extra_top_paths = {path for path in top_slice if path not in case.expected_target_paths and path not in case.forbidden_target_paths}
        denominator = max(len(top_slice), 1)
        noise_rate = (len(extra_top_paths) + len(forbidden_target_hits)) / denominator
        passed = not missing_target_paths and not missing_test_types_by_target and not forbidden_target_hits and top_path_correct

        results.append(
            EvaluationCaseResult(
                name=case.name,
                found_target_paths=found_target_paths,
                top_path=top_path,
                missing_target_paths=missing_target_paths,
                missing_test_types_by_target=missing_test_types_by_target,
                forbidden_target_hits=forbidden_target_hits,
                target_recall=target_recall,
                top_path_correct=top_path_correct,
                test_type_recall=test_type_recall,
                noise_rate=noise_rate,
                passed=passed,
            )
        )

        total_expected_targets += expected_target_count
        total_found_expected_targets += expected_target_count - len(missing_target_paths)
        total_expected_test_types += expected_test_type_count
        total_found_expected_test_types += expected_test_type_count - missing_test_type_count
        top_hits += 1 if top_path_correct else 0
        total_noise += noise_rate

    case_count = len(results) or 1
    overall_target_recall = 1.0 if total_expected_targets == 0 else total_found_expected_targets / total_expected_targets
    overall_top_path_accuracy = top_hits / case_count
    overall_test_type_recall = (
        1.0 if total_expected_test_types == 0 else total_found_expected_test_types / total_expected_test_types
    )
    average_noise_rate = total_noise / case_count
    pass_rate = sum(1 for result in results if result.passed) / case_count

    return EvaluationSummary(
        case_results=results,
        overall_target_recall=overall_target_recall,
        overall_top_path_accuracy=overall_top_path_accuracy,
        overall_test_type_recall=overall_test_type_recall,
        average_noise_rate=average_noise_rate,
        pass_rate=pass_rate,
    )


def render_evaluation_markdown(summary: EvaluationSummary) -> str:
    """Render evaluation metrics into markdown."""
    lines: list[str] = []
    lines.append("# Test Generator Evaluation")
    lines.append("")
    lines.append(f"- **Overall target recall:** {summary.overall_target_recall:.2f}")
    lines.append(f"- **Overall top-path accuracy:** {summary.overall_top_path_accuracy:.2f}")
    lines.append(f"- **Overall test-type recall:** {summary.overall_test_type_recall:.2f}")
    lines.append(f"- **Average noise rate:** {summary.average_noise_rate:.2f}")
    lines.append(f"- **Pass rate:** {summary.pass_rate:.2f}")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for result in summary.case_results:
        lines.append(f"- **{result.name}**")
        lines.append(f"  - Passed: `{result.passed}`")
        lines.append(f"  - Top path: `{result.top_path}`")
        lines.append(f"  - Target recall: {result.target_recall:.2f}")
        lines.append(f"  - Top-path accuracy: `{result.top_path_correct}`")
        lines.append(f"  - Test-type recall: {result.test_type_recall:.2f}")
        lines.append(f"  - Noise rate: {result.noise_rate:.2f}")
        if result.missing_target_paths:
            lines.append(f"  - Missing targets: {', '.join(f'`{item}`' for item in sorted(result.missing_target_paths))}")
        if result.forbidden_target_hits:
            lines.append(f"  - Forbidden targets: {', '.join(f'`{item}`' for item in sorted(result.forbidden_target_hits))}")
        if result.missing_test_types_by_target:
            for target_path, missing_types in sorted(result.missing_test_types_by_target.items()):
                lines.append(
                    f"  - Missing test types for `{target_path}`: {', '.join(f'`{item}`' for item in sorted(missing_types))}"
                )
    lines.append("")
    return "\n".join(lines)


def run_builtin_evaluation(
    *,
    output_dir: Path,
    output_name: str = "test-generator-eval",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run the built-in evaluation corpus and persist a markdown report."""
    with tempfile.TemporaryDirectory(prefix="test-generator-eval-") as temp_dir:
        cases = build_builtin_eval_cases(Path(temp_dir))
        summary = evaluate_cases(cases)
    markdown = render_evaluation_markdown(summary)
    output_path = build_output_path(output_dir, "test_generator_eval", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="test_generator_eval",
        output_path=output_path,
        summary=(
            f"Test generator evaluation completed: "
            f"target recall {summary.overall_target_recall:.2f}, "
            f"top-path accuracy {summary.overall_top_path_accuracy:.2f}, "
            f"pass rate {summary.pass_rate:.2f}."
        ),
        metadata=build_run_metadata(
            artifact_type="evaluation_report",
            subject="test_generator",
            subject_type="skill",
            warning_count=sum(1 for result in summary.case_results if not result.passed),
            extra={
                "case_count": len(summary.case_results),
                "overall_target_recall": summary.overall_target_recall,
                "overall_top_path_accuracy": summary.overall_top_path_accuracy,
                "overall_test_type_recall": summary.overall_test_type_recall,
                "average_noise_rate": summary.average_noise_rate,
                "pass_rate": summary.pass_rate,
            },
        ),
    )
