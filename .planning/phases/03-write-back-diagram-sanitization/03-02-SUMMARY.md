---
phase: 03-write-back-diagram-sanitization
plan: "02"
subsystem: skill
tags: [git, conflict-detection, push-auth, token-masking, tdd, python, writeback]

requires:
  - phase: 03-write-back-diagram-sanitization
    plan: "01"
    provides: split_kanban, reconstruct_kanban, apply_status_change, _content_changed, sanitize_body

provides:
  - "writeback.py: _run_git + _get_remote_url + _is_behind_origin + _push_with_auth + _write_repo"
  - "test_writeback.py: 38 new tests (bare-remote harness) covering conflict/push/idempotency/branch/sanitize-order"

affects:
  - 03-03 (batch confirm + run() + main() call _write_repo per repo from plan 02)

tech-stack:
  added: []
  patterns:
    - "_run_git arg-list wrapper: subprocess.run(['git'] + args, capture_output=True) — never shell=True"
    - "fetch-then-rev-list conflict detection: _is_behind_origin fetches FIRST to avoid stale refs (Pitfall 4)"
    - "HTTPS+KF_PAT save/restore: _push_with_auth saves SSH URL, sets HTTPS token URL in arg-list, restores in finally"
    - "Conservative conflict: fetch failure returns (True, -1) — never skip conflict check on error"
    - "_make_bare_remote() test harness: git init --bare + git clone in tempfile.mkdtemp(); no network, no org push"
    - "_write_repo orchestration: conflict -> read -> apply_status_change -> sanitize_body -> reconstruct -> idempotency gate -> write -> commit -> push"

key-files:
  created: []
  modified:
    - ".claude/skills/activity-sync/writeback.py (added _run_git, _get_remote_url, _is_behind_origin, _push_with_auth, _write_repo + sanitize_body import)"
    - ".claude/skills/activity-sync/test_writeback.py (38 new tests in 9 sections; _make_bare_remote harness)"

key-decisions:
  - "sanitize_body imported into writeback.py from sanitize.py — avoids duplicating the import and keeps writeback.py as the orchestration layer"
  - "test shim pattern for _push_with_auth: monkey-patch the module-level function to redirect pushes to the local bare file:// URL; restores original after test"
  - "branch-name read AFTER initial commit: git clone of empty bare repo is in detached HEAD before first commit; branch name is only meaningful after git commit"
  - "Invalid git subcommand (not unknown flag) for _run_git error test: git ignores unknown flags to rev-parse with rc=0; only invalid subcommands return rc!=0"

patterns-established:
  - "Token URL never printed/logged: https_url is constructed and passed directly to arg-list subprocess — never appears in print() or logging"
  - "finally-restore pattern: token URL is always cleaned up even when push fails; [WARN] on restore failure but no re-raise"
  - "Per-repo error boundary: _write_repo catches all exceptions and returns outcome='failed'; never propagates to the batch caller"

requirements-completed: [WB-03, WB-04]

duration: 10min
completed: "2026-06-04"
---

# Phase 3 Plan 02: Git Helpers + _write_repo Single-Repo Write Path Summary

**Conflict-gated (fetch + rev-list), token-masked HTTPS push with SSH-URL finally-restore, and a fully orchestrated single-repo write/commit/push — 98/98 tests GREEN against a throwaway bare git remote with zero network access**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-04T11:29:00Z
- **Completed:** 2026-06-04T11:39:26Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `_run_git()`: arg-list-only subprocess wrapper with timeout handling; mirrors reconcile.py/repo_enum.py pattern verbatim
- `_get_remote_url()`: reads `origin` remote URL for save/restore cycle
- `_is_behind_origin()`: fetches first (Pitfall 4 — stale refs), then `rev-list --count HEAD..origin/<branch>`; returns `(True, N)` if behind, `(False, 0)` if up-to-date, `(True, -1)` on fetch error (conservative — never skip conflict check)
- `_push_with_auth()`: saves SSH URL, sets HTTPS+token URL in arg-list subprocess, configures KF Bot identity, pushes `HEAD:<branch>`, restores URL in `finally`; token never printed (T-03-05)
- `_write_repo()`: full single-repo orchestrator — conflict gate → read → `apply_status_change` → `sanitize_body` → `reconstruct_kanban` → idempotency byte-compare → write → git add/commit → push → manifest-entry dict; per-repo errors caught and returned as `outcome='failed'`
- `test_writeback.py`: 38 new tests across 9 sections using `_make_bare_remote()` throwaway bare remote harness; no network, no live org push

## Task Commits

