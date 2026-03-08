from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.doc_writer.eval import evaluate_cases, run_builtin_evaluation
from ai_skills_toolkit.skills.doc_writer.eval_corpus import build_builtin_eval_cases


def test_doc_writer_eval_corpus_meets_readiness_thresholds(tmp_path: Path) -> None:
    cases = build_builtin_eval_cases(tmp_path / "corpus")
    summary = evaluate_cases(cases)

    assert len(summary.case_results) >= 4
    assert summary.overall_fragment_recall >= 0.95
    assert summary.average_noise_rate <= 0.10
    assert summary.pass_rate >= 0.95


def test_doc_writer_eval_writes_markdown(tmp_path: Path) -> None:
    result = run_builtin_evaluation(output_dir=tmp_path / "generated", output_name="eval")
    text = result.output_path.read_text(encoding="utf-8")

    assert "# Doc Writer Evaluation" in text
    assert "Overall fragment recall" in text
    assert result.metadata["overall_fragment_recall"] >= 0.95
