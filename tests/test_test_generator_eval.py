from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.test_generator.eval import evaluate_cases, run_builtin_evaluation
from ai_skills_toolkit.skills.test_generator.eval_corpus import build_builtin_eval_cases


def test_test_generator_eval_corpus_meets_readiness_thresholds(tmp_path: Path) -> None:
    cases = build_builtin_eval_cases(tmp_path / "corpus")
    summary = evaluate_cases(cases)

    assert len(summary.case_results) >= 6
    assert summary.overall_target_recall >= 0.95
    assert summary.overall_top_path_accuracy >= 0.95
    assert summary.overall_test_type_recall >= 0.90
    assert summary.average_noise_rate <= 0.20
    assert summary.pass_rate >= 0.95


def test_test_generator_eval_writes_markdown(tmp_path: Path) -> None:
    result = run_builtin_evaluation(output_dir=tmp_path / "generated", output_name="eval")
    text = result.output_path.read_text(encoding="utf-8")

    assert "# Test Generator Evaluation" in text
    assert "Overall target recall" in text
    assert result.metadata["overall_top_path_accuracy"] >= 0.95
