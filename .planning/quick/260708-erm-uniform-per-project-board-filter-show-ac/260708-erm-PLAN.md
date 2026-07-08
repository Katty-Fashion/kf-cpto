---
phase: quick
plan: 260708-erm
type: auto
autonomous: true
---

# 260708-erm — Uniform Board-Visibility Filter

## Objective

Add a uniform `_board_task_visible()` helper to `scripts/aggregator.py` so per-project
and unified kanban boards show only current-sprint / active work instead of dumping
every task. Done tasks outside the sprint window are dropped from boards but remain
in Task Summary tables and pie charts.

## Rule

A task is VISIBLE ON THE BOARD if EITHER:
- (a) ACTIVE — status is not "Done" (Todo / In Progress / Review), OR
- (b) DATED within the project's sprint window — [start, end] OVERLAPS [sprint_start, sprint_end].

Old or undated Done tasks are dropped from boards. Summaries and pies are unchanged.

## Tasks

### Task 1 — Add `_board_task_visible()` helper

Add a module-level, typed helper in `scripts/aggregator.py`:

```python
def _board_task_visible(task: dict, sprint_start, sprint_end) -> bool:
    """Return True if task should appear on the kanban board.

    Active tasks (not Done) always show. Done tasks only show if they are
    dated within the project's current sprint window [sprint_start, sprint_end].
    """
    if str(task.get("status", "")).strip() != "Done":
        return True
    ss = iso_date(sprint_start)
    se = iso_date(sprint_end)
    if ss is None or se is None:
        return False
    ts = iso_date(task.get("start"))
    te = iso_date(task.get("end"))
    a = ts or te
    b = te or ts
    if a is None:
        return False
    return a <= se and b >= ss
```

### Task 2 — Apply filter in `generate_project_page()`

In the board-building loop (~line 593), gate each task through `_board_task_visible()`.
The Task Summary table and pie emit ALL tasks — no change there.

### Task 3 — Apply filter in `generate_unified_kanban()`

In the cross-project board-building loop (~line 350), apply the same helper per task
using each project's own `meta["sprint_start"]` / `meta["sprint_end"]`.

## Verification

- `python scripts/aggregator.py` runs clean.
- R3-AAS board shrinks (Done cards outside sprint window removed).
- Migration boards (kf-platform, kf-fe, kf-be) NOT empty (Todo tasks always visible).
- Task Summary + pie still show ALL tasks.
- Determinism: two consecutive runs produce identical output (only `generated:` timestamp differs).

## Commit

Atomic: `scripts/aggregator.py` only. Do NOT commit generated docs or plan files.
