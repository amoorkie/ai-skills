"""Built-in evaluation corpus for deploy_helper."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.deploy_helper.eval_types import EvaluationCase


def _build_docker_auto_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    return EvaluationCase(
        name="docker-auto-detect",
        repo_path=repo,
        input_overrides={"platform": "auto", "app_name": "sample-app"},
        expected_platform="docker",
        expected_detected_files={"Dockerfile"},
        expected_commands={
            'docker build -t sample-app:latest "."',
            'docker run --rm -p 8000:8000 --env-file ".env" sample-app:latest',
        },
    )


def _build_ambiguous_auto_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (repo / "vercel.json").write_text('{"version": 2}\n', encoding="utf-8")
    return EvaluationCase(
        name="ambiguous-auto-falls-back-to-generic",
        repo_path=repo,
        input_overrides={"platform": "auto"},
        expected_platform="generic",
        expected_detected_files={"Dockerfile", "vercel.json"},
        expected_notes={"Multiple deployment platform markers detected"},
    )


def _build_scoped_service_case(repo: Path) -> EvaluationCase:
    api_dir = repo / "services" / "api"
    api_dir.mkdir(parents=True)
    (repo / ".git").mkdir()
    (api_dir / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (api_dir / "package.json").write_text(
        '{"name":"api","scripts":{"build":"vite build","test":"vitest"}}',
        encoding="utf-8",
    )
    (api_dir / "pyproject.toml").write_text(
        "[project]\n"
        "name='api'\n"
        "[project.optional-dependencies]\n"
        "dev=['pytest>=8']\n"
        "[tool.pytest.ini_options]\n"
        "testpaths=['tests']\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="service-scope-propagates-into-commands",
        repo_path=repo,
        input_overrides={"platform": "docker", "service_path": "services/api", "app_name": "api"},
        expected_platform="docker",
        expected_detected_files={"services/api/Dockerfile", "services/api/package.json", "services/api/pyproject.toml"},
        expected_commands={
            'python -m pip install -e "./services/api[dev]"',
            'python -m pytest "services/api"',
            'npm --prefix "services/api" install',
            'npm --prefix "services/api" run build',
            'docker build -t api:latest "services/api"',
        },
        expected_notes={"Detection scope limited to `services/api`."},
        forbidden_commands={
            'npm install',
            'npm run build',
            'docker build -t api:latest "."',
        },
    )


def _build_manifest_hints_case(repo: Path) -> EvaluationCase:
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "package.json").write_text(
        '{'
        '"name":"sample",'
        '"scripts":{"build":"vite build","test":"vitest","start":"node server.js"}'
        '}',
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        "[project]\n"
        "name='sample-app'\n"
        "[project.optional-dependencies]\n"
        "dev=['pytest>=8']\n"
        "[project.scripts]\n"
        "sample_app='sample_app.cli:main'\n"
        "[tool.pytest.ini_options]\n"
        "testpaths=['tests']\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="manifest-signals-produce-commands",
        repo_path=repo,
        input_overrides={"platform": "generic"},
        expected_platform="generic",
        expected_commands={
            'python -m pip install -e ".[dev]"',
            "python -m pytest",
            "python -m sample_app.cli --help",
            "npm install",
            "npm run build",
            "npm run test",
            "npm run start",
        },
        expected_manifest_signals={
            "Python project metadata detected (`pyproject.toml`)",
            "Node scripts detected (`package.json`)",
        },
    )


def build_builtin_eval_cases(root: Path) -> list[EvaluationCase]:
    """Create the built-in evaluation corpus under the provided root directory."""
    root.mkdir(parents=True, exist_ok=True)
    return [
        _build_docker_auto_case(root / "case_docker_auto"),
        _build_ambiguous_auto_case(root / "case_ambiguous_auto"),
        _build_scoped_service_case(root / "case_scoped_service"),
        _build_manifest_hints_case(root / "case_manifest_hints"),
    ]
