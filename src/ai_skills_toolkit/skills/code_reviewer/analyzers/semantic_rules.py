"""Cross-file and contract-level review rules."""

from __future__ import annotations

from ai_skills_toolkit.skills.code_reviewer.analyzers.common import line_number_for_pattern, make_finding
from ai_skills_toolkit.skills.code_reviewer.schema import ReviewFinding


def _semantic_service_path_scope_mismatch(rel_path: str, content: str) -> list[ReviewFinding]:
    detect_call = "_detect_files(repo, service_path=data.service_path)"
    command_call = "commands = _commands_for_platform(platform, data.app_name, manifest_commands)"
    if detect_call not in content or command_call not in content:
        return []
    return [
        make_finding(
            rule_id="deploy.service-path-command-scope-mismatch",
            severity="high",
            category="correctness",
            scope="cross-file",
            path=rel_path,
            line=line_number_for_pattern(content, command_call),
            title="Service scope is not propagated into deploy commands",
            detail=(
                "Deployment detection is scoped with `service_path`, but command generation still builds repo-root "
                "commands. In monorepos this can target the wrong build context or deploy the wrong service."
            ),
            recommendation=(
                "Pass the selected service scope into command generation and emit platform commands with an explicit "
                "working directory, prefix, or build context."
            ),
            confidence=0.97,
            impact="high",
            likelihood="high",
            blast_radius="cross-skill",
            tests_to_add=["Add deploy-helper tests that assert scoped commands use the selected service path."],
            inferred=True,
            evidence=[
                f"Scoped detection call found in `{rel_path}`: `{detect_call}`.",
                f"Command generation call still omits service scope: `{command_call}`.",
            ],
        )
    ]


def _semantic_service_path_validator_weakness(rel_path: str, content: str) -> list[ReviewFinding]:
    if "def validate_service_path" not in content:
        return []
    if "normalized.startswith(\".\")" not in content and "normalized.startswith('.')" not in content:
        return []
    if any(marker in content for marker in ("relative_to(", ".resolve(", "PurePosixPath")):
        return []
    return [
        make_finding(
            rule_id="validation.path-traversal-parent-segments",
            severity="high",
            category="security",
            scope="contract",
            path=rel_path,
            line=line_number_for_pattern(content, "def validate_service_path"),
            title="Path validator allows parent-directory traversal",
            detail=(
                "The validator rejects leading dots but does not reject parent segments later in the path. Values like "
                "`services/../../other` can still escape the intended repository subdirectory."
            ),
            recommendation=(
                "Normalize the path semantically and reject any path that contains parent segments or resolves outside "
                "the repository root."
            ),
            confidence=0.96,
            impact="high",
            likelihood="high",
            blast_radius="cross-skill",
            fix_complexity="small",
            tests_to_add=["Add validation tests for parent-directory traversal inputs like `services/../../other`."],
            inferred=True,
            evidence=[
                f"Validator normalizes string input in `{rel_path}` but only rejects leading dots.",
                "No semantic path-boundary check for later `..` segments was found.",
            ],
        )
    ]


def _semantic_hidden_ci_signal_mismatch(sources: dict[str, str]) -> list[ReviewFinding]:
    skill_path = "src/ai_skills_toolkit/skills/repo_analyzer/skill.py"
    schema_path = "src/ai_skills_toolkit/skills/repo_analyzer/schema.py"
    skill_content = sources.get(skill_path)
    schema_content = sources.get(schema_path)
    if not skill_content or not schema_content:
        return []
    if ".github/workflows" not in skill_content:
        return []
    if "_has_github_workflows(" in skill_content:
        return []
    if "include_hidden: bool = False" not in schema_content:
        return []
    if "_iter_repo_files(repo_path, data.include_hidden)" not in skill_content:
        return []
    if "whitelist" in skill_content.lower() or "allowlist" in skill_content.lower():
        return []
    return [
        make_finding(
            rule_id="repo.hidden-ci-signal-mismatch",
            severity="medium",
            category="operability",
            scope="cross-file",
            path=skill_path,
            line=line_number_for_pattern(skill_content, ".github/workflows"),
            title="Hidden CI directories are referenced but skipped by default scan policy",
            detail=(
                "The analyzer tries to infer GitHub Actions usage from `.github/workflows`, but default scans exclude "
                "hidden directories. That under-reports CI signals and can mislead downstream docs or deploy plans."
            ),
            recommendation=(
                "Scan known infrastructure directories separately or whitelist `.github` when collecting operational "
                "signals without enabling all hidden files."
            ),
            confidence=0.94,
            likelihood="high",
            blast_radius="cross-skill",
            tests_to_add=["Add analyzer tests proving GitHub Actions signals are visible in default runs."],
            affected_paths=[skill_path, schema_path],
            inferred=True,
            evidence=[
                f"`{skill_path}` references `.github/workflows` as a tooling signal.",
                f"`{schema_path}` defaults `include_hidden` to `False`.",
            ],
        )
    ]


def _semantic_manifest_selection_ambiguity(rel_path: str, content: str) -> list[ReviewFinding]:
    if "def _manifest_paths" not in content:
        return []
    pyproject_pick = 'next((repo_path / item for item in detected_files if Path(item).name == "pyproject.toml"), None)'
    package_pick = 'next((repo_path / item for item in detected_files if Path(item).name == "package.json"), None)'
    if pyproject_pick not in content and package_pick not in content:
        return []
    if "Multiple manifest" in content or "multiple manifest" in content.lower():
        return []
    return [
        make_finding(
            rule_id="deploy.manifest-selection-ambiguity",
            severity="medium",
            category="operability",
            scope="cross-file",
            path=rel_path,
            line=line_number_for_pattern(content, "def _manifest_paths"),
            title="Deploy helper picks the first manifest without disambiguating monorepos",
            detail=(
                "Manifest discovery takes the first matching `pyproject.toml` or `package.json` from detected files. "
                "In multi-service repositories that can synthesize commands from the wrong application context."
            ),
            recommendation=(
                "Detect multiple manifests explicitly and require `service_path` or emit an ambiguity note instead of "
                "silently choosing the first match."
            ),
            confidence=0.93,
            likelihood="high",
            blast_radius="cross-skill",
            tests_to_add=["Add deploy-helper tests for multiple manifests in a monorepo root scan."],
            inferred=True,
            evidence=[
                f"`{rel_path}` selects manifests with `next(...)`, which silently prefers the first match.",
                "No ambiguity handling for multiple Python or Node manifests was found in manifest selection.",
            ],
        )
    ]


def extract_semantic_findings(sources: dict[str, str]) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for rel_path, content in sources.items():
        if rel_path.endswith("skills/deploy_helper/skill.py"):
            findings.extend(_semantic_service_path_scope_mismatch(rel_path, content))
            findings.extend(_semantic_manifest_selection_ambiguity(rel_path, content))
        elif rel_path.endswith("skills/deploy_helper/schema.py"):
            findings.extend(_semantic_service_path_validator_weakness(rel_path, content))
    findings.extend(_semantic_hidden_ci_signal_mismatch(sources))
    return findings
