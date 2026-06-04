#!/usr/bin/env python3
"""
Activity Sync — Repo Enumerator

Read-only pipeline that enumerates tracked repos from repos-local/, fetches each
repo's remote state before reading, parses every kanban.md through the canonical
scripts/utils.py parsers, asserts the kf-cpto working tree stays clean, and returns
a structured record list for Phase 2 consumption.

Usage:
    python .claude/skills/activity-sync/repo_enum.py

Structured return shape (one dict per enumerated repo):
    {
        "name":             str,         # repo directory name
        "local_path":       str,         # absolute path to repos-local/<name>
        "remote_url":       str,         # git remote get-url origin
        "branch":           str,         # detected default branch (main/master)
        "fetch_status":     str,         # "up-to-date" | "new-commits" | "fetch-failed"
        "kanban_exists":    bool,        # True if kanban.md present
        "meta":             dict,        # normalize_frontmatter output
        "tasks":            list[dict],  # parse_kanban_tasks output
        "valid_task_count": int,         # sum(1 for t in tasks if t["status"] in TASK_STATUSES)
    }

Phase 2 entry point:
    from repo_enum import run
    records = run()
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

# sys.path injection — 4 .parent levels from repo_enum.py to repo root
# Chain: repo_enum.py -> activity-sync/ -> skills/ -> .claude/ -> repo_root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils import (  # noqa: E402
    ORG,
    TASK_STATUSES,
    parse_kanban_frontmatter,
    parse_kanban_tasks,
    normalize_frontmatter,
)

# Module-level constants (SCREAMING_SNAKE_CASE per CLAUDE.md)
REPOS_LOCAL_DIR = _REPO_ROOT / "repos-local"
SKILL_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Private git helpers
# ---------------------------------------------------------------------------

def _run_git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    """Internal git subprocess wrapper. Uses arg-list subprocess; never shell-interpolated."""
    return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)


def _is_git_repo(path: str) -> bool:
    """Return True if path is a valid git repository."""
    result = _run_git(["-C", path, "rev-parse", "--git-dir"])
    return result.returncode == 0


def _get_remote_url(repo_path: str) -> str:
    """Return the origin remote URL, or empty string if unavailable."""
    result = _run_git(["-C", repo_path, "remote", "get-url", "origin"])
    return result.stdout.strip() if result.returncode == 0 else ""


def _get_default_branch(repo_path: str) -> str:
    """Detect current branch from local checkout HEAD.

    Uses rev-parse --abbrev-ref HEAD (the remote tracking ref is unset in these
    clones, so we read from local HEAD instead).
    Falls back to 'main' for detached HEAD or any error.
    """
    result = _run_git(["-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode == 0:
        branch = result.stdout.strip()
        if branch and branch != "HEAD":  # HEAD = detached state
            return branch
    return "main"  # safe fallback


def _fetch_repo(repo_path: str, branch: str) -> str:
    """Fetch origin and return fetch status string. Non-fatal.

    Compares origin/<branch> SHA before and after git fetch origin to determine
    whether new commits arrived (REPO-02).

    Returns:
        "up-to-date"  — remote SHA unchanged
        "new-commits" — remote SHA changed
        "fetch-failed" — git fetch exited non-zero (Warning logged; run continues)
    """
    tracking_ref = f"origin/{branch}"

    before = _run_git(["-C", repo_path, "rev-parse", tracking_ref])
    before_sha = before.stdout.strip() if before.returncode == 0 else None

    fetch = _run_git(["-C", repo_path, "fetch", "origin"])
    if fetch.returncode != 0:
        print(f"Warning: fetch failed for {repo_path}: {fetch.stderr.strip()}")
        return "fetch-failed"

    after = _run_git(["-C", repo_path, "rev-parse", tracking_ref])
    after_sha = after.stdout.strip() if after.returncode == 0 else None

    return "up-to-date" if before_sha == after_sha else "new-commits"


def _assert_kf_cpto_clean(kf_cpto_root: Path) -> None:
    """Assert the kf-cpto working tree is unchanged after the skill run.

    Raises RuntimeError if git status --porcelain is non-empty (criterion 3).
    """
    result = _run_git(["-C", str(kf_cpto_root), "status", "--porcelain"])
    if result.stdout.strip():
        raise RuntimeError(
            f"[ERROR] kf-cpto working tree is dirty after skill run:\n{result.stdout}"
        )
    print("[INFO] kf-cpto working tree: CLEAN")


# ---------------------------------------------------------------------------
# Enumeration and parsing helpers
# ---------------------------------------------------------------------------

def enumerate_repos(repos_local: Path) -> list[str]:
    """Return sorted list of repo names present in repos-local/ (REPO-01).

    Scans repos-local/ membership at runtime — NO static repo list.
    Non-git subdirectories are skipped with a Warning.
    """
    if not repos_local.exists():
        print(f"Warning: repos-local/ directory not found at {repos_local}")
        return []

    names = []
    for entry in repos_local.iterdir():
        if not entry.is_dir():
            continue
        if _is_git_repo(str(entry)):
            names.append(entry.name)
        else:
            print(f"Warning: repos-local/{entry.name} is not a valid git repo — skipping")

    return sorted(names)


def _read_kanban(repo_name: str, repos_local: Path) -> dict[str, Any]:
    """Read and parse kanban.md from repos-local/ checkout (REPO-03).

    Reads the file directly from repos-local/ and calls the canonical parsers.
    The utils convenience loader is not used here — it is hardwired to the CI
    repos/ dir. Path must come from REPOS_LOCAL_DIR.

    Parity check uses sum(1 for t in tasks if t["status"] in TASK_STATUSES) to match
    aggregator.py lines 102-109 — NOT total row count (R3-AAS: 181 rows, 0 valid).
    """
    kanban_path = repos_local / repo_name / "kanban.md"

    if not kanban_path.exists():
        print(f"Warning: {repo_name}: kanban.md missing — run bootstrap.py first")
        return {
            "exists": False,
            "meta": normalize_frontmatter({}),
            "tasks": [],
            "valid_task_count": 0,
            "raw": "",
        }

    content = kanban_path.read_text(encoding="utf-8")
    meta = normalize_frontmatter(parse_kanban_frontmatter(content))
    tasks = parse_kanban_tasks(content, project=repo_name)
    valid_count = sum(1 for t in tasks if t["status"] in TASK_STATUSES)

    return {
        "exists": True,
        "meta": meta,
        "tasks": tasks,
        "valid_task_count": valid_count,
        "raw": content,
    }


# ---------------------------------------------------------------------------
# Phase-2 importable entry point
# ---------------------------------------------------------------------------

def run() -> list[dict[str, Any]]:
    """Enumerate repos-local/, fetch each repo, parse kanban.md, assert clean tree.

    This is the Phase 2 importable callable — it returns the structured record list
    without calling sys.exit. main() delegates to this function.

    Returns:
        list of repo records (one per enumerated repo in repos-local/)
    """
    print("Activity Sync — Repo Enum — Starting...")

    repo_names = enumerate_repos(REPOS_LOCAL_DIR)

    if not repo_names:
        print("[WARN] No valid git repos found in repos-local/ — nothing to enumerate")
        print("Activity Sync — Repo Enum — Done!")
        return []

    records: list[dict[str, Any]] = []

    for name in repo_names:
        local_path = REPOS_LOCAL_DIR / name
        local_path_str = str(local_path)

        # Resolve remote URL and branch
        remote_url = _get_remote_url(local_path_str)
        branch = _get_default_branch(local_path_str)

        # REPO-02: fetch before read; compare before/after SHA
        fetch_status = _fetch_repo(local_path_str, branch)
        print(f"[INFO] {name}: {fetch_status} (branch: {branch})")

        # REPO-03: parse kanban.md via canonical utils parsers
        kanban = _read_kanban(name, REPOS_LOCAL_DIR)

        valid_count = kanban["valid_task_count"]

        # Log valid-status count; 0 is expected for non-standard repos (e.g. R3-AAS)
        if valid_count == 0 and kanban["exists"]:
            print(f"[INFO] {name}: 0 valid-status tasks (non-standard kanban format)")
        elif kanban["exists"]:
            print(f"[INFO] {name}: {valid_count} valid-status tasks")

        # Criterion 1: print (name, local_path, remote_url) tuple per repo
        print(f"({name!r}, {local_path_str!r}, {remote_url!r})")

        record: dict[str, Any] = {
            "name": name,
            "local_path": local_path_str,
            "remote_url": remote_url,
            "branch": branch,
            "fetch_status": fetch_status,
            "kanban_exists": kanban["exists"],
            "meta": kanban["meta"],
            "tasks": kanban["tasks"],
            "valid_task_count": valid_count,
        }
        records.append(record)

    # Print structured summary
    print("")
    print("--- Enumerated repos ---")
    for r in records:
        print(f"  {r['name']}: branch={r['branch']}, fetch={r['fetch_status']}, "
              f"valid_tasks={r['valid_task_count']}")
    print("------------------------")

    # Criterion 3: assert kf-cpto working tree is clean post-run
    _assert_kf_cpto_clean(_REPO_ROOT)

    print("Activity Sync — Repo Enum — Done!")
    return records


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Delegate to run() and map success/failure to exit codes."""
    try:
        run()
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
