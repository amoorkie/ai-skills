# prompt_debugger Examples

## CLI
```bash
python -m ai_skills_toolkit prompt-debugger --prompt "Build a login API quickly." --goal "Ship safely"
```

Prompt with explicit context and model target:
```bash
python -m ai_skills_toolkit prompt-debugger \
  --prompt "Create a deployment runbook for staged rollouts with rollback criteria and output format." \
  --goal "Minimize incident risk during release" \
  --context "Small platform team, weekly deploys, strict audit trail" \
  --target-model "gpt-5"
```

## Python API
```python
from pathlib import Path
from ai_skills_toolkit.skills.prompt_debugger import PromptDebuggerInput, run

result = run(
    PromptDebuggerInput(
        prompt="Create a deployment plan for our service.",
        goal="Reduce incidents during rollout",
        context="Small team, weekly releases",
    ),
    output_dir=Path("generated"),
    output_name="deployment-plan-prompt-debug",
)
print(result.output_path)
```

Expected output location:
- `generated/prompt_debugger/<output-name>.md`
