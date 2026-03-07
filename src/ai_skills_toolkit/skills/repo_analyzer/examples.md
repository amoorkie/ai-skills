# repo_analyzer Examples

## CLI
```bash
python -m ai_skills_toolkit repo-analyzer --repo-path . --output-name my-repo-scan
```

With hidden files and higher scan cap:
```bash
python -m ai_skills_toolkit repo-analyzer \
  --repo-path . \
  --include-hidden \
  --max-files 20000 \
  --largest-file-count 20 \
  --output-name deep-scan
```

## Python API
```python
from pathlib import Path
from ai_skills_toolkit.skills.repo_analyzer import RepoAnalyzerInput, run

result = run(
    RepoAnalyzerInput(repo_path=Path("."), max_files=10000),
    output_dir=Path("generated"),
    output_name="baseline-scan",
)
print(result.output_path)
```

Expected output location:
- `generated/repo_analyzer/<output-name>.md`
