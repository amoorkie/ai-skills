"""Aggregate readiness runner for built-in skill evaluations."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.skills.architecture_designer import run_builtin_evaluation as run_architecture_designer_eval
from ai_skills_toolkit.skills.code_reviewer import run_builtin_evaluation as run_code_reviewer_eval
from ai_skills_toolkit.skills.deploy_helper import run_builtin_evaluation as run_deploy_helper_eval
from ai_skills_toolkit.skills.doc_writer import run_builtin_evaluation as run_doc_writer_eval
from ai_skills_toolkit.skills.figma_ui_architect import run_builtin_evaluation as run_figma_ui_architect_eval
from ai_skills_toolkit.skills.prompt_debugger import run_builtin_evaluation as run_prompt_debugger_eval
from ai_skills_toolkit.skills.repo_analyzer import run_builtin_evaluation as run_repo_analyzer_eval
from ai_skills_toolkit.skills.test_generator import run_builtin_evaluation as run_test_generator_eval

EvalRunner = Callable[..., SkillRunResult]

EVALUATION_RUNNERS: list[tuple[str, EvalRunner]] = [
    ("architecture_designer", run_architecture_designer_eval),
    ("code_reviewer", run_code_reviewer_eval),
    ("deploy_helper", run_deploy_helper_eval),
    ("doc_writer", run_doc_writer_eval),
    ("figma_ui_architect", run_figma_ui_architect_eval),
    ("prompt_debugger", run_prompt_debugger_eval),
    ("repo_analyzer", run_repo_analyzer_eval),
    ("test_generator", run_test_generator_eval),
]

METRIC_LABELS = {
    "overall_rule_recall": "rule recall",
    "overall_cluster_recall": "cluster recall",
    "overall_target_recall": "target recall",
    "overall_top_path_accuracy": "top-path accuracy",
    "overall_test_type_recall": "test-type recall",
    "overall_fragment_recall": "fragment recall",
    "overall_project_kind_accuracy": "project-kind accuracy",
    "overall_signal_recall": "signal recall",
    "overall_platform_accuracy": "platform accuracy",
    "overall_language_accuracy": "language accuracy",
    "overall_task_accuracy": "task accuracy",
    "overall_recall": "recall",
    "pass_rate": "pass rate",
}


def _metric_summary(metadata: dict[str, object]) -> str:
    parts: list[str] = []
    for key, label in METRIC_LABELS.items():
        value = metadata.get(key)
        if isinstance(value, float):
            parts.append(f"{label} {value:.2f}")
    return ", ".join(parts) if parts else "no aggregate metrics"


def render_readiness_markdown(results: list[SkillRunResult]) -> str:
    """Render a consolidated readiness report from individual skill evaluations."""
    passed = [result for result in results if result.metadata.get("warning_count", 0) == 0]
    failed = [result for result in results if result.metadata.get("warning_count", 0) != 0]

    lines: list[str] = []
    lines.append("# Skills Readiness Report")
    lines.append("")
    lines.append(f"- **Skills evaluated:** {len(results)}")
    lines.append(f"- **Passed:** {len(passed)}")
    lines.append(f"- **Failed:** {len(failed)}")
    lines.append("")
    lines.append("## Skill Evaluations")
    lines.append("")
    for result in results:
        status = "PASS" if result.metadata.get("warning_count", 0) == 0 else "FAIL"
        lines.append(f"### `{result.skill_name}`")
        lines.append("")
        lines.append(f"- Status: `{status}`")
        lines.append(f"- Summary: {result.summary}")
        lines.append(f"- Metrics: {_metric_summary(result.metadata)}")
        lines.append(f"- Report: `{result.output_path}`")
        lines.append("")
    if failed:
        lines.append("## Follow-up")
        lines.append("")
        lines.extend([f"- Investigate `{result.skill_name}` readiness report." for result in failed])
        lines.append("")
    return "\n".join(lines)


def run_all_evaluations(
    *,
    output_dir: Path,
    output_name: str = "skills-readiness",
    overwrite: bool = False,
) -> SkillRunResult:
    """Run every built-in skill evaluation and persist a consolidated report."""
    results: list[SkillRunResult] = []
    for skill_name, runner in EVALUATION_RUNNERS:
        results.append(
            runner(
                output_dir=output_dir,
                output_name=f"{skill_name}-readiness",
                overwrite=overwrite,
            )
        )

    markdown = render_readiness_markdown(results)
    output_path = build_output_path(output_dir, "readiness", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)

    failed_skills = [result.skill_name for result in results if result.metadata.get("warning_count", 0) != 0]
    return SkillRunResult(
        skill_name="readiness",
        output_path=output_path,
        summary=f"Readiness suite completed: {len(results) - len(failed_skills)}/{len(results)} skills passed.",
        metadata=build_run_metadata(
            artifact_type="readiness_report",
            subject="skills",
            subject_type="toolkit",
            warning_count=len(failed_skills),
            extra={
                "skill_count": len(results),
                "passed_skill_count": len(results) - len(failed_skills),
                "failed_skills": failed_skills,
            },
        ),
    )
