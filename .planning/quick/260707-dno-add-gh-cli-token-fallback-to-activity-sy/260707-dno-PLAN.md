---
id: 260707-dno
title: Add gh CLI token fallback to activity-sync
type: quick
date: 2026-07-07
---

# Plan: Add gh CLI Token Fallback to Activity-Sync

## Goal

Make the activity-sync skill resolve its GitHub token as:
`KF_PAT` -> `GITHUB_TOKEN` -> `gh auth token` (gh CLI keyring)

CI/org keeps using its `KF_PAT` secret; local dev with an authenticated gh CLI
works with no env var and no plaintext PAT on disk.

## Files in scope

- `.claude/skills/activity-sync/reconcile.py` — token resolution helpers + `_build_headers()`
- `.claude/skills/activity-sync/writeback.py` — push-time token read (~line 611)
- `.claude/skills/activity-sync/test_reconcile.py` — new hermetic tests for resolver
- `.claude/skills/activity-sync/SKILL.md` — environment variables table

## Tasks

### T1 — reconcile.py token resolution

- Add `_gh_auth_token() -> Optional[str]`: subprocess arg-list call to `gh auth token`,
  5s timeout, return stdout.strip() on rc==0 and non-empty; catch
  `(FileNotFoundError, subprocess.SubprocessError, OSError)` -> None.
  Never print token or stderr. NO `shell=True`.
- Add `_resolve_github_token() -> Optional[str]`: `KF_PAT or GITHUB_TOKEN or _gh_auth_token()`.
- Refactor `_build_headers()` to call `_resolve_github_token()`. Update warning text.
  Keep T-02-05 (never print token). Keep `Bearer {token}` header build unchanged.

### T2 — writeback.py push credential

- Replace `os.environ.get("KF_PAT", "")` at push time with
  `reconcile._resolve_github_token() or ""`.
  writeback already imports `from reconcile import STATUS_RANK` — call
  `reconcile._resolve_github_token()` the same way.
- Broaden [ERROR] message to mention gh: "No GitHub token available
  (KF_PAT/GITHUB_TOKEN unset and gh auth token failed). Authenticate gh or set KF_PAT."
- Preserve T-03-12: token read at push time only, never at import.
- Never log the token.

### T3 — tests in test_reconcile.py

- Add `_FakeSubprocess` context manager monkeypatching `reconcile.subprocess.run`.
- Add env context manager saving/restoring `KF_PAT`/`GITHUB_TOKEN` (reuse existing
  `_EnvPatch` class already present in test_reconcile.py).
- Test cases via `check(...)`:
  1. KF_PAT set -> `_resolve_github_token()` returns KF_PAT value; gh not consulted.
  2. Both env vars unset + gh returns token -> returns gh token.
  3. Both env vars unset + gh unavailable (FileNotFoundError) -> returns None;
     `_build_headers()` omits Authorization header; still returns Accept header.
- All hermetic — no real gh call, no network.

### T4 — SKILL.md doc note

- In the Environment variables table, update token notes to describe the
  `KF_PAT -> GITHUB_TOKEN -> gh auth token` resolution order.
- Add a note that a locally gh-authenticated dev needs no env var.
- [LABEL] text-pills only, no emojis.

## Constraints

- Security: token/stderr never printed; subprocess arg-list only; 5s timeout.
- `python .claude/skills/activity-sync/test_reconcile.py` must exit 0.
- Sanity-check: `python -c "import sys; sys.path.insert(0,'.claude/skills/activity-sync'); import reconcile; print(reconcile._resolve_github_token.__name__)"`.
- Commit code atomically (reconcile+writeback; tests; SKILL.md doc).
- Do NOT commit PLAN.md/SUMMARY.md — orchestrator handles docs commit.
- Do NOT push.
