# Coding Conventions

**Analysis Date:** 2026-06-04

## Language and Runtime

The codebase is **Python 3.11** (CI target in `.github/workflows/aggregate.yml`). The `scripts/` layer uses `from __future__ import annotations` in newer files (`auto_blocks.py`, `sheets_sync.py`) for deferred type evaluation. All scripts carry the `#!/usr/bin/env python3` shebang and a module-level docstring.

## Naming Patterns

**Files:**
- Python scripts use `snake_case.py` — `aggregator.py`, `auto_blocks.py`, `sheets_sync.py`, `validate_auto_blocks.py`, `utils.py`, `discover.py`
- Jekyll data files use `snake_case.yml` — `sync_status.yml`, `loe.yml`, `calendar.yml`
- Jekyll includes/layouts use `snake_case.html` — `card.html`, `sidebar.html`, `default.html`
- Generated markdown output files use `kebab-case.md` — `unified-kanban.md`, `loe-report.md`, `dependency-graph.md`, `migration-gantt.md`
- Per-project pages under `docs/_projects/` are named by repo name, e.g. `{project}.md`

**Functions:**
- `snake_case` for all Python functions: `load_projects()`, `parse_kanban_tasks()`, `normalize_frontmatter()`, `now_iso()`, `build_loe_rows()`
- Private/internal helpers prefixed with underscore: `_status_legend()`, `_get_sheet_id()`, `_list_backup_tabs()`, `_MARKER_OPEN_RE`, `_STATUS_DEFAULTS`
- Generator functions named `generate_*`: `generate_unified_kanban()`, `generate_project_page()`, `generate_dependency_graph()`
- Render functions named `render_*`: `render_calendar()`, `render_meta_header()` in `scripts/auto_blocks.py`

**Variables:**
- Module-level constants in `SCREAMING_SNAKE_CASE`: `ORG`, `BASE_DIR`, `REPOS_DIR`, `LOE_DATA_FILE`, `TASK_STATUSES`, `STATUS_COLORS`, `LIVE_TAB`, `STAGING_TAB`, `MAX_WRITE_RETRIES`
- Local variables in `snake_case`: `loe_rows`, `project_data`, `backup_name`, `sprint_len`
- Loop variables are short and descriptive: `project`, `task`, `row`, `ph`, `cdef`

**Types:**
- Type hints used consistently for function signatures in `utils.py` and `auto_blocks.py`
- Return types annotated: `-> str`, `-> dict`, `-> list[dict]`, `-> list[str]`, `-> float`, `-> bool`
- `dict[str, Any]` used for flexible YAML-parsed dicts (requires `from typing import Any`)
- `tuple[str, int, int, int, int]` for structured return values (`find_marker_pairs`)
- `Callable[[dict], str]` for renderer registry: `AUTO_BLOCK_RENDERERS` in `scripts/auto_blocks.py`

## Code Style

**Formatting:**
- No automated formatter config file detected (no `pyproject.toml`, `.flake8`, `setup.cfg`)
- Line length appears to follow PEP 8 (~88-100 chars); multiline string building uses list + `"\n".join(lines)` pattern throughout
- 4-space indentation, consistent across all scripts

**Linting:**
- No linting config files present; `# noqa: BLE001` suppression comments appear in `sheets_sync.py` on broad `except Exception` catches, indicating awareness of linting rules (likely Ruff or flake8 BLE001 = blind exception)

## Module Organization

**Single source of truth in `utils.py`:**
All shared constants, path objects, and utility functions live in `scripts/utils.py`. No other script re-declares constants. Import pattern:

```python
from utils import (
    DATA_DIR,
    DOCS_DIR,
    LOE_DATA_FILE,
    ORG,
    TASK_STATUSES,
    load_projects,
    now_iso,
    update_sync_status,
)
```

**Section dividers in larger files:**
`sheets_sync.py` and `auto_blocks.py` use `# --- comment --- #` separator blocks with descriptive names to group related functions:

```python
# --------------------------------------------------------------------------- #
# Data loading                                                                 #
# --------------------------------------------------------------------------- #
```

## Import Organization

**Order (observed):**
1. `from __future__ import annotations` (when present)
2. Standard library imports (`os`, `re`, `sys`, `time`, `traceback`, `subprocess`, `pathlib`, `datetime`, `typing`)
3. Third-party imports (`yaml`, `requests`, `google.*`)
4. Local project imports (`from utils import ...`, `from auto_blocks import ...`)

