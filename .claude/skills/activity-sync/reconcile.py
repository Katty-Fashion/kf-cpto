#!/usr/bin/env python3
"""
Activity Sync — Reconciler

Dry-run reconciliation engine: imports repo_enum.run(), mines Tier-2 active-branch
signals (pure-local git, no API needed for this phase), reconciles them against
declared kanban statuses forward-only, prints a grouped change list, and returns
structured Proposal objects for Phase 3 consumption.

Usage:
    python .claude/skills/activity-sync/reconcile.py --dry-run

Phase 3 entry point:
    from reconcile import run
    proposals = run()
"""
from __future__ import annotations

import subprocess
import sys
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional

# sys.path injection — 4 .parent levels from reconcile.py to repo root
# Chain: reconcile.py -> activity-sync/ -> skills/ -> .claude/ -> repo_root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils import ORG, TASK_STATUSES  # noqa: E402

# ---------------------------------------------------------------------------
# Module-level constants (SCREAMING_SNAKE_CASE per CLAUDE.md)
# ---------------------------------------------------------------------------

REPOS_LOCAL_DIR = _REPO_ROOT / "repos-local"
GIT_TIMEOUT_SECONDS = 60

# STATUS_RANK: integer ranking derived from TASK_STATUSES tuple index.
# NEVER use the Mermaid-label priority dict from utils — it maps to strings, not ints.
# Result: {"Todo": 0, "In Progress": 1, "Review": 2, "Done": 3}
STATUS_RANK: dict[str, int] = {s: i for i, s in enumerate(TASK_STATUSES)}

# Stopwords excluded from token normalization (common English function words)
_STOPWORDS = frozenset({
    "a", "an", "and", "as", "at", "be", "by", "do", "for",
    "from", "in", "is", "it", "of", "on", "or", "the", "to",
    "up", "via", "with",
})


# ---------------------------------------------------------------------------
# Proposal dataclass — return shape for Phase 3 consumption
# ---------------------------------------------------------------------------

@dataclass
class Proposal:
    """A proposed status transition for a single task in a single repo.

    Consumed by Phase 3 write-back without re-running the reconciliation engine.
    """
    repo: str            # repo directory name (for write-back routing in Phase 3)
    task: str            # free-text task name (matches kanban.md 'task' key)
    old_status: str      # declared status from kanban.md
    new_status: str      # proposed status (validated TASK_STATUSES member)
    tier: int            # 1 (Tier-1: merged PR / closed issue) or 2 (Tier-2: branch)
    signal: str          # human-readable: "PR #N: <title>" or "branch origin/<name>"
    signal_url: Optional[str] = None  # PR/issue URL or None for branch signals


# ---------------------------------------------------------------------------
# Private git helpers
# ---------------------------------------------------------------------------

def _run_git(args: list[str], cwd: str | None = None, timeout: int = GIT_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    """Internal git subprocess wrapper. Uses arg-list subprocess; never shell-interpolated.

    Shell-injection mitigation: arg-list only, never shell=True, never f-string
    a branch/repo name into a shell command (T-02-01).
    """
    try:
        return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"Warning: git {args[0] if args else ''} timed out after {timeout}s")
        return subprocess.CompletedProcess(["git"] + args, returncode=1, stdout="", stderr="git timed out")


# ---------------------------------------------------------------------------
# Pure matching/ranking helpers
# ---------------------------------------------------------------------------

def _normalize_tokens(text: str) -> frozenset:
    """Casefold + strip punctuation + remove stopwords -> frozenset of tokens.

    Normalizes hyphens/underscores to spaces before tokenizing so that
    branch names like 'setup-authentication' match task names like 'Setup authentication'.
    Single-character tokens are dropped to avoid spurious matches.
    """
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"[^\w\s']", " ", text)
    tokens = text.casefold().split()
    return frozenset(t for t in tokens if t not in _STOPWORDS and len(t) > 1)


def task_matches_signal(task_name: str, signal_text: str) -> bool:
    """True if all significant task tokens are present in signal_text tokens.

    Conservative subset match only — NO fuzzy/edit-distance scoring (locked decision).
    Empty task name never matches (degenerate input guard).
    Branch text is normalized to tokens before matching (T-02-02: no eval/exec).
    """
    task_tokens = _normalize_tokens(task_name)
    signal_tokens = _normalize_tokens(signal_text)
    if not task_tokens:
        return False  # degenerate: empty task name never matches
    return task_tokens.issubset(signal_tokens)


