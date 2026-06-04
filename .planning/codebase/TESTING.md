# Testing Patterns

**Analysis Date:** 2026-06-04

## Test Framework

**Runner:** None — no automated test framework is installed or configured. No `pytest.ini`, `setup.cfg`, `pyproject.toml`, `tox.ini`, or `requirements-test.txt` is present in the repository. No test files (`test_*.py`, `*_test.py`, `*.spec.*`) were found anywhere outside of `venv/`.

**Assertion Library:** Not applicable.

**Run Commands:**
```bash
# No test runner configured.
# The only automated validation is:
python scripts/validate_auto_blocks.py   # lint auto-block markers in docs/
```

## Validation in Place of Tests

The project substitutes structured validation scripts and CI gates for unit tests.

### Auto-Block Linter — `scripts/validate_auto_blocks.py`

The only formal "test" in the project. Walks `docs/` recursively and verifies:

- Every page declaring `auto_blocks: [...]` in frontmatter has matching `<!-- AUTO:name -->` / `<!-- /AUTO:name -->` HTML comment pairs in the body
- Every marker pair is declared in `auto_blocks:`
- Every declared block name maps to a registered renderer in `AUTO_BLOCK_RENDERERS`

Exits non-zero on any violation — used as a CI hard gate in `.github/workflows/aggregate.yml` ("Validate auto-blocks in augmented Jekyll pages" step).

```python
def check_page(path: Path) -> list[str]:
    """Return a list of error strings (empty if the page is clean)."""
    errors: list[str] = []
    ...
    missing = declared_set - marker_names
    if missing:
        errors.append(...)
    orphan = marker_names - declared_set
    ...
    unknown = declared_set - known
    ...
    return errors
```

Location: `scripts/validate_auto_blocks.py`

### CI Workflow Validation

The CI pipeline in `.github/workflows/aggregate.yml` acts as an integration smoke test:

1. `python scripts/discover.py` — validates GitHub API connectivity and org access
2. `python scripts/validate_auto_blocks.py` — lints augmented pages (hard gate; non-zero exit fails the job)
3. `python scripts/aggregator.py` — full aggregation run; any unhandled exception fails the job
4. `python scripts/sheets_sync.py` — downstream export; designed to exit 0 even on failure (soft gate)

If any hard-gate step fails, the CI job fails and the Pages deploy does not proceed.

## Test Coverage

**Current:** Zero. No unit or integration tests cover:

- `utils.py` parsing functions (`parse_kanban_tasks`, `parse_kanban_frontmatter`, `parse_effort_days`, `normalize_frontmatter`)
- `auto_blocks.py` renderer logic (`render_calendar`, `render_meta_header`)
- `auto_blocks.py` marker injection engine (`inject_auto_blocks`, `find_marker_pairs`)
- `aggregator.py` report generators (`generate_unified_kanban`, `generate_loe_report`, etc.)
- `sheets_sync.py` Sheets API helpers (`ensure_staging_tab`, `validate_staged`, `swap_staging_into_live`)
- `discover.py` GitHub API logic

The `validate_auto_blocks.py` script itself has no tests.

## Error Handling as Behavioral Spec

Explicit error handling in production code serves as the de facto specification for edge cases:

**`utils.py` `parse_kanban_tasks()`** — prints a warning for unknown status values (valid statuses are `TASK_STATUSES` tuple); callers receive the task with the invalid status rather than an exception.

**`utils.py` `normalize_frontmatter()`** — coerces `depends_on` and `tags` to lists if they arrive as strings; applies `FRONTMATTER_DEFAULTS` for all missing keys.

**`utils.py` `load_sync_status()`** — returns structured defaults if `sync_status.yml` is missing or corrupt. Deep-merges partial sections so callers can safely overwrite one section without erasing another.

**`auto_blocks.py` `find_marker_pairs()`** — raises `ValueError` on mismatched marker counts, name mismatches, or close-before-open positions. These are caught by the linter and by `aggregator.py`'s `process_page()` try/except.

**`sheets_sync.py` `write_with_retry()`** — retries up to `MAX_WRITE_RETRIES` (3) times with exponential backoff starting at 1 second. Raises `RuntimeError` after all retries fail.

## Adding Tests — Recommended Approach

If a test layer is introduced, these patterns apply given the existing codebase shape:

**Framework:** `pytest` — matches Python 3.11 target, minimal configuration required.

**Test file location:** Co-locate under a `tests/` directory at project root, mirroring the `scripts/` module names:
```
tests/
├── test_utils.py          # parse_kanban_tasks, parse_effort_days, normalize_frontmatter
├── test_auto_blocks.py    # render_calendar, render_meta_header, inject_auto_blocks
├── test_aggregator.py     # generate_unified_kanban, build_loe_rows
└── test_validate.py       # check_page
```

**Test data:** Use inline fixture strings for kanban markdown inputs rather than file fixtures — all parsers accept `str` input.

**Mocking:** Use `unittest.mock.patch` for:
- `Path.read_text` / `Path.write_text` in file I/O functions
- `requests.get` in `discover.py`
- Google API service objects in `sheets_sync.py`
- `os.environ` lookups for secret env vars

**Highest-value test targets (by risk):**

1. `parse_kanban_tasks()` — 4-col vs 6-col detection, header/separator row skipping, status validation
2. `inject_auto_blocks()` — marker replacement, idempotency, mismatched marker errors
3. `build_loe_rows()` — canonical LOE intermediate shape contract with `sheets_sync.py`
4. `normalize_frontmatter()` — type coercion, alias normalization, defaults

## CI/CD Testing Integration

`.github/workflows/aggregate.yml` runs on:
- Push to `master`
- `repository_dispatch` (type `kanban-updated`) — triggered by project repos
- Weekly schedule (`cron: '0 4 * * 1'`)
- Manual `workflow_dispatch`

The "Validate auto-blocks" step is the only mandatory validation gate. All other script steps fail the job via Python exception propagation.

---

*Testing analysis: 2026-06-04*
