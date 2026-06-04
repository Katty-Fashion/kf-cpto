<!-- refreshed: 2026-06-04 -->
# Architecture

**Analysis Date:** 2026-06-04

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│               katty-fashion GitHub Org (N project repos)            │
│         each repo: kanban.md (YAML frontmatter + task table)        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  GitHub API (discover) + git clone (aggregate)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Pipeline Layer (GitHub Actions)                    │
│             `.github/workflows/aggregate.yml`                        │
│                                                                      │
│  discover.py → clone repos → validate_auto_blocks.py → aggregator.py│
│            → commit docs/ → deploy gh-pages → sheets_sync.py        │
└───────┬──────────────────────────┬──────────────────────────────────┘
        │                          │
        ▼                          ▼
┌───────────────────┐   ┌──────────────────────────────────────────────┐
│  Canonical Store  │   │          Jekyll Site (docs/)                 │
│  `docs/_data/`    │   │                                              │
│  loe.yml          │   │  _projects/*.md  (per-project pages)         │
│  sync_status.yml  │   │  unified-kanban.md, unified-calendar.md      │
│  calendar.yml     │   │  loe-report.md, dependency-graph.md          │
└───────┬───────────┘   │  migration-gantt.md (augmented, prose+auto)  │
        │               └──────────────────────┬───────────────────────┘
        │                                      │ Jekyll build → gh-pages
        ▼                                      ▼
┌─────────────────────┐         ┌────────────────────────────────────┐
│  Google Sheets      │         │  GitHub Pages (canonical dashboard) │
│  (downstream export)│         │  https://katty-fashion.github.io/  │
│  `sheets_sync.py`   │         │         kf-cpto/                   │
└─────────────────────┘         └────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| discover.py | Scans GitHub org for repos with `kanban.md`; writes `repos/discovered.txt` | `scripts/discover.py` |
| utils.py | Shared constants, parsers (`kanban.md` frontmatter + tasks), sync-status I/O | `scripts/utils.py` |
| aggregator.py | Loads all project kanban data; generates all docs/ pages; writes `loe.yml` | `scripts/aggregator.py` |
| auto_blocks.py | Renders idempotent `AUTO:*` sections inside augmented Jekyll pages | `scripts/auto_blocks.py` |
| validate_auto_blocks.py | CI lint: verifies AUTO marker/renderer/frontmatter consistency | `scripts/validate_auto_blocks.py` |
| sheets_sync.py | Downstream export: reads `loe.yml`, stages → validates → swaps into Google Sheets | `scripts/sheets_sync.py` |
| aggregate.yml | Primary CI/CD orchestrator; runs the full pipeline on push/schedule/dispatch | `.github/workflows/aggregate.yml` |
| sync_to_sheets.yml | Standalone weekday Sheets sync (reads pre-existing `loe.yml`; no full rebuild) | `.github/workflows/sync_to_sheets.yml` |
| Jekyll site | Renders markdown to HTML using Pico CSS + MermaidJS | `docs/` |
| templates/ | Seed files for new project repos (kanban.md template + notify workflow) | `templates/` |

## Pattern Overview

**Overall:** Git-native pull aggregation pipeline with Pages-first topology.

**Key Characteristics:**
- Source of truth lives in distributed per-project `kanban.md` files; this repo aggregates, never owns project data.
- GitHub Pages is the canonical, always-available dashboard; Google Sheets is a downstream consumer that never blocks the pipeline (exits 0 on failure).
- A single canonical intermediate file (`docs/_data/loe.yml`) decouples the parser (aggregator.py) from the exporter (sheets_sync.py) — "one parser, one canonical intermediate."
- Augmented pages (e.g., `migration-gantt.md`) carry a mix of hand-edited prose and auto-rendered sections marked with `<!-- AUTO:name -->` / `<!-- /AUTO:name -->` comment pairs; `auto_blocks.py` replaces only the interior of those pairs idempotently.
- All sync health is recorded in `docs/_data/sync_status.yml` and surfaced live on the dashboard sidebar and index banner.

## Layers

**Discovery Layer:**
- Purpose: Enumerate project repos dynamically at CI runtime.
- Location: `scripts/discover.py`
- Contains: GitHub API pagination, kanban.md existence check, `repos/discovered.txt` writer.
- Depends on: `requests`, `KF_PAT` env var, `utils.ORG`, `utils.DISCOVERED_FILE`.
- Used by: `aggregate.yml` (step 1); `utils.load_projects()` fallback.

**Data Loading / Parsing Layer:**
- Purpose: Parse `kanban.md` frontmatter and task tables into Python dicts.
- Location: `scripts/utils.py` — `parse_kanban_frontmatter()`, `parse_kanban_tasks()`, `normalize_frontmatter()`, `load_project_kanban()`, `load_all_project_data()`
- Contains: regex-based YAML frontmatter extractor; 4-col and 6-col Markdown table parser; effort string parser (`Nd`).
- Depends on: `pyyaml`, `repos/{project}/kanban.md` files.
- Used by: `aggregator.py`.

**Aggregation / Generation Layer:**
- Purpose: Transform parsed project data into all output docs and the canonical LOE intermediate.
- Location: `scripts/aggregator.py`
- Contains: `generate_unified_kanban()`, `generate_unified_calendar()`, `generate_loe_report()`, `generate_dependency_graph()`, `generate_project_page()`, `build_loe_rows()`, `write_loe_yaml()`.
- Depends on: `utils.py` (parsers, constants), `auto_blocks.py` (post-generation injection).
- Used by: `aggregate.yml` pipeline step.

**Auto-Blocks Engine:**
- Purpose: Idempotently inject computed content (calendar table, meta-header) into augmented prose pages.
- Location: `scripts/auto_blocks.py`
- Contains: `AUTO_BLOCK_RENDERERS` registry (`calendar`, `meta-header`), marker parser (`find_marker_pairs()`), `inject_auto_blocks()`, `process_page()`, `load_context()`.
- Depends on: `docs/_data/*.yml` context files (especially `calendar.yml`).
- Used by: `aggregator.py` (post-generation pass); `validate_auto_blocks.py` (CI lint).

**Downstream Export Layer:**
- Purpose: Export canonical LOE data to Google Sheets using a shadow-tab swap pattern.
- Location: `scripts/sheets_sync.py`
- Contains: `load_loe_from_yaml()`, `sync_to_sheets()`, shadow-tab helpers, `file_sync_failure_issue()`, `notify_chat()`.
- Depends on: `docs/_data/loe.yml` (written by aggregator; never re-parses kanban.md), `google-api-python-client`.
- Used by: `aggregate.yml` (step after Pages deploy); `sync_to_sheets.yml` (standalone weekday schedule).

**Presentation Layer (Jekyll):**
- Purpose: Render markdown docs to a navigable HTML dashboard.
- Location: `docs/`
- Contains: `_layouts/default.html` (Pico CSS + MermaidJS), `_includes/sidebar.html` (project nav + sync-status badge), `_data/` (YAML data files), `_projects/*.md` (Jekyll collection), top-level view pages.
- Depends on: Pico CSS CDN, MermaidJS CDN (v11 ESM), `jekyll-feed`, `jekyll-seo-tag`.
- Used by: GitHub Pages (`gh-pages` branch).

## Data Flow

### Primary Pipeline (aggregate.yml)

1. `discover.py` queries GitHub API for repos with `kanban.md`; writes `repos/discovered.txt` (`scripts/discover.py:75`)
2. CI clones each discovered repo into `repos/{name}/` (shallow depth 1) (`.github/workflows/aggregate.yml:41`)
3. `validate_auto_blocks.py` checks augmented pages for marker/renderer consistency; exits non-zero on error (`scripts/validate_auto_blocks.py:70`)
4. `aggregator.py` calls `load_all_project_data()` → reads each `repos/{project}/kanban.md` → builds unified pages in `docs/` and per-project pages in `docs/_projects/` (`scripts/aggregator.py:536`)
5. `aggregator.py` runs `auto_blocks.process_page()` on every `docs/**/*.md` to refresh AUTO sections (`scripts/aggregator.py:572`)
6. `aggregator.py` writes canonical LOE rows to `docs/_data/loe.yml` (`scripts/aggregator.py:585`)
7. `aggregator.py` updates `docs/_data/sync_status.yml` aggregator section (`scripts/aggregator.py:590`)
8. CI commits `docs/` changes and pushes to master (`aggregate.yml:63`)
9. `peaceiris/actions-gh-pages` deploys `docs/` to the `gh-pages` branch → GitHub Pages serves the site (`aggregate.yml:69`)
10. `sheets_sync.py` reads `docs/_data/loe.yml`, stages to `LOE_staging`, validates, swaps into live `LOE` tab (`scripts/sheets_sync.py:320`)
11. CI commits `docs/_data/sync_status.yml` sheets_export section update (`aggregate.yml:89`)
12. Google Chat webhook notification sent (`aggregate.yml:106`)

### Kanban Update Push (repository_dispatch)

1. A project repo's `notify-kf-cpto.yml` detects a push to `kanban.md` (`templates/.github/workflows/notify-kf-cpto.yml:7`)
2. It sends a `repository_dispatch` event with type `kanban-updated` to `katty-fashion/kf-cpto` (`templates/.github/workflows/notify-kf-cpto.yml:20`)
3. `aggregate.yml` triggers on this event type and runs the full pipeline above (`aggregate.yml:7`)

### Auto-Blocks Injection Sub-Flow

1. `aggregator.py` calls `auto_blocks.load_context(DATA_DIR)` — loads all `docs/_data/*.yml` files keyed by stem (`scripts/auto_blocks.py:232`)
2. For each `docs/**/*.md`, `process_page()` reads file content, calls `inject_auto_blocks()` (`scripts/auto_blocks.py:218`)
3. `inject_auto_blocks()` parses frontmatter for `auto_blocks: [...]` list; finds `<!-- AUTO:name -->` / `<!-- /AUTO:name -->` marker pairs; calls the registered renderer; replaces interior in reverse order to preserve offsets (`scripts/auto_blocks.py:169`)
4. File written back only if content changed (idempotent) (`scripts/auto_blocks.py:222`)

**State Management:**
- Pipeline state is persisted in `docs/_data/sync_status.yml` (two sections: `aggregator`, `sheets_export`). Read-modify-write via `utils.update_sync_status()`. Both the aggregator and sheets_sync update their own section independently, so a sheets failure preserves the aggregator's recorded state.

## Key Abstractions

**kanban.md (project data contract):**
- Purpose: Single file per project repo that carries all project metadata (YAML frontmatter) and task data (Markdown table).
- Examples: `templates/kanban.md`, `repos/{project}/kanban.md` (cloned at runtime)
- Pattern: YAML frontmatter block (`---`) followed by a Markdown table (4-col or 6-col). Parsed by `utils.parse_kanban_frontmatter()` and `utils.parse_kanban_tasks()`.

**loe.yml (canonical intermediate):**
- Purpose: Decouples kanban parser from Sheets exporter. Aggregator writes it; sheets_sync reads it. No second parse of raw kanban.md.
- Location: `docs/_data/loe.yml`
- Pattern: `{generated_at, row_count, rows: [{project, sprint, task, assignee, effort_days, start, end, status}]}`. Written by `aggregator.build_loe_rows()` / `write_loe_yaml()`.

**AUTO blocks (augmented page sections):**
- Purpose: Embed computed/dynamic content inside otherwise hand-edited prose documents.
- Examples: `docs/migration-gantt.md` (blocks: `meta-header`, `calendar`)
- Pattern: Page declares `auto_blocks: [name1, name2]` in frontmatter; body contains `<!-- AUTO:name -->` ... `<!-- /AUTO:name -->` marker pairs. `auto_blocks.AUTO_BLOCK_RENDERERS` maps names to renderer functions.

**sync_status.yml (operational health):**
- Purpose: Records the last run outcome for the aggregator and sheets export; rendered live in the dashboard sidebar and index banner.
- Location: `docs/_data/sync_status.yml`
- Pattern: Two top-level YAML sections (`aggregator`, `sheets_export`). Updated by `utils.update_sync_status(section, **fields)` (read-modify-write).

## Entry Points

**aggregate.yml (CI/CD primary):**
- Location: `.github/workflows/aggregate.yml`
- Triggers: push to master, `repository_dispatch` (kanban-updated), weekly schedule (Monday 04:00 UTC), manual dispatch.
- Responsibilities: Full pipeline — discover, clone, validate, aggregate, deploy Pages, sync Sheets, notify Chat.

**sync_to_sheets.yml (standalone Sheets refresh):**
- Location: `.github/workflows/sync_to_sheets.yml`
- Triggers: Weekdays 09:00 UTC schedule, manual dispatch.
- Responsibilities: Re-runs discover + clone + sheets_sync only; does not rebuild Pages.

**scripts/aggregator.py (Python main):**
- Location: `scripts/aggregator.py:536` (`main()`)
- Triggers: Called by `aggregate.yml`; can be run locally with cloned repos present.
- Responsibilities: Load all project data, generate all docs/ output, inject auto-blocks, write loe.yml, update sync_status.

**scripts/sheets_sync.py (Python main):**
- Location: `scripts/sheets_sync.py:387` (`main()`)
- Triggers: Called by both workflows after aggregation.
- Responsibilities: Read `loe.yml`, stage → validate → swap into Google Sheets, record status, exit 0 always.

## Architectural Constraints

- **Threading:** Single-threaded Python scripts running sequentially in CI. No async or worker threads.
- **Global state:** `utils.PROJECT_BRANCHES` is a module-level dict populated as a side-effect of `load_projects()`. Any script that imports `utils` and calls `load_projects()` populates this global. (`scripts/utils.py:37`)
- **Circular imports:** None detected. `aggregator.py` and `sheets_sync.py` both import from `utils.py`; `aggregator.py` imports from `auto_blocks.py`; `validate_auto_blocks.py` imports from `auto_blocks.py`. No cycles.
- **Exit 0 invariant:** `sheets_sync.py` always exits 0 regardless of failure, by design. This is intentional — Pages must not be blocked by Sheets failures. Do not change this behavior.
- **No static project list:** `discover.py` dynamically builds `repos/discovered.txt` at pipeline start. `utils.load_projects()` falls back to `docs/_config.yml` `kf_projects` key only for local dev without a prior discover run.
- **Repos dir is runtime-only:** `repos/` is in `.gitignore` and populated by CI shallow-clones. Never commit files under `repos/`.

## Anti-Patterns

### Re-parsing kanban.md in sheets_sync.py

**What happens:** Adding kanban.md parsing logic directly to `sheets_sync.py` instead of reading from `loe.yml`.
**Why it's wrong:** The aggregator is the single parser. Duplicating parsing logic breaks the "one parser, one canonical intermediate" contract and risks diverging interpretations of effort, status, or column format.
**Do this instead:** Always read `docs/_data/loe.yml` in `sheets_sync.py`. If the schema needs new fields, extend `aggregator.build_loe_rows()` and `write_loe_yaml()` (`scripts/aggregator.py:489`).

### Blocking the workflow on Sheets failure

**What happens:** Letting `sheets_sync.py` exit non-zero or raising uncaught exceptions that fail the workflow.
**Why it's wrong:** The dashboard (GitHub Pages) would fail to deploy on every Sheets API error, making the canonical view unavailable to the team.
**Do this instead:** All exception handling in `sheets_sync.py:main()` catches `Exception`, records the failure in `sync_status.yml`, files a GitHub issue, and returns 0 (`scripts/sheets_sync.py:397`).

### Hardcoding project names

**What happens:** Adding project names to `docs/_config.yml` `kf_projects` or hardcoding them in scripts.
**Why it's wrong:** Projects are discovered dynamically via `discover.py`. Any static list will drift out of sync as repos are added or archived.
**Do this instead:** Add `kanban.md` to the project repo. `discover.py` will find it on the next pipeline run.

## Error Handling

**Strategy:** Fail-fast in aggregation (bad kanban.md data surfaces as console warnings but continues); fail-silent in Sheets export (all errors caught, recorded, issue filed, exit 0).

**Patterns:**
- `validate_auto_blocks.py` exits non-zero in CI to block merges with malformed AUTO markers.
- `utils.parse_kanban_tasks()` prints a `Warning:` for unknown task statuses but continues parsing.
- `sheets_sync.py` wraps its entire `main()` body in a bare `except Exception` block, ensuring the exit code is always 0.
- `auto_blocks.inject_auto_blocks()` raises `ValueError` on mismatched/unknown markers; `aggregator.py` catches `ValueError` per page and prints `WARN:` without aborting the run (`scripts/aggregator.py:578`).
- `utils.update_sync_status()` uses read-modify-write so a partial failure in one section never erases the other section's recorded state.

## Cross-Cutting Concerns

**Logging:** `print()` to stdout/stderr throughout all scripts. No structured logging framework. CI captures all output in workflow logs.
**Validation:** Auto-block marker hygiene is enforced pre-merge by `validate_auto_blocks.py` (CI step in `aggregate.yml:54`). Task status validity is warned at parse time in `utils.parse_kanban_tasks()`.
**Authentication:** GitHub API uses `KF_PAT` (Personal Access Token with repo scope) passed as env var. Google Sheets uses a service account with `GSHEET_CLIENT_EMAIL` + `GSHEET_PRIVATE_KEY` env vars assembled at runtime in `sheets_sync.get_sheets_service()`.

---

*Architecture analysis: 2026-06-04*