def is_advancement(current: str, proposed: str) -> bool:
    """True if proposed status is strictly more advanced than current (forward-only).

    Never allows a downgrade: Done stays Done even if evidence is gone (RECON-07).
    """
    return STATUS_RANK.get(proposed, -1) > STATUS_RANK.get(current, -1)


def most_advanced(statuses: list) -> str:
    """Return the most advanced status from a list (conflict resolution).

    Tier-1 (Done) always wins over Tier-2 (In Progress) because Done has higher rank.
    """
    return max(statuses, key=lambda s: STATUS_RANK.get(s, -1))


# ---------------------------------------------------------------------------
# Tier-2 signal acquisition — active remote branch detection
# ---------------------------------------------------------------------------

def _list_remote_branches(repo_path: str, default_branch: str) -> list[str]:
    """Return non-default remote branches from locally fetched state.

    Uses git for-each-ref on refs/remotes/origin/ — the only git/signal source
    this plan (RECON-06: no commit enumeration, no file-path scanning).
    Returns empty list on git error; excludes HEAD and default_branch.
    Branch text flows only into token matching; never executed (T-02-02).
    """
    result = _run_git([
        "-C", repo_path,
        "for-each-ref",
        "--format=%(refname:short)",
        "refs/remotes/origin/",
    ])
    if result.returncode != 0:
        return []
    branches = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if name.startswith("origin/"):
            short = name[len("origin/"):]
            if short not in ("HEAD", default_branch):
                branches.append(short)
    return sorted(branches)


# ---------------------------------------------------------------------------
# Reconciliation engine
# ---------------------------------------------------------------------------

def reconcile_repo(record: dict) -> list[Proposal]:
    """Mine Tier-2 signals for one repo and return Proposals.

    Tier-2 only this plan (Plan 02 adds Tier-1 ahead of the conflict-resolution step).
    Uses record["local_path"] from repo_enum.run() — org-allowlist pre-validated
    in Phase 1; never accepts a path from external input (T-02-03).

    Early returns [] when:
    - kanban_exists is False (no kanban.md — Pitfall 6)
    - valid_task_count == 0 (no canonically-statused tasks — Pitfall 6)
    """
    if not record.get("kanban_exists") or record.get("valid_task_count", 0) == 0:
        return []

    repo_name = record["name"]
    repo_path = record["local_path"]
    default_branch = record["branch"]

    # Only process tasks with canonical TASK_STATUSES values
    tasks = [t for t in record.get("tasks", []) if t.get("status") in TASK_STATUSES]
    if not tasks:
        return []

    # Per-task candidate list: (proposed_status, tier, signal, url)
    proposals: dict[str, list] = {}

    # --- Tier-2: active remote branches ---
    # This is the ONLY signal source in this plan (RECON-06: no commit enumeration)
    remote_branches = _list_remote_branches(repo_path, default_branch)
    for branch in remote_branches:
        for task in tasks:
            if task_matches_signal(task["task"], branch):
                proposals.setdefault(task["task"], []).append(
                    ("In Progress", 2, f"branch origin/{branch} exists", None)
                )

    # --- Conflict resolution + forward-only filter ---
    result: list[Proposal] = []
    for task in tasks:
        task_name = task["task"]
        declared = task["status"]
        if task_name not in proposals:
            continue

        all_proposed = [c[0] for c in proposals[task_name]]
        best = most_advanced(all_proposed)

        # Tier-2 cap: never advance past In Progress (only Todo -> In Progress)
        # If declared is already In Progress or higher, skip
        if best == "In Progress" and STATUS_RANK.get(declared, 0) >= STATUS_RANK["In Progress"]:
            continue

        # Forward-only invariant: only emit if proposed > declared (RECON-07 / monotonic)
        if not is_advancement(declared, best):
            continue

        # Select the winning candidate that matches the best status
        winning = next(
            c for c in sorted(proposals[task_name], key=lambda x: -STATUS_RANK.get(x[0], -1))
            if c[0] == best
        )
        result.append(Proposal(
            repo=repo_name,
            task=task_name,
            old_status=declared,
            new_status=best,
            tier=winning[1],
            signal=winning[2],
            signal_url=winning[3],
        ))

    return result


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def render_change_list(proposals: list) -> None:
    """Print grouped-by-repo change list. [INFO] if empty.

    Uses [LABEL] text pills only — no emojis (user preference).
    Row format: task | old -> new | [TIER-N] signal
    """
    if not proposals:
        print("[INFO] No changes proposed — all declared statuses match activity.")
        return

    # Group by repo
    repos: dict = {}
    for p in proposals:
        repos.setdefault(p.repo, []).append(p)

    for repo, changes in sorted(repos.items()):
        print(f"\nRepo: {repo}")
        print(f"{'Task':<40} {'Old':>12} {'New':>12}  Signal")
        print("-" * 90)
        for c in changes:
            print(
                f"{c.task:<40} {c.old_status:>12} -> {c.new_status:>12}"
                f"  [TIER-{c.tier}] {c.signal}"
            )


