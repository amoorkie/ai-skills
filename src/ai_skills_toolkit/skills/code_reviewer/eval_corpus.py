"""Built-in evaluation corpus for code_reviewer."""

from __future__ import annotations

from pathlib import Path
import subprocess

from ai_skills_toolkit.skills.code_reviewer.eval_types import EvaluationCase


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True, text=True)


def _build_ast_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "risky.py").write_text(
        "import requests\n\n"
        "def f(x, items=[]):\n"
        "    requests.get('https://example.com')\n"
        "    return eval(x)\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="ast-risk-patterns",
        repo_path=repo,
        expected_rule_ids={
            "python.eval",
            "python.mutable-default-arg",
            "python.network-no-timeout",
        },
    )


def _build_semantic_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    module = repo / "src" / "ai_skills_toolkit" / "skills" / "deploy_helper"
    module.mkdir(parents=True)
    (module / "schema.py").write_text(
        "def validate_service_path(value):\n"
        "    normalized = value.replace('\\\\', '/').strip().strip('/')\n"
        "    if normalized.startswith('.'):\n"
        "        raise ValueError('bad')\n"
        "    return normalized\n",
        encoding="utf-8",
    )
    (module / "skill.py").write_text(
        "from pathlib import Path\n\n"
        "def _manifest_paths(repo_path: Path, detected_files: list[str]):\n"
        '    pyproject = next((repo_path / item for item in detected_files if Path(item).name == "pyproject.toml"), None)\n'
        '    package_json = next((repo_path / item for item in detected_files if Path(item).name == "package.json"), None)\n'
        "    return pyproject, package_json\n\n"
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
    return EvaluationCase(
        name="semantic-deploy-contracts",
        repo_path=repo,
        expected_rule_ids={
            "validation.path-traversal-parent-segments",
            "deploy.service-path-command-scope-mismatch",
            "deploy.manifest-selection-ambiguity",
        },
        expected_cluster_ids={"scoped-deploy-integrity"},
    )


def _build_diff_graph_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    _init_git_repo(repo)
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
    return EvaluationCase(
        name="diff-graph-context",
        repo_path=repo,
        expected_rule_ids={"repo.todo-fixme", "python.network-no-timeout"},
        input_overrides={"changed_only": True, "diff_context_hops": 1},
    )


def _build_subprocess_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "ops.py").write_text(
        "import subprocess\n\n"
        "def deploy():\n"
        "    subprocess.run('echo hi', shell=True)\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="subprocess-shell-risk",
        repo_path=repo,
        expected_rule_ids={"python.subprocess-shell-true"},
    )


def _build_bare_except_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "handler.py").write_text(
        "def handle():\n"
        "    try:\n"
        "        return 1\n"
        "    except:\n"
        "        return 0\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="bare-except-risk",
        repo_path=repo,
        expected_rule_ids={"python.bare-except"},
        expected_cluster_ids={"error-boundary-handling"},
    )


def _build_hidden_ci_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    module = repo / "src" / "ai_skills_toolkit" / "skills" / "repo_analyzer"
    module.mkdir(parents=True)
    (module / "schema.py").write_text(
        "class RepoAnalyzerInput:\n"
        "    include_hidden: bool = False\n",
        encoding="utf-8",
    )
    (module / "skill.py").write_text(
        "def analyze_repository(data):\n"
        "    files, total_dirs = _iter_repo_files(repo_path, data.include_hidden)\n"
        "    return _detect_tooling_signals(files)\n\n"
        "def _detect_tooling_signals(files):\n"
        "    return ['GitHub Actions CI/CD (`.github/workflows`)']\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="hidden-ci-signal-drift",
        repo_path=repo,
        expected_rule_ids={"repo.hidden-ci-signal-mismatch"},
        expected_cluster_ids={"operational-signal-integrity"},
    )


def _build_clean_cli_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "cli.py").write_text(
        "def main():\n"
        "    print('normal cli output')\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="clean-cli-no-finding",
        repo_path=repo,
        forbidden_rule_ids={"python.print-debug", "python.broad-except-exception", "python.bare-except"},
    )


def _build_safe_network_case(repo: Path) -> EvaluationCase:
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "http_client.py").write_text(
        "import requests\n\n"
        "def fetch():\n"
        "    return requests.get('https://example.com', timeout=5)\n",
        encoding="utf-8",
    )
    return EvaluationCase(
        name="safe-network-no-finding",
        repo_path=repo,
        forbidden_rule_ids={"python.network-no-timeout"},
    )


def build_builtin_eval_cases(root: Path) -> list[EvaluationCase]:
    """Create the built-in evaluation corpus under the provided root directory."""
    return [
        _build_ast_case(root / "case_ast"),
        _build_semantic_case(root / "case_semantic"),
        _build_diff_graph_case(root / "case_diff"),
        _build_subprocess_case(root / "case_subprocess"),
        _build_bare_except_case(root / "case_bare_except"),
        _build_hidden_ci_case(root / "case_hidden_ci"),
        _build_clean_cli_case(root / "case_clean_cli"),
        _build_safe_network_case(root / "case_safe_network"),
    ]
