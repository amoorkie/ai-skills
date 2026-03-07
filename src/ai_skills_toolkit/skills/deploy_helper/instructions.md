# deploy_helper Instructions

## Purpose
Generate an actionable deployment plan for a local repository with platform-aware guidance.

## Inputs
- `repo_path`
- `platform` (`auto`, `generic`, `docker`, `render`, `vercel`, `cloudflare`)
- `environment`
- `app_name`
- `required_env_vars`

## Output Contract
- Save markdown to `/generated/deploy_helper/`
- Never overwrite existing files silently
- Include checklist, commands, environment variables, and rollback notes

## Platform Detection
When `platform=auto`, detect from known files:
- `wrangler.toml` -> Cloudflare
- `vercel.json` -> Vercel
- `render.yaml`/`render.yml` -> Render
- `Dockerfile`/`docker-compose*` -> Docker
- otherwise -> Generic deployment plan

