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


def test_test_generator_prioritizes_behavior_heavy_modules(sample_repo: Path) -> None:
    heavy = sample_repo / "src" / "service.py"
    heavy.write_text(
        "class Service:\n"
        "    def run(self, value):\n"
        "        if value < 0:\n"
        "            raise ValueError('bad')\n"
        "        return helper(value)\n\n"
        "def helper(value):\n"
        "    if value:\n"
        "        return value * 2\n"
        "    return 0\n",
        encoding="utf-8",
    )
    tiny = sample_repo / "src" / "schema.py"
    tiny.write_text(
        "class Payload:\n"
        "    pass\n",
        encoding="utf-8",
    )

    result = generate_test_plan(TGInput(repo_path=sample_repo, max_targets=5))

    assert result.targets[0].path == "src/service.py"
    assert result.targets[0].target_type == "stateful-service"
    assert result.targets[0].priority_score > result.targets[1].priority_score
    assert any("branching" == test_type for test_type in result.targets[0].suggested_test_types)
    assert any("public API surface" in idea for idea in result.targets[0].test_ideas)


def test_test_generator_ignores_false_risk_markers_in_strings(sample_repo: Path) -> None:
    module = sample_repo / "src" / "risk_strings.py"
    module.write_text(
        "def describe():\n"
        "    text = 'bypass TODO except: sample'\n"
        "    return text\n",
        encoding="utf-8",
    )

    result = generate_test_plan(TGInput(repo_path=sample_repo, max_targets=5))
    target = next(item for item in result.targets if item.path == "src/risk_strings.py")

    assert target.risk_notes == []


def test_test_generator_detects_real_risk_markers(sample_repo: Path) -> None:
    module = sample_repo / "src" / "risky_flow.py"
    module.write_text(
        "def handle():\n"
        "    try:\n"
        "        return 1\n"
        "    except:\n"
        "        pass\n"
        "    # TODO: add metrics\n",
        encoding="utf-8",
    )

    result = generate_test_plan(TGInput(repo_path=sample_repo, max_targets=5))
    target = next(item for item in result.targets if item.path == "src/risky_flow.py")

    assert "Contains bare except blocks." in target.risk_notes
    assert "Contains TODO/FIXME markers." in target.risk_notes
    assert "Contains pass statements; behavior may be incomplete." in target.risk_notes


def test_test_generator_prioritizes_integration_and_entrypoint_modules(sample_repo: Path) -> None:
    cli_module = sample_repo / "src" / "cli.py"
    cli_module.write_text(
        "import requests\n"
        "import subprocess\n\n"
        "def main():\n"
        "    requests.get('https://example.com')\n"
        "    subprocess.run(['echo', 'hi'])\n"
        "    return 0\n",
        encoding="utf-8",
    )
    utility_module = sample_repo / "src" / "helpers.py"
    utility_module.write_text(
        "def normalize(value):\n"
        "    return value.strip()\n",
        encoding="utf-8",
    )

    result = generate_test_plan(TGInput(repo_path=sample_repo, max_targets=5))
    cli_target = next(target for target in result.targets if target.path == "src/cli.py")
    utility_target = next(target for target in result.targets if target.path == "src/helpers.py")

    assert cli_target.target_type == "entrypoint"
    assert cli_target.priority_score > utility_target.priority_score
    assert "cli" in cli_target.suggested_test_types
    assert "integration-boundary" in cli_target.suggested_test_types
    assert any("Mock outbound network calls" in idea for idea in cli_target.test_ideas)


def test_test_generator_focus_path_overrides_default_order(sample_repo: Path) -> None:
    heavy = sample_repo / "src" / "service.py"
    heavy.write_text(
        "def alpha(value):\n"
        "    if value < 0:\n"
        "        raise ValueError('bad')\n"
        "    return value\n",
        encoding="utf-8",
    )
    focused = sample_repo / "src" / "billing.py"
    focused.write_text(
        "def create_invoice(value):\n"
        "    return value\n",
        encoding="utf-8",
    )

    result = generate_test_plan(TGInput(repo_path=sample_repo, max_targets=5, focus_paths=["billing.py"]))

    assert result.targets[0].path == "src/billing.py"
    assert any("Matches focus path `billing.py`." == reason for reason in result.targets[0].priority_reasons)


def test_test_generator_skips_hidden_and_cache_directories(sample_repo: Path) -> None:
    hidden_dir = sample_repo / ".hidden"
    cache_dir = sample_repo / ".pytest_cache"
    hidden_dir.mkdir()
    cache_dir.mkdir()
    (hidden_dir / "shadow.py").write_text("def hidden():\n    return 1\n", encoding="utf-8")
    (cache_dir / "cached.py").write_text("def cached():\n    return 1\n", encoding="utf-8")

    result = generate_test_plan(TGInput(repo_path=sample_repo, max_targets=10))
    paths = {target.path for target in result.targets}

    assert ".hidden/shadow.py" not in paths
    assert ".pytest_cache/cached.py" not in paths


def test_test_generator_output_includes_priority_reasons_and_test_ideas(sample_repo: Path, tmp_path: Path) -> None:
    module = sample_repo / "src" / "ops.py"
    module.write_text(
        "import requests\n\n"
        "def fetch_data():\n"
        "    requests.get('https://example.com')\n"
        "    return 1\n",
        encoding="utf-8",
    )

    output = run(
        TGInput(repo_path=sample_repo, include_edge_cases=True),
        output_dir=tmp_path / "generated",
        output_name="test-plan-rich",
    )
    text = output.output_path.read_text(encoding="utf-8")

    assert "Priority score:" in text
    assert "Why this is high priority:" in text
    assert "Suggested test types:" in text
    assert "Concrete test ideas:" in text
    assert "Mock outbound network calls" in text
    assert output.metadata["top_target_paths"][0] == "src/ops.py"
