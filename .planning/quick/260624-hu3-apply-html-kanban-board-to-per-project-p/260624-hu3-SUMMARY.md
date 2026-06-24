---
phase: quick-260624-hu3
plan: "01"
subsystem: aggregator
tags: [kanban, css, sheets, refactor]
dependency_graph:
  requires: [260624-eqy]
  provides: [per-project-html-kanban, static-card-style, native-sheet-id]
  affects: [scripts/aggregator.py, docs/assets/css/custom.css, scripts/sheets_sync.py]
tech_stack:
  added: []
  patterns: [link_project kwarg-only param, static div card pattern]
key_files:
  modified:
    - scripts/aggregator.py
    - docs/assets/css/custom.css
    - scripts/sheets_sync.py
decisions:
  - "link_project=True default preserves unified kanban output byte-for-byte"
  - "Static card uses div not a; hover is reset to base look (no affordance)"
  - "Per-task id field removed from per-project grouping loop (was unused after mermaid removal)"
metrics:
  duration: ~10m
  completed: "2026-06-24"
  tasks_completed: 3
  files_modified: 3
---

# Phase quick-260624-hu3 Plan 01: Per-project HTML Kanban Board Summary

**One-liner:** HTML/CSS column board with static (link-free) cards replaces Mermaid kanban + status-pill system on per-project pages; unified view unchanged.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Per-project HTML kanban board via generalized _render_kanban_board | b203c86 | scripts/aggregator.py |
| 2 | Delete dead pill code and CSS, add static-card style | 0b64472 | scripts/aggregator.py, docs/assets/css/custom.css |
| 3 | Update DEFAULT_SUMMARY_SHEET_ID to native sheet id | 6c2f800 | scripts/sheets_sync.py |

## What Changed

**Task 1 — aggregator.py:**
- `_render_kanban_board` gains `*, link_project: bool = True` kwarg
- `link_project=True` (default): unchanged linked `<a class="kanban-card">` with project prefix
- `link_project=False`: `<div class="kanban-card kanban-card--static">{task}</div>`, no href, no prefix
- `generate_project_page`: removed `_status_legend()` call and entire `mermaid kanban` block; replaced with `_render_kanban_board(statuses, link_project=False)`; Task Summary, LOE Summary, Sprint Timeline gantt unchanged

**Task 2 — aggregator.py + custom.css:**
- `_status_legend()` function deleted (zero callers confirmed)
- Entire `/* ===== Status Pills ===== */` CSS block removed: `.status-legend`, `.status-pill`, four `.status-pill--*` rules
- Added `.kanban-card--static { cursor: default }` and matching `:hover` reset near existing `.kanban-card` rules

**Task 3 — sheets_sync.py:**
- `DEFAULT_SUMMARY_SHEET_ID` updated from `"11hdbqxDl-9MVEEUovS_jpGJSe52TSy19"` to `"1jLa-1Kh49ewIuPErPmIzp2dBLoGxxEvn4Fz3z_cxAaY"` (native R3Group Google Sheet)
- CI still uses `GSHEET_SUMMARY_ID` secret; this is the local fallback only
- Exit-0 invariant unaffected

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All checks passed:

- Per-project `generate_project_page` output: `kanban-card--static` present, `kanban-board` present, no `status-pill`, no `status-legend`, no mermaid kanban fence, `href=` absent from board section, no `project:` prefix on task text, Task Summary + LOE Summary retained
- Unified `generate_unified_kanban` output: linked `<a class="kanban-card">` with `project: task` text, no `kanban-card--static`
- `grep -rn "_status_legend" scripts/` empty
- `grep -n "status-pill" docs/assets/css/custom.css` empty
- `DEFAULT_SUMMARY_SHEET_ID` shows new native id, old id absent
- `ast.parse` clean for both `aggregator.py` and `sheets_sync.py`

## Self-Check: PASSED

- b203c86 exists in git log: confirmed
- 0b64472 exists in git log: confirmed
- 6c2f800 exists in git log: confirmed
- scripts/aggregator.py modified: confirmed
- docs/assets/css/custom.css modified: confirmed
- scripts/sheets_sync.py modified: confirmed
