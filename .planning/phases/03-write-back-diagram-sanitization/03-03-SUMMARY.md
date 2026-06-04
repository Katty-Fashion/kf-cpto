---
phase: 03-write-back-diagram-sanitization
plan: "03"
subsystem: skill
tags: [git, batch-confirm, recovery-manifest, run-main, tdd, python, writeback]

requires:
  - phase: 03-write-back-diagram-sanitization
    plan: "02"
    provides: _write_repo + all git helpers (conflict/push/idempotency)

provides:
  - "writeback.py: MANIFESTS_DIR, _confirm_batch, _write_manifest, run(), main()"
  - "test_writeback.py: 44 new tests (batch confirm + manifest + run/main); 142 total"
  - "SKILL.md: Phase 3 write-back command + [CONFLICT] + manifest + SC-1 human-UAT note"

affects:
  - "WB-02: single batch-confirm gate before any push"
  - "WB-05: per-run JSON recovery manifest in gitignored manifests/ dir"

tech-stack:
  added:
    - "json (stdlib) — manifest serialization"
    - "datetime.timezone (stdlib) — UTC run_id timestamp"
  patterns:
    - "run(proposals, dry_run) composition: enum_run -> _confirm_batch (once) -> per-repo _write_repo (continue-after-conflict) -> _write_manifest -> tally"
    - "KF_PAT read at push time inside run() only — never at import time (T-03-12)"
    - "module-level input() shadow: _wb.input = stub enables single-prompt testing without patching builtins"
    - "os.environ KF_PAT set in test for non-dry-run path; unset after via pop()"

key-files:
  created: []
  modified:
    - ".claude/skills/activity-sync/writeback.py (added MANIFESTS_DIR, _confirm_batch, _write_manifest, run, main, _confirm_batch_preview, _enum_records_fallback_writeback; updated module docstring and imports)"
    - ".claude/skills/activity-sync/test_writeback.py (44 new tests in 7 sections; fixed relative_to dead code; KF_PAT env stub for non-dry-run path)"
    - ".claude/skills/activity-sync/SKILL.md (updated description; added Phase 3 write-back section; SC-1 UAT note; updated script locations table)"

decisions:
  - "module-level input() shadow: _wb.input = stub to test confirm prompt count — avoids patching builtins and keeps test isolation clean"
  - "dry_run path calls _confirm_batch_preview() (no input()) rather than skipping confirmation entirely — gives operator a preview even in dry mode"
  - "KF_PAT read inside run() at push time (after confirmation), not in main() — matches T-03-12 requirement (fail-fast only when a real push would occur)"
  - "continue-after-conflict loop: sorted(proposals_by_repo.items()) for deterministic order in tests"

metrics:
  duration: ~9min
  completed: "2026-06-04"
  tasks: 2
  files_modified: 3
---

# Phase 3 Plan 03: Batch Orchestration + Recovery Manifest + run()/main() Summary

**Single batch-confirm table + per-run JSON recovery manifest + continue-after-conflict run()/main() orchestration — 142/142 tests GREEN; SKILL.md documents write path and SC-1 human-UAT gate**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-06-04T11:43:25Z
- **Completed:** 2026-06-04T11:52:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `MANIFESTS_DIR`: `Path(__file__).parent / "manifests"` — gitignored by Plan 01; verified via `git check-ignore`
- `_confirm_batch(proposals_by_repo)`: prints ONE `[INFO]` summary table (repo × task × old→new) and reads a SINGLE `input()` prompt per run — never inside the per-repo loop; returns True/False (WB-02; T-03-09)
- `_confirm_batch_preview(proposals_by_repo)`: same table display without prompting — used by dry_run path
- `_write_manifest(manifests_dir, run_id, repos_results)`: writes `{run_id}.json` with run_id, UTC timestamp, total_repos, summary tally (succeeded/failed/conflict/skipped), and repos list; OSError non-fatal — prints Warning, run continues (WB-05)
- `run(proposals, dry_run=False)`: full batch orchestrator — groups by repo, calls enum_run() once, single batch confirm, KF_PAT env fail-fast at push time (T-03-12), loops with continue-after-conflict, writes manifest, prints [TALLY]; returns list of manifest-entry dicts (no sys.exit)
- `main()`: argparse `--dry-run`; delegates to `reconcile.run()` then `writeback.run()`; maps success/RuntimeError to exit codes; ends with `if __name__ == "__main__": sys.exit(main())`
- `SKILL.md` Phase 3 section: write-back command + `--dry-run` + output pills + manifest schema + [CONFLICT] handling + environment variable table + [IMPORTANT] SC-1 human-validated UAT note

## Task Commits

1. **Task 1+2 RED scaffold** - `f2e472e` (test) — RED failing imports + all new tests
2. **Task 1+2 GREEN implementation** - `b2754ed` (feat) — all 142 tests GREEN; SKILL.md updated

