from __future__ import annotations

from pathlib import Path
import subprocess

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
    rule_ids = {finding.rule_id for finding in report.findings}
    assert "Bare except" in titles
    assert "Use of eval" in titles
    assert "python.bare-except" in rule_ids
    assert "python.eval" in rule_ids


def test_code_reviewer_writes_output(sample_repo: Path, tmp_path: Path) -> None:
    output = run(
        CodeReviewerInput(repo_path=sample_repo),
        output_dir=tmp_path / "generated",
        output_name="code-review",
    )
    text = output.output_path.read_text(encoding="utf-8")
    assert "# Code Review Report" in text
    assert "## Risk Overview" in text
    assert "## Top Risk Clusters" in text
    assert "## Findings" in text
    assert "## Coverage" in text
    assert "## Assumptions" in text
    assert "Category:" in text
    assert "Scope:" in text
    assert "Impact:" in text
    assert "Recommended fix:" in text


def test_code_reviewer_ignores_tokens_inside_strings_and_cli_prints(sample_repo: Path) -> None:
    module = sample_repo / "src" / "notes.py"
    module.write_text(
        'MESSAGE = "TODO eval(assert value) except: pass"\n'
        "def describe():\n"
        "    return MESSAGE\n",
        encoding="utf-8",
    )
    cli_module = sample_repo / "src" / "cli.py"
    cli_module.write_text(
        "def main():\n"
        "    print('intentional cli output')\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))
    findings_by_path = {finding.path: finding.title for finding in report.findings}

    assert "src/notes.py" not in findings_by_path
    assert "src/cli.py" not in findings_by_path


def test_code_reviewer_reports_todo_only_in_comments(sample_repo: Path) -> None:
    module = sample_repo / "src" / "todo_module.py"
    module.write_text(
        "def work():\n"
        "    value = 'TODO in string should be ignored'\n"
        "    # TODO: implement retries\n"
        "    return value\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))
    todo_findings = [finding for finding in report.findings if finding.title == "Unresolved TODO/FIXME"]

    assert len(todo_findings) == 1
    assert todo_findings[0].path == "src/todo_module.py"
    assert todo_findings[0].category == "maintainability"
    assert todo_findings[0].scope == "single-file"
    assert todo_findings[0].occurrence_count == 1
    assert todo_findings[0].fix_complexity == "small"


def test_code_reviewer_skips_hidden_and_cache_directories(sample_repo: Path) -> None:
    hidden_dir = sample_repo / ".hidden"
    cache_dir = sample_repo / ".pytest_cache"
    hidden_dir.mkdir()
    cache_dir.mkdir()
    (hidden_dir / "risky.py").write_text("eval('1 + 1')\n", encoding="utf-8")
    (cache_dir / "risky.py").write_text("eval('1 + 1')\n", encoding="utf-8")

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))

    assert not any(finding.path.endswith("risky.py") for finding in report.findings)


