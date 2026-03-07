# figma_ui_architect Examples

## CLI
```bash
python -m ai_skills_toolkit figma-ui-architect \
  --product-name "Partner Admin Console" \
  --product-goal "Help partner operations teams triage and resolve account exceptions faster." \
  --user "Partner Ops Manager" \
  --user "Support Specialist" \
  --jtbd "When exception volume rises, I need prioritized queues so SLA misses are reduced." \
  --constraint "Desktop-first, tablet fallback only"
```

## Python API
```python
from pathlib import Path
from ai_skills_toolkit.skills.figma_ui_architect import FigmaUiArchitectInput, run

result = run(
    FigmaUiArchitectInput(
        product_name="Fleet Command Dashboard",
        product_goal="Enable logistics managers to monitor incidents and dispatch actions in one place.",
        users=["Fleet manager", "Dispatcher"],
        jtbds=["When incidents spike, I need fast prioritization so SLAs are protected."],
        constraints=["Must support role-based visibility", "Desktop-first for operations center screens"],
    ),
    output_dir=Path("generated"),
    output_name="fleet-command-ui-architecture",
)
print(result.output_path)
```

Expected output location:
- `generated/figma_ui_architect/<output-name>.md`
