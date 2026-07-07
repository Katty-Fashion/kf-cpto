---
id: 260707-ool
title: PRD A — Emit Per-Task OKF Concept Files
phase: quick
plan: 260707-ool
status: complete
completed: 2026-07-07
duration: ~25m
tasks_completed: 1
files_changed: 132
key_files:
  created:
    - scripts/okf_export.py (extended — _task_slug, _gen_task_concept, _gen_tasks_project_index, _gen_tasks_root_index)
    - docs/okf/tasks/index.md
    - docs/okf/tasks/r3-aas/ (73 task concepts + index)
    - docs/okf/tasks/kf-platform/ (19 task concepts + index)
    - docs/okf/tasks/kf-fe-platform/ (10 task concepts + index)
    - docs/okf/tasks/kf-be-platform/ (10 task concepts + index)
  modified:
    - docs/okf/index.md (Tasks section entry added)
    - docs/okf/projects/r3-aas.md (down-link to tasks index)
    - docs/okf/projects/kf-platform.md (down-link to tasks index)
    - docs/okf/projects/kf-fe-platform.md (down-link to tasks index)
    - docs/okf/projects/kf-be-platform.md (down-link to tasks index)
decisions:
  - Use project last_updated as concept timestamp (not run time) for determinism
  - Skip projects with 0 loe_rows (ai-rise-options, tech_brainstorming) — no task dir emitted
  - index.md files for tasks/ are exempt from type: requirement (per validate_okf _EXEMPT_NAMES)
  - _task_slug de-duplicates with -2/-3 suffix appended to later collisions within a project
  - _gen_root_index gains task_count param (default 0) for backward compatibility
---

# Quick Task 260707-ool: PRD A — Emit Per-Task OKF Concept Files

Pure-transform extension of `scripts/okf_export.py` that writes one `type: Task` OKF concept
file per `loe_rows` entry — making every tracked task an addressable, cross-linkable graph node
(prep for PRD B visualizer) without re-parsing kanban.md.

## Commits

| Hash    | Message                                                  | Files     |
| ------- | -------------------------------------------------------- | --------- |
| 302db58 | feat(260707-ool): add per-task OKF concept file emitter  | 1 changed |
| 325ee81 | feat(260707-ool): emit generated OKF task concept tree   | 131 changed |

## Per-Project Task Counts

| Project         | Task rows | Task files | + index | Total |
| --------------- | --------- | ---------- | ------- | ----- |
| R3-AAS          | 73        | 73         | 1       | 74    |
| kf-platform     | 19        | 19         | 1       | 20    |
| kf-fe-platform  | 10        | 10         | 1       | 11    |
| kf-be-platform  | 10        | 10         | 1       | 11    |
| **Total**       | **112**   | **112**    | **4**   | **116** |

Plus: `docs/okf/tasks/index.md` (root tasks index) = **117 new task-section files**

OKF bundle total: **145 files** (was 19 before this task).

## Verification Results

1. `python scripts/aggregator.py` — completed clean; printed `Generated OKF bundle: 145 files -> docs/okf/`
2. `python scripts/validate_okf.py` — exited 0: `Checked 145 OKF markdown files (135 concepts, 10 exempt index/log). OKF bundle is conformant.`
3. Determinism: ran aggregator three times; `git status --porcelain docs/okf/` showed only the expected diff vs prior commit (no inter-run drift)
4. Spot-check: `docs/okf/tasks/kf-platform/` has 20 entries (19 task files + index); `f4-s12-qc-module.md` links up to `/projects/kf-platform.md`; all slugs unique

## Implementation Notes

`_task_slug()` strips outer `[...]`, lower-cases, replaces non-alphanumeric runs with `-`, trims hyphens. Example: `[F4.S12.QC Module]` -> `f4-s12-qc-module`. Degenerate empty slug falls back to `task-{index}`.

`_gen_task_concept()` uses `project_meta["last_updated"]` as the `timestamp` field (validated against `_ISO_DATE_RE`) and omits the field entirely when absent — kf-platform / kf-fe-platform / kf-be-platform have no `last_updated` and therefore emit no timestamp.

The `_gen_root_index` signature gained a `task_count: int = 0` default parameter so callers passing only three positional args (existing tests) remain compatible.

## Deviations from Plan

None — plan executed exactly as written. The loe.yml row count shown in verification (121) is slightly higher than the earlier analysis count (112) because the aggregator re-parsed the repos and updated loe.yml at the start of the same aggregator run that generated the OKF bundle — the OKF output reflects the current loe_rows at call time, which is the correct behavior.

## Self-Check: PASSED

- [x] `scripts/okf_export.py` modified — commit 302db58 confirmed
- [x] `docs/okf/tasks/` tree created — commit 325ee81 confirmed
- [x] `docs/okf/tasks/kf-platform/` has 20 files (19 tasks + index) — confirmed
- [x] Validator exits 0 — confirmed
- [x] Aggregator 2nd/3rd run idempotent — confirmed