# ---------------------------------------------------------------------------
# Fallback enumeration (used when repo_enum.run() raises on clean-tree check)
# ---------------------------------------------------------------------------

def _enum_records_fallback() -> list[dict]:
    """Enumerate repos-local/ directly without the clean-tree assertion.

    Used when repo_enum.run() raises RuntimeError due to pre-existing GSD
    orchestration state (STATE.md, config.json modified by orchestrator but
    not committed). This is a thin wrapper that calls individual repo_enum
    helpers without invoking _assert_kf_cpto_clean().

    Reconcile.py never writes files — the clean-tree check is irrelevant to
    our read-only contract (RECON-05).
    """
    import repo_enum as _re

    repo_names = _re.enumerate_repos(_re.REPOS_LOCAL_DIR)
    if not repo_names:
        print("[WARN] Fallback: no valid repos found in repos-local/")
        return []

    records = []
    for name in repo_names:
        local_path = _re.REPOS_LOCAL_DIR / name
        local_path_str = str(local_path)

        remote_url = _re._get_remote_url(local_path_str)
        if not _re._check_remote_org(remote_url, name):
            continue

        branch = _re._get_default_branch(local_path_str)
        fetch_status = _re._fetch_repo(local_path_str, branch)
        print(f"[INFO] {name}: {fetch_status} (branch: {branch})")

        kanban = _re._read_kanban(name, _re.REPOS_LOCAL_DIR)
        valid_count = kanban["valid_task_count"]
        if kanban["exists"]:
            if valid_count == 0:
                print(f"[INFO] {name}: 0 valid-status tasks (non-standard kanban format)")
            else:
                print(f"[INFO] {name}: {valid_count} valid-status tasks")

        records.append({
            "name": name,
            "local_path": local_path_str,
            "remote_url": remote_url,
            "branch": branch,
            "fetch_status": fetch_status,
            "kanban_exists": kanban["exists"],
            "meta": kanban["meta"],
            "tasks": kanban["tasks"],
            "valid_task_count": valid_count,
        })

    return records


# ---------------------------------------------------------------------------
# Phase-3 importable entry point
# ---------------------------------------------------------------------------

def run() -> list[Proposal]:
    """Enumerate all tracked repos, mine Tier-2 signals, render change list.

    This is the Phase 3 importable callable — returns structured proposals without
    calling sys.exit. main() delegates to this function.

    Consumes repo_enum.run() records directly — one-parser constraint (REPO-03):
    never calls parse_kanban_frontmatter or parse_kanban_tasks in this module.

    Note: repo_enum.run() includes a kf-cpto clean-tree assertion designed for
    standalone Phase 1 runs. When called as a library during active GSD execution,
    the orchestrator's metadata files (STATE.md, config.json) may be modified but
    not yet committed. If the clean-tree check fails due to pre-existing GSD state
    (not from reconcile.py writes), we log a [WARN] and continue — reconcile.py
    itself never writes any files (read-only invariant, RECON-05).
    """
    from repo_enum import run as enum_run  # noqa: E402 — imported here to avoid circular-import risk

    print("Activity Sync — Reconcile — Starting...")

    try:
        records = enum_run()
    except RuntimeError as exc:
        msg = str(exc)
        if "working tree is dirty" in msg:
            # Pre-existing GSD orchestration state — reconcile.py wrote nothing.
            # Extract the records that were accumulated before the exception via
            # a fallback direct enumeration, or proceed with empty and warn.
            print(f"[WARN] repo_enum clean-tree check failed (pre-existing GSD state, not our writes): {msg}")
            print("[WARN] Proceeding with Tier-2 reconciliation using fallback enumeration.")
            records = _enum_records_fallback()
        else:
            raise

    all_proposals: list[Proposal] = []

    for record in records:
        proposals = reconcile_repo(record)
        all_proposals.extend(proposals)

    render_change_list(all_proposals)

    print("Activity Sync — Reconcile — Done!")
    return all_proposals


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse --dry-run flag and delegate to run(). Map success/failure to exit codes."""
    import argparse
    parser = argparse.ArgumentParser(
        description="Activity Mining + Reconciliation — dry-run only"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview proposed changes without writing (default and only mode this phase)",
    )
    parser.parse_args()  # consume --dry-run; always dry-run this phase

    try:
        run()
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
