---
phase: 01-repo-access-foundation
reviewed: 2026-06-04T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - .claude/skills/activity-sync/bootstrap.py
  - .claude/skills/activity-sync/repo_enum.py
  - .claude/skills/activity-sync/SKILL.md
  - .gitignore
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-06-04T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed two Python skill scripts (`bootstrap.py`, `repo_enum.py`), the skill index (`SKILL.md`), and `.gitignore`. The implementation is structurally sound: subprocess calls use arg-list form throughout (no `shell=True`), Python 3.9 compatibility is correctly handled via `from __future__ import annotations`, the canonical `scripts/utils.py` parsers are reused without adding a second parser, and `repos-local/` is correctly gitignored. The read-only/clean-tree guarantee is enforced via `_assert_kf_cpto_clean`.

Key concerns: (1) The stated security constraint "clone only from the katty-fashion org" is enforced at bootstrap clone time but **not** at enumeration time — `ORG` is imported in `repo_enum.py` but never used for remote URL validation, meaning any git repo manually placed in `repos-local/` gets enumerated and parsed without origin checks. (2) `bootstrap.main()` always exits 0 even when every clone fails, masking complete failures. (3) `_seed_markers` has no error handling for missing template files, which crashes bootstrap with an unhandled `FileNotFoundError`. (4) `subprocess.run` has no timeout, so `git fetch`/`git clone` on a slow or unreachable remote blocks indefinitely.

---

## Warnings

### WR-01: `ORG` Imported but Never Used — Remote URL Org Validation Missing

**File:** `.claude/skills/activity-sync/repo_enum.py:44-50`
**Issue:** `ORG` is imported from `utils` on line 45 but is referenced nowhere in the module body. The project context explicitly states "clone only from the katty-fashion org" as a security requirement. `bootstrap.py` enforces this at clone time via the hardcoded `KF_ORG` constant, but `repo_enum.py` enumerates and fully parses any valid git repo present in `repos-local/` regardless of its `origin` remote URL. A git repo manually placed in `repos-local/` pointing to an arbitrary origin would be silently enumerated, its `kanban.md` parsed, and its record returned to Phase 2 consumers indistinguishably from a legitimate tracked repo.

**Fix:** Add an org allowlist check in `enumerate_repos` or at the top of the `run()` loop. Remove the dead import only after adding the check:

```python
_ALLOWED_ORG_HOSTS = (
    f"git@github.com:{utils.ORG}/",
    f"https://github.com/{utils.ORG}/",
    f"git@github.com:Katty-Fashion/",   # SSH display-name variant
    f"https://github.com/Katty-Fashion/",
)

def _check_remote_org(remote_url: str, name: str) -> bool:
    """Return True if remote_url belongs to the allowed org."""
    if not remote_url:
        print(f"Warning: {name} has no origin remote — skipping")
        return False
    if not any(remote_url.startswith(prefix) for prefix in _ALLOWED_ORG_HOSTS):
        print(f"Warning: {name} remote URL {remote_url!r} is not in allowed org — skipping")
        return False
    return True
```

Then gate on `_check_remote_org(remote_url, name)` in the `run()` loop after `remote_url = _get_remote_url(...)`.

---

### WR-02: `bootstrap.main()` Always Exits 0 Even on Complete Clone Failure

**File:** `.claude/skills/activity-sync/bootstrap.py:98-123`
**Issue:** `main()` unconditionally returns `0` regardless of how many repos failed to clone. If SSH keys are absent or network is unavailable, every `_clone_repo` call returns `False`, `skipped_count` equals `len(TRACKED_REPOS)`, and the process still exits 0. The caller (human or CI) receives a false success signal; warnings in stdout are the only indication of failure. This differs from `repo_enum.py`'s `main()`, which returns 1 on error.

**Fix:** Return a non-zero exit code when all repos failed (or optionally when any failed):

