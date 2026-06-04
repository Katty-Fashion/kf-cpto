---
phase: 01-repo-access-foundation
plan: "04"
subsystem: activity-sync/repo_enum
tags: [gap-closure, repo-enumeration, marker-check, SC-1, REPO-01]
dependency_graph:
  requires: [01-01, 01-02, 01-03]
  provides: [enumerate_repos-marker-filter]
  affects: [.claude/skills/activity-sync/repo_enum.py]
tech_stack:
  added: []
  patterns: [runtime-marker-presence-check, Path.exists-guard]
key_files:
  created: []
  modified: [.claude/skills/activity-sync/repo_enum.py]
decisions:
  - "Marker check placed inside enumerate_repos() after _is_git_repo() guard, before appending — READ-ONLY; no seeding here (seeding remains bootstrap.py's responsibility)"
  - "Warning message matches ROADMAP SC-1 text exactly: '{name} missing required markers (kanban.md + notify-kf-cpto.yml) — skipping'"
  - "Committed untracked 01-VERIFICATION.md to clean the working tree for the probe run (Rule 3 auto-fix)"
metrics:
  duration: "~5 minutes"
  completed: "2026-06-04"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
---

# Phase 01 Plan 04: Marker-Presence Filter for enumerate_repos() Summary

**One-liner:** Runtime kanban.md + notify-kf-cpto.yml existence guard in enumerate_repos() closes SC-1 / REPO-01 without static list or seeding logic.

## What Was Built

Patched `enumerate_repos()` in `.claude/skills/activity-sync/repo_enum.py` (lines 186-210) to check for both required markers after the `_is_git_repo()` guard. A git repo under `repos-local/` that is missing either `kanban.md` or `.github/workflows/notify-kf-cpto.yml` is now skipped with an exact Warning instead of silently enumerated. The 6 currently-cloned real repos carry both markers and are unaffected.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add marker-presence filter to enumerate_repos() | bd16702 | .claude/skills/activity-sync/repo_enum.py |
| 2 | Prove skip-on-missing-marker + happy-path no-regression | bd16702 (probe run only, no new files) | gap-probe-marker-skip.sh executed; all assertions passed |

## Verification Results

- `grep -c 'notify-kf-cpto' repo_enum.py` (non-comment) = **3** (was 0 before this plan)
- `grep -c 'TRACKED_REPOS' repo_enum.py` = **0** (no static list introduced)
- Module imports cleanly under Python 3.9.6
- Probe output:
  ```
  Warning: __gap_probe__ missing required markers (kanban.md + notify-kf-cpto.yml) — skipping
  OK skip+noregress: ['R3-AAS', 'ai-rise-options', 'kf-be-platform', 'kf-fe-platform', 'kf-platform', 'tech_brainstorming']
  TREE CLEAN — gap probe PASSED
  ```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Untracked 01-VERIFICATION.md caused dirty tree for probe**
- **Found during:** Task 2 (first probe run)
- **Issue:** `.planning/phases/01-repo-access-foundation/01-VERIFICATION.md` existed on disk (created during prior verification pass) but was never staged/committed, making `git status --porcelain` non-empty. The live `repo_enum.py` run calls `_assert_kf_cpto_clean()` which raises a `RuntimeError` and exits 1, causing the probe to fail with `LIVE RUN FAILED (non-zero exit)`.
- **Fix:** Committed `01-VERIFICATION.md` (commit 53e034b) to clean the working tree, then re-ran the probe successfully.
- **Files modified:** `.planning/phases/01-repo-access-foundation/01-VERIFICATION.md`
- **Commit:** 53e034b

## Known Stubs

None. No placeholder data, TODOs, or incomplete implementations.

## Threat Flags

None. The change is purely read-only (`Path.exists()` checks only); no new network endpoints, auth paths, or file writes introduced.

## Self-Check: PASSED

- [x] `.claude/skills/activity-sync/repo_enum.py` exists and contains `notify-kf-cpto`
- [x] Commit bd16702 exists: `git log --oneline | grep bd16702` confirmed
- [x] Commit 53e034b exists: `git log --oneline | grep 53e034b` confirmed
- [x] No static TRACKED_REPOS added
- [x] Python 3.9 import clean
- [x] Probe final line: `TREE CLEAN — gap probe PASSED`
- [x] SC-1 / REPO-01 gap closed
