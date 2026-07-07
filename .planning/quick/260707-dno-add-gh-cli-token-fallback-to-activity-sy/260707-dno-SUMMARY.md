---
id: 260707-dno
title: Add gh CLI token fallback to activity-sync
date: 2026-07-07
status: complete
tags: [activity-sync, security, local-dev, token-resolution]
key-decisions:
  - Three-step token resolution (KF_PAT -> GITHUB_TOKEN -> gh auth token) keeps CI unchanged while enabling gh-authenticated local dev
  - subprocess arg-list only, 5s timeout, never logs token or stderr (T-02-05)
  - _FakeSubprocess monkeypatches reconcile.subprocess.run (not the global subprocess module) to stay hermetic
---

# Quick Task 260707-dno: Add gh CLI Token Fallback to Activity-Sync Summary

**One-liner:** Three-step GitHub token resolution (KF_PAT -> GITHUB_TOKEN -> gh auth token) lets local gh-authenticated devs run activity-sync without any env var or plaintext PAT on disk.

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| T1 | reconcile.py: _gh_auth_token() + _resolve_github_token() helpers; _build_headers() refactored | Done |
| T2 | writeback.py: push-time token uses reconcile._resolve_github_token() | Done |
| T3 | test_reconcile.py: 15 new hermetic tests + fix pre-existing _build_headers tests | Done |
| T4 | SKILL.md: document token resolution order in env vars table | Done |

## Commits

| Hash | Message |
|------|---------|
| `2fdc157` | feat(260707-dno): add gh CLI token fallback to activity-sync |

## Key Changes

### reconcile.py

Added two private helpers near `_build_headers()`:

- `_gh_auth_token() -> Optional[str]` — runs `["gh", "auth", "token"]` via subprocess arg-list, 5s timeout. Returns `stdout.strip()` on exit 0 and non-empty; returns None on any failure (`FileNotFoundError`, `SubprocessError`, `OSError`, non-zero exit). Never prints token or stderr (T-02-05).
- `_resolve_github_token() -> Optional[str]` — returns `KF_PAT or GITHUB_TOKEN or _gh_auth_token()`. Single source of truth for token resolution across the skill.

Refactored `_build_headers()` to call `_resolve_github_token()`. Updated warning text:
> "Warning: No KF_PAT/GITHUB_TOKEN set and `gh auth token` unavailable — API rate limits will be very low."

### writeback.py

Push-time token read (~line 611) replaced from:
```python
kf_pat = os.environ.get("KF_PAT", "")
```
to:
```python
import reconcile as _reconcile
kf_pat = _reconcile._resolve_github_token() or ""
```

Error message broadened to mention gh: "No GitHub token available (KF_PAT/GITHUB_TOKEN unset and gh auth token failed). Authenticate gh or set KF_PAT before pushing."

T-03-12 preserved: token read at push time only, never at import.

### test_reconcile.py

Added two reusable context-manager fakes following the existing save-restore pattern:
- `_FakeSubprocess(token_or_none)` — monkeypatches `reconcile.subprocess.run`; `called` flag for assertion
- `_FakeSubprocessRaises()` — raises `FileNotFoundError` to simulate gh not installed

New test assertions (15 checks):
1. KF_PAT set -> returns KF_PAT; gh NOT consulted
2. GITHUB_TOKEN set (KF_PAT unset) -> returns GITHUB_TOKEN; gh NOT consulted
3. Both env vars unset + gh returns token -> returns gh CLI token; gh WAS consulted
4. Both env vars unset + gh exits 1 -> returns None
5. Both env vars unset + FileNotFoundError -> returns None
6. _build_headers() with only gh CLI available -> Authorization header present; no Warning; token never printed
7. _build_headers() all sources exhausted -> no Authorization; Accept header present; Warning printed

Fixed pre-existing `_build_headers()` no-token tests: wrapped with `_FakeSubprocess(None)` so they don't accidentally succeed via a locally-authenticated gh session.

### SKILL.md

Updated the [RECONCILE] section description and the Environment variables table to document the `KF_PAT -> GITHUB_TOKEN -> gh auth token` resolution order. Added [NOTE] block explaining that a locally gh-authenticated developer needs no env var.

## Test Output (final run)

```
--- Results: 113 passed, 0 failed ---
```

All 113 assertions pass (98 pre-existing + 15 new).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing _build_headers no-token tests failed after gh fallback was added**

- **Found during:** T3 (first test run after T1 implementation)
- **Issue:** Existing tests at the `_build_headers()` section used `_EnvPatch({"KF_PAT": None, "GITHUB_TOKEN": None})` without mocking subprocess. After adding `_gh_auth_token()`, a locally-authenticated gh session returned a real token, causing "no Authorization header" and "Warning printed" assertions to fail.
- **Fix:** Wrapped the existing no-token test block with `_FakeSubprocess(None)` so subprocess.run is stubbed regardless of local gh state. Classes `_FakeSubprocess` and `_FakeSubprocessRaises` were defined in the `_EnvPatch` vicinity (before `_build_headers` tests) to be available for both old and new tests.
- **Files modified:** `.claude/skills/activity-sync/test_reconcile.py`
- **Commit:** `2fdc157`

## Security Notes

- Token value never appears in any print statement, warning, manifest, or log (T-02-05)
- `_gh_auth_token()` uses arg-list subprocess (never `shell=True`)
- 5s timeout bounds the gh call
- stderr from `gh auth token` is never read or logged
- `writeback.py` error message broadened but still contains no token value

## Self-Check: PASSED

- [x] `2fdc157` commit exists in git log
- [x] `.claude/skills/activity-sync/reconcile.py` — `_resolve_github_token` function defined
- [x] `.claude/skills/activity-sync/writeback.py` — push-time token updated
- [x] `.claude/skills/activity-sync/test_reconcile.py` — 113 passed, 0 failed
- [x] `.claude/skills/activity-sync/SKILL.md` — token resolution order documented
- [x] No file deletions in commit
