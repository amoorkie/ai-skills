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

# Code Review: ai-skills-toolkit

**Репозиторий:** https://github.com/amoorkie/ai-skills.git
**Версия:** 0.2.0 (Phase 2)
**Дата ревью:** 2026-03-07
**Рецензент:** Claude (Opus 4.6)

---

## Общая оценка: ВЫСОКОЕ КАЧЕСТВО

Проект представляет собой модульный CLI-тулкит из 8 AI-скиллов для автоматизации
типичных задач разработки. Все скиллы работают на основе эвристик и шаблонов
(без LLM в рантайме) — это осознанное решение для Phase 2.

---

## Архитектура и структура проекта

### Стек
- Python 3.11+, Pydantic 2.7+, hatchling (сборка)
- CLI на argparse с subcommand на каждый скилл
- Вывод — Markdown-файлы в `generated/`

### Структура каждого скилла (единообразная)
```
skills/<name>/
  ├── skill.py          — основная логика
  ├── schema.py         — Pydantic-модели входа/выхода
  ├── __init__.py       — публичный API
  ├── instructions.md   — документация
  └── examples.md       — примеры использования
```

### Поток данных
```
CLI args → Pydantic Input → Core logic → render_markdown() → safe_write_text() → SkillRunResult
```

**Оценка архитектуры: A** — чистая модульная структура, легко расширяемая.

---

## Обзор скиллов

### 1. repo_analyzer — ОТЛИЧНО
- Сканирует структуру репозитория, определяет языки (28 расширений), крупнейшие файлы, ключевые файлы
- Исключение служебных директорий (`.git`, `node_modules`, `__pycache__` и т.д.)
- Флаг `--include-hidden` и лимит `--max-files`
- Корректная обработка ошибок чтения файлов с записью в notes

### 2. code_reviewer — ХОРОШО
- Эвристический статический анализ Python-кода
- Обнаруживает: `bare except`, `eval()`, `print()` в продакшне, `TODO/FIXME`, `assert` вне тестов
- Приоритизация: high → medium → low с фильтрацией `--no-low-severity`
- **Замечание:** regex-подход, не AST — достаточно для Phase 2, но ограничен

### 3. test_generator — ХОРОШО
- Находит функции/классы через regex, формирует план тестов
- Приоритизация по focus_paths и размеру файла
- Включает заготовки pytest и заметки о рисковых паттернах
- **Замечание:** regex-based extraction — некоторые edge cases могут быть пропущены

### 4. deploy_helper — ХОРОШО
- Автоопределение платформы: Cloudflare → Vercel → Render → Docker → Generic
- По маркерным файлам (wrangler.toml, vercel.json, Dockerfile и т.д.)
- Чеклист из 7 пунктов, платформо-специфичные команды, раздел rollback
- **Замечание:** чеклисты шаблонные, не адаптированы под конкретный проект

### 5. figma_ui_architect — ХОРОШО
- Генерация UI/UX-спецификации для дизайн-команд
- Покрывает: цели, пользователей, JTBD, потоки, экраны, naming-конвенции, состояния
- Включает 5 состояний взаимодействия (loading, empty, success, error, permission-denied)
- **Замечание:** шаблонный вывод, не учитывает специфику конкретного продукта

### 6. architecture_designer — ХОРОШО
- Техническая архитектурная спецификация
- 6 компонентов, 5 API-эндпоинтов, 5 сущностей данных
- Безопасность (RBAC, шифрование, аудит), риски и митигации, фазы доставки
- **Замечание:** шаблон достаточно общий, может не подходить для специфичных доменов

### 7. prompt_debugger — ОТЛИЧНО (лучший скилл)
- Диагностика промптов: длина, формат вывода, guardrails, читаемость
- 3 варианта улучшения: Structured Strict, Concise Execution, Self-Evaluating
- Учитывает goal, context, target_model
- Практически полезный инструмент с хорошей эвристикой

### 8. doc_writer — ХОРОШО
- Повторно использует `analyze_repository()` из repo_analyzer (DRY)
- Генерирует: обзор, структуру, технологии, ключевые файлы, чеклист настройки
- Раздел "suggested next documentation" — полезное дополнение

---

## Качество кода

| Критерий | Оценка | Комментарий |
|----------|--------|-------------|
| Организация кода | A | Чистая модульная структура, единообразные паттерны |
| Валидация входных данных | A | Pydantic-схемы с field_validator |
| Обработка ошибок | B+ | Хорошая защита от перезаписи, можно улучшить контекст ошибок |
| Тестовое покрытие | B | Базовые тесты есть, пограничные случаи не покрыты |
| Документация | A | README, instructions.md, examples.md для каждого скилла |
| Расширяемость | A | Легко добавить новый скилл по шаблону |
| Безопасность | A | Path.resolve(), safe_write_text(), нет хардкода секретов |

---

## Найденные проблемы

### Критические: НЕТ

### Средние

#### 1. Дублирование валидатора `repo_path` (5+ файлов)
**Файлы:** schema.py в repo_analyzer, code_reviewer, test_generator, deploy_helper, doc_writer

Один и тот же валидатор повторяется в 5 скиллах:
```python
@field_validator("repo_path")
@classmethod
def validate_repo_path(cls, value: Path) -> Path:
    resolved = value.resolve()
    if not resolved.exists():
        raise ValueError(f"Path does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"Path is not a directory: {resolved}")
    return resolved
```

