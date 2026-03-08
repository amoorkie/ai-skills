"""Implementation for deploy_helper."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult, build_run_metadata
from ai_skills_toolkit.core.repo_scan import DEFAULT_EXCLUDED_DIRS, iter_repo_files
from ai_skills_toolkit.skills.deploy_helper.schema import DeployHelperInput, DeployPlan

PLATFORM_MARKERS: dict[str, tuple[str, ...]] = {
    "cloudflare": ("wrangler.toml",),
    "vercel": ("vercel.json",),
    "render": ("render.yaml", "render.yml"),
    "docker": ("Dockerfile", "docker-compose.yml", "docker-compose.yaml"),
}


def _detect_files(repo_path: Path, service_path: str | None = None) -> list[str]:
    wanted = {
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "render.yaml",
        "render.yml",
        "vercel.json",
        "wrangler.toml",
        "Procfile",
        "pyproject.toml",
        "package.json",
        "requirements.txt",
    }
    base_path = repo_path if service_path is None else repo_path / service_path
    if not base_path.exists() or not base_path.is_dir():
        return []
    found, _ = iter_repo_files(
        repo_path,
        scan_root=base_path,
        include_hidden=False,
        excluded_dirs=DEFAULT_EXCLUDED_DIRS,
        file_filter=lambda path: path.name in wanted,
    )
    return sorted({path.relative_to(repo_path).as_posix() for path in found})


def _candidate_platforms(detected_files: list[str]) -> list[str]:
    names = {Path(item).name for item in detected_files}
    candidates: list[str] = []
    for platform, markers in PLATFORM_MARKERS.items():
        if any(marker in names for marker in markers):
            candidates.append(platform)
    return candidates


def _resolve_platform(selected: str, candidates: list[str], prefer_platform: str | None) -> tuple[str, list[str]]:
    notes: list[str] = []
    if selected != "auto":
        return selected, notes
    if prefer_platform and prefer_platform in candidates:
        notes.append(f"Auto-detect ambiguity resolved via preferred platform: {prefer_platform}.")
        return prefer_platform, notes
    if len(candidates) == 1:
        return candidates[0], notes
    if len(candidates) > 1:
        notes.append(
            "Multiple deployment platform markers detected; generated a generic plan to avoid choosing the wrong target."
        )
        notes.append(
            "Set `platform`, `prefer_platform`, or `service_path` to scope the deployment plan to a specific service."
        )
        return "generic", notes
    return "generic", notes


def _load_toml(path: Path) -> dict:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _scoped_command(command: str, service_path: str | None) -> str:
    if not service_path:
        return command
    if command == "npm install":
        return f'npm --prefix "{service_path}" install'
    if command.startswith("npm run "):
        return command.replace("npm run ", f'npm --prefix "{service_path}" run ', 1)
    if command.startswith("python -m pip install -e "):
        if '".[dev]"' in command:
            return f'python -m pip install -e "./{service_path}[dev]"'
        return f'python -m pip install -e "./{service_path}"'
    if command == "python -m pytest":
        return f'python -m pytest "{service_path}"'
    if command.startswith("python -m ") and command.endswith(" --help"):
        return f'cd "{service_path}" && {command}'
    return command


def _manifest_paths(
    repo_path: Path,
    detected_files: list[str],
    *,
    service_path: str | None,
) -> tuple[Path | None, Path | None, list[str]]:
    notes: list[str] = []
    pyprojects = [repo_path / item for item in detected_files if Path(item).name == "pyproject.toml"]
    package_jsons = [repo_path / item for item in detected_files if Path(item).name == "package.json"]

    pyproject: Path | None = pyprojects[0] if len(pyprojects) == 1 else None
    package_json: Path | None = package_jsons[0] if len(package_jsons) == 1 else None

    if len(pyprojects) > 1 and service_path is None:
        notes.append("Multiple `pyproject.toml` files detected; scoped Python command hints require `service_path`.")
    if len(package_jsons) > 1 and service_path is None:
        notes.append("Multiple `package.json` files detected; scoped Node command hints require `service_path`.")
    return pyproject, package_json, notes


def _manifest_signals(
    repo_path: Path,
    detected_files: list[str],
    *,
    service_path: str | None,
) -> tuple[list[str], list[str], list[str]]:
    signals: list[str] = []
    commands: list[str] = []
    pyproject_path, package_json_path, notes = _manifest_paths(
        repo_path,
        detected_files,
        service_path=service_path,
    )

    if pyproject_path and pyproject_path.exists():
        pyproject = _load_toml(pyproject_path)
        project = pyproject.get("project", {})
        optional_dependencies = project.get("optional-dependencies", {})
        scripts = project.get("scripts", {})
        tool_section = pyproject.get("tool", {})

        if project.get("name"):
            signals.append(f"Python project metadata detected (`{pyproject_path.relative_to(repo_path).as_posix()}`)")
        if optional_dependencies.get("dev"):
            commands.append(_scoped_command('python -m pip install -e ".[dev]"', service_path))
            signals.append("Python dev dependency group detected (`project.optional-dependencies.dev`)")
        else:
            commands.append(_scoped_command("python -m pip install -e .", service_path))
        if "pytest" in tool_section:
            commands.append(_scoped_command("python -m pytest", service_path))
            signals.append("Pytest configuration detected (`tool.pytest`)")
        elif any("pytest" in str(item).lower() for item in optional_dependencies.get("dev", [])):
            commands.append(_scoped_command("python -m pytest", service_path))
        if scripts:
            module_name = next(iter(scripts.values()), "").split(":", maxsplit=1)[0]
            if module_name:
                commands.append(_scoped_command(f"python -m {module_name} --help", service_path))
            signals.append(f"Python CLI entrypoints detected ({len(scripts)} configured)")

    if package_json_path and package_json_path.exists():
        package_json = _load_json(package_json_path)
        scripts = package_json.get("scripts", {})
        if scripts:
            signals.append(f"Node scripts detected (`{package_json_path.relative_to(repo_path).as_posix()}`)")
            commands.append(_scoped_command("npm install", service_path))
            for script_name in ("build", "test", "start", "dev"):
                if script_name in scripts:
                    commands.append(_scoped_command(f"npm run {script_name}", service_path))
    return signals, commands, notes


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _commands_for_platform(
    platform: str,
    app_name: str,
    manifest_commands: list[str],
    *,
    service_path: str | None,
) -> list[str]:
    commands: list[str] = []
    if platform == "docker":
        commands.extend(
            [
            f'docker build -t {app_name}:latest "{service_path or "."}"',
            f'docker run --rm -p 8000:8000 --env-file "{(service_path + "/.env") if service_path else ".env"}" {app_name}:latest',
            ]
        )
    elif platform == "render":
        commands.extend(
            [
            f'# Ensure render.yaml is present and connected to your repo{f" under {service_path}" if service_path else ""}.',
            "git push origin main",
            "# Trigger deploy in Render dashboard or via Blueprint sync.",
            ]
        )
    elif platform == "vercel":
        commands.extend(
            [
            "npm i -g vercel",
            f'vercel {"--cwd " + chr(34) + service_path + chr(34) + " " if service_path else ""}--prod'.strip(),
            ]
        )
    elif platform == "cloudflare":
        commands.extend(
            [
            "npm i -g wrangler",
            f'wrangler {"--cwd " + chr(34) + service_path + chr(34) + " " if service_path else ""}deploy'.strip(),
            ]
        )
    else:
        commands.extend(
            [
                f'python -m pip install -r "{(service_path + "/requirements.txt") if service_path else "requirements.txt"}"  # if present',
                f'python -m ai_skills_toolkit repo-analyzer --repo-path .{f"  # inspect service path: {service_path}" if service_path else ""}',
                "# Configure target platform deployment command.",
            ]
        )
    return _dedupe(manifest_commands + commands)


def _default_checklist(platform: str, environment: str, manifest_signals: list[str]) -> list[str]:
    checklist = [
        f"Confirm target environment: {environment}",
        "Validate build and test pipeline on current commit",
        "Ensure required secrets are configured in deployment platform",
        "Run pre-deploy smoke checks",
        "Deploy and verify health checks",
        "Monitor logs/metrics for at least 15 minutes after release",
        "Prepare rollback path and owner",
    ]
    if platform in {"render", "vercel", "cloudflare"}:
        checklist.insert(1, "Confirm project is linked to correct cloud account/team")
    if any("Node scripts detected" in signal for signal in manifest_signals):
        checklist.insert(2, "Verify package manager lockfile and npm script assumptions before deploy")
    if any("Python project metadata detected" in signal for signal in manifest_signals):
        checklist.insert(2, "Confirm Python install/test commands from project metadata still match CI")
    return checklist


def generate_deploy_plan(data: DeployHelperInput) -> DeployPlan:
    """Inspect repository and produce a deployment plan with platform-aware commands."""
    repo = data.repo_path.resolve()
    detected_files = _detect_files(repo, service_path=data.service_path)
    candidates = _candidate_platforms(detected_files)
    platform, notes = _resolve_platform(data.platform, candidates, data.prefer_platform)
    manifest_signals, manifest_commands, manifest_notes = _manifest_signals(
        repo,
        detected_files,
        service_path=data.service_path,
    )
    notes.extend(manifest_notes)
    commands = _commands_for_platform(
        platform,
        data.app_name,
        manifest_commands,
        service_path=data.service_path,
    )
    checklist = _default_checklist(platform, data.environment, manifest_signals)
    env_vars = sorted(set(data.required_env_vars))
    if not detected_files:
        if data.service_path:
            notes.append(f"No common deployment marker files detected under `{data.service_path}`; using generic plan.")
        else:
            notes.append("No common deployment marker files detected; using generic plan.")
    elif data.service_path:
        notes.append(f"Detection scope limited to `{data.service_path}`.")
    return DeployPlan(
        repository=str(repo),
        platform=platform,
        detected_files=detected_files,
        candidate_platforms=candidates,
        manifest_signals=manifest_signals,
        checklist=checklist,
        commands=commands,
        env_vars=env_vars,
        notes=notes,
    )


def render_markdown(plan: DeployPlan, app_name: str, environment: str) -> str:
    """Render deployment plan into markdown."""
    lines: list[str] = []
    lines.append("# Deployment Helper Plan")
    lines.append("")
    lines.append(f"- **Repository:** `{plan.repository}`")
    lines.append(f"- **Application:** `{app_name}`")
    lines.append(f"- **Environment:** `{environment}`")
    lines.append(f"- **Platform:** `{plan.platform}`")
    lines.append("")
    if plan.candidate_platforms:
        lines.append("## Candidate Platforms")
        lines.append("")
        lines.extend([f"- `{item}`" for item in plan.candidate_platforms])
        lines.append("")
    if plan.manifest_signals:
        lines.append("## Manifest Signals")
        lines.append("")
        lines.extend([f"- {item}" for item in plan.manifest_signals])
        lines.append("")
    lines.append("## Detected Deployment Files")
    lines.append("")
    if plan.detected_files:
        lines.extend([f"- `{item}`" for item in plan.detected_files])
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Pre-Deployment Checklist")
    lines.append("")
    lines.extend([f"- {item}" for item in plan.checklist])
    lines.append("")
    lines.append("## Suggested Commands")
    lines.append("")
    lines.extend([f"- `{cmd}`" for cmd in plan.commands])
    lines.append("")
    lines.append("## Environment Variables")
    lines.append("")
    if plan.env_vars:
        lines.extend([f"- `{item}`" for item in plan.env_vars])
    else:
        lines.append("- Define required variables for your runtime and secrets provider.")
    lines.append("")
    lines.append("## Rollback Notes")
    lines.append("")
    lines.append("- Keep last known-good release identifier.")
    lines.append("- Revert traffic to previous stable artifact if health checks fail.")
    lines.append("- Capture post-incident notes and add regression checks.")
    lines.append("")
    if plan.notes:
        lines.append("## Notes")
        lines.append("")
        lines.extend([f"- {item}" for item in plan.notes])
        lines.append("")
    return "\n".join(lines)


def run(
    data: DeployHelperInput,
    *,
    output_dir: Path = Path("generated"),
    output_name: str = "deployment-plan",
    overwrite: bool = False,
) -> SkillRunResult:
    """Execute deploy_helper and persist deployment markdown plan."""
    plan = generate_deploy_plan(data)
    markdown = render_markdown(plan, app_name=data.app_name, environment=data.environment)
    output_path = build_output_path(output_dir, "deploy_helper", output_name)
    safe_write_text(output_path, markdown, overwrite=overwrite)
    return SkillRunResult(
        skill_name="deploy_helper",
        output_path=output_path,
        summary=f"Deployment plan generated for platform `{plan.platform}`.",
        metadata=build_run_metadata(
            artifact_type="deployment_plan",
            subject=plan.repository,
            subject_type="repository",
            warning_count=len(plan.notes),
            extra={
                "platform": plan.platform,
                "repository": plan.repository,
                "candidate_platform_count": len(plan.candidate_platforms),
                "detected_file_count": len(plan.detected_files),
                "manifest_signal_count": len(plan.manifest_signals),
            },
        ),
    )
