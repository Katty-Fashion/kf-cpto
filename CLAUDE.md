<!-- GSD:project-start source:PROJECT.md -->
## Project

**kf-cpto — Activity-Driven Migration Dashboard**

kf-cpto is the CPTO aggregation hub for the katty-fashion GitHub org: it pulls per-project `kanban.md` files, builds a unified Jekyll dashboard on GitHub Pages (kanban, sprint calendar, LOE report, dependency graph, migration gantt), and exports key LOE data downstream to a Google Workspace `LOE` Sheet. This milestone adds a **local Claude skill** that turns the dashboard from a hand-maintained artifact into an **activity-driven** one — reading real repo activity, reconciling it against the declared plan, writing corrections back to the tracked repos, and modelling over-capacity work as **agentic effort instead of new headcount**.

**Core Value:** One command turns *actual repo activity* into an accurate, deployed dashboard and LOE Sheet — with work beyond a person's capacity flowing to a synthetic Agentic assignee instead of a hire recommendation.

### Constraints

- **Tech stack**: Python 3.9+ scripts + Jekyll/Ruby site — Keep CI deterministic; the skill produces inputs, CI renders/deploys
- **Execution**: Skill runs locally in Claude Code, reaching sibling repos via symlink — No reliance on the skill at CI time; CI stays self-contained
- **External writes**: Pushes to tracked project repos are batch-confirmed once, never per-repo prompted — Matches the org-scan workflow preference; avoids interactive stalls across N repos
- **Topology**: Pages canonical, Sheets downstream, exit-0 on Sheets failure — Dashboard availability must never depend on the Sheet
- **Parser discipline**: Extend `aggregator.build_loe_rows()` / `write_loe_yaml()` for new fields; never add a second kanban parser — Preserves the canonical-intermediate contract
- **Runtime dirs**: Never commit `repos/` (shallow clones) — gitignored, populated at runtime only
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.9+ (venv pinned to 3.9; CI runs on 3.11) — all automation scripts in `scripts/`
- Ruby — Jekyll static site generation in `docs/`
- Liquid (Jekyll templating) — `docs/_layouts/`, `docs/_includes/`
- YAML — data files, frontmatter, workflow config
- JavaScript — browser-side Mermaid rendering in `docs/_layouts/default.html`
- Bash — inline CI steps in `.github/workflows/aggregate.yml`
## Runtime
- Minimum: 3.9 (local venv at `venv/lib/python3.9`)
- CI: 3.11 (set via `actions/setup-python@v5` in workflows)
- Managed by `github-pages` gem (pins Jekyll 3.10.0)
- Lockfile: `docs/Gemfile.lock` (present, bundled with Bundler 2.4.10)
- No build step; ESM module loaded directly from CDN at runtime
- pip (no lockfile — `requirements.txt` uses `>=` bounds only)
- Local venv: `venv/`
- Bundler 2.4.10
- Lockfile: `docs/Gemfile.lock`
## Frameworks
- Jekyll 3.10.0 (via `github-pages` gem 232) — builds `docs/` into GitHub Pages
- Config: `docs/_config.yml`
- Collections: `_projects` (auto-output enabled, permalink `/projects/:name/`)
- kramdown 2.4.0 (Jekyll default parser)
- Pico CSS v2 — loaded from CDN (`https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css`)
- Custom overrides: `docs/assets/css/custom.css`
- Mermaid v11 — loaded from CDN (`https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs`)
- Supports: kanban, gantt, pie, graph LR diagrams
- Theme: `forest`, securityLevel: `loose`
- `jekyll-feed` — RSS feed
- `jekyll-seo-tag` — SEO metadata
## Key Dependencies
- `pyyaml>=6.0` — YAML parsing for kanban.md frontmatter and `_data/*.yml` files
- `google-auth>=2.0` — Service account credentials for Google Sheets API
- `google-api-python-client>=2.0` — Google Sheets v4 API client
- `requests>=2.28` — GitHub REST API calls in `scripts/discover.py` and chat webhooks
- Same four packages above installed directly in CI steps
- `github-pages 232` — meta-gem that pins all Jekyll dependencies for GitHub Pages compatibility
- `jekyll 3.10.0` — static site builder
- `kramdown 2.4.0` — Markdown parser
- `liquid 4.0.4` — Liquid templating engine
- `mermaid` — not a gem; loaded client-side from CDN
## Configuration
- `KF_PAT` — GitHub Personal Access Token; used by `discover.py` for org API calls and git push
- `GSHEET_ID` — Google Spreadsheet ID for LOE export
- `GSHEET_CLIENT_EMAIL` — Service account email for Sheets API auth
- `GSHEET_PRIVATE_KEY` — RSA private key for service account (newlines escaped as `\n`)
- `GOOGLE_CHAT_WEBHOOK` — Incoming webhook URL for Google Chat notifications
- `GITHUB_TOKEN` — Standard Actions token; used for GitHub Pages deploy
- `docs/_data/calendar.yml` — Migration project calendar config (start date, total weeks, phases)
- `docs/_data/loe.yml` — Canonical LOE intermediate written by `scripts/aggregator.py`
- `docs/_data/sync_status.yml` — Aggregator and Sheets export health state
- `docs/_config.yml` — title, baseurl, markdown engine, plugins, collection definitions
## Platform Requirements
- Python 3.9+ with pip
- Ruby + Bundler 2.x (for local Jekyll preview: `bundle exec jekyll serve` from `docs/`)
- GitHub CLI (`gh`) — used by `scripts/sheets_sync.py` for filing failure issues
- GitHub Actions (ubuntu-latest runners) — all CI/CD
- GitHub Pages (`gh-pages` branch) — static site hosting at `https://katty-fashion.github.io/kf-cpto/`
- Google Workspace — Sheets API (service account required)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Language and Runtime
## Naming Patterns
- Python scripts use `snake_case.py` — `aggregator.py`, `auto_blocks.py`, `sheets_sync.py`, `validate_auto_blocks.py`, `utils.py`, `discover.py`
- Jekyll data files use `snake_case.yml` — `sync_status.yml`, `loe.yml`, `calendar.yml`
- Jekyll includes/layouts use `snake_case.html` — `card.html`, `sidebar.html`, `default.html`
- Generated markdown output files use `kebab-case.md` — `unified-kanban.md`, `loe-report.md`, `dependency-graph.md`, `migration-gantt.md`
- Per-project pages under `docs/_projects/` are named by repo name, e.g. `{project}.md`
- `snake_case` for all Python functions: `load_projects()`, `parse_kanban_tasks()`, `normalize_frontmatter()`, `now_iso()`, `build_loe_rows()`
- Private/internal helpers prefixed with underscore: `_status_legend()`, `_get_sheet_id()`, `_list_backup_tabs()`, `_MARKER_OPEN_RE`, `_STATUS_DEFAULTS`
- Generator functions named `generate_*`: `generate_unified_kanban()`, `generate_project_page()`, `generate_dependency_graph()`
- Render functions named `render_*`: `render_calendar()`, `render_meta_header()` in `scripts/auto_blocks.py`
- Module-level constants in `SCREAMING_SNAKE_CASE`: `ORG`, `BASE_DIR`, `REPOS_DIR`, `LOE_DATA_FILE`, `TASK_STATUSES`, `STATUS_COLORS`, `LIVE_TAB`, `STAGING_TAB`, `MAX_WRITE_RETRIES`
- Local variables in `snake_case`: `loe_rows`, `project_data`, `backup_name`, `sprint_len`
- Loop variables are short and descriptive: `project`, `task`, `row`, `ph`, `cdef`
- Type hints used consistently for function signatures in `utils.py` and `auto_blocks.py`
- Return types annotated: `-> str`, `-> dict`, `-> list[dict]`, `-> list[str]`, `-> float`, `-> bool`
- `dict[str, Any]` used for flexible YAML-parsed dicts (requires `from typing import Any`)
- `tuple[str, int, int, int, int]` for structured return values (`find_marker_pairs`)
- `Callable[[dict], str]` for renderer registry: `AUTO_BLOCK_RENDERERS` in `scripts/auto_blocks.py`
## Code Style
- No automated formatter config file detected (no `pyproject.toml`, `.flake8`, `setup.cfg`)
- Line length appears to follow PEP 8 (~88-100 chars); multiline string building uses list + `"\n".join(lines)` pattern throughout
- 4-space indentation, consistent across all scripts
- No linting config files present; `# noqa: BLE001` suppression comments appear in `sheets_sync.py` on broad `except Exception` catches, indicating awareness of linting rules (likely Ruff or flake8 BLE001 = blind exception)
## Module Organization
## Import Organization
## Error Handling
- YAML parse failures silently return `{}` or empty defaults: `except yaml.YAMLError: return {}`
- File not found is checked explicitly with `.exists()` before reading: `if kanban_path.exists():`
- Warning messages printed with `print(f"Warning: ...")` for non-fatal issues (missing kanban.md, unknown task status)
- Critical failures that should surface but not crash use `except ValueError as e: print(f"WARN: ...")` in `aggregator.py`
- Sheets sync uses a broad `except Exception` with `# noqa: BLE001` + full `traceback.format_exc()` to catch all failures while keeping the pipeline exit-0
- Retry logic in `write_with_retry()` (`scripts/sheets_sync.py`) uses exponential backoff: `delay *= 2`
- `main()` functions return `int` and the caller does `sys.exit(main())`
- `sheets_sync.py` returns `0` even on failure — intentional design to keep downstream CI steps running
- `validate_auto_blocks.py` returns `1` on errors — this is a hard CI gate
## Docstrings
## Logging
- Progress/info messages use bare `print(f"...")`: `print("KF Aggregator — Starting...")`
- Warnings use `print(f"Warning: ...")` prefix
- Errors use `print(tb, file=sys.stderr)` for full tracebacks
- Step completion uses `print(f"Generated {filename}")` pattern
- The main entry functions open and close with a name banner: `print("KF Aggregator — Starting...")` ... `print("KF Aggregator — Done!")`
## Data Flow Convention
## Frontmatter Defaults
## Text Pills Convention
## Commit Message Standard
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Overview
```text
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
- Source of truth lives in distributed per-project `kanban.md` files; this repo aggregates, never owns project data.
- GitHub Pages is the canonical, always-available dashboard; Google Sheets is a downstream consumer that never blocks the pipeline (exits 0 on failure).
- A single canonical intermediate file (`docs/_data/loe.yml`) decouples the parser (aggregator.py) from the exporter (sheets_sync.py) — "one parser, one canonical intermediate."
- Augmented pages (e.g., `migration-gantt.md`) carry a mix of hand-edited prose and auto-rendered sections marked with `<!-- AUTO:name -->` / `<!-- /AUTO:name -->` comment pairs; `auto_blocks.py` replaces only the interior of those pairs idempotently.
- All sync health is recorded in `docs/_data/sync_status.yml` and surfaced live on the dashboard sidebar and index banner.
## Layers
- Purpose: Enumerate project repos dynamically at CI runtime.
- Location: `scripts/discover.py`
- Contains: GitHub API pagination, kanban.md existence check, `repos/discovered.txt` writer.
- Depends on: `requests`, `KF_PAT` env var, `utils.ORG`, `utils.DISCOVERED_FILE`.
- Used by: `aggregate.yml` (step 1); `utils.load_projects()` fallback.
- Purpose: Parse `kanban.md` frontmatter and task tables into Python dicts.
- Location: `scripts/utils.py` — `parse_kanban_frontmatter()`, `parse_kanban_tasks()`, `normalize_frontmatter()`, `load_project_kanban()`, `load_all_project_data()`
- Contains: regex-based YAML frontmatter extractor; 4-col and 6-col Markdown table parser; effort string parser (`Nd`).
- Depends on: `pyyaml`, `repos/{project}/kanban.md` files.
- Used by: `aggregator.py`.
- Purpose: Transform parsed project data into all output docs and the canonical LOE intermediate.
- Location: `scripts/aggregator.py`
- Contains: `generate_unified_kanban()`, `generate_unified_calendar()`, `generate_loe_report()`, `generate_dependency_graph()`, `generate_project_page()`, `build_loe_rows()`, `write_loe_yaml()`.
- Depends on: `utils.py` (parsers, constants), `auto_blocks.py` (post-generation injection).
- Used by: `aggregate.yml` pipeline step.
- Purpose: Idempotently inject computed content (calendar table, meta-header) into augmented prose pages.
- Location: `scripts/auto_blocks.py`
- Contains: `AUTO_BLOCK_RENDERERS` registry (`calendar`, `meta-header`), marker parser (`find_marker_pairs()`), `inject_auto_blocks()`, `process_page()`, `load_context()`.
- Depends on: `docs/_data/*.yml` context files (especially `calendar.yml`).
- Used by: `aggregator.py` (post-generation pass); `validate_auto_blocks.py` (CI lint).
- Purpose: Export canonical LOE data to Google Sheets using a shadow-tab swap pattern.
- Location: `scripts/sheets_sync.py`
- Contains: `load_loe_from_yaml()`, `sync_to_sheets()`, shadow-tab helpers, `file_sync_failure_issue()`, `notify_chat()`.
- Depends on: `docs/_data/loe.yml` (written by aggregator; never re-parses kanban.md), `google-api-python-client`.
- Used by: `aggregate.yml` (step after Pages deploy); `sync_to_sheets.yml` (standalone weekday schedule).
- Purpose: Render markdown docs to a navigable HTML dashboard.
- Location: `docs/`
- Contains: `_layouts/default.html` (Pico CSS + MermaidJS), `_includes/sidebar.html` (project nav + sync-status badge), `_data/` (YAML data files), `_projects/*.md` (Jekyll collection), top-level view pages.
- Depends on: Pico CSS CDN, MermaidJS CDN (v11 ESM), `jekyll-feed`, `jekyll-seo-tag`.
- Used by: GitHub Pages (`gh-pages` branch).
## Data Flow
### Primary Pipeline (aggregate.yml)
### Kanban Update Push (repository_dispatch)
### Auto-Blocks Injection Sub-Flow
- Pipeline state is persisted in `docs/_data/sync_status.yml` (two sections: `aggregator`, `sheets_export`). Read-modify-write via `utils.update_sync_status()`. Both the aggregator and sheets_sync update their own section independently, so a sheets failure preserves the aggregator's recorded state.
## Key Abstractions
- Purpose: Single file per project repo that carries all project metadata (YAML frontmatter) and task data (Markdown table).
- Examples: `templates/kanban.md`, `repos/{project}/kanban.md` (cloned at runtime)
- Pattern: YAML frontmatter block (`---`) followed by a Markdown table (4-col or 6-col). Parsed by `utils.parse_kanban_frontmatter()` and `utils.parse_kanban_tasks()`.
- Purpose: Decouples kanban parser from Sheets exporter. Aggregator writes it; sheets_sync reads it. No second parse of raw kanban.md.
- Location: `docs/_data/loe.yml`
- Pattern: `{generated_at, row_count, rows: [{project, sprint, task, assignee, effort_days, start, end, status}]}`. Written by `aggregator.build_loe_rows()` / `write_loe_yaml()`.
- Purpose: Embed computed/dynamic content inside otherwise hand-edited prose documents.
- Examples: `docs/migration-gantt.md` (blocks: `meta-header`, `calendar`)
- Pattern: Page declares `auto_blocks: [name1, name2]` in frontmatter; body contains `<!-- AUTO:name -->` ... `<!-- /AUTO:name -->` marker pairs. `auto_blocks.AUTO_BLOCK_RENDERERS` maps names to renderer functions.
- Purpose: Records the last run outcome for the aggregator and sheets export; rendered live in the dashboard sidebar and index banner.
- Location: `docs/_data/sync_status.yml`
- Pattern: Two top-level YAML sections (`aggregator`, `sheets_export`). Updated by `utils.update_sync_status(section, **fields)` (read-modify-write).
## Entry Points
- Location: `.github/workflows/aggregate.yml`
- Triggers: push to master, `repository_dispatch` (kanban-updated), weekly schedule (Monday 04:00 UTC), manual dispatch.
- Responsibilities: Full pipeline — discover, clone, validate, aggregate, deploy Pages, sync Sheets, notify Chat.
- Location: `.github/workflows/sync_to_sheets.yml`
- Triggers: Weekdays 09:00 UTC schedule, manual dispatch.
- Responsibilities: Re-runs discover + clone + sheets_sync only; does not rebuild Pages.
- Location: `scripts/aggregator.py:536` (`main()`)
- Triggers: Called by `aggregate.yml`; can be run locally with cloned repos present.
- Responsibilities: Load all project data, generate all docs/ output, inject auto-blocks, write loe.yml, update sync_status.
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
### Blocking the workflow on Sheets failure
### Hardcoding project names
## Error Handling
- `validate_auto_blocks.py` exits non-zero in CI to block merges with malformed AUTO markers.
- `utils.parse_kanban_tasks()` prints a `Warning:` for unknown task statuses but continues parsing.
- `sheets_sync.py` wraps its entire `main()` body in a bare `except Exception` block, ensuring the exit code is always 0.
- `auto_blocks.inject_auto_blocks()` raises `ValueError` on mismatched/unknown markers; `aggregator.py` catches `ValueError` per page and prints `WARN:` without aborting the run (`scripts/aggregator.py:578`).
- `utils.update_sync_status()` uses read-modify-write so a partial failure in one section never erases the other section's recorded state.
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
