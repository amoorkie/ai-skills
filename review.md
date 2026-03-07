# Review: ai-skills Toolkit Skills

- Репозиторий: `https://github.com/amoorkie/ai-skills`
- Дата ревью: 2026-03-08
- Область: `src/ai_skills_toolkit/skills/*`, `src/ai_skills_toolkit/cli.py`, тесты в `tests/*`

## Findings

### [P2] Неверная сортировка приоритета в `test_generator`

- Риск: при равном фокус-приоритете выше выбираются более мелкие файлы, что искажает список `max_targets` и снижает практическую ценность плана тестирования.
- Место: [`src/ai_skills_toolkit/skills/test_generator/skill.py#L53`](https://github.com/amoorkie/ai-skills/blob/main/src/ai_skills_toolkit/skills/test_generator/skill.py#L53)
- Деталь: используется `-p.stat().st_size` вместе с `reverse=True`, что приводит к обратному ожидаемому ранжированию по размеру.

### [P2] `code_reviewer` неустойчив к ошибкам чтения отдельных файлов

- Риск: один проблемный файл (например, `PermissionError`/`OSError`) может прервать весь отчёт ревью вместо частичного результата.
- Место: [`src/ai_skills_toolkit/skills/code_reviewer/skill.py#L92`](https://github.com/amoorkie/ai-skills/blob/main/src/ai_skills_toolkit/skills/code_reviewer/skill.py#L92)
- Деталь: `read_text(...)` вызывается без локальной обработки исключений на уровне файла.

### [P3] Ложноположительные срабатывания правила `eval(` в `code_reviewer`

- Риск: правило может ошибочно маркировать безопасные вызовы вида `ast.literal_eval(...)`, создавая шум в отчёте.
- Место: [`src/ai_skills_toolkit/skills/code_reviewer/skill.py#L43`](https://github.com/amoorkie/ai-skills/blob/main/src/ai_skills_toolkit/skills/code_reviewer/skill.py#L43)
- Деталь: используется подстрочное условие `"eval(" in stripped` без контекстной проверки токена/AST.

### [P3] Полный рекурсивный обход репозитория в `deploy_helper`

- Риск: на больших монорепозиториях ухудшается производительность из-за `rglob("*")` по всему дереву, включая тяжёлые директории.
- Место: [`src/ai_skills_toolkit/skills/deploy_helper/skill.py#L33`](https://github.com/amoorkie/ai-skills/blob/main/src/ai_skills_toolkit/skills/deploy_helper/skill.py#L33)
- Деталь: фильтрация нужных маркеров происходит после полного обхода, без исключений директорий.

## Тестовые пробелы

- В CLI smoke-тестах отсутствуют команды `doc-writer`, `architecture-designer`, `figma-ui-architect`: [`tests/test_cli.py`](https://github.com/amoorkie/ai-skills/blob/main/tests/test_cli.py)
- Нет теста, который фиксирует ошибку сортировки таргетов в `test_generator`: [`tests/test_test_generator.py`](https://github.com/amoorkie/ai-skills/blob/main/tests/test_test_generator.py)
- Нет теста на ложноположительный кейс `literal_eval` для `code_reviewer`: [`tests/test_code_reviewer.py`](https://github.com/amoorkie/ai-skills/blob/main/tests/test_code_reviewer.py)

## Summary

Приоритет исправлений:

1. Исправить сортировку таргетов в `test_generator` (P2).
2. Добавить graceful-handling ошибок чтения в `code_reviewer` (P2).
3. Снизить шум эвристики `eval(` и оптимизировать обход в `deploy_helper` (P3).