```python
def main() -> int:
    print("Activity Sync — Bootstrap — Starting...")

    repos_local = REPOS_LOCAL_DIR
    repos_local.mkdir(exist_ok=True)

    cloned_count = 0
    skipped_count = 0

    for repo in TRACKED_REPOS:
        name = repo["name"]
        branch = repo["branch"]
        success = _clone_repo(name, branch, repos_local)
        if success:
            cloned_count += 1
            _seed_markers(repos_local / name, _REPO_ROOT)
        else:
            skipped_count += 1

    print(
        f"[INFO] Bootstrap complete: {cloned_count} repos ready, "
        f"{skipped_count} failed (see Warning lines above)"
    )
    print("Activity Sync — Bootstrap — Done!")
    # Exit non-zero if no repos are ready (total failure)
    return 1 if cloned_count == 0 else 0
```

---

### WR-03: `_seed_markers` Has No Error Handling — Uncaught `FileNotFoundError` Crashes Bootstrap

**File:** `.claude/skills/activity-sync/bootstrap.py:74-95`
**Issue:** `shutil.copy(templates_dir / "kanban.md", kanban_dest)` and the `notify-kf-cpto.yml` copy are unguarded. If `templates/` is absent, if the source files have been deleted, or if `templates_dir` resolves incorrectly (e.g., `_REPO_ROOT` is wrong), both calls raise `FileNotFoundError`. There is no `try/except` in `_seed_markers` or in the `main()` for loop that calls it, so the exception propagates uncaught, crashing the process mid-loop — leaving some repos cloned but unseeded and some not yet attempted. `main()` also has no `try/except`, so the exit code becomes Python's default error exit (1) rather than a controlled failure.

**Fix:** Guard each copy with existence checks and catch copy errors:

```python
def _seed_markers(repo_path: Path, kf_cpto_root: Path) -> None:
    templates_dir = kf_cpto_root / "templates"
    if not templates_dir.exists():
        print(f"Warning: templates/ dir not found at {templates_dir} — skipping seed for {repo_path.name}")
        return

    kanban_src = templates_dir / "kanban.md"
    kanban_dest = repo_path / "kanban.md"
    if not kanban_dest.exists():
        if kanban_src.exists():
            shutil.copy(kanban_src, kanban_dest)
            print(f"[INFO] Seeded kanban.md in {repo_path.name}")
        else:
            print(f"Warning: templates/kanban.md absent — cannot seed {repo_path.name}")

    notify_src = templates_dir / ".github" / "workflows" / "notify-kf-cpto.yml"
    notify_dest = repo_path / ".github" / "workflows" / "notify-kf-cpto.yml"
    if not notify_dest.exists():
        if notify_src.exists():
            notify_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(notify_src, notify_dest)
            print(f"[INFO] Seeded notify-kf-cpto.yml in {repo_path.name}")
        else:
            print(f"Warning: templates notify workflow absent — cannot seed {repo_path.name}")
```

---

### WR-04: No Subprocess Timeout — `git fetch` / `git clone` Can Hang Indefinitely

**File:** `.claude/skills/activity-sync/bootstrap.py:43-45`, `.claude/skills/activity-sync/repo_enum.py:61-63`
**Issue:** Both files share a `_run_git` helper that calls `subprocess.run(...)` without a `timeout` parameter. A full clone of a large repo (`tech_brainstorming`, `R3-AAS`) or a `git fetch` on a slow/unreachable remote will block the calling process indefinitely. In the Claude Code skill context this hangs the entire session with no recovery path short of a process kill.

**Fix:** Add a `timeout` parameter to `_run_git` with sensible defaults (clone operations need more time than fetch):

```python
def _run_git(args: list[str], cwd: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Internal git subprocess wrapper. Always uses arg-list form; no shell interpolation."""
    try:
        return subprocess.run(
            ["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        # Return a synthetic failed result so callers handle it uniformly
        import subprocess as sp
        r = sp.CompletedProcess(["git"] + args, returncode=1, stdout="", stderr="git timed out")
        return r
```

Pass `timeout=600` (10 min) for clone operations in `_clone_repo` and `timeout=60` for fetch/rev-parse.

---

### WR-05: `_fetch_repo` Returns `"up-to-date"` When Tracking Ref Never Resolves (Masked Failure)

