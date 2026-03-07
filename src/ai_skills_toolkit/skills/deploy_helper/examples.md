# deploy_helper Examples

## CLI
```bash
python -m ai_skills_toolkit deploy-helper --repo-path . --platform auto --app-name my-service
```

Explicit platform and required secrets:
```bash
python -m ai_skills_toolkit deploy-helper \
  --repo-path . \
  --platform docker \
  --environment production \
  --app-name my-service \
  --env-var DATABASE_URL \
  --env-var API_KEY
```

## Python API
```python
from pathlib import Path

from ai_skills_toolkit.skills.deploy_helper import DeployHelperInput, run

result = run(
    DeployHelperInput(
        repo_path=Path("."),
        platform="auto",
        app_name="ai-skills-toolkit",
        required_env_vars=["OPENAI_API_KEY"],
    ),
    output_dir=Path("generated"),
    output_name="deploy-plan",
)
print(result.output_path)
```

