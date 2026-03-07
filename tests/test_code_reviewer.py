from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.code_reviewer import CodeReviewerInput, review_repository, run


def test_code_reviewer_detects_high_risk_patterns(sample_repo: Path) -> None:
    risky = sample_repo / "src" / "risky.py"
    risky.write_text(
        "def f(x):\n"
        "    try:\n"
        "        return eval(x)\n"
        "    except:\n"
        "        print('bad')\n"
        "        return None\n",
        encoding="utf-8",
    )
    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))
    titles = {finding.title for finding in report.findings}
    assert "Bare except" in titles
    assert "Use of eval" in titles


def test_code_reviewer_writes_output(sample_repo: Path, tmp_path: Path) -> None:
    output = run(
        CodeReviewerInput(repo_path=sample_repo),
        output_dir=tmp_path / "generated",
        output_name="code-review",
    )
    text = output.output_path.read_text(encoding="utf-8")
    assert "# Code Review Report" in text
    assert "## Findings" in text

