from __future__ import annotations

from pathlib import Path

import pytest

from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput, analyze_repository, run


def test_repo_analyzer_inspects_local_repo(sample_repo: Path) -> None:
    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo))
    assert analysis.total_files >= 3
    assert analysis.has_git_dir is True
    assert analysis.project_kind == "python_cli"
    assert analysis.test_file_count == 0
    assert "Python" in analysis.language_breakdown
    assert "src/main.py" in analysis.entrypoints
    assert any("pyproject.toml" in signal for signal in analysis.tooling_signals)
    assert analysis.manifest_summary
    assert analysis.dependency_surface
    assert analysis.runtime_surface
    assert analysis.service_map
    assert analysis.boundary_hotspots
    assert analysis.internal_module_graph
    assert analysis.hotspot_ranking
    assert analysis.observed_signals
    assert analysis.inferred_characteristics
    assert analysis.assumed_defaults
    assert analysis.confidence in {"medium", "high"}
    assert any(item.path.endswith("src/main.py") for item in analysis.largest_files)


def test_repo_analyzer_no_silent_overwrite(sample_repo: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "generated"
    run(
        RepoAnalyzerInput(repo_path=sample_repo),
        output_dir=output_dir,
        output_name="report",
        overwrite=False,
    )
    with pytest.raises(FileExistsError):
        run(
            RepoAnalyzerInput(repo_path=sample_repo),
            output_dir=output_dir,
            output_name="report",
            overwrite=False,
        )


def test_repo_analyzer_excludes_hidden_files_by_default(sample_repo: Path) -> None:
    hidden_file = sample_repo / ".env"
    hidden_file.write_text("KEY=value\n", encoding="utf-8")
    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo, include_hidden=False))
    assert not any(stat.path == ".env" for stat in analysis.largest_files)


def test_repo_analyzer_counts_tests_and_detects_frontend_projects(sample_repo: Path) -> None:
    tests_dir = sample_repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (sample_repo / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (sample_repo / "src" / "main.tsx").write_text("export const App = () => null;\n", encoding="utf-8")

    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo))

    assert analysis.test_file_count == 1
    assert analysis.project_kind in {"frontend_app", "multi_language_toolkit", "python_cli"}


def test_repo_analyzer_detects_github_actions_even_when_hidden_files_are_excluded(sample_repo: Path) -> None:
    workflows_dir = sample_repo / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: ci\n", encoding="utf-8")

    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo, include_hidden=False))

    assert any(".github/workflows" in signal for signal in analysis.tooling_signals)


def test_repo_analyzer_can_classify_monorepos_and_manifest_details(sample_repo: Path) -> None:
    api_dir = sample_repo / "services" / "api"
    web_dir = sample_repo / "services" / "web"
    api_dir.mkdir(parents=True)
    web_dir.mkdir(parents=True)
    (api_dir / "pyproject.toml").write_text("[project]\nname='api'\n", encoding="utf-8")
    (web_dir / "package.json").write_text('{"name":"web","scripts":{"build":"vite build"}}\n', encoding="utf-8")

    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo))

    assert analysis.project_kind == "monorepo"
    assert any("Node package `web`" in item for item in analysis.manifest_summary)
    assert any("multiple deployable services" in item.lower() for item in analysis.inferred_characteristics)


def test_repo_analyzer_exposes_internal_graph_and_ranked_hotspots(sample_repo: Path) -> None:
    package_dir = sample_repo / "src" / "app"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "service.py").write_text(
        "from app import helpers\n"
        "from app import models\n\n"
        "def run():\n"
        "    return helpers.load() + models.VALUE\n",
        encoding="utf-8",
    )
    (package_dir / "helpers.py").write_text("def load():\n    return 1\n", encoding="utf-8")
    (package_dir / "models.py").write_text("VALUE = 2\n", encoding="utf-8")

    analysis = analyze_repository(RepoAnalyzerInput(repo_path=sample_repo))

    assert any("fan-out" in item for item in analysis.internal_module_graph)
    assert any("score" in item for item in analysis.hotspot_ranking)