def test_code_reviewer_detects_mutable_defaults_subprocess_shell_and_network_timeouts(sample_repo: Path) -> None:
    module = sample_repo / "src" / "ops.py"
    module.write_text(
        "import requests\n"
        "import subprocess\n\n"
        "def bad(items=[]):\n"
        "    requests.get('https://example.com')\n"
        "    subprocess.run('echo hi', shell=True)\n"
        "    return items\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))
    rule_ids = {finding.rule_id for finding in report.findings if finding.path == "src/ops.py"}

    assert "python.mutable-default-arg" in rule_ids
    assert "python.network-no-timeout" in rule_ids
    assert "python.subprocess-shell-true" in rule_ids


def test_code_reviewer_detects_broad_exception_handler(sample_repo: Path) -> None:
    module = sample_repo / "src" / "broad_except.py"
    module.write_text(
        "def handle():\n"
        "    try:\n"
        "        return 1\n"
        "    except Exception:\n"
        "        return 0\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))
    matching = [finding for finding in report.findings if finding.path == "src/broad_except.py"]

    assert any(finding.rule_id == "python.broad-except-exception" for finding in matching)


def test_code_reviewer_detects_service_scope_command_mismatch(sample_repo: Path) -> None:
    module = sample_repo / "src" / "ai_skills_toolkit" / "skills" / "deploy_helper"
    module.mkdir(parents=True)
    (module / "skill.py").write_text(
        "def _detect_files(repo, service_path=None):\n"
        "    return []\n\n"
        "def _commands_for_platform(platform, app_name, manifest_commands):\n"
        "    return ['docker build -t app:latest .', 'vercel --prod']\n\n"
        "def generate_deploy_plan(data):\n"
        "    repo = data.repo_path.resolve()\n"
        "    detected_files = _detect_files(repo, service_path=data.service_path)\n"
        "    manifest_commands = []\n"
        "    commands = _commands_for_platform(platform, data.app_name, manifest_commands)\n"
        "    return commands\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))

    assert any(finding.rule_id == "deploy.service-path-command-scope-mismatch" for finding in report.findings)


def test_code_reviewer_detects_path_traversal_validation_gap(sample_repo: Path) -> None:
    module = sample_repo / "src" / "ai_skills_toolkit" / "skills" / "deploy_helper"
    module.mkdir(parents=True, exist_ok=True)
    (module / "schema.py").write_text(
        "def validate_service_path(value):\n"
        "    normalized = value.replace('\\\\', '/').strip().strip('/')\n"
        "    if not normalized:\n"
        "        raise ValueError('empty')\n"
        "    if normalized.startswith('.'):\n"
        "        raise ValueError('bad')\n"
        "    return normalized\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))

    assert any(finding.rule_id == "validation.path-traversal-parent-segments" for finding in report.findings)


def test_code_reviewer_detects_hidden_ci_signal_mismatch(sample_repo: Path) -> None:
    skill_module = sample_repo / "src" / "ai_skills_toolkit" / "skills" / "repo_analyzer"
    skill_module.mkdir(parents=True)
    (skill_module / "schema.py").write_text(
        "class RepoAnalyzerInput:\n"
        "    include_hidden: bool = False\n",
        encoding="utf-8",
    )
    (skill_module / "skill.py").write_text(
        "def analyze_repository(data):\n"
        "    files, total_dirs = _iter_repo_files(repo_path, data.include_hidden)\n"
        "    return _detect_tooling_signals(files)\n\n"
        "def _detect_tooling_signals(files):\n"
        "    return ['GitHub Actions CI/CD (`.github/workflows`)']\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))

    assert any(finding.rule_id == "repo.hidden-ci-signal-mismatch" for finding in report.findings)


def test_code_reviewer_skips_hidden_ci_mismatch_when_direct_workflow_probe_exists(sample_repo: Path) -> None:
    skill_module = sample_repo / "src" / "ai_skills_toolkit" / "skills" / "repo_analyzer"
    skill_module.mkdir(parents=True)
    (skill_module / "schema.py").write_text(
        "class RepoAnalyzerInput:\n"
        "    include_hidden: bool = False\n",
        encoding="utf-8",
    )
    (skill_module / "skill.py").write_text(
        "def _has_github_workflows(repo_path):\n"
        "    return True\n\n"
        "def analyze_repository(data):\n"
        "    files, total_dirs = _iter_repo_files(repo_path, data.include_hidden)\n"
        "    return _detect_tooling_signals(repo_path, files)\n\n"
        "def _detect_tooling_signals(repo_path, files):\n"
        "    if _has_github_workflows(repo_path):\n"
        "        return ['GitHub Actions CI/CD (`.github/workflows`)']\n"
        "    return []\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))

    assert not any(finding.rule_id == "repo.hidden-ci-signal-mismatch" for finding in report.findings)


def test_code_reviewer_detects_manifest_selection_ambiguity(sample_repo: Path) -> None:
    module = sample_repo / "src" / "ai_skills_toolkit" / "skills" / "deploy_helper"
    module.mkdir(parents=True, exist_ok=True)
    (module / "skill.py").write_text(
        "from pathlib import Path\n\n"
        "def _manifest_paths(repo_path: Path, detected_files: list[str]):\n"
        '    pyproject = next((repo_path / item for item in detected_files if Path(item).name == "pyproject.toml"), None)\n'
        '    package_json = next((repo_path / item for item in detected_files if Path(item).name == "package.json"), None)\n'
        "    return pyproject, package_json\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))

    assert any(finding.rule_id == "deploy.manifest-selection-ambiguity" for finding in report.findings)


def test_code_reviewer_clusters_duplicate_findings_and_records_evidence(sample_repo: Path) -> None:
    module = sample_repo / "src" / "todo_cluster.py"
    module.write_text(
        "def work():\n"
        "    # TODO: first item\n"
        "    value = 1\n"
        "    # TODO: second item\n"
        "    return value\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))
    todo_findings = [finding for finding in report.findings if finding.rule_id == "repo.todo-fixme"]

    assert len(todo_findings) == 1
    assert todo_findings[0].occurrence_count == 2
    assert len(todo_findings[0].evidence) == 2


def test_code_reviewer_output_includes_cluster_and_evidence_details(sample_repo: Path, tmp_path: Path) -> None:
    module = sample_repo / "src" / "ops.py"
    module.write_text(
        "import requests\n\n"
        "def call_once():\n"
        "    requests.get('https://example.com/one')\n\n"
        "def call_twice():\n"
        "    requests.get('https://example.com/two')\n",
        encoding="utf-8",
    )

    output = run(
        CodeReviewerInput(repo_path=sample_repo),
        output_dir=tmp_path / "generated",
        output_name="code-review-golden",
    )
    text = output.output_path.read_text(encoding="utf-8")

    assert "Occurrences clustered: 2" in text
    assert "Evidence:" in text
    assert "Category: `operability`" in text
    assert "Scope: `runtime`" in text
    assert "Likelihood: `high`" in text
    assert output.metadata["review_coverage_mode"] == "ast+token+semantic"
    assert "src/ops.py" in output.metadata["top_risk_areas"]


def test_code_reviewer_builds_risk_clusters_and_coverage(sample_repo: Path) -> None:
    deploy_module = sample_repo / "src" / "ai_skills_toolkit" / "skills" / "deploy_helper"
    deploy_module.mkdir(parents=True, exist_ok=True)
    (deploy_module / "schema.py").write_text(
        "def validate_service_path(value):\n"
        "    normalized = value.replace('\\\\', '/').strip().strip('/')\n"
        "    if normalized.startswith('.'):\n"
        "        raise ValueError('bad')\n"
        "    return normalized\n",
        encoding="utf-8",
    )
    (deploy_module / "skill.py").write_text(
        "def _detect_files(repo, service_path=None):\n"
        "    return []\n\n"
        "def _commands_for_platform(platform, app_name, manifest_commands):\n"
        "    return []\n\n"
        "def generate_deploy_plan(data):\n"
        "    repo = data.repo_path.resolve()\n"
        "    detected_files = _detect_files(repo, service_path=data.service_path)\n"
        "    manifest_commands = []\n"
        "    commands = _commands_for_platform(platform, data.app_name, manifest_commands)\n"
        "    return commands\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=sample_repo, include_tests=False))

    assert report.review_mode == "ast+token+semantic"
    assert report.coverage["ast_rules"] is True
    assert report.coverage["semantic_rules"] is True
    assert report.assumptions
    assert any(cluster.cluster_id == "scoped-deploy-integrity" for cluster in report.top_risk_clusters)


def test_code_reviewer_changed_only_uses_git_diff_context(tmp_path: Path) -> None:
    repo = tmp_path / "git_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True, text=True)
    (repo / "src").mkdir()
    (repo / "src" / "tracked.py").write_text("def stable():\n    return 1\n", encoding="utf-8")
    (repo / "src" / "other.py").write_text("def other():\n    return 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True, capture_output=True, text=True)

    (repo / "src" / "tracked.py").write_text(
        "def stable():\n"
        "    # TODO: changed path\n"
        "    return 1\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=repo, changed_only=True))

    assert any(finding.path == "src/tracked.py" for finding in report.findings)
    assert not any(finding.path == "src/other.py" for finding in report.findings)
    assert report.coverage["diff_aware"] is True
    assert report.coverage["import_graph_context"] is True
    assert report.review_mode == "ast+token+semantic+diff+graph"


def test_code_reviewer_changed_only_expands_to_import_graph_neighbors(tmp_path: Path) -> None:
    repo = tmp_path / "git_repo_graph"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True, text=True)
    (repo / "src").mkdir()
    (repo / "src" / "pkg").mkdir()
    (repo / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "src" / "core.py").write_text("def stable():\n    return 1\n", encoding="utf-8")
    (repo / "src" / "pkg" / "consumer.py").write_text(
        "from core import stable\n"
        "import requests\n\n"
        "def use_it():\n"
        "    return stable()\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True, capture_output=True, text=True)

    (repo / "src" / "core.py").write_text(
        "def stable():\n"
        "    # TODO: changed core\n"
        "    return 1\n",
        encoding="utf-8",
    )
    (repo / "src" / "pkg" / "consumer.py").write_text(
        "from core import stable\n"
        "import requests\n\n"
        "def use_it():\n"
        "    requests.get('https://example.com')\n"
        "    return stable()\n",
        encoding="utf-8",
    )

    report = review_repository(CodeReviewerInput(repo_path=repo, changed_only=True, diff_context_hops=1))

    assert any(finding.path == "src/core.py" for finding in report.findings)
    assert any(finding.path == "src/pkg/consumer.py" for finding in report.findings)
    assert any(finding.rule_id == "python.network-no-timeout" for finding in report.findings)
