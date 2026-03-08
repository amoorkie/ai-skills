from __future__ import annotations

from ai_skills_toolkit.skills.code_reviewer import evaluate_cases
from ai_skills_toolkit.skills.code_reviewer.eval_corpus import build_builtin_eval_cases


def test_code_reviewer_eval_corpus_has_full_expected_recall(tmp_path) -> None:
    summary = evaluate_cases(build_builtin_eval_cases(tmp_path))

    assert summary.overall_rule_recall >= 0.95
    assert summary.overall_cluster_recall >= 0.95
    assert summary.pass_rate >= 0.95
    assert len(summary.case_results) == 8
    assert sum(1 for result in summary.case_results if result.passed) >= 7


def test_code_reviewer_eval_corpus_keeps_noise_rate_bounded(tmp_path) -> None:
    summary = evaluate_cases(build_builtin_eval_cases(tmp_path))

    assert summary.average_noise_rate <= 0.12
    by_name = {result.name: result for result in summary.case_results}
    assert by_name["semantic-deploy-contracts"].found_cluster_ids == {"scoped-deploy-integrity"}
    assert by_name["clean-cli-no-finding"].forbidden_rule_hits == set()
    assert by_name["safe-network-no-finding"].forbidden_rule_hits == set()