**Рекомендация:** Вынести в `core/validators.py` или создать `BaseRepoInput`.

#### 2. CLI — длинная цепочка if/elif (cli.py:170-282)
113 строк однотипного диспатчинга. При добавлении новых скиллов будет расти линейно.

**Рекомендация:** Использовать реестр скиллов (dict или декоратор):
```python
SKILL_REGISTRY = {
    "repo-analyzer": (RepoAnalyzerInput, run_repo_analyzer, "repo-analysis"),
    ...
}
```

### Незначительные

#### 3. Эвристики code_reviewer ограничены
Текущие 5 паттернов покрывают базовые случаи. Можно добавить:
- Неиспользуемые импорты
- Слишком длинные функции (> N строк)
- Отсутствие type hints в публичных API
- Hardcoded credentials patterns

#### 4. Нет интеграционных тестов CLI
`test_cli.py` тестирует парсинг, но не полный цикл `main()` → файл на диске.

#### 5. Нет проверки кодировки файлов
`repo_analyzer` и `code_reviewer` читают файлы через `read_text()` без обработки
`UnicodeDecodeError` для бинарных файлов.

---

## Рекомендации для Phase 3

1. **AST-анализ** вместо regex для code_reviewer и test_generator — повысит точность
2. **Skill registry** — упростит CLI и сделает скиллы plug-and-play
3. **Shared base models** — для DRY валидации repo_path
4. **Конфигурационный файл** — `.ai-skills.toml` для настройки по проекту
5. **Параллельное выполнение** — запуск нескольких скиллов одновременно
6. **Обработка бинарных файлов** — graceful skip при UnicodeDecodeError

---

## Итог

Проект **одобрен** — высокое качество для Phase 2. Код чистый, консистентный,
хорошо документирован и безопасен. Основной вектор развития — переход от шаблонов
к более интеллектуальному анализу (AST, семантика) и уменьшение дублирования
через shared-компоненты.


Рецензент - GPT 5.4
Ниже именно ревью с упором на дефекты и риски. Тесты сейчас зеленые: python -m pytest -q проходит, но это скорее подтверждает, что набор тестов пока не ловит несколько важных проблем.

code_reviewer массово дает ложные срабатывания, потому что ищет паттерны по сырым строкам, включая строковые литералы и собственные шаблоны. В результате он сам помечает свои же правила как eval/TODO/assert. Это подрывает доверие к ключевому скиллу. См. skill.py (line 27), skill.py (line 43), skill.py (line 63), skill.py (line 73). Я отдельно воспроизвел это на контенте, где есть только строки вроде "eval(" и "TODO": скилл все равно возвращает findings.

test_generator сортирует цели в обратную сторону и поднимает наверх наименее полезные файлы. В ключе сортировки уже стоит -p.stat().st_size, а затем еще используется reverse=True, поэтому первыми идут более мелкие файлы вроде schema.py, а не более содержательные модули. Это видно и по реальному прогону на этом репо. См. skill.py (line 53).

test_generator так же, как и code_reviewer, строит risk_notes по наивному substring matching, поэтому ловит ложные bare except, TODO/FIXME и даже pass внутри обычного текста. У меня _risk_notes() пометил строку "bypass auth" как наличие pass statement. См. skill.py (line 38), skill.py (line 44).

Генерация имени output-файла ломает не-ASCII сценарии: любые кириллические --output-name схлопываются в output.md. В текущем окружении это особенно заметно. slugify("отчет"), slugify("тест") и slugify("арх-спек") все дают один и тот же результат. Это создает неожиданные коллизии и ложные FileExistsError. См. io.py (line 10).

architecture_designer и figma_ui_architect выглядят как кастомные генераторы, но по сути отдают почти полностью захардкоженные шаблоны. У architecture_designer API surface, entities, risks и open questions не зависят от домена продукта, поэтому одинаковые эндпоинты /auth/session и /resources попадают и в payroll, и в chat app. См. architecture skill (line 14), architecture skill (line 121), figma skill (line 44), figma skill (line 50). Это не просто “generic output”, а риск вводить пользователя в заблуждение псевдо-специфичностью.

doc_writer в секции top-level structure раскрывает hidden entries, хотя repo_analyzer по умолчанию их скрывает. То есть документация может засветить .git, .env и другие скрытые артефакты, даже когда основной анализ их исключает. См. skill.py (line 14), skill.py (line 49).

Что улучшить в первую очередь:

Перевести code_reviewer и test_generator с substring-эвристик на tokenize/AST хотя бы для Python, чтобы не срабатывать на строках, комментариях и markdown-шаблонах.
Исправить ranking в test_generator и добавить scoring по “ценности для тестирования”: публичные функции, размер, сложность, количество веток, наличие I/O.
Заменить ASCII-only slugify на Unicode-safe transliteration или хотя бы fallback с хешем исходной строки.
Для architecture_designer и figma_ui_architect либо честно позиционировать их как boilerplate template generators, либо реально подмешивать входные требования в компоненты, endpoints, flows, states и open questions.
Синхронизировать поведение doc_writer с repo_analyzer по hidden-файлам и исключениям.
Расширить тесты негативными кейсами: false positives, Unicode output names, ranking target selection, hidden file leakage.
Главный пробел в тестах: они почти везде проверяют “файл создался” и “секция присутствует”, но почти не проверяют качество и правдивость вывода. Именно поэтому текущие проблемы проходят suite без сопротивления.