**No star imports** — all imports are explicit. Local module imports use relative names without package prefix (scripts run from `scripts/` directory via `PYTHONPATH`).

## Error Handling

**Patterns:**
- YAML parse failures silently return `{}` or empty defaults: `except yaml.YAMLError: return {}`
- File not found is checked explicitly with `.exists()` before reading: `if kanban_path.exists():`
- Warning messages printed with `print(f"Warning: ...")` for non-fatal issues (missing kanban.md, unknown task status)
- Critical failures that should surface but not crash use `except ValueError as e: print(f"WARN: ...")` in `aggregator.py`
- Sheets sync uses a broad `except Exception` with `# noqa: BLE001` + full `traceback.format_exc()` to catch all failures while keeping the pipeline exit-0
- Retry logic in `write_with_retry()` (`scripts/sheets_sync.py`) uses exponential backoff: `delay *= 2`

**Exit codes:**
- `main()` functions return `int` and the caller does `sys.exit(main())`
- `sheets_sync.py` returns `0` even on failure — intentional design to keep downstream CI steps running
- `validate_auto_blocks.py` returns `1` on errors — this is a hard CI gate

## Docstrings

**Style:** Google-style docstrings with `Args:` and `Returns:` sections where applicable:

```python
def parse_kanban_tasks(content: str, project: str = "") -> list[dict[str, str]]:
    """Extract tasks from kanban markdown table.

    Supports both 4-column and 6-column formats:
      4-col: | Task | Assignee | Effort | Status |
      6-col: | Task | Assignee | Effort | Start | End | Status |

    Returns:
        List of task dicts with keys: task, assignee, effort, start, end, status
    """
```

**Module docstrings:** Every script has a multi-line module docstring explaining purpose, design properties, and usage. These are the primary docs — there is no separate API documentation.

## Logging

**Framework:** `print()` — no structured logging library.

**Patterns:**
- Progress/info messages use bare `print(f"...")`: `print("KF Aggregator — Starting...")`
- Warnings use `print(f"Warning: ...")` prefix
- Errors use `print(tb, file=sys.stderr)` for full tracebacks
- Step completion uses `print(f"Generated {filename}")` pattern
- The main entry functions open and close with a name banner: `print("KF Aggregator — Starting...")` ... `print("KF Aggregator — Done!")`

## Data Flow Convention

**Canonical intermediate file:** `docs/_data/loe.yml` is written by `aggregator.py` and consumed by `sheets_sync.py`. Scripts never re-parse source data independently — they read from the canonical intermediate. Defined in `scripts/utils.py` as `LOE_DATA_FILE`.

**Idempotency:** Aggregator and auto-block injection are designed to be idempotent. Re-running produces identical output for identical input. Auto-block injection compares `updated != original` before writing (`scripts/auto_blocks.py` `process_page()`).

**Status persistence:** `docs/_data/sync_status.yml` is the shared status file, always written with `save_sync_status()`. The read-modify-write helper `update_sync_status(section, **fields)` is the standard interface — callers never write it directly.

## Frontmatter Defaults

Kanban frontmatter normalization uses a `FRONTMATTER_DEFAULTS` dict in `utils.py` with all expected keys. `normalize_frontmatter()` applies these defaults before any consumer uses the data. Add new optional frontmatter keys to `FRONTMATTER_DEFAULTS` first.

## Text Pills Convention

Planning documents use `[LABEL]` text pills instead of emoji icons. Labels include `[REFACTOR]`, `[NEW]`, `[BUGFIX]`, `[INTEGRATION]`, `[SETUP]`, `[WARN]`, `[BLOCKER]`, `[OK]`. Every document that uses pills must include a Glossary table defining each pill. See `docs/migration-gantt.md` section 1.2 for the canonical example.

## Commit Message Standard

Conventional Commits format, enforced by `.claude/agents/gitops-engineer.md`:

```
<type>(<scope>): <description>

<optional body explaining what and why>
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`

No emoji footers. No AI attribution lines. CI commits use `[skip ci]` suffix: `chore: auto-update unified docs [skip ci]`.

---

*Convention analysis: 2026-06-04*
