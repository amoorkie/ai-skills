# test_generator Examples

## CLI
```bash
python -m ai_skills_toolkit test-generator --repo-path . --output-name baseline-test-plan
```

Focus on specific module paths:
```bash
python -m ai_skills_toolkit test-generator \
  --repo-path . \
  --focus-path "src/ai_skills_toolkit/core" \
  --focus-path "src/ai_skills_toolkit/cli.py" \
  --max-targets 10
```

## Python API
```python
from pathlib import Path

from ai_skills_toolkit.skills.test_generator import TestGeneratorInput, run

result = run(
    TestGeneratorInput(
        repo_path=Path("."),
        focus_paths=["src/ai_skills_toolkit/skills"],
        include_edge_cases=True,
    ),
    output_dir=Path("generated"),
    output_name="skills-test-plan",
)
print(result.output_path)
```

