from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.deploy_helper.eval import evaluate_cases, run_builtin_evaluation
from ai_skills_toolkit.skills.deploy_helper.eval_corpus import build_builtin_eval_cases


def test_deploy_helper_eval_corpus_meets_readiness_thresholds(tmp_path: Path) -> None:
    cases = build_builtin_eval_cases(tmp_path / "corpus")
    summary = evaluate_cases(cases)

    assert len(summary.case_results) >= 4
    assert summary.overall_platform_accuracy >= 0.95
    assert summary.overall_recall >= 0.95
    assert summary.average_noise_rate <= 0.10
    assert summary.pass_rate >= 0.95


def test_deploy_helper_eval_writes_markdown(tmp_path: Path) -> None:
    result = run_builtin_evaluation(output_dir=tmp_path / "generated", output_name="eval")
    text = result.output_path.read_text(encoding="utf-8")

    assert "# Deploy Helper Evaluation" in text
    assert "Overall platform accuracy" in text
    assert result.metadata["overall_recall"] >= 0.95
