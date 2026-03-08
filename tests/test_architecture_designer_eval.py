from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.architecture_designer.eval import evaluate_cases, run_builtin_evaluation
from ai_skills_toolkit.skills.architecture_designer.eval_corpus import build_builtin_eval_cases


def test_architecture_designer_eval_corpus_meets_readiness_thresholds() -> None:
    summary = evaluate_cases(build_builtin_eval_cases())

    assert len(summary.case_results) >= 3
    assert summary.overall_recall >= 0.90
    assert summary.pass_rate >= 0.95


def test_architecture_designer_eval_writes_markdown(tmp_path: Path) -> None:
    result = run_builtin_evaluation(output_dir=tmp_path / "generated", output_name="eval")
    text = result.output_path.read_text(encoding="utf-8")

    assert "# Architecture Designer Evaluation" in text
    assert "Overall recall" in text
    assert result.metadata["overall_recall"] >= 0.90
