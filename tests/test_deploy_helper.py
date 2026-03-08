from __future__ import annotations

from pathlib import Path

import pytest

from ai_skills_toolkit.skills.deploy_helper import DeployHelperInput, generate_deploy_plan, run


def test_deploy_helper_auto_detects_platform(sample_repo: Path) -> None:
    (sample_repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    plan = generate_deploy_plan(DeployHelperInput(repo_path=sample_repo, platform="auto"))
    assert plan.platform == "docker"
    assert plan.candidate_platforms == ["docker"]
    assert any("Dockerfile" in item for item in plan.detected_files)


def test_deploy_helper_writes_output(sample_repo: Path, tmp_path: Path) -> None:
    output = run(
        DeployHelperInput(repo_path=sample_repo, platform="generic", app_name="sample-app"),
        output_dir=tmp_path / "generated",
        output_name="deploy-plan",
    )
    text = output.output_path.read_text(encoding="utf-8")
    assert "# Deployment Helper Plan" in text
    assert "## Suggested Commands" in text
    assert "## Manifest Signals" in text


def test_deploy_helper_detects_deep_marker_files(sample_repo: Path) -> None:
    service_dir = sample_repo / "apps" / "web" / "frontend"
    service_dir.mkdir(parents=True)
    (service_dir / "vercel.json").write_text('{"version": 2}\n', encoding="utf-8")

    plan = generate_deploy_plan(DeployHelperInput(repo_path=sample_repo, platform="auto"))

    assert plan.platform == "vercel"
    assert "apps/web/frontend/vercel.json" in plan.detected_files


def test_deploy_helper_returns_generic_plan_for_ambiguous_auto_detection(sample_repo: Path) -> None:
    (sample_repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (sample_repo / "vercel.json").write_text('{"version": 2}\n', encoding="utf-8")

    plan = generate_deploy_plan(DeployHelperInput(repo_path=sample_repo, platform="auto"))

    assert plan.platform == "generic"
    assert set(plan.candidate_platforms) == {"docker", "vercel"}
    assert any("Multiple deployment platform markers detected" in note for note in plan.notes)


def test_deploy_helper_can_prefer_platform_when_auto_detection_is_ambiguous(sample_repo: Path) -> None:
    (sample_repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (sample_repo / "vercel.json").write_text('{"version": 2}\n', encoding="utf-8")

    plan = generate_deploy_plan(
        DeployHelperInput(
            repo_path=sample_repo,
            platform="auto",
            prefer_platform="vercel",
        )
    )

    assert plan.platform == "vercel"
    assert any("preferred platform: vercel" in note for note in plan.notes)


def test_deploy_helper_can_scope_detection_to_service_path(sample_repo: Path) -> None:
    api_dir = sample_repo / "services" / "api"
    web_dir = sample_repo / "services" / "web"
    api_dir.mkdir(parents=True)
    web_dir.mkdir(parents=True)
    (api_dir / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (web_dir / "vercel.json").write_text('{"version": 2}\n', encoding="utf-8")

    plan = generate_deploy_plan(
        DeployHelperInput(
            repo_path=sample_repo,
            platform="auto",
            service_path="services/web",
        )
    )

    assert plan.platform == "vercel"
    assert plan.detected_files == ["services/web/vercel.json"]
    assert any("Detection scope limited to `services/web`." in note for note in plan.notes)
    assert 'vercel --cwd "services/web" --prod' in plan.commands


def test_deploy_helper_skips_hidden_and_cache_marker_files(sample_repo: Path) -> None:
    hidden_dir = sample_repo / ".hidden"
    cache_dir = sample_repo / ".pytest_cache"
    hidden_dir.mkdir()
    cache_dir.mkdir()
    (hidden_dir / "vercel.json").write_text('{"version": 2}\n', encoding="utf-8")
    (cache_dir / "render.yaml").write_text("services: []\n", encoding="utf-8")

    plan = generate_deploy_plan(DeployHelperInput(repo_path=sample_repo, platform="auto"))

    assert plan.platform == "generic"
    assert plan.candidate_platforms == []
    assert ".hidden/vercel.json" not in plan.detected_files
    assert ".pytest_cache/render.yaml" not in plan.detected_files


def test_deploy_helper_uses_pyproject_and_package_scripts_when_present(sample_repo: Path) -> None:
    (sample_repo / "package.json").write_text(
        '{'
        '"name":"sample",'
        '"scripts":{"build":"vite build","test":"vitest","start":"node server.js"}'
        '}',
        encoding="utf-8",
    )
    (sample_repo / "pyproject.toml").write_text(
        "[project]\n"
        "name='sample-app'\n"
        "[project.optional-dependencies]\n"
        "dev=['pytest>=8']\n"
        "[project.scripts]\n"
        "sample-app='sample_app.cli:main'\n"
        "[tool.pytest.ini_options]\n"
        "testpaths=['tests']\n",
        encoding="utf-8",
    )

    plan = generate_deploy_plan(DeployHelperInput(repo_path=sample_repo, platform="generic"))

    assert "python -m pip install -e \".[dev]\"" in plan.commands
    assert "python -m pytest" in plan.commands
    assert "python -m sample_app.cli --help" in plan.commands
    assert "npm install" in plan.commands
    assert "npm run build" in plan.commands
    assert "npm run test" in plan.commands
    assert any("Python project metadata detected" in signal for signal in plan.manifest_signals)
    assert any("Node scripts detected" in signal for signal in plan.manifest_signals)


def test_deploy_helper_rejects_parent_directory_service_paths(sample_repo: Path) -> None:
    with pytest.raises(ValueError):
        DeployHelperInput(repo_path=sample_repo, service_path="services/../../other")


def test_deploy_helper_scopes_manifest_commands_and_docker_context(sample_repo: Path) -> None:
    api_dir = sample_repo / "services" / "api"
    api_dir.mkdir(parents=True)
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

    plan = generate_deploy_plan(
        DeployHelperInput(repo_path=sample_repo, platform="docker", service_path="services/api", app_name="api")
    )

    assert 'python -m pip install -e "./services/api[dev]"' in plan.commands
    assert 'python -m pytest "services/api"' in plan.commands
    assert 'npm --prefix "services/api" install' in plan.commands
    assert 'npm --prefix "services/api" run build' in plan.commands
    assert 'docker build -t api:latest "services/api"' in plan.commands


def test_deploy_helper_reports_manifest_ambiguity_without_service_scope(sample_repo: Path) -> None:
    api_dir = sample_repo / "services" / "api"
    web_dir = sample_repo / "services" / "web"
    api_dir.mkdir(parents=True)
    web_dir.mkdir(parents=True)
    (api_dir / "pyproject.toml").write_text("[project]\nname='api'\n", encoding="utf-8")
    (web_dir / "pyproject.toml").write_text("[project]\nname='web'\n", encoding="utf-8")
    (api_dir / "package.json").write_text('{"name":"api"}\n', encoding="utf-8")
    (web_dir / "package.json").write_text('{"name":"web"}\n', encoding="utf-8")

    plan = generate_deploy_plan(DeployHelperInput(repo_path=sample_repo, platform="generic"))

    assert any("Multiple `pyproject.toml` files detected" in note for note in plan.notes)
    assert any("Multiple `package.json` files detected" in note for note in plan.notes)