## Files Created/Modified

- `.claude/skills/activity-sync/writeback.py` — Added `MANIFESTS_DIR`, `json`, `datetime/timezone` imports; `_confirm_batch`, `_confirm_batch_preview`, `_write_manifest`, `run`, `_enum_records_fallback_writeback`, `main`; updated module docstring; `if __name__ == "__main__": sys.exit(main())`
- `.claude/skills/activity-sync/test_writeback.py` — Extended imports with `_confirm_batch, _write_manifest, MANIFESTS_DIR, run, main`; 7 new test sections (44 new tests); fixed dead `relative_to` code; added `os.environ["KF_PAT"]` for non-dry-run test path
- `.claude/skills/activity-sync/SKILL.md` — Updated frontmatter description; Phase 3 write-back section; updated script locations table

## Decisions Made

- **module-level input() shadow**: `_wb.input = stub` at the writeback module level shadows the builtin `input()` for test purposes. This avoids patching the global builtins dict (fragile) and keeps test isolation clean — each test sets and removes the stub around its run.
- **dry_run calls _confirm_batch_preview (no prompt)**: consistent user experience — dry mode shows the same summary table as live mode but skips the y/N gate. The operator sees exactly what would be written.
- **KF_PAT read after confirmation, not in main()**: the token is needed only if the user confirms a non-dry run. Reading it in main() would check it before the batch-confirm table is shown, which violates the principle of "fail on the thing you actually need, when you need it."
- **continue-after-conflict loop uses sorted() for deterministic test order**: ensures manifest entries appear in a consistent order across Python dict iteration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test's `_manifest_file.relative_to(repo_root)` raised ValueError — tmpdir outside repo**
- **Found during:** Task 1 GREEN (test run)
- **Issue:** The manifest was written to a `tempfile.mkdtemp()` path (`/tmp/...`), which is not under the kf-cpto repo root (`/Users/machina/Dev/kf-cpto`). `relative_to()` raised `ValueError`. The line was dead code (the result was never used).
- **Fix:** Removed the dead `relative_to()` call; the gitignore test now goes directly to `MANIFESTS_DIR / "test-run-gitignore.json"` which is under the repo root.
- **Files modified:** `.claude/skills/activity-sync/test_writeback.py`
- **Commit:** `b2754ed`

**2. [Rule 1 - Bug] continue-after-conflict test hung on missing KF_PAT env var**
- **Found during:** Task 2 GREEN (first full test run)
- **Issue:** `run(..., dry_run=False)` with non-empty proposals reaches the KF_PAT env check. In the test environment `KF_PAT` is unset, so `run()` printed `[ERROR]` and raised `RuntimeError` — but the test had no try/except, causing a hang-looking failure (the test section printed its header then went silent because RuntimeError propagated uncaught at module level).
- **Fix:** Added `os.environ["KF_PAT"] = "DUMMY_TOKEN_FOR_TESTS"` before the `run()` call in the continue-after-conflict test; cleaned up with `os.environ.pop("KF_PAT", None)` in the cleanup block.
- **Files modified:** `.claude/skills/activity-sync/test_writeback.py`
- **Commit:** `b2754ed`

---

**Total deviations:** 2 auto-fixed (Rule 1 — test harness bugs)
**Impact on plan:** Both were test infrastructure issues. Implementation is correct and all behaviors verified.

## Known Stubs

None. All functions are fully implemented and verified:
- `_confirm_batch`: single-prompt batch confirmation (WB-02)
- `_write_manifest`: non-raising recovery manifest writer (WB-05)
- `run()`: full batch orchestrator with continue-after-conflict and manifest
- `main()`: CLI entry point with --dry-run; delegates to reconcile.run() + run()

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes beyond what was planned in the threat model:
- T-03-09 (unconfirmed batch push): mitigated by `_confirm_batch` single-prompt gate + tests assert exactly one prompt
- T-03-10 (no partial-failure record): mitigated by `_write_manifest` + continue-after-conflict; every repo outcome is recorded
- T-03-11 (manifest committed): mitigated; `manifests/` is gitignored (Plan 01); `git check-ignore` verified in tests
- T-03-12 (KF_PAT at import time): mitigated; `os.environ.get("KF_PAT")` is inside `run()`, after confirmation, never at import time or in dry-run path
- T-03-13 (one failure stops batch): mitigated; `_write_repo` never raises; loop continues past conflict/failure

## Self-Check

**Files exist:**
- `writeback.py`: FOUND (modified in place)
- `test_writeback.py`: FOUND (modified in place)
- `SKILL.md`: FOUND (modified in place)

**Commits:**
- `f2e472e`: FOUND (test RED scaffold)
- `b2754ed`: FOUND (feat GREEN implementation)

## Self-Check: PASSED
