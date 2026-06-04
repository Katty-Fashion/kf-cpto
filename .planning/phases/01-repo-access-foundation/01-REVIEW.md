---
phase: 01-repo-access-foundation
reviewed: 2026-06-04T07:45:01Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - .claude/skills/activity-sync/bootstrap.py
  - .claude/skills/activity-sync/repo_enum.py
  - .claude/skills/activity-sync/SKILL.md
  - .gitignore
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 01: Code Review Report (Re-Review after Fix Pass)

**Reviewed:** 2026-06-04T07:45:01Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Re-review after fix pass targeting WR-01 through WR-05 and IN-01 through IN-04 from the
prior review. All six previously-reported fixes are correctly applied and confirmed
resolved. No regressions were introduced by the fix pass.

One new critical defect surfaces: `_assert_kf_cpto_clean` never checks whether
`git status` itself succeeded, so any git failure (timeout, `_run_git` returning the
synthetic `CompletedProcess` with `stdout=""`, or `git` not on PATH) silently passes the
clean-tree assertion — the exact safety guarantee the function is supposed to enforce.

Two new warnings and two new info items are documented below. All are net-new findings
not present in the prior review.

---

## Confirmed Resolved (Prior Findings)

| ID | Description | Status |
|----|-------------|--------|
| WR-01 | `ORG` used via `_check_remote_org()` to skip non-org remotes | RESOLVED |
| WR-02 | `bootstrap.main()` returns 1 on total clone failure | RESOLVED |
| WR-03 | `_seed_markers` guards `templates_dir` + per-file existence + `OSError` | RESOLVED |
| WR-04 | `GIT_TIMEOUT_SECONDS` / `GIT_CLONE_TIMEOUT_SECONDS` added; `_run_git` catches `TimeoutExpired` | RESOLVED |
| WR-05 | `_fetch_repo` returns `"fetch-failed"` when both SHAs are `None` | RESOLVED |
| IN-03 | `[WARN]` replaced with `Warning:` in `_read_kanban` | RESOLVED |
| IN-04 | Docstring syntax corrected; both files parse cleanly (AST verified) | RESOLVED |

---

## Critical Issues

### CR-01: `_assert_kf_cpto_clean` never checks `returncode` — git failure silently passes the assertion

**File:** `.claude/skills/activity-sync/repo_enum.py:163-173`

**Issue:** The clean-tree assertion only checks `result.stdout.strip()` and raises
`RuntimeError` when output is non-empty. It never checks `result.returncode`. If
`git status` fails for any reason — wrong `cwd`, git not on PATH, or a
`subprocess.TimeoutExpired` (which `_run_git` catches and converts to a synthetic
`CompletedProcess` with `returncode=1` and `stdout=""`) — the function prints
`[INFO] kf-cpto working tree: CLEAN` and returns normally.

The safety guarantee in criterion 3 ("kf-cpto working tree is unchanged after the skill
run") is silently voided on any git error, including the timeout case that was just added
by the WR-04 fix. The timeout fix inadvertently made this gap more reachable: a slow git
status now returns `stdout=""` and `returncode=1`, which passes the assertion.

```python
# Current (broken):
result = _run_git(["-C", str(kf_cpto_root), "status", "--porcelain"])
if result.stdout.strip():          # no returncode check
    raise RuntimeError(...)
print("[INFO] kf-cpto working tree: CLEAN")

# Fix: check returncode before trusting stdout
result = _run_git(["-C", str(kf_cpto_root), "status", "--porcelain"])
if result.returncode != 0:
    raise RuntimeError(
        f"[ERROR] git status failed in kf-cpto (returncode={result.returncode}): "
        f"{result.stderr.strip()}"
    )
if result.stdout.strip():
    raise RuntimeError(
        f"[ERROR] kf-cpto working tree is dirty after skill run:\n{result.stdout}"
    )
print("[INFO] kf-cpto working tree: CLEAN")
```

---

## Warnings

### WR-01: `git fetch origin` in `_fetch_repo` uses the 60-second general timeout

**File:** `.claude/skills/activity-sync/repo_enum.py:148`

**Issue:** `_fetch_repo` calls `_run_git([..., "fetch", "origin"])` without an explicit
`timeout` argument, inheriting `GIT_TIMEOUT_SECONDS = 60`. For full (non-shallow) clones
with substantial history — the stated requirement in SKILL.md ("full clone — no
`--depth=1`; Phase 2 needs git history") — an incremental fetch that pulls many new
commits can exceed 60 seconds on slow connections or large repos. The constant
`GIT_CLONE_TIMEOUT_SECONDS = 300` exists in `repo_enum.py` at line 59 but is never
passed to any call — it is dead code in this file.

A spurious 60-second timeout during fetch returns `"fetch-failed"`, causing Phase 2 to
operate on stale kanban data with no clear indication that the underlying cause was a
timeout rather than a real fetch error.

```python
# Fix: pass GIT_CLONE_TIMEOUT_SECONDS to the fetch call in _fetch_repo
fetch = _run_git(
    ["-C", repo_path, "fetch", "origin"],
    timeout=GIT_CLONE_TIMEOUT_SECONDS,
)
```

This also eliminates the dead constant (IN-01 below).

### WR-02: Inconsistent print-prefix style — one `[WARN]` survives in `repo_enum.py`

**File:** `.claude/skills/activity-sync/repo_enum.py:256`

**Issue:** The IN-03 fix replaced `[WARN]` with `Warning:` in `_read_kanban`, but one
`[WARN]` call was left unchanged in `run()`:

```python
print("[WARN] No valid git repos found in repos-local/ — nothing to enumerate")
```

Every other non-fatal message in both files uses `Warning:` (the project convention from
CLAUDE.md, matching `scripts/utils.py`). This inconsistency breaks log filtering:
`grep "^Warning:"` misses this message.

```python
# Fix:
print("Warning: no valid git repos found in repos-local/ — run bootstrap.py first")
```

---

## Info

### IN-01: `GIT_CLONE_TIMEOUT_SECONDS` is defined but unused in `repo_enum.py`

**File:** `.claude/skills/activity-sync/repo_enum.py:59`

**Issue:** `GIT_CLONE_TIMEOUT_SECONDS = 300` is declared at module level. The comment on
line 57 states "clone callers pass `GIT_CLONE_TIMEOUT_SECONDS` instead," but
`repo_enum.py` has no clone operations and no call passes this constant. It is referenced
only in its own definition and the adjacent comment — dead code.

**Fix:** Use it in `_fetch_repo` as shown in WR-01, or remove it. An unused constant
named `*CLONE*` in a module that performs no cloning is misleading.

### IN-02: SKILL.md documents `[WARN]` prefix and "absent" wording that do not match actual output

**File:** `.claude/skills/activity-sync/SKILL.md:41,76`

**Issue:** Two places in SKILL.md document output that the scripts do not actually emit:

1. Line 41 (bootstrap section): `[WARN] on clone failure` — `bootstrap.py` emits
   `Warning: clone failed for {name}: ...`
2. Line 76 (output format section): `[WARN] <repo-name>: kanban.md absent` —
   `repo_enum.py:215` emits `Warning: {repo_name}: kanban.md missing — run bootstrap.py first`

The `[WARN]` vs `Warning:` difference means a consumer using SKILL.md as a contract would
write incorrect grep patterns.

```markdown
# Fix line 41:
- `Warning:` on clone failure (non-fatal; continues to next repo)

# Fix line 76:
Warning: <repo-name>: kanban.md missing — run bootstrap.py first
```

---

_Reviewed: 2026-06-04T07:45:01Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
