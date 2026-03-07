# doc_writer Examples

## CLI
```bash
python -m ai_skills_toolkit doc-writer --repo-path . --title "Onboarding Guide" --output-name onboarding-doc
```

Without setup checklist:
```bash
python -m ai_skills_toolkit doc-writer \
  --repo-path . \
  --title "Architecture Handoff Notes" \
  --audience "Platform engineers" \
  --no-setup-checklist \
  --output-name platform-handoff
```

## Python API
```python
from pathlib import Path
from ai_skills_toolkit.skills.doc_writer import DocWriterInput, run

result = run(
    DocWriterInput(
        repo_path=Path("."),
        title="Engineering Primer",
        audience="Backend and platform engineers",
    ),
    output_dir=Path("generated"),
    output_name="engineering-primer",
)
print(result.summary)
```

Expected output location:
- `generated/doc_writer/<output-name>.md`
