from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.prompt_debugger.eval import evaluate_cases, run_builtin_evaluation
from ai_skills_toolkit.skills.prompt_debugger.eval_corpus import build_builtin_eval_cases


def test_prompt_debugger_eval_corpus_meets_readiness_thresholds() -> None:
    summary = evaluate_cases(build_builtin_eval_cases())

    assert len(summary.case_results) >= 4
    assert summary.overall_language_accuracy >= 0.95
    assert summary.overall_task_accuracy >= 0.95
    assert summary.overall_recall >= 0.90
    assert summary.average_noise_rate <= 0.10
    assert summary.pass_rate >= 0.95


def test_prompt_debugger_eval_writes_markdown(tmp_path: Path) -> None:
    result = run_builtin_evaluation(output_dir=tmp_path / "generated", output_name="eval")
    text = result.output_path.read_text(encoding="utf-8")

    assert "# Prompt Debugger Evaluation" in text
    assert "Overall language accuracy" in text
    assert result.metadata["overall_task_accuracy"] >= 0.95
