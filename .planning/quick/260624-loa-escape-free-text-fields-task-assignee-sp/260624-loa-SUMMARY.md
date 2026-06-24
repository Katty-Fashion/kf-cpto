---
phase: quick-260624-loa
plan: "01"
subsystem: aggregator
tags: [security, hardening, markdown, yaml, escaping]
dependency_graph:
  requires: []
  provides: [_md_cell helper, YAML-safe frontmatter description]
  affects: [scripts/aggregator.py]
tech_stack:
  added: [import json]
  patterns: [_md_cell for Markdown table cell escaping, json.dumps for YAML scalar safety]
key_files:
  modified: [scripts/aggregator.py]
decisions:
  - "_md_cell escapes & before < and > (ampersand-first order prevents double-encoding)"
  - "json.dumps(description) chosen for frontmatter: valid YAML flow scalar, handles embedded quotes and newlines natively"
  - "sprint_period left unescaped in Status table (computed from already-escaped sprint_start/sprint_end meta values that are validated as ISO dates)"
  - "deps_display, builder_link, edit_url, numeric/effort totals, kanban board cards, Mermaid helpers left untouched per plan constraints"
metrics:
  duration: "~10m"
  completed: "2026-06-24"
  tasks_completed: 2
  tasks_total: 2
---

# Phase quick-260624-loa Plan 01: Free-text Markdown/YAML escaping Summary

**One-liner:** Added `_md_cell()` helper to neutralize `&<>|` and CR/LF in Markdown table cells, and switched project-page `description` frontmatter to `json.dumps()` for YAML-safe scalar emission.

## Tasks Completed

| Task | Description | Commit |
| --- | --- | --- |
| 1 | Add `_md_cell` helper + wrap free-text Markdown interpolations | 5c0ce0c |
| 2 | Emit YAML-safe `description` frontmatter via `json.dumps` | 5c0ce0c |

Both tasks were committed atomically in a single commit (Tasks 1 and 2 are tightly coupled — `import json` belongs with the `json.dumps` change, and both touch `generate_project_page`).

## Changes Made

### `_md_cell(value: str) -> str` helper (new, after `_html_escape`)

Coerces to str, then applies in order:
- `&` -> `&amp;` (ampersand first, before other replacements)
- `<` -> `&lt;`
- `>` -> `&gt;`
- `|` -> `\|` (Markdown column-delimiter escape)
- `\r` and `\n` -> single space (no multi-line cells)

### Wrapped interpolation points

| Function | Cell(s) wrapped |
| --- | --- |
| `generate_unified_kanban` Summary table | `project` |
| `generate_loe_report` per-project table | `project`, `sprint` |
| `generate_loe_report` assignee table | `assignee` |
| `generate_project_page` frontmatter | `description` via `json.dumps` (not `_md_cell`) |
| `generate_project_page` body quote line | `description` |
| `generate_project_page` Status table | `type_display`, `po`, `lead`, `sprint`, each tag in `tags` |
| `generate_project_page` Task Summary 6-col | `task['task']`, `task['assignee']`, `task.get('start','')`, `task.get('end','')` |
| `generate_project_page` Task Summary 4-col | `task['task']`, `task['assignee']` |
| `generate_dependency_graph` legend | `display` |

### Untouched (per plan constraints)

- `deps_display` (Markdown links with `relative_url`)
- `builder_link`, `edit_url` (constructed URLs)
- `numeric`/`effort`/`total` values, `count_cols`
- `_render_kanban_board` cards (already `_html_escape`'d)
- `mermaid_label_safe`, `mermaid_gantt_label` (own escaping)
- `sprint_period` (derived from ISO-validated meta fields)

## Verification Results

Both plan `<automated>` verifications passed:

```
TASK1 OK  — raw <script> absent; escaped pipe does not add a column (6 total | - 1 \| = 5 delimiter boundaries for 4-col table)
TASK2 OK  — yaml.safe_load round-trips description with embedded quote and newline
```

Syntax check clean:
```
python -c "import ast; ast.parse(open('scripts/aggregator.py').read())"  -> clean
```

## Deviations from Plan

None — plan executed exactly as written. Both tasks committed together in one atomic commit (they are logically inseparable: `import json` + `json.dumps` change).

## Known Stubs

None.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The changes are purely output-escaping on existing code paths — they reduce the trust surface rather than expanding it.

## Self-Check: PASSED

- [x] `scripts/aggregator.py` exists and contains `def _md_cell`
- [x] Commit `5c0ce0c` exists on `worktree-agent-a0dea9e885d8e51e5`
- [x] Both automated verifications printed OK
- [x] Syntax check clean
