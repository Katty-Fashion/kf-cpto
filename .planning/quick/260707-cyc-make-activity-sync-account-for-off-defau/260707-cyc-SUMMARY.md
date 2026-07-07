---
phase: quick-260707-cyc
plan: 01
subsystem: activity-sync
tags: [reconciler, integration-branches, tier-1, tier-2, testing, readme]
key-files:
  created: []
  modified:
    - .claude/skills/activity-sync/reconcile.py
    - .claude/skills/activity-sync/test_reconcile.py
    - .claude/skills/activity-sync/SKILL.md
    - README.md
decisions:
  - "INTEGRATION_BRANCH_GLOBS is the single config point — no per-repo override map, no hardcoded repo or branch names in logic paths"
  - "Tier-1 iterates integration set, short-circuits on first True (any-branch semantics); conservative gate preserved (True only counts)"
  - "Tier-2 filters integration_branches from active-branch scan via set membership — default_branch was already excluded by _list_remote_branches; extras excluded explicitly"
  - "_integration_branches reuses _list_remote_branches to avoid a second for-each-ref call"
metrics:
  duration: "~10 min"
  completed: "2026-07-07"
  tasks: 3
  files: 4
---

# Quick Task 260707-cyc: Make Activity Sync Account for Off-Default Integration Branches

Activity-sync's reconciler now treats `uat`, `work`, and `*-migration` branches as integration targets — merges reachable from any of these are reported Done, and they are excluded from the Tier-2 active-branch scan so finished work is never demoted to In Progress.

## What Was Built

**reconcile.py** — INTEGRATION_BRANCH_GLOBS constant + integration-branch set logic:
- Added `import fnmatch` (stdlib, alongside `import re`)
- Added `INTEGRATION_BRANCH_GLOBS = ["uat", "work", "*-migration"]` with explanatory comment at module constants block; no hardcoded repo/branch names in logic
- Added `_integration_branches(repo_path, default_branch) -> list[str]` helper: builds `{default_branch}` union with glob-matched extras from `_list_remote_branches`
- Tier-1: replaces single `_is_merge_reachable(..., default_branch)` call with a loop over `integration_branches`, short-circuiting on first True
- Tier-2: filters `integration_branches` set from the `remote_branches` list before the task-match loop

**test_reconcile.py** — 3 new tests (91 pre-existing + 7 new = 98 total):
- Added `_FakeReachableByBranch` context manager: `lambda path, sha, branch: mapping.get(branch)`
- Test A: merge reachable only via `*-migration` branch → Tier-1 Done (not In Progress)
- Test B: integration branch excluded from Tier-2 → no proposal emitted
- Test C: plain feature branch (not matching globs) still surfaces as Tier-2 In Progress

**SKILL.md** — `[NOTE]` added in RECONCILE section's [TIER-1]/[TIER-2] bullets documenting the INTEGRATION-BRANCH SET contract; references `INTEGRATION_BRANCH_GLOBS`; text-pills convention preserved

**README.md** — How-It-Works mermaid diagram now has 6 repo nodes (A–F) each with `|push trigger| GHA` edge; added `ai-rise-options` and `tech_brainstorming`; generator discipline-split statement untouched

## Commits

| Task | Commit | Files |
|------|--------|-------|
| T1: reconcile.py integration-branch set | bba5f23 | `.claude/skills/activity-sync/reconcile.py` |
| T2: test_reconcile.py 3 new tests | 4a055f0 | `.claude/skills/activity-sync/test_reconcile.py` |
| T3: README 6-node diagram + SKILL.md note | c0cda38 | `README.md`, `.claude/skills/activity-sync/SKILL.md` |

## Verify Output

### Task 1 verify (INTEGRATION_BRANCH_GLOBS + helper importable)
```
['uat', 'work', '*-migration']
_integration_branches
```

### Task 2 verify (test suite exit 0, all PASS)
```
--- reconcile_repo integration-branch set ---
  PASS: Test A: non-default integration branch Done -> 1 proposal
  PASS: Test A: new_status is Done
  PASS: Test A: tier is 1
  PASS: Test B: integration branch excluded from Tier-2 -> no proposal
  PASS: Test C: plain feature branch -> 1 proposal
  PASS: Test C: new_status is In Progress
  PASS: Test C: tier is 2

--- Results: 98 passed, 0 failed ---
```

### Task 3 verify (grep gate)
```
OK
```

## Deviations from Plan

None — plan executed exactly as written.

## Security Posture

All branch/sha values continue to flow only into arg-list `_run_git` calls. No `shell=True` introduced. No f-string interpolation into shell commands. The integration branch loop adds no new shell-interpolation surface: `_ib` is passed as a positional arg to `_is_merge_reachable`, which passes it as `f"origin/{default_branch}"` into `_run_git`'s arg list.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. Changes are logic-only within the existing reconcile.py execution model.

## Self-Check: PASSED

- `.claude/skills/activity-sync/reconcile.py` — FOUND (bba5f23)
- `.claude/skills/activity-sync/test_reconcile.py` — FOUND (4a055f0)
- `.claude/skills/activity-sync/SKILL.md` — FOUND (c0cda38)
- `README.md` — FOUND (c0cda38)
- All 3 commits confirmed in git log
