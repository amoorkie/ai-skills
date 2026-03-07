"""Implementation for deploy_helper."""

from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.core.io import build_output_path, safe_write_text
from ai_skills_toolkit.core.models import SkillRunResult
from ai_skills_toolkit.skills.deploy_helper.schema import DeployHelperInput, DeployPlan

PLATFORM_MARKERS: dict[str, tuple[str, ...]] = {
    "cloudflare": ("wrangler.toml",),
    "vercel": ("vercel.json",),
    "render": ("render.yaml", "render.yml"),
    "docker": ("Dockerfile", "docker-compose.yml", "docker-compose.yaml"),
}


def _detect_files(repo_path: Path) -> list[str]:
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
        "requirements.txt",
    }
    found: list[str] = []
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_path).as_posix()
        if path.name in wanted and rel.count("/") <= 3:
            found.append(rel)
    return sorted(set(found))


def _resolve_platform(selected: str, detected_files: list[str]) -> str:
    if selected != "auto":
        return selected
    names = {Path(item).name for item in detected_files}
    for platform, markers in PLATFORM_MARKERS.items():
        if any(marker in names for marker in markers):
            return platform
    return "generic"


def _commands_for_platform(platform: str, app_name: str) -> list[str]:
    if platform == "docker":
        return [
            f"docker build -t {app_name}:latest .",
            f"docker run --rm -p 8000:8000 --env-file .env {app_name}:latest",
        ]
    if platform == "render":
        return [
            "# Ensure render.yaml is present and connected to your repo.",
            "git push origin main",
            "# Trigger deploy in Render dashboard or via Blueprint sync.",
        ]
    if platform == "vercel":
        return [
            "npm i -g vercel",
            "vercel --prod",
        ]
    if platform == "cloudflare":
        return [
            "npm i -g wrangler",
            "wrangler deploy",
        ]
    return [
        "python -m pip install -r requirements.txt  # if present",
        "python -m ai_skills_toolkit repo-analyzer --repo-path .",
        "# Configure target platform deployment command.",
    ]


def _default_checklist(platform: str, environment: str) -> list[str]:
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
    return checklist


def generate_deploy_plan(data: DeployHelperInput) -> DeployPlan:
    """Inspect repository and produce a deployment plan with platform-aware commands."""
    repo = data.repo_path.resolve()
    detected_files = _detect_files(repo)
    platform = _resolve_platform(data.platform, detected_files)
    commands = _commands_for_platform(platform, data.app_name)
    checklist = _default_checklist(platform, data.environment)
    env_vars = sorted(set(data.required_env_vars))
    notes: list[str] = []
    if not detected_files:
        notes.append("No common deployment marker files detected; using generic plan.")
    return DeployPlan(
        repository=str(repo),
        platform=platform,
        detected_files=detected_files,
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
        metadata={"platform": plan.platform, "repository": plan.repository},
    )

