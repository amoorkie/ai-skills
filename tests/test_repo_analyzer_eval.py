from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.repo_analyzer.eval import evaluate_cases, run_builtin_evaluation
from ai_skills_toolkit.skills.repo_analyzer.eval_corpus import build_builtin_eval_cases


def test_repo_analyzer_eval_corpus_meets_readiness_thresholds(tmp_path: Path) -> None:
    cases = build_builtin_eval_cases(tmp_path / "corpus")
    summary = evaluate_cases(cases)

    assert len(summary.case_results) >= 4
    assert summary.overall_project_kind_accuracy >= 0.95
    assert summary.overall_signal_recall >= 0.95
    assert summary.average_noise_rate <= 0.10
    assert summary.pass_rate >= 0.95


def test_repo_analyzer_eval_writes_markdown(tmp_path: Path) -> None:
    result = run_builtin_evaluation(output_dir=tmp_path / "generated", output_name="eval")
    text = result.output_path.read_text(encoding="utf-8")

    assert "# Repo Analyzer Evaluation" in text
    assert "Overall project-kind accuracy" in text
    assert result.metadata["overall_signal_recall"] >= 0.95
