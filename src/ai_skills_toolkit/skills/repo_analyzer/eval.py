"""Evaluation helpers for repo_analyzer."""

from __future__ import annotations

from pathlib import Path
import tempfile

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.repo_analyzer.eval_corpus import build_builtin_eval_cases
from ai_skills_toolkit.skills.repo_analyzer.eval_types import EvaluationCase, EvaluationCaseResult, EvaluationSummary
from ai_skills_toolkit.skills.repo_analyzer.schema import RepoAnalyzerInput
from ai_skills_toolkit.skills.repo_analyzer.skill import analyze_repository


def evaluate_cases(cases: list[EvaluationCase]) -> EvaluationSummary:
    """Run a batch of evaluation cases against the repo analyzer."""
    results: list[EvaluationCaseResult] = []
    total_cases = len(cases) or 1
    total_project_kind_hits = 0
    total_expected_signals = 0
    total_found_expected_signals = 0
    total_noise = 0.0

    for case in cases:
        analysis = analyze_repository(RepoAnalyzerInput(repo_path=case.repo_path, include_hidden=case.include_hidden))
        project_kind_correct = case.expected_project_kind is None or analysis.project_kind == case.expected_project_kind
        missing_entrypoints = case.expected_entrypoints - set(analysis.entrypoints)
        missing_tooling_signals = case.expected_tooling_signals - set(analysis.tooling_signals)
        forbidden_largest_hits = {
            item.path for item in analysis.largest_files if item.path in case.forbidden_largest_paths
        }

        expected_signal_count = len(case.expected_entrypoints) + len(case.expected_tooling_signals)
        found_expected_signals = expected_signal_count - len(missing_entrypoints) - len(missing_tooling_signals)
        signal_recall = 1.0 if expected_signal_count == 0 else found_expected_signals / expected_signal_count
        denominator = max(expected_signal_count + len(case.forbidden_largest_paths), 1)
        noise_rate = len(forbidden_largest_hits) / denominator
        passed = project_kind_correct and not missing_entrypoints and not missing_tooling_signals and not forbidden_largest_hits

        results.append(
            EvaluationCaseResult(
                name=case.name,
                project_kind_correct=project_kind_correct,
                missing_entrypoints=missing_entrypoints,
                missing_tooling_signals=missing_tooling_signals,
                forbidden_largest_hits=forbidden_largest_hits,
                signal_recall=signal_recall,
                noise_rate=noise_rate,
                passed=passed,
            )
        )

        total_project_kind_hits += 1 if project_kind_correct else 0
        total_expected_signals += expected_signal_count
        total_found_expected_signals += found_expected_signals
        total_noise += noise_rate

    overall_project_kind_accuracy = total_project_kind_hits / total_cases
    overall_signal_recall = 1.0 if total_expected_signals == 0 else total_found_expected_signals / total_expected_signals
    average_noise_rate = total_noise / total_cases
    pass_rate = sum(1 for result in results if result.passed) / total_cases

    return EvaluationSummary(
        case_results=results,
        overall_project_kind_accuracy=overall_project_kind_accuracy,
        overall_signal_recall=overall_signal_recall,
        average_noise_rate=average_noise_rate,
        pass_rate=pass_rate,
    )


def render_evaluation_markdown(summary: EvaluationSummary) -> str:
    """Render evaluation metrics into markdown."""
    lines: list[str] = []
    lines.append("# Repo Analyzer Evaluation")
    lines.append("")
    lines.append(f"- **Overall project-kind accuracy:** {summary.overall_project_kind_accuracy:.2f}")
    lines.append(f"- **Overall signal recall:** {summary.overall_signal_recall:.2f}")
    lines.append(f"- **Average noise rate:** {summary.average_noise_rate:.2f}")
    lines.append(f"- **Pass rate:** {summary.pass_rate:.2f}")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for result in summary.case_results:
        lines.append(f"- **{result.name}**")
        lines.append(f"  - Passed: `{result.passed}`")
        lines.append(f"  - Project kind correct: `{result.project_kind_correct}`")
        lines.append(f"  - Signal recall: {result.signal_recall:.2f}")
        lines.append(f"  - Noise rate: {result.noise_rate:.2f}")
        if result.missing_entrypoints:
            lines.append(f"  - Missing entrypoints: {', '.join(f'`{item}`' for item in sorted(result.missing_entrypoints))}")
        if result.missing_tooling_signals:
            lines.append(
                f"  - Missing tooling signals: {', '.join(f'`{item}`' for item in sorted(result.missing_tooling_signals))}"
            )
        if result.forbidden_largest_hits:
            lines.append(
                f"  - Forbidden largest-file hits: {', '.join(f'`{item}`' for item in sorted(result.forbidden_largest_hits))}"
            )
    lines.append("")
    return "\n".join(lines)


def run_builtin_evaluation(
    *,
    output_dir: Path,
    output_name: str = "repo-analyzer-eval",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run the built-in evaluation corpus and persist a markdown report."""
    with tempfile.TemporaryDirectory(prefix="repo-analyzer-eval-") as temp_dir:
        cases = build_builtin_eval_cases(Path(temp_dir))
        summary = evaluate_cases(cases)
    markdown = render_evaluation_markdown(summary)
    output_path = build_output_path(output_dir, "repo_analyzer_eval", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="repo_analyzer_eval",
        output_path=output_path,
        summary=(
            f"Repo analyzer evaluation completed: "
            f"project-kind accuracy {summary.overall_project_kind_accuracy:.2f}, "
            f"signal recall {summary.overall_signal_recall:.2f}, "
            f"pass rate {summary.pass_rate:.2f}."
        ),
        metadata=build_run_metadata(
            artifact_type="evaluation_report",
            subject="repo_analyzer",
            subject_type="skill",
            warning_count=sum(1 for result in summary.case_results if not result.passed),
            extra={
                "case_count": len(summary.case_results),
                "overall_project_kind_accuracy": summary.overall_project_kind_accuracy,
                "overall_signal_recall": summary.overall_signal_recall,
                "average_noise_rate": summary.average_noise_rate,
                "pass_rate": summary.pass_rate,
            },
        ),
    )
