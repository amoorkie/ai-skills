from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.deploy_helper import DeployHelperInput
from ai_skills_toolkit.skills.deploy_helper import run as run_deploy_helper
from ai_skills_toolkit.skills.doc_writer import DocWriterInput
from ai_skills_toolkit.skills.doc_writer import run as run_doc_writer
from ai_skills_toolkit.skills.prompt_debugger import PromptDebuggerInput
from ai_skills_toolkit.skills.prompt_debugger import run as run_prompt_debugger
from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput
from ai_skills_toolkit.skills.repo_analyzer import run as run_repo_analyzer
from ai_skills_toolkit.skills.test_generator import TestGeneratorInput as TGInput
from ai_skills_toolkit.skills.test_generator import run as run_test_generator


def test_repo_analysis_and_doc_writer_artifacts_reflect_repository_signals(
    sample_repo: Path, tmp_path: Path
) -> None:
    tests_dir = sample_repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (sample_repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (sample_repo / ".github" / "workflows").mkdir(parents=True)
    (sample_repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")

    repo_result = run_repo_analyzer(
        RepoAnalyzerInput(repo_path=sample_repo),
        output_dir=tmp_path / "generated",
        output_name="repo-artifact",
    )
    doc_result = run_doc_writer(
        DocWriterInput(
            repo_path=sample_repo,
            title="Platform Guide",
            audience="Platform engineers",
        ),
        output_dir=tmp_path / "generated",
        output_name="doc-artifact",
    )

    repo_text = repo_result.output_path.read_text(encoding="utf-8")
    doc_text = doc_result.output_path.read_text(encoding="utf-8")

    assert "## Observed Signals" in repo_text
    assert "## Inferred Characteristics" in repo_text
    assert "## Manifest Summary" in repo_text
    assert "## Runtime Surface" in repo_text
    assert "## Dependency Surface" in repo_text
    assert "## Service Map" in repo_text
    assert "## Boundary Hotspots" in repo_text
    assert "## Internal Module Graph" in repo_text
    assert "## Hotspot Ranking" in repo_text
    assert "## Runtime Signals" in repo_text
    assert "- **Project kind:** `python_cli`" in repo_text
    assert "- **Confidence:** `high`" in repo_text
    assert "Docker container build" in repo_text
    assert "- **Test files discovered:** `1`" in repo_text

    assert "## Audience Guidance" in doc_text
    assert "Validate packaging, CI, test entrypoints, and deployment markers" in doc_text
    assert "Verify container build assumptions before relying on local runtime parity." in doc_text
    assert "Deployment and container operations runbook" in doc_text


def test_deploy_helper_artifact_uses_manifest_hints(sample_repo: Path, tmp_path: Path) -> None:
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
    (sample_repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")

    result = run_deploy_helper(
        DeployHelperInput(repo_path=sample_repo, platform="docker", app_name="sample-app"),
        output_dir=tmp_path / "generated",
        output_name="deploy-artifact",
    )
    text = result.output_path.read_text(encoding="utf-8")

    assert "## Manifest Signals" in text
    assert "Python project metadata detected" in text
    assert "Node scripts detected" in text
    assert '`python -m pip install -e ".[dev]"`' in text
    assert "`python -m pytest`" in text
    assert "`npm run build`" in text
    assert '`docker build -t sample-app:latest "."`' in text


def test_prompt_debugger_artifact_localizes_and_specializes_variants(
    tmp_path: Path,
) -> None:
    result = run_prompt_debugger(
        PromptDebuggerInput(
            prompt=(
                "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u044c \u043f\u043b\u0430\u043d "
                "\u0434\u0435\u043f\u043b\u043e\u044f \u0441 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430\u043c\u0438, "
                "\u0432\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u0435\u0439 \u0438 \u043e\u0442\u043a\u0430\u0442\u043e\u043c. "
                "\u0424\u043e\u0440\u043c\u0430\u0442 \u043e\u0442\u0432\u0435\u0442\u0430: markdown."
            )
        ),
        output_dir=tmp_path / "generated",
        output_name="prompt-artifact",
    )
    text = result.output_path.read_text(encoding="utf-8")

    assert "## Improved Prompt Variants" in text
    assert "\u0424\u043e\u0440\u043c\u0430\u0442 \u043e\u0442\u0432\u0435\u0442\u0430" in text
    assert "\u043e\u0442\u043a\u0430\u0442" in text.lower()
    assert result.metadata["language"] == "ru"
    assert result.metadata["task_type"] == "deployment"


def test_test_generator_artifact_includes_priority_reasoning_and_concrete_ideas(
    sample_repo: Path, tmp_path: Path
) -> None:
    (sample_repo / "src" / "cli.py").write_text(
        "import requests\n\n"
        "def main():\n"
        "    requests.get('https://example.com')\n"
        "    return 0\n",
        encoding="utf-8",
    )
    (sample_repo / "src" / "schemas.py").write_text(
        "class Payload:\n"
        "    value: str\n",
        encoding="utf-8",
    )

    result = run_test_generator(
        TGInput(repo_path=sample_repo, focus_paths=["cli.py"]),
        output_dir=tmp_path / "generated",
        output_name="test-generator-artifact",
    )
    text = result.output_path.read_text(encoding="utf-8")

    assert "Priority score:" in text
    assert "Why this is high priority:" in text
    assert "Suggested test types:" in text
    assert "Concrete test ideas:" in text
    assert "Matches focus path `cli.py`." in text
    assert "Mock outbound network calls" in text
    assert result.metadata["top_target_paths"][0] == "src/cli.py"
