"""Built-in evaluation corpus for doc_writer."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.doc_writer.eval_types import EvaluationCase


def _build_ai_agents_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "README.md").write_text("# Sample\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    (repo / "src" / "cli.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    return EvaluationCase(
        name="ai-agents-audience",
        repo_path=repo,
        title="Agent Guide",
        audience="AI agents",
        expected_fragments={
            "## Executive Summary",
            "## Audience Guidance",
            "Agent operating notes and repository navigation map",
            "Use the runtime signals, key files, and top-level structure below",
        },
    )


def _build_platform_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (repo / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    return EvaluationCase(
        name="platform-audience-with-runtime-signals",
        repo_path=repo,
        title="Platform Guide",
        audience="Platform engineers",
        expected_fragments={
            "## Setup Checklist",
            "Validate packaging, CI, test entrypoints, and deployment markers",
            "Verify container build assumptions before relying on local runtime parity.",
            "Run the detected test suite before making behavioral changes.",
            "GitHub Actions CI/CD (`.github/workflows`)",
            "Deployment and container operations runbook",
        },
    )


def _build_hidden_top_level_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "README.md").write_text("# Sample\n", encoding="utf-8")
    (repo / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    return EvaluationCase(
        name="hidden-top-level-entries-excluded",
        repo_path=repo,
        title="Repo Doc",
        audience="Engineers",
        expected_fragments={"## Top-Level Structure", "`README.md`"},
        forbidden_fragments={"`.env`"},
    )


def _build_no_setup_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("def app():\n    return 1\n", encoding="utf-8")
    return EvaluationCase(
        name="setup-checklist-can-be-skipped",
        repo_path=repo,
        title="Repo Doc",
        audience="Engineers",
        include_setup_checklist=False,
        expected_fragments={"## Suggested Next Documentation", "Domain model and glossary"},
        forbidden_fragments={"## Setup Checklist"},
    )


def build_builtin_eval_cases(root: Path) -> list[EvaluationCase]:
    """Create the built-in evaluation corpus under the provided root directory."""
    root.mkdir(parents=True, exist_ok=True)
    return [
        _build_ai_agents_case(root / "case_ai_agents"),
        _build_platform_case(root / "case_platform"),
        _build_hidden_top_level_case(root / "case_hidden"),
        _build_no_setup_case(root / "case_no_setup"),
    ]
