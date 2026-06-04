#!/usr/bin/env python3
"""
Bootstrap helper: clone missing tracked repos into repos-local/ and seed markers.

Run once on a fresh machine before using repo_enum.py. Idempotent — already-present
repos are skipped; seeding only writes files that are absent.

Usage:
    python .claude/skills/activity-sync/bootstrap.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# SSH clone org segment — capital F matches GitHub display-name form.
# (utils.ORG = "katty-fashion" is the lowercase API/directory form; SSH URLs need Katty-Fashion.)
KF_ORG = "Katty-Fashion"

REPOS_LOCAL_DIR = _REPO_ROOT / "repos-local"

# Timeout for git subprocess calls (seconds).  Clone needs more time for large repos.
GIT_TIMEOUT_SECONDS = 60
GIT_CLONE_TIMEOUT_SECONDS = 300

# Curated allowlist — membership in repos-local/ IS the tracked set after bootstrap.
# This constant lives ONLY here; repo_enum.py scans repos-local/ at runtime (REPO-01).
# "branch" is the remote default branch for each repo.
TRACKED_REPOS = [
    {"name": "kf-be-platform",     "branch": "main"},
    {"name": "kf-fe-platform",     "branch": "main"},
    {"name": "kf-platform",        "branch": "master"},
    {"name": "R3-AAS",             "branch": "main"},
    {"name": "ai-rise-options",    "branch": "master"},
    {"name": "tech_brainstorming", "branch": "main"},
]


def _run_git(args: list[str], cwd: str | None = None, timeout: int = GIT_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    """Internal git subprocess wrapper. Always uses arg-list form; no shell interpolation (T-02-01)."""
    try:
        return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"Warning: git {args[0] if args else ''} timed out after {timeout}s")
        return subprocess.CompletedProcess(["git"] + args, returncode=1, stdout="", stderr="git timed out")


def _clone_repo(name: str, branch: str, repos_local: Path) -> bool:
    """Clone a tracked repo into repos-local/ via full SSH clone.

    Full clone (not shallow) because Phase 2 activity mining needs git history.
    URL is built from the hardcoded KF_ORG constant + curated name only (T-02-01, T-02-02).
    Returns True on success or if the repo is already present; False on failure (non-fatal).
    """
    target = repos_local / name
    if target.exists():
        print(f"[INFO] {name}: already present at {target}")
        return True

    # arg-list subprocess — no shell interpolation of repo/branch strings (T-02-01)
    result = _run_git(
        ["clone", "-b", branch,
         f"git@github.com:{KF_ORG}/{name}.git",
         str(target)],
        timeout=GIT_CLONE_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        print(f"Warning: clone failed for {name}: {result.stderr.strip()}")
        return False

    print(f"[INFO] Cloned {name} -> {target}")
    return True


def _seed_markers(repo_path: Path, kf_cpto_root: Path) -> None:
    """Copy kanban.md and notify workflow from templates/ into repo if absent.

    Targets are built as repos_local/<name>/... where <name> comes from the
    curated allowlist — no path traversal possible (T-02-03).
    Writes only within the cloned repo dir; never touches the kf-cpto working tree.
    Missing or unreadable template sources emit a Warning and continue rather
    than raising an unhandled FileNotFoundError.
    """
    templates_dir = kf_cpto_root / "templates"

    if not templates_dir.exists():
        print(f"Warning: templates/ dir not found at {templates_dir} — skipping seed for {repo_path.name}")
        return

    kanban_src = templates_dir / "kanban.md"
    kanban_dest = repo_path / "kanban.md"
    if not kanban_dest.exists():
        if kanban_src.exists():
            try:
                shutil.copy(kanban_src, kanban_dest)
                print(f"[INFO] Seeded kanban.md in {repo_path.name}")
            except OSError as exc:
                print(f"Warning: could not seed kanban.md in {repo_path.name}: {exc}")
        else:
            print(f"Warning: templates/kanban.md absent — cannot seed {repo_path.name}")

    notify_src = templates_dir / ".github" / "workflows" / "notify-kf-cpto.yml"
    notify_dest = repo_path / ".github" / "workflows" / "notify-kf-cpto.yml"
    if not notify_dest.exists():
        if notify_src.exists():
            try:
                notify_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(notify_src, notify_dest)
                print(f"[INFO] Seeded notify-kf-cpto.yml in {repo_path.name}")
            except OSError as exc:
                print(f"Warning: could not seed notify-kf-cpto.yml in {repo_path.name}: {exc}")
        else:
            print(f"Warning: templates notify workflow absent — cannot seed {repo_path.name}")


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
    # Exit non-zero only on total failure (no repos ready at all).
    # Partial success (some cloned, some skipped) still returns 0 with warnings above.
    return 1 if cloned_count == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
