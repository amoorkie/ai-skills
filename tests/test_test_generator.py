from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.test_generator import TestGeneratorInput as TGInput
from ai_skills_toolkit.skills.test_generator import generate_test_plan, run


def test_test_generator_discovers_python_targets(sample_repo: Path) -> None:
    module = sample_repo / "src" / "calc.py"
    module.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    result = generate_test_plan(TGInput(repo_path=sample_repo, max_targets=10))
    assert result.targets
    assert any(target.path.endswith("src/calc.py") for target in result.targets)


def test_test_generator_writes_markdown(sample_repo: Path, tmp_path: Path) -> None:
    output = run(
        TGInput(repo_path=sample_repo, include_edge_cases=True),
        output_dir=tmp_path / "generated",
        output_name="test-plan",
    )
    text = output.output_path.read_text(encoding="utf-8")
    assert "## Target Matrix" in text
    assert "## Pytest Starter Template" in text
