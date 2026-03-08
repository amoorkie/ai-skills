"""Built-in evaluation corpus for repo_analyzer."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.repo_analyzer.eval_types import EvaluationCase


def _build_python_cli_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    (repo / "src" / "main.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    return EvaluationCase(
        name="python-cli-signals",
        repo_path=repo,
        expected_project_kind="python_cli",
        expected_entrypoints={"src/main.py"},
        expected_tooling_signals={"Python packaging manifest (`pyproject.toml`)"},
    )


def _build_frontend_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "package.json").write_text('{"name":"frontend"}\n', encoding="utf-8")
    (repo / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (repo / "src" / "main.tsx").write_text("export const App = () => null;\n", encoding="utf-8")
    return EvaluationCase(
        name="frontend-app-signals",
        repo_path=repo,
        expected_project_kind="frontend_app",
        expected_tooling_signals={"Node package manifest (`package.json`)"},
    )


def _build_hidden_ci_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("def app():\n    return 1\n", encoding="utf-8")
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    return EvaluationCase(
        name="hidden-ci-signal-visible",
        repo_path=repo,
        include_hidden=False,
        expected_project_kind="python_service",
        expected_entrypoints={"src/app.py"},
        expected_tooling_signals={"GitHub Actions CI/CD (`.github/workflows`)"},
    )


def _build_hidden_file_exclusion_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "README.md").write_text("# Sample\n", encoding="utf-8")
    (repo / "src" / "main.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
    return EvaluationCase(
        name="hidden-files-excluded-from-largest-list",
        repo_path=repo,
        include_hidden=False,
        expected_project_kind="python_cli",
        expected_entrypoints={"src/main.py"},
        forbidden_largest_paths={".env"},
    )


def build_builtin_eval_cases(root: Path) -> list[EvaluationCase]:
    """Create the built-in evaluation corpus under the provided root directory."""
    root.mkdir(parents=True, exist_ok=True)
    return [
        _build_python_cli_case(root / "case_python_cli"),
        _build_frontend_case(root / "case_frontend"),
        _build_hidden_ci_case(root / "case_hidden_ci"),
        _build_hidden_file_exclusion_case(root / "case_hidden_files"),
    ]