1. **Task 1+2 RED scaffold** - `7181772` (test) — RED failing imports
2. **Task 1+2 GREEN implementation** - `f695e4f` (feat) — all 98 tests GREEN

## Files Created/Modified

- `.claude/skills/activity-sync/writeback.py` — Added git constants (`GIT_TIMEOUT_SECONDS`, `_KF_ORG`), `_run_git`, `_get_remote_url`, `_is_behind_origin`, `_push_with_auth`, `_write_repo`; added `import os, subprocess`; added `from sanitize import sanitize_body`
- `.claude/skills/activity-sync/test_writeback.py` — Added `import shutil, subprocess` to imports; expanded writeback imports to include all new functions; added `_make_bare_remote()` harness and 38 new tests

## Decisions Made

- **sanitize_body imported at writeback module level**: Keeps the import chain clean — writeback.py is the orchestration layer and owns the full transformation pipeline.
- **Test shim via monkey-patching**: `_push_with_auth` is replaced at module level for tests that need to push to the local bare file:// URL instead of `github.com`. The shim is restored in a `finally` block after each test section.
- **Branch name read after initial commit**: `git clone` of an empty bare repo leaves the workdir in a detached HEAD state (`rev-parse --abbrev-ref HEAD` returns `HEAD`). The branch name is only meaningful after the first `git commit`, so the test reads it post-commit.
- **Invalid subcommand for _run_git error test**: `git rev-parse --unknown-flag` exits 0 on this git version (flags starting with `--` that are unrecognized are silently passed through in some git versions). Using an invalid subcommand (`git invalid-subcommand-xyz`) reliably returns rc=1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test uses invalid git subcommand instead of unknown flag**
- **Found during:** Task 1 (GREEN phase — first test run)
- **Issue:** `git rev-parse --bad-flag-that-does-not-exist` returned rc=0 on this git version; the test expected rc!=0.
- **Fix:** Changed test to use `git invalid-subcommand-xyz-notacommand` which reliably returns rc=1.
- **Files modified:** `.claude/skills/activity-sync/test_writeback.py`
- **Commit:** `f695e4f`

**2. [Rule 1 - Bug] Branch name read before initial commit gives detached HEAD**
- **Found during:** Task 2 (GREEN phase — `_write_repo: succeeds on branch 'main'` test)
- **Issue:** `_write_repo_on_branch("main")` read the branch name before the initial commit; a fresh clone of an empty bare repo is in detached HEAD state, so `rev-parse --abbrev-ref HEAD` returned `HEAD`, not a branch name. `git branch -m HEAD main` failed silently, leaving the local branch on `master`. The test then pushed to `origin main` (correct) but the workdir tracking ref was `master`, causing `rev-list --count HEAD..origin/main` to fail with "ambiguous argument".
- **Fix:** Moved initial `git commit` before the `rev-parse --abbrev-ref HEAD` call in `_write_repo_on_branch()`.
- **Files modified:** `.claude/skills/activity-sync/test_writeback.py`
- **Commit:** `f695e4f`

---

**Total deviations:** 2 auto-fixed (Rule 1 — test fixture bugs)
**Impact on plan:** Both were test harness issues, not implementation bugs. Implementation is correct and all behaviors verified.

## Issues Encountered

None beyond the test fixture deviations documented above.

## Known Stubs

None. All functions are fully implemented and verified:
- `_run_git`, `_get_remote_url`, `_is_behind_origin`, `_push_with_auth` — complete git helpers
- `_write_repo` — complete single-repo orchestrator with conflict/succeeded/skipped/failed outcomes

Plan 03 adds `run()`, `main()`, batch confirmation, and manifest writing on top of this complete foundation.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes introduced. The `_push_with_auth` function intentionally handles the KF_PAT token boundary (T-03-05) — this is a planned mitigation, not a new threat surface.

## Self-Check

**Created files:**
- `writeback.py`: FOUND (modified in place)
- `test_writeback.py`: FOUND (modified in place)

**Commits:**
- `7181772`: FOUND (test RED scaffold)
- `f695e4f`: FOUND (feat GREEN implementation)

## Self-Check: PASSED

## Next Phase Readiness

- Plan 03 can import `_write_repo` and call it per-repo inside `run()` after batch confirmation
- All WB-03 and WB-04 requirements fulfilled and verified against throwaway bare remotes
- SC-4 idempotency (single-repo) verified: second run with unchanged content returns `outcome='skipped'` and zero additional commits
- Token masking (T-03-05) tested: captured output of push call contains no `{token}@github.com` substring
- Branch-agnostic: `record['branch']` is passed through the full push chain; tested with both `master` and `main`

---
*Phase: 03-write-back-diagram-sanitization*
*Completed: 2026-06-04*
