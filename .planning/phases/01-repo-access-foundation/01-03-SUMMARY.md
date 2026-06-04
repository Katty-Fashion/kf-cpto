---
phase: 01-repo-access-foundation
plan: "03"
subsystem: infra
tags: [python, git, subprocess, kanban-parser, repos-local]

requires:
  - phase: 01-repo-access-foundation plan 01
    provides: gitignore fine-grained exclusion enabling .claude/skills/ to be tracked
  - phase: 01-repo-access-foundation plan 02
    provides: repos-local/ populated with 6 full SSH clones via bootstrap.py

provides:
  - repo_enum.py: read-only pipeline enumerating repos-local/ membership at runtime
  - run() -> list[dict]: importable Phase 2 callable returning structured repo records
  - REPO-01: runtime repo enumeration by repos-local/ scan (no static list)
  - REPO-02: git fetch origin per repo before read with up-to-date/new-commits logging
  - REPO-03: canonical utils parser reuse via sys.path injection (no second parser)

affects: [02-activity-mining, 03-write-back, phase-02]

tech-stack:
  added: []
  patterns:
    - "sys.path injection (4 .parent) to import scripts/utils.py from skill modules"
    - "Before/after origin/<branch> SHA comparison for fetch-new-commit detection"
    - "run() -> list[dict] importable callable; main() delegates to run(); sys.exit(main())"
    - "valid_task_count = sum(1 for t in tasks if t['status'] in TASK_STATUSES) for aggregator parity"

key-files:
  created:
    - .claude/skills/activity-sync/repo_enum.py
  modified: []

key-decisions:
  - "repo_enum.py contains NO static repo list — repos-local/ membership is the tracked set (REPO-01)"
  - "Parity check uses valid-status count not total row count (R3-AAS: 181 rows, 0 valid — expected)"
  - "run() is the Phase 2 importable entry; main() delegates to it; no sys.exit inside run()"
  - "from __future__ import annotations at top of file for Python 3.9 compatibility with PEP 604 str | None"

patterns-established:
  - "Pattern: _run_git() private subprocess wrapper — arg-list only, no shell=True"
  - "Pattern: _fetch_repo() returns 'up-to-date'/'new-commits'/'fetch-failed'; fetch failure is non-fatal"
  - "Pattern: _assert_kf_cpto_clean() raises RuntimeError if porcelain output non-empty"
  - "Pattern: enumerate_repos() scans repos-local/ iterdir(); skips non-git with Warning:"

requirements-completed: [REPO-01, REPO-02, REPO-03]

duration: 3min
completed: 2026-06-04
---

# Phase 01 Plan 03: Repo Enum Summary

**repo_enum.py read-only pipeline: runtime repos-local/ enumeration, git fetch with SHA comparison, canonical utils.py parser reuse, clean-tree assertion, and importable run() -> list[dict] for Phase 2**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-04T07:25:52Z
- **Completed:** 2026-06-04T07:28:53Z
- **Tasks:** 2 (1 implementation, 1 checkpoint auto-verified)
- **Files modified:** 1 created

## Accomplishments

- Created `.claude/skills/activity-sync/repo_enum.py` (288 lines) satisfying all four phase success criteria
- Live run confirmed: 6 repos enumerated with (name, local_path, remote_url) tuples; all fetched up-to-date; kf-platform parity = 39 (cross-check matched); R3-AAS 0 valid-status (expected, non-error); kf-cpto tree CLEAN
- Checkpoint pre-authorized and verified deterministically — all criteria passed without human intervention

## Task Commits

1. **Task 1: Write repo_enum.py read-only pipeline** - `0c9df86` (feat)
2. **Task 2: Checkpoint — live run (pre-authorized, auto-verified)** - no code change

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `.claude/skills/activity-sync/repo_enum.py` — Read-only pipeline: enumerate repos-local/, fetch per repo (before/after SHA), parse kanban.md via utils parsers, assert clean tree, return list[dict] for Phase 2

## Decisions Made

- Kept all forbidden strings (load_project_kanban, symbolic-ref, shell=True, len(tasks)) out of source entirely — even from comments — because the plan's static verification does a plain string search
- Used `from __future__ import annotations` at top of file ensuring PEP 604 `str | None` annotations defer on Python 3.9 venv
- run() is the sole Phase 2 importable callable; main() delegates to it ensuring no sys.exit in the importable path

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed forbidden strings from inline comments**
- **Found during:** Task 1 static verification
- **Issue:** The plan's automated static check (`assert 'load_project_kanban' not in src`) does a plain-string search on the entire file. Initial implementation had reference strings in docstrings and comments (e.g. "Does NOT call load_project_kanban()", "NOT len(tasks)", "NOT symbolic-ref refs/remotes/origin/HEAD", "no shell=True") — each causing the assertion to fail.
- **Fix:** Rephrased all four offending comments to convey the same intent without using the forbidden string literal. Three separate inline edits.
- **Files modified:** .claude/skills/activity-sync/repo_enum.py
- **Verification:** Static check prints PASS
- **Committed in:** 0c9df86 (Task 1 commit — all edits were pre-commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — verification failure from comment phrasing)
**Impact on plan:** No scope change. Comments rephrased; behavior unchanged.

## Issues Encountered

None beyond the comment-phrasing deviation documented above.

## User Setup Required

None — no external service configuration required. repos-local/ was already populated by Plan 02.

## Next Phase Readiness

- Phase 2 (activity mining) can `from repo_enum import run` and consume the structured records immediately
- All 6 repos enumerated with correct branch detection (main/master mix handled)
- R3-AAS non-standard kanban format handled gracefully (0 valid-status, [INFO] logged)
- Phase access foundation is complete: REPO-01, REPO-02, REPO-03 all satisfied

---
*Phase: 01-repo-access-foundation*
*Completed: 2026-06-04*
