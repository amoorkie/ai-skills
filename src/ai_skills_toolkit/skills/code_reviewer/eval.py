"""Evaluation helpers for code_reviewer."""

from __future__ import annotations

from pathlib import Path
import tempfile

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.code_reviewer.eval_types import EvaluationCase, EvaluationCaseResult, EvaluationSummary
from ai_skills_toolkit.skills.code_reviewer.schema import CodeReviewerInput
from ai_skills_toolkit.skills.code_reviewer.skill import review_repository
from ai_skills_toolkit.skills.code_reviewer.eval_corpus import build_builtin_eval_cases


def evaluate_cases(cases: list[EvaluationCase]) -> EvaluationSummary:
    """Run a batch of evaluation cases against the reviewer."""
    results: list[EvaluationCaseResult] = []
    total_expected_rules = 0
    total_found_expected_rules = 0
    total_expected_clusters = 0
    total_found_expected_clusters = 0
    total_noise = 0.0

    for case in cases:
        reviewer_input = CodeReviewerInput(repo_path=case.repo_path, **case.input_overrides)
        report = review_repository(reviewer_input)
        found_rule_ids = {finding.rule_id for finding in report.findings}
        found_cluster_ids = {cluster.cluster_id for cluster in report.top_risk_clusters}
        missing_rule_ids = case.expected_rule_ids - found_rule_ids
        missing_cluster_ids = case.expected_cluster_ids - found_cluster_ids
        forbidden_rule_hits = found_rule_ids & case.forbidden_rule_ids
        extra_rule_ids = found_rule_ids - case.expected_rule_ids - case.forbidden_rule_ids

        expected_rule_count = len(case.expected_rule_ids)
        expected_cluster_count = len(case.expected_cluster_ids)
        rule_recall = 1.0 if expected_rule_count == 0 else (expected_rule_count - len(missing_rule_ids)) / expected_rule_count
        cluster_recall = (
            1.0
            if expected_cluster_count == 0
            else (expected_cluster_count - len(missing_cluster_ids)) / expected_cluster_count
        )
        total_found = len(found_rule_ids) or 1
        noise_rate = (len(extra_rule_ids) + len(forbidden_rule_hits)) / total_found
        passed = not missing_rule_ids and not missing_cluster_ids and not forbidden_rule_hits

        results.append(
            EvaluationCaseResult(
                name=case.name,
                found_rule_ids=found_rule_ids,
                found_cluster_ids=found_cluster_ids,
                missing_rule_ids=missing_rule_ids,
                missing_cluster_ids=missing_cluster_ids,
                forbidden_rule_hits=forbidden_rule_hits,
                extra_rule_ids=extra_rule_ids,
                rule_recall=rule_recall,
                cluster_recall=cluster_recall,
                noise_rate=noise_rate,
                passed=passed,
            )
        )

        total_expected_rules += expected_rule_count
        total_found_expected_rules += expected_rule_count - len(missing_rule_ids)
        total_expected_clusters += expected_cluster_count
        total_found_expected_clusters += expected_cluster_count - len(missing_cluster_ids)
        total_noise += noise_rate

    case_count = len(results) or 1
    overall_rule_recall = 1.0 if total_expected_rules == 0 else total_found_expected_rules / total_expected_rules
    overall_cluster_recall = (
        1.0 if total_expected_clusters == 0 else total_found_expected_clusters / total_expected_clusters
    )
    pass_rate = sum(1 for result in results if result.passed) / case_count
    average_noise_rate = total_noise / case_count

    return EvaluationSummary(
        case_results=results,
        overall_rule_recall=overall_rule_recall,
        overall_cluster_recall=overall_cluster_recall,
        average_noise_rate=average_noise_rate,
        pass_rate=pass_rate,
    )


def render_evaluation_markdown(summary: EvaluationSummary) -> str:
    """Render evaluation metrics into markdown."""
    lines: list[str] = []
    lines.append("# Code Reviewer Evaluation")
    lines.append("")
    lines.append(f"- **Overall rule recall:** {summary.overall_rule_recall:.2f}")
    lines.append(f"- **Overall cluster recall:** {summary.overall_cluster_recall:.2f}")
    lines.append(f"- **Average noise rate:** {summary.average_noise_rate:.2f}")
    lines.append(f"- **Pass rate:** {summary.pass_rate:.2f}")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for result in summary.case_results:
        lines.append(f"- **{result.name}**")
        lines.append(f"  - Passed: `{result.passed}`")
        lines.append(f"  - Rule recall: {result.rule_recall:.2f}")
        lines.append(f"  - Cluster recall: {result.cluster_recall:.2f}")
        lines.append(f"  - Noise rate: {result.noise_rate:.2f}")
        if result.missing_rule_ids:
            lines.append(f"  - Missing rules: {', '.join(f'`{item}`' for item in sorted(result.missing_rule_ids))}")
        if result.missing_cluster_ids:
            lines.append(f"  - Missing clusters: {', '.join(f'`{item}`' for item in sorted(result.missing_cluster_ids))}")
        if result.forbidden_rule_hits:
            lines.append(f"  - Forbidden hits: {', '.join(f'`{item}`' for item in sorted(result.forbidden_rule_hits))}")
    lines.append("")
    return "\n".join(lines)


def run_builtin_evaluation(
    *,
    output_dir: Path,
    output_name: str = "code-review-eval",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run the built-in evaluation corpus and persist a markdown report."""
    with tempfile.TemporaryDirectory(prefix="code-reviewer-eval-") as temp_dir:
        cases = build_builtin_eval_cases(Path(temp_dir))
        summary = evaluate_cases(cases)
    markdown = render_evaluation_markdown(summary)
    output_path = build_output_path(output_dir, "code_reviewer_eval", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="code_reviewer_eval",
        output_path=output_path,
        summary=(
            f"Code reviewer evaluation completed: "
            f"rule recall {summary.overall_rule_recall:.2f}, "
            f"cluster recall {summary.overall_cluster_recall:.2f}, "
            f"pass rate {summary.pass_rate:.2f}."
        ),
        metadata=build_run_metadata(
            artifact_type="evaluation_report",
            subject="code_reviewer",
            subject_type="skill",
            warning_count=sum(1 for result in summary.case_results if not result.passed),
            extra={
                "case_count": len(summary.case_results),
                "overall_rule_recall": summary.overall_rule_recall,
                "overall_cluster_recall": summary.overall_cluster_recall,
                "average_noise_rate": summary.average_noise_rate,
                "pass_rate": summary.pass_rate,
            },
        ),
    )
