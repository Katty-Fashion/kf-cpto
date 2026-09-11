---
status: complete
phase: quick-260911-gq5
plan: 01
one-liner: "Explicit GitHub Refs column (#N PR/issue numbers) drives task status for repos whose PR titles never token-match, plus header-driven Status-cell write-back fixing Note-cell corruption on non-4/6-col tables"
tags: [activity-sync, kanban-groom, reconcile, writeback, refs]
requirements: [REFS-01, REFS-02, WB-COL-01, GROOM-REFS-01, DOC-REFS-01]
key-files:
  created: []
  modified:
    - scripts/utils.py
    - .claude/skills/activity-sync/reconcile.py
    - .claude/skills/activity-sync/test_reconcile.py
    - .claude/skills/activity-sync/writeback.py
    - .claude/skills/activity-sync/test_writeback.py
    - .claude/skills/activity-sync/SKILL.md
    - .claude/skills/kanban-groom/groom.py
    - .claude/skills/kanban-groom/SKILL.md
commits:
  - hash: 3fa208d
    message: "feat(activity-sync): resolve explicit GitHub refs from kanban Refs column"
  - hash: 91b11c0
    message: "fix(activity-sync): address kanban Status cell by header column index"
  - hash: 0494f3e
    message: "feat(kanban-groom): surface Refs column and [NO-REFS] flag; document explicit refs"
metrics:
  duration: "~55min"
  completed: "2026-09-11"
---

# Quick Task 260911-gq5: Add explicit GitHub refs matching to activity-sync Summary

## What shipped

R3-AAS has 87 merged PRs and 0 issues, but its conventional-commit PR titles
never contain kanban task names, so `task_matches_signal` (token matching)
never fires there and every status on that board stayed hand-maintained. This
task adds an explicit `Refs` column (`#N` PR/issue numbers) that the
reconciler resolves against real GitHub state as a task's own definition of
done, and fixes a latent write-back bug where `apply_status_change()`
addressed the Status cell as `parts[-2]` — which is only correct for 4-col and
6-col tables and would have silently overwritten the Note cell on R3-AAS's
5-col and 7-col tables.

### Task 1 — Canonical refs parsing + explicit-reference matching (commit `3fa208d`)

- `scripts/utils.py` (the one canonical parser): added `refs`/`ref`/`pr`/`prs`/`github`
  aliases to `_COLUMN_ALIASES`; `parse_kanban_tasks()` now emits `task["refs"]`
  (raw cell string, `""` when the column is absent); added `parse_refs(text) ->
  list[int]` extracting unique `#N` numbers in first-seen order.
- `.claude/skills/activity-sync/reconcile.py`: added `_list_open_prs()`
  (mirrors `_list_merged_prs`'s pagination/rate-limit conventions, fires ONLY
  when a repo has at least one task with a non-empty Refs cell) and
  `_classify_ref()` (resolves a `#N` against merged/open PRs or a direct issue
  lookup, with an explicit guard so a closed-unmerged PR is never
  misclassified as a closed issue). `reconcile_repo()` now feeds
  explicit-reference proposals into the same `proposals` dict token matching
  already uses: all refs resolved -> Done (tier 1, signal suffixed `(ref)`);
  any open ref or partial resolution -> In Progress (tier 2); nothing
  resolved and nothing open -> no proposal. Token-matching code path is
  untouched.
- `test_reconcile.py`: added `_FakeOpenPRs` / `_SpyOpenPRs` fakes and full
  coverage of the refs behavior matrix, including the "zero refs -> zero
  `_list_open_prs` calls" and "refs present -> called" proofs.

### Task 2 — Header-driven Status cell addressing (commit `91b11c0`)

- `.claude/skills/activity-sync/writeback.py`: rewrote `apply_status_change()`
  to locate the Status column per-table via `utils._map_columns` /
  `utils._split_row` (same primitives the canonical parser uses) instead of
  assuming Status is always `parts[-2]`. A header row followed by a separator
  row sets that table's `status_idx`; the separator row itself is never
  touched. A data row under a header with no Status column is skipped with a
  `[WARN]` instead of corrupting an arbitrary cell. CR-02 (no-trailing-pipe
  skip) and WR-01 (invalid-status reject) are preserved verbatim.
