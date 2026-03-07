# architecture_designer Examples

## CLI
```bash
python -m ai_skills_toolkit architecture-designer \
  --product-name "Ops Control Center" \
  --product-goal "Enable operations teams to monitor and resolve incidents quickly." \
  --primary-user "SRE" \
  --primary-user "Support Engineer" \
  --functional-requirement "Incident dashboard" \
  --functional-requirement "Rule-based escalation" \
  --non-functional-requirement "99.9% uptime" \
  --constraint "Single cloud region in phase 1"
```

## Python API
```python
from pathlib import Path
from ai_skills_toolkit.skills.architecture_designer import ArchitectureDesignerInput, run

result = run(
    ArchitectureDesignerInput(
        product_name="Revenue Intelligence Hub",
        product_goal="Give finance managers reliable daily metrics and anomaly alerts.",
        primary_users=["Finance manager", "Ops analyst"],
        functional_requirements=["KPI dashboard", "Alert triage", "CSV export"],
        non_functional_requirements=["99.9% uptime", "<400ms p95 dashboard API"],
    ),
    output_dir=Path("generated"),
    output_name="revenue-intel-architecture",
)
print(result.output_path)
```

Expected output location:
- `generated/architecture_designer/<output-name>.md`
