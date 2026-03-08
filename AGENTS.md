## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file.

### Available skills
- `code-reviewer`: Run the local ai-skills-toolkit code reviewer against a repository and return a prioritized heuristic review report. Use when the user asks for a review with the Code Reviewer skill, `code-reviewer`, or `CodeReviewer`. (file: C:/Users/amoor/.codex/skills/code-reviewer/SKILL.md)
- `codereviewer`: Alias for `code-reviewer`. Use when the user explicitly asks for `CodeReviewer`. (file: C:/Users/amoor/.codex/skills/codereviewer/SKILL.md)

### How to use skills
- If the user names one of these skills or asks to review code with the toolkit-backed Code Reviewer flow, open the referenced `SKILL.md` and follow it.
- Prefer `code-reviewer` as the canonical skill and `codereviewer` as the compatibility alias.