- `test_writeback.py`: added 5-col (`Task/Owner/Effort/Status/Note`) and 7-col
  (`Task/Assignee/Effort/Start/End/Status/Note Stand-up`) fixtures with
  byte-identity assertions on the trailing Note cell, a no-Status-column
  fixture, and a separator-row-untouched check.

### Task 3 — Groom visibility + docs (commit `0494f3e`)

- `.claude/skills/kanban-groom/groom.py`: `cmd_list` now prints a `Refs`
  column; `_flags()` (via a new shared `_cell_of()` helper) adds `[NO-REFS]`
  when a task is In Progress/Review with an empty or dash-only refs cell; the
  `[INFO]` summary line appends `· N NO-REFS` when non-zero. `cmd_set` needed
  no code change — it already merges literal header labels into `colmap`, so
  `refs="#3, #40"` worked immediately (verified against a temp `REPOS_LOCAL`,
  never against real `repos-local/` content).
- Both `SKILL.md` files documented: the `Refs` column semantics, `[REFS]` /
  `[NO-REFS]` text pills, the closed-unmerged-PR guard, the bounded-API-call
  guarantee, and worked examples.

## Test results (honest, exact counts)

Run from repo root with `venv/bin/python` (Python 3.9):

- `.claude/skills/activity-sync/test_reconcile.py` — **140 passed, 0 failed**
- `.claude/skills/activity-sync/test_writeback.py` — **206 passed, 0 failed**
- `scripts/test_generate_kanban.py` — **59 passed, 1 failed**
  ("invalid end falls back to duration" — confirmed via `git stash` to be a
  **pre-existing failure on master, unrelated to this task's files**
  (`generate_kanban.py` was never touched by this plan). Out of scope per the
  executor's scope-boundary rule; logged here rather than silently ignored,
  not fixed.)
- `scripts/validate_auto_blocks.py` — exit 0, "All augmented pages are clean."
- Smoke import (`utils, aggregator, auto_blocks`) — `ok`
- `venv/bin/python .claude/skills/kanban-groom/groom.py list R3-AAS` — read-only
  smoke passed (30 tasks, 5 `[NO-REFS]`); no writes to `repos-local/`.

## Deviations from Plan

None — plan executed exactly as written. The one pre-existing test failure
(`test_generate_kanban.py::gantt invalid-date fallback`) predates this task
(reproduced identically via `git stash`) and touches a file (`generate_kanban.py`)
outside this plan's `files_modified` list, so per the SCOPE BOUNDARY rule it was
left unfixed and is documented here instead.

## Constraint verification

- No emojis introduced anywhere (`git diff` scanned for emoji code points — none found).
- No `from __future__ import annotations` added to `scripts/utils.py`; no `X | None`
  runtime annotations added there.
- `docs/_data/loe.yml`, `build_loe_rows`, `write_loe_yaml`, and `.github/workflows/*`
  untouched (verified via `git diff` against the pre-task commit).
- `repos-local/` untouched — `git status --porcelain -- repos-local/` empty throughout
  (Task 3's `set` verification ran against a tempdir `REPOS_LOCAL`).
- One conventional commit per task, in task order (`3fa208d`, `91b11c0`, `0494f3e`).

## Known Stubs

None.

## Threat Flags

None — all STRIDE dispositions in the plan's threat register (T-gq5-01
through T-gq5-06, T-gq5-SC) were implemented as specified: `_REF_RE` extracts
digits only (no free text reaches the issue URL); `_classify_ref` guards the
`pull_request` key before ever reading `state == "closed"`; `merged_by_number`
is populated only after the existing `_is_merge_reachable` gate passes;
`apply_status_change` addresses columns via header mapping with byte-identity
tests on Note cells; no new dependencies were introduced.

## Self-Check: PASSED

- FOUND: scripts/utils.py
- FOUND: .claude/skills/activity-sync/reconcile.py
- FOUND: .claude/skills/activity-sync/test_reconcile.py
- FOUND: .claude/skills/activity-sync/writeback.py
- FOUND: .claude/skills/activity-sync/test_writeback.py
- FOUND: .claude/skills/activity-sync/SKILL.md
- FOUND: .claude/skills/kanban-groom/groom.py
- FOUND: .claude/skills/kanban-groom/SKILL.md
- FOUND: commit 3fa208d
- FOUND: commit 91b11c0
- FOUND: commit 0494f3e
