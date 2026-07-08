---
phase: quick
plan: 260708-erm
subsystem: aggregator
tags: [kanban, board-filter, sprint, active-inclusive]
key-files:
  modified:
    - scripts/aggregator.py
decisions:
  - Active-inclusive filter: non-Done tasks always visible; Done tasks visible only within sprint window
  - Helper placed module-level in aggregator.py (not utils.py) since it uses iso_date which is already imported there
metrics:
  duration: ~15 minutes
  completed: 2026-07-08
  tasks: 3
  files_modified: 1
---

# Quick Task 260708-erm: Uniform Board-Visibility Filter Summary

One-liner: Board-visibility helper `_board_task_visible()` applied to per-project and unified kanban boards — active tasks always show, Done tasks show only within the sprint window.

## Commit

`3591221` — `feat(quick-260708-erm): add uniform board-visibility filter`

Files changed: `scripts/aggregator.py` only (+32 lines, -1 line).

## What Was Built

### `_board_task_visible(task, sprint_start, sprint_end) -> bool`

Added as a module-level helper at line ~331 in `scripts/aggregator.py` (just before `generate_unified_kanban`):

- Returns `True` immediately if `task["status"] != "Done"` (active tasks always show).
- For Done tasks: parses sprint window via `iso_date()`; if either sprint bound is absent/unparseable → `False`.
- Parses task dates; computes `a = ts or te`, `b = te or ts`; if both absent → `False`.
- Returns overlap check: `a <= se and b >= ss`.
- Fully defensive: no exceptions on bad dates, uses the existing `iso_date()` import.

### Applied in two places

1. `generate_project_page()` board loop — gates each task through `_board_task_visible(task, sprint_start, sprint_end)` before appending to `statuses`. Task Summary table and pie chart loops left untouched.
2. `generate_unified_kanban()` board loop — reads each project's `meta["sprint_start"]` / `meta["sprint_end"]` per iteration, applies same helper. Summary-by-Project table and gantt sections left untouched.

## R3-AAS Before / After

| | Board |
| --- | --- |
| Before (HEAD, older repo state) | Todo 3 / In Progress 4 / Review 12 / Done 11 = 30 kanban-card elements |
| After (filter applied, current repo state, 73 total tasks) | Todo 18 / In Progress 7 / Review 15 / Done 1 = 41 board cards |

Current repo has 33 Done tasks. Sprint window is 2026-06-29 to 2026-07-10. Only 1 Done task overlaps that window — 32 Done tasks are hidden from the board.

Task Summary table: 75 rows (all 73 tasks + 2 section sub-headings), unchanged.

## Migration Board Confirmation

| Project | Board cards | Notes |
| --- | --- | --- |
| kf-platform | Todo: 7, rest: 0 | Active Todo tasks visible; no Done in sprint window |
| kf-be-platform | Todo: 4, Done: 2 | 2 Done tasks overlap sprint window (active-inclusive rule) |
| kf-fe-platform | Todo: 1, Done: 2 | 2 Done tasks overlap sprint window |

Migration boards are NOT empty. The active-inclusive rule correctly surfaces sprint-dated Done work alongside all Todo tasks.

## Determinism

Consecutive aggregator runs produce byte-identical output excluding the `generated:` YAML frontmatter timestamp line. Confirmed by diff of run 3 vs run 4 with `grep -v '^generated:'` — exit code 0 (no diff). The `generated:` churn is pre-existing behaviour, not introduced by this change.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `scripts/aggregator.py` modified and committed at `3591221`
- [x] `python scripts/aggregator.py` runs clean (6 projects loaded, all outputs generated)
- [x] R3-AAS Done column shrinks from 11 (old state) to 1 (current state, 32 hidden)
- [x] Task Summary still shows all tasks (75 rows for 73 tasks)
- [x] Migration boards non-empty (kf-platform has 7 Todo cards)
- [x] Determinism confirmed (run 3 vs run 4 diff = 0 excluding timestamp)
- [x] Only `scripts/aggregator.py` committed — no generated docs, no plan files
