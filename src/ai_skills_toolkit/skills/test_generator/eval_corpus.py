"""Built-in evaluation corpus for test_generator."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.test_generator.eval_types import EvaluationCase


def _build_behavior_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "service.py").write_text(
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
    (repo / "src" / "schema.py").write_text(
        "class Payload:\n"
        "    pass\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="behavior-heavy-beats-schema",
        repo_path=repo,
        expected_target_paths={"src/service.py"},
        expected_top_path="src/service.py",
        expected_test_types_by_target={"src/service.py": {"contract", "branching"}},
        forbidden_target_paths={"src/schema.py"},
    )


def _build_focus_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "service.py").write_text(
        "def alpha(value):\n"
        "    if value < 0:\n"
        "        raise ValueError('bad')\n"
        "    return value\n",
        encoding="utf-8",
    )
    (repo / "src" / "billing.py").write_text(
        "def create_invoice(value):\n"
        "    return value\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="focus-path-prioritized",
        repo_path=repo,
        expected_target_paths={"src/billing.py"},
        expected_top_path="src/billing.py",
        expected_test_types_by_target={"src/billing.py": {"contract"}},
        input_overrides={"focus_paths": ["billing.py"]},
    )


def _build_entrypoint_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "cli.py").write_text(
        "import requests\n"
        "import subprocess\n\n"
        "def main():\n"
        "    requests.get('https://example.com')\n"
        "    subprocess.run(['echo', 'hi'])\n"
        "    return 0\n",
        encoding="utf-8",
    )
    (repo / "src" / "helpers.py").write_text(
        "def normalize(value):\n"
        "    return value.strip()\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="entrypoint-boundary-priority",
        repo_path=repo,
        expected_target_paths={"src/cli.py"},
        expected_top_path="src/cli.py",
        expected_test_types_by_target={"src/cli.py": {"cli", "integration-boundary", "subprocess"}},
    )


def _build_async_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "workers.py").write_text(
        "async def sync_jobs(client):\n"
        "    if client is None:\n"
        "        raise ValueError('client required')\n"
        "    return await client.fetch()\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="async-module-needs-async-tests",
        repo_path=repo,
        expected_target_paths={"src/workers.py"},
        expected_top_path="src/workers.py",
        expected_test_types_by_target={"src/workers.py": {"async", "branching"}},
    )


def _build_hidden_exclusion_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / ".hidden").mkdir()
    (repo / ".pytest_cache").mkdir()
    (repo / "src" / "service.py").write_text(
        "def run(value):\n"
        "    return value * 2\n",
        encoding="utf-8",
    )
    (repo / ".hidden" / "shadow.py").write_text(
        "def hidden():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    (repo / ".pytest_cache" / "cached.py").write_text(
        "def cached():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="hidden-and-cache-excluded",
        repo_path=repo,
        expected_target_paths={"src/service.py"},
        expected_top_path="src/service.py",
        forbidden_target_paths={".hidden/shadow.py", ".pytest_cache/cached.py"},
    )


def _build_schema_penalty_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "service.py").write_text(
        "def transform(value):\n"
        "    if not value:\n"
        "        raise ValueError('missing')\n"
        "    return value.upper()\n",
        encoding="utf-8",
    )
    (repo / "src" / "schemas.py").write_text(
        "class Payload:\n"
        "    value: str\n\n"
        "class Response:\n"
        "    ok: bool\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="schema-modules-do-not-dominate",
        repo_path=repo,
        expected_target_paths={"src/service.py"},
        expected_top_path="src/service.py",
        expected_test_types_by_target={"src/service.py": {"contract", "branching"}},
        forbidden_target_paths={"src/schemas.py"},
    )


def build_builtin_eval_cases(root: Path) -> list[EvaluationCase]:
    """Create the built-in evaluation corpus under the provided root directory."""
    root.mkdir(parents=True, exist_ok=True)
    return [
        _build_behavior_case(root / "case_behavior"),
        _build_focus_case(root / "case_focus"),
        _build_entrypoint_case(root / "case_entrypoint"),
        _build_async_case(root / "case_async"),
        _build_hidden_exclusion_case(root / "case_hidden"),
        _build_schema_penalty_case(root / "case_schema"),
    ]