**File:** `.claude/skills/activity-sync/repo_enum.py:93-117`
**Issue:** When `_get_default_branch` falls back to `"main"` (detached HEAD or error) but the actual remote default branch is something else, `rev-parse origin/main` will fail both before and after fetch — `before_sha = None`, `after_sha = None`. The comparison `None == None` evaluates to `True`, so the function returns `"up-to-date"`. This masks the underlying problem (wrong tracking ref) with a misleading success status. The caller logs `"up-to-date"` and proceeds to parse a potentially stale or incorrect kanban.md.

**Fix:** Distinguish the "both None" case explicitly:

```python
after = _run_git(["-C", repo_path, "rev-parse", tracking_ref])
after_sha = after.stdout.strip() if after.returncode == 0 else None

if before_sha is None and after_sha is None:
    print(f"Warning: tracking ref {tracking_ref!r} not found in {repo_path} — branch name may be wrong")
    return "fetch-failed"

return "up-to-date" if before_sha == after_sha else "new-commits"
```

---

## Info

### IN-01: `ORG` Is a Dead Import in `repo_enum.py`

**File:** `.claude/skills/activity-sync/repo_enum.py:45`
**Issue:** `ORG` is imported from `utils` but is not referenced anywhere in the module. This is a dead import (confirmed: the only occurrence is the import line itself). It was presumably imported in anticipation of remote URL validation (see WR-01), but that code was never written.

**Fix:** Either implement remote URL validation using `ORG` (as described in WR-01) or remove it from the import statement until it is needed:

```python
from utils import (  # noqa: E402
    TASK_STATUSES,
    parse_kanban_frontmatter,
    parse_kanban_tasks,
    normalize_frontmatter,
)
```

---

### IN-02: `_clone_repo` Does Not Verify Existing Directory Is a Valid Git Repo

**File:** `.claude/skills/activity-sync/bootstrap.py:48-71`
**Issue:** When `target.exists()`, `_clone_repo` returns `True` immediately without checking whether the directory is a valid git repo (e.g., it could be a leftover from a failed clone with a partial `.git/`). `_seed_markers` is then called on this potentially corrupt directory. `repo_enum.py` later correctly skips non-git directories via `_is_git_repo()`, creating an inconsistency: bootstrap reports success and seeds templates, but the repo will be skipped at enumeration time.

**Fix:** Add a git-repo validity check before the early return:

```python
if target.exists():
    result = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--git-dir"],
        capture_output=True
    )
    if result.returncode == 0:
        print(f"[INFO] {name}: already present at {target}")
        return True
    print(f"Warning: {name}: directory exists but is not a valid git repo — re-cloning")
    shutil.rmtree(target)   # remove corrupt clone before re-cloning
```

---

### IN-03: Mixed Warning-Message Format in `repo_enum.py` Violates CLAUDE.md Convention

**File:** `.claude/skills/activity-sync/repo_enum.py:172`
**Issue:** CLAUDE.md specifies `print(f"Warning: ...")` for non-fatal warnings. `_read_kanban` (line 172) uses `"[WARN] {name}: kanban.md missing"` — the bracket-pill format — while all other non-fatal messages in the same file use the `"Warning: ..."` convention (`_fetch_repo` line 111, `enumerate_repos` lines 144, 154). This is an inconsistency within the file and against the project standard.

**Fix:** Change line 172 to follow the project convention:

```python
print(f"Warning: {repo_name}: kanban.md missing — run bootstrap.py first")
```

---

### IN-04: `_read_kanban` Docstring Contains Invalid Python Syntax in Code Example

**File:** `.claude/skills/activity-sync/repo_enum.py:168`
**Issue:** The docstring states: `"Parity check uses sum(1 for t if t["status"] in TASK_STATUSES)"`. This is syntactically invalid Python — it is missing `in tasks` between `t` and `if`. The actual code on line 184 is correct (`sum(1 for t in tasks if t["status"] in TASK_STATUSES)`). A reader could copy the docstring example verbatim and get a `SyntaxError`.

**Fix:** Correct the docstring example:

```python
# Parity check uses sum(1 for t in tasks if t["status"] in TASK_STATUSES) to match
# aggregator.py lines 102-109 — NOT total row count (R3-AAS: 181 rows, 0 valid).
```

---

_Reviewed: 2026-06-04T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
