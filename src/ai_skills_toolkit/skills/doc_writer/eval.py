"""Evaluation helpers for doc_writer."""

from __future__ import annotations

from pathlib import Path
import tempfile

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.doc_writer.eval_corpus import build_builtin_eval_cases
from ai_skills_toolkit.skills.doc_writer.eval_types import EvaluationCase, EvaluationCaseResult, EvaluationSummary
from ai_skills_toolkit.skills.doc_writer.schema import DocWriterInput
from ai_skills_toolkit.skills.doc_writer.skill import generate_document


def evaluate_cases(cases: list[EvaluationCase]) -> EvaluationSummary:
    """Run a batch of evaluation cases against the doc writer."""
    results: list[EvaluationCaseResult] = []
    total_expected_fragments = 0
    total_found_expected_fragments = 0
    total_noise = 0.0

    for case in cases:
        document = generate_document(
            DocWriterInput(
                repo_path=case.repo_path,
                title=case.title,
                audience=case.audience,
                include_setup_checklist=case.include_setup_checklist,
            )
        )
        missing_fragments = {fragment for fragment in case.expected_fragments if fragment not in document}
        forbidden_fragments_found = {fragment for fragment in case.forbidden_fragments if fragment in document}
        expected_count = len(case.expected_fragments)
        fragment_recall = 1.0 if expected_count == 0 else (expected_count - len(missing_fragments)) / expected_count
        denominator = max(len(case.expected_fragments) + len(case.forbidden_fragments), 1)
        noise_rate = len(forbidden_fragments_found) / denominator
        passed = not missing_fragments and not forbidden_fragments_found

        results.append(
            EvaluationCaseResult(
                name=case.name,
                missing_fragments=missing_fragments,
                forbidden_fragments_found=forbidden_fragments_found,
                fragment_recall=fragment_recall,
                noise_rate=noise_rate,
                passed=passed,
            )
        )

        total_expected_fragments += expected_count
        total_found_expected_fragments += expected_count - len(missing_fragments)
        total_noise += noise_rate

    case_count = len(results) or 1
    overall_fragment_recall = (
        1.0 if total_expected_fragments == 0 else total_found_expected_fragments / total_expected_fragments
    )
    average_noise_rate = total_noise / case_count
    pass_rate = sum(1 for result in results if result.passed) / case_count

    return EvaluationSummary(
        case_results=results,
        overall_fragment_recall=overall_fragment_recall,
        average_noise_rate=average_noise_rate,
        pass_rate=pass_rate,
    )


def render_evaluation_markdown(summary: EvaluationSummary) -> str:
    """Render evaluation metrics into markdown."""
    lines: list[str] = []
    lines.append("# Doc Writer Evaluation")
    lines.append("")
    lines.append(f"- **Overall fragment recall:** {summary.overall_fragment_recall:.2f}")
    lines.append(f"- **Average noise rate:** {summary.average_noise_rate:.2f}")
    lines.append(f"- **Pass rate:** {summary.pass_rate:.2f}")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for result in summary.case_results:
        lines.append(f"- **{result.name}**")
        lines.append(f"  - Passed: `{result.passed}`")
        lines.append(f"  - Fragment recall: {result.fragment_recall:.2f}")
        lines.append(f"  - Noise rate: {result.noise_rate:.2f}")
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
    output_name: str = "doc-writer-eval",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run the built-in evaluation corpus and persist a markdown report."""
    with tempfile.TemporaryDirectory(prefix="doc-writer-eval-") as temp_dir:
        cases = build_builtin_eval_cases(Path(temp_dir))
        summary = evaluate_cases(cases)
    markdown = render_evaluation_markdown(summary)
    output_path = build_output_path(output_dir, "doc_writer_eval", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="doc_writer_eval",
        output_path=output_path,
        summary=(
            f"Doc writer evaluation completed: "
            f"fragment recall {summary.overall_fragment_recall:.2f}, "
            f"pass rate {summary.pass_rate:.2f}."
        ),
        metadata=build_run_metadata(
            artifact_type="evaluation_report",
            subject="doc_writer",
            subject_type="skill",
            warning_count=sum(1 for result in summary.case_results if not result.passed),
            extra={
                "case_count": len(summary.case_results),
                "overall_fragment_recall": summary.overall_fragment_recall,
                "average_noise_rate": summary.average_noise_rate,
                "pass_rate": summary.pass_rate,
            },
        ),
    )
