# code_reviewer Examples

## CLI
```bash
python -m ai_skills_toolkit code-reviewer --repo-path . --output-name review-baseline
```

Review including tests and ignore low-severity findings:
```bash
python -m ai_skills_toolkit code-reviewer \
  --repo-path . \
  --include-tests \
  --no-low-severity \
  --max-findings 50
```

## Python API
```python
from pathlib import Path

from ai_skills_toolkit.skills.code_reviewer import CodeReviewerInput, run

result = run(
    CodeReviewerInput(
        repo_path=Path("."),
        include_tests=False,
        include_low_severity=True,
    ),
    output_dir=Path("generated"),
    output_name="code-review",
)
print(result.output_path)
```

