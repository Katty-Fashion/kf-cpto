#!/usr/bin/env python3
"""
Activity Sync — Write-Back (string builders + git operations + batch orchestration)

Consumes reconcile.run() Proposal objects and applies them to kanban.md files
in repos-local/. Provides a single batch-confirm gate (WB-02) and a per-run JSON
recovery manifest (WB-05).

String-builder responsibilities:
- split_kanban()          — split kanban.md into (frontmatter_str, body_str)
- roundtrip_frontmatter() — ruamel.yaml round-trip preserving # comments (WB-01)
- reconstruct_kanban()    — rejoin frontmatter + body into the corrected string
- apply_status_change()   — targeted status-cell replacement by task name
- _content_changed()      — byte-compare idempotency gate

Git operation responsibilities (Plan 02):
- _run_git()              — arg-list subprocess wrapper (never shell=True)
- _get_remote_url()       — read origin remote URL
- _is_behind_origin()     — fetch + rev-list --count conflict detection (WB-03)
- _push_with_auth()       — HTTPS+KF_PAT push with finally-restore (WB-04)
- _write_repo()           — single-repo write/commit/push orchestrator

Batch orchestration responsibilities (Plan 03):
- _confirm_batch()        — single y/N summary prompt over all repos × proposals (WB-02)
- _write_manifest()       — per-run JSON recovery manifest in manifests/ (WB-05)
- run()                   — fan _write_repo over all repos, continue past conflicts
- main()                  — CLI entry point: reconcile.run() -> run(); --dry-run flag

Usage:
    from writeback import run
    # or as a CLI:
    python .claude/skills/activity-sync/writeback.py [--dry-run]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

# sys.path injection — 4 .parent levels from writeback.py to repo root
# Chain: writeback.py -> activity-sync/ -> skills/ -> .claude/ -> repo_root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from sanitize import sanitize_body  # noqa: E402
from utils import ORG, TASK_STATUSES  # noqa: E402

# ---------------------------------------------------------------------------
# Module constants (SCREAMING_SNAKE_CASE per CLAUDE.md)
# ---------------------------------------------------------------------------

# Regex for splitting kanban.md into frontmatter + body.
# Matches the opening '---\n<content>\n---\n' block at the start of the file.
# re.DOTALL allows '.*?' to span newlines.
_FM_RE = re.compile(r'^---\n(.*?)\n---\n?', re.DOTALL)

# Canonical commit message for all write-back commits (no [skip ci] — dispatch is the point).
COMMIT_MSG = "chore(kanban): reconcile task statuses from repo activity"

# Timeout for individual git subprocess calls (seconds).
GIT_TIMEOUT_SECONDS = 60

# KF GitHub org (matches utils.ORG)
_KF_ORG = "katty-fashion"

# Per-run JSON recovery manifests (WB-05). Gitignored — never committed.
# Chain: writeback.py -> activity-sync/ -> skills/ -> .claude/ -> repo_root/
#        -> .claude/skills/activity-sync/manifests/
MANIFESTS_DIR = Path(__file__).parent / "manifests"


# ---------------------------------------------------------------------------
# Git subprocess helpers (Plan 02: WB-03, WB-04)
# ---------------------------------------------------------------------------

def _run_git(
    args: list[str],
    cwd: str | None = None,
    timeout: int = GIT_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess:
    """Internal git subprocess wrapper. Arg-list only — never shell=True.

    Shell-injection mitigation (T-03-06): arg-list form ensures no branch/repo/
    token value is interpolated by a shell. Mirrors reconcile.py / repo_enum.py
    pattern verbatim.

    Args:
        args:    Git sub-command and flags (e.g. ["fetch", "origin"]).
        cwd:     Working directory for the subprocess, or None for CWD.
        timeout: Max seconds to wait; returns non-zero CompletedProcess on expiry.

    Returns:
        subprocess.CompletedProcess with returncode, stdout, stderr as strings.
    """
    try:
        return subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"Warning: git {args[0] if args else ''} timed out after {timeout}s")
        return subprocess.CompletedProcess(
            ["git"] + args, returncode=1, stdout="", stderr="git timed out"
        )


def _get_remote_url(repo_path: str) -> str:
    """Return the origin remote URL, or empty string if unavailable.

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        URL string (SSH or file:// or HTTPS) or empty string on failure.
    """
    result = _run_git(["-C", repo_path, "remote", "get-url", "origin"])
    return result.stdout.strip() if result.returncode == 0 else ""


def _is_behind_origin(repo_path: str, branch: str) -> tuple[bool, int]:
    """Return (is_behind, behind_count) for local checkout vs origin/<branch>.

    Fetches first (Pitfall 4: stale refs without fetch). Then counts commits
    in origin/<branch> that are not in HEAD. Count > 0 means the local checkout
    is behind and a push would be non-fast-forward — abort with [CONFLICT].

    Security (T-03-04): conservative — fetch failure also returns (True, -1) so
    we never accidentally skip the conflict check due to a transient error.

    Args:
        repo_path: Absolute path to the git repository.
        branch:    Default branch name from record['branch'] (e.g. 'main' or 'master').

    Returns:
        (True, N)  if local is N commits behind origin/<branch>.
        (False, 0) if local is up-to-date.
        (True, -1) on fetch error or rev-list error (conservative conflict).
    """
    fetch_r = _run_git(["-C", repo_path, "fetch", "origin"])
    if fetch_r.returncode != 0:
        print(f"Warning: fetch failed for {repo_path}: {fetch_r.stderr.strip()}")
        return True, -1  # conservative — treat fetch failure as conflict

    rev_r = _run_git(["-C", repo_path, "rev-list", "--count", f"HEAD..origin/{branch}"])
    if rev_r.returncode != 0:
        print(f"Warning: rev-list failed for {repo_path}: {rev_r.stderr.strip()}")
        return True, -1  # conservative

    count = int(rev_r.stdout.strip() or "0")
    return count > 0, count


def _push_with_auth(
    repo_path: str,
    repo_name: str,
    branch: str,
    kf_pat: str,
) -> tuple[bool, str]:
    """Push HEAD to origin/<branch> using HTTPS+KF_PAT auth. Restore SSH URL after.

    Security (T-03-05): saves original SSH URL, sets HTTPS+token URL in arg-list
    (never shell=True, never string-interpolated via shell), pushes, then restores
    in a finally block. NEVER prints or logs the HTTPS URL containing the token.

    Sets git identity to "KF Bot" / bot@katty-fashion.dev (matches aggregate.yml).

    Pitfall 1: if URL restore fails, logs [WARN] but does not re-raise — the token
    would persist in .git/config (local file, never committed), and the operator
    can manually fix with `git remote set-url origin <ssh_url>`.

    Args:
        repo_path: Absolute path to the git repository.
        repo_name: Repository name (e.g. 'kf-be-platform') — used in HTTPS URL.
        branch:    Target branch (from record['branch']).
        kf_pat:    GitHub Personal Access Token with repo scope.

    Returns:
        (True, sha_string)  on successful push.
        (False, error_msg)  on failure (no raise — callers handle failure gracefully).
    """
    original_url = _get_remote_url(repo_path)
    # Build HTTPS URL — arg-list only (T-03-06); NEVER print this URL (T-03-05)
    https_url = f"https://{kf_pat}@github.com/{_KF_ORG}/{repo_name}.git"
    try:
        set_r = _run_git(["-C", repo_path, "remote", "set-url", "origin", https_url])
        if set_r.returncode != 0:
            return False, f"remote set-url failed: {set_r.stderr.strip()}"

        # Set commit identity (mirrors aggregate.yml git config step)
        _run_git(["-C", repo_path, "config", "user.name", "KF Bot"])
        _run_git(["-C", repo_path, "config", "user.email", "bot@katty-fashion.dev"])

        push_r = _run_git(["-C", repo_path, "push", "origin", f"HEAD:{branch}"])
        if push_r.returncode != 0:
            return False, f"push failed: {push_r.stderr.strip()}"

        sha_r = _run_git(["-C", repo_path, "rev-parse", "HEAD"])
        sha = sha_r.stdout.strip() if sha_r.returncode == 0 else "unknown"
        return True, sha
    finally:
        # Always attempt URL restore — token must not persist in .git/config (T-03-05)
        if original_url:
            restore_r = _run_git(["-C", repo_path, "remote", "set-url", "origin", original_url])
            if restore_r.returncode != 0:
                # Pitfall 1: log [WARN] but do not re-raise; .git/config is local-only
                print(
                    f"[WARN] Failed to restore remote URL for {repo_path}. "
                    f"Run manually: git -C {repo_path} remote set-url origin {original_url}"
                )


# ---------------------------------------------------------------------------
# Single-repo write orchestrator (Plan 02: _write_repo)
# ---------------------------------------------------------------------------

def _write_repo(
    record: dict,
    proposals_for_repo: list,
    kf_pat: str,
    run_id: str,
) -> dict:
    """Apply proposals to one repo's kanban.md and push the result.

    Implements the full single-repo write sequence from 03-RESEARCH.md:
    conflict-check → read → apply_status_change → sanitize_body → reconstruct →
    idempotency gate → write → git add/commit → push → manifest entry.

    Per-repo errors are caught and returned as outcome='failed' — never raised
    (the batch run in Plan 03 must continue across repos).

    Args:
        record:             Repo record dict with 'name', 'local_path', 'remote_url', 'branch'.
        proposals_for_repo: List of Proposal-like objects with .task, .old_status, .new_status.
        kf_pat:             GitHub PAT for push auth (never printed).
        run_id:             Run identifier for logging (e.g. '20260604T112000Z').

    Returns:
        Manifest entry dict:
        {
          'repo':       str,
          'outcome':    'succeeded' | 'failed' | 'conflict' | 'skipped',
          'pushed_sha': str | None,
          'changes':    list[dict],   # [{task, old_status, new_status}, ...]
          'error':      str | None,
        }
    """
    repo_name = record["name"]
    repo_path = record["local_path"]
    branch = record["branch"]
    kanban_path = Path(repo_path) / "kanban.md"

    try:
        # Step 1: Conflict gate — fetch + rev-list --count (WB-03)
        is_behind, behind_count = _is_behind_origin(repo_path, branch)
        if is_behind:
            if behind_count >= 0:
                msg = f"local checkout is {behind_count} commit(s) behind origin/{branch}"
            else:
                msg = "fetch failed (conservative conflict)"
            print(f"[CONFLICT] {repo_name}: {msg} — skipping write")
            return {
                "repo": repo_name,
                "outcome": "conflict",
                "pushed_sha": None,
                "changes": [],
                "error": msg,
            }

        # Step 2: Read fresh kanban.md
        content = kanban_path.read_text(encoding="utf-8")
        fm_str, body_str = split_kanban(content)

        # Step 3: Apply status replacements by raw task name (BEFORE sanitize)
        # Anti-pattern: sanitizing first would alter task name cells, breaking match
        for proposal in proposals_for_repo:
            body_str, _ = apply_status_change(body_str, proposal.task, proposal.new_status)

        # Step 4: Sanitize all task-table data cells
        body_str = sanitize_body(body_str)

        # Step 5: Reconstruct full kanban.md string
        new_content = reconstruct_kanban(fm_str, body_str)

        # Step 6: Idempotency gate — byte-compare (SC-4)
        if not _content_changed(str(kanban_path), new_content):
            print(f"[SKIP] {repo_name}: content unchanged (idempotent no-op)")
            return {
                "repo": repo_name,
                "outcome": "skipped",
                "pushed_sha": None,
                "changes": [],
                "error": None,
            }

        # Step 7: Write file
        kanban_path.write_text(new_content, encoding="utf-8")

        # Step 8: git config + add + commit
        _run_git(["-C", repo_path, "config", "user.name", "KF Bot"])
        _run_git(["-C", repo_path, "config", "user.email", "bot@katty-fashion.dev"])
        _run_git(["-C", repo_path, "add", "kanban.md"])
        commit_r = _run_git(["-C", repo_path, "commit", "-m", COMMIT_MSG])
        if commit_r.returncode != 0:
            return {
                "repo": repo_name,
                "outcome": "failed",
                "pushed_sha": None,
                "changes": [],
                "error": f"commit failed: {commit_r.stderr.strip()}",
            }

        # Step 9: Push with token + restore URL (WB-04)
        ok, sha_or_err = _push_with_auth(repo_path, repo_name, branch, kf_pat)
        if not ok:
            return {
                "repo": repo_name,
                "outcome": "failed",
                "pushed_sha": None,
                "changes": [],
                "error": sha_or_err,
            }

        changes = [
            {
                "task": p.task,
                "old_status": p.old_status,
                "new_status": p.new_status,
            }
            for p in proposals_for_repo
        ]
        print(f"[DONE] {repo_name}: pushed {sha_or_err[:8]} (branch: {branch})")
        return {
            "repo": repo_name,
            "outcome": "succeeded",
            "pushed_sha": sha_or_err,
            "changes": changes,
            "error": None,
        }

    except Exception as exc:  # noqa: BLE001
        import traceback
        tb = traceback.format_exc()
        print(f"[FAIL] {repo_name}: unexpected error — {exc}", file=sys.stderr)
        print(tb, file=sys.stderr)
        return {
            "repo": repo_name,
            "outcome": "failed",
            "pushed_sha": None,
            "changes": [],
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Batch orchestration (Plan 03: WB-02, WB-05)
# ---------------------------------------------------------------------------

def _confirm_batch(proposals_by_repo: dict) -> bool:
    """Print a single summary table and read ONE y/N prompt for the whole batch.

    Exactly one prompt is read per call — never inside the per-repo loop (WB-02).
    Confirms destructive ops once as a batch, matching the org-scan preference
    (see project MEMORY.md: "confirm destructive ops once as a batch").

    Args:
        proposals_by_repo: dict[repo_name, list[Proposal-like objects]]

    Returns:
        True if the user answered y/yes (case-insensitive); False otherwise.
    """
    total_repos = len(proposals_by_repo)
    total_changes = sum(len(ps) for ps in proposals_by_repo.values())

    print(
        f"\n[INFO] Write-back summary — {total_repos} repo(s), "
        f"{total_changes} proposed change(s):\n"
    )
    print(f"  {'Repo':<30} {'Task':<40} {'Change'}")
    print(f"  {'-'*30} {'-'*40} {'-'*25}")
    for repo_name in sorted(proposals_by_repo):
        for p in proposals_by_repo[repo_name]:
            change_str = f"{p.old_status} -> {p.new_status}"
            print(f"  {repo_name:<30} {p.task:<40} {change_str}")
    print()

    # Single prompt — EXACTLY one input() call per run (WB-02; T-03-09)
    answer = input(f"Proceed with {total_changes} write(s) to {total_repos} repo(s)? [y/N]: ")
    return answer.strip().lower() in ("y", "yes")


def _write_manifest(
    manifests_dir: Path,
    run_id: str,
    repos_results: list[dict],
) -> None:
    """Write a per-run JSON recovery manifest to manifests_dir/{run_id}.json.

    Records every repo's outcome, pushed sha, change list, and error for
    audit / partial-batch recovery (WB-05).

    Security (T-03-11): manifests_dir is gitignored — the manifest is never
    committed into kf-cpto. No token is stored in the manifest.

    This function NEVER raises on OSError (manifest write failure must not abort
    the run). Prints a Warning on failure and returns silently.

    Args:
        manifests_dir: Directory for manifest files (typically MANIFESTS_DIR).
        run_id:        Run identifier string (UTC timestamp, e.g. '20260604T114000Z').
        repos_results: List of manifest-entry dicts from _write_repo().
    """
    # Tally outcomes
    summary: dict[str, int] = {"succeeded": 0, "failed": 0, "conflict": 0, "skipped": 0}
    for entry in repos_results:
        outcome = entry.get("outcome", "failed")
        if outcome in summary:
            summary[outcome] += 1
        else:
            summary["failed"] += 1

    manifest: dict = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_repos": len(repos_results),
        "summary": summary,
        "repos": repos_results,
    }

    try:
        manifests_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifests_dir / f"{run_id}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"[INFO] Manifest written: {manifest_path}")
    except OSError as exc:  # noqa: BLE001 — non-fatal; manifest failure must not abort run
        print(f"Warning: failed to write manifest to {manifests_dir}/{run_id}.json: {exc}")


def run(proposals: list, dry_run: bool = False) -> list[dict]:
    """Batch-orchestrate write-back over all repos in the proposal list.

    Flow:
        1. Group proposals by repo name.
        2. Pair each repo group with its enum record (from repo_enum.run()).
        3. Call _confirm_batch() ONCE — or skip if dry_run=True.
        4. If confirmed (and not dry_run), read KF_PAT from env (fail-fast if unset).
        5. Loop over repos: call _write_repo() per repo; continue past conflicts/failures.
        6. Call _write_manifest() with all results.
        7. Print [DONE]/[CONFLICT]/[SKIP]/[FAIL] tally.
        8. Return the list of manifest-entry dicts (no sys.exit).

    Security (T-03-12): KF_PAT is read from os.environ only inside run() at push time,
    fail-fast with a clear [ERROR] if unset when a non-dry push is requested. Never read
    at import time.

    Args:
        proposals: List of Proposal-like objects with .repo, .task, .old_status, .new_status.
        dry_run:   If True, print the summary but write and push nothing. No KF_PAT needed.

    Returns:
        List of manifest-entry dicts (one per repo that had proposals).
    """
    from repo_enum import run as enum_run  # noqa: E402 — deferred to avoid circular import

    print("Activity Sync — Write-Back — Starting...")

    if not proposals:
        print("[INFO] No changes proposed — nothing to write.")
        return []

    # Group proposals by repo name
    proposals_by_repo: dict = {}
    for p in proposals:
        proposals_by_repo.setdefault(p.repo, []).append(p)

    # Build lookup of enum records by repo name
    try:
        records_list = enum_run()
    except RuntimeError as exc:
        # Pre-existing GSD orchestration state (same pattern as reconcile.py)
        msg = str(exc)
        if "working tree is dirty" in msg:
            print(f"[WARN] repo_enum clean-tree check failed (pre-existing GSD state): {msg}")
            print("[WARN] Continuing with direct repo enumeration.")
            records_list = _enum_records_fallback_writeback()
        else:
            raise
    records_by_name: dict = {r["name"]: r for r in records_list}

    # Dry-run path: print summary, write nothing, no KF_PAT needed (T-03-12)
    if dry_run:
        print("[INFO] --dry-run: previewing changes (no write, no push).")
        _confirm_batch_preview(proposals_by_repo)
        print("[INFO] Dry-run complete — no files written, no pushes made.")
        return []

    # Single batch-confirm (WB-02, T-03-09): exactly one prompt for the whole batch
    if not _confirm_batch(proposals_by_repo):
        print("[INFO] Batch write cancelled by operator.")
        return []

    # Read KF_PAT at push time only (T-03-12: never at import time)
    kf_pat = os.environ.get("KF_PAT", "")
    if not kf_pat:
        print("[ERROR] KF_PAT environment variable is unset. Set KF_PAT to your GitHub PAT before pushing.")
        raise RuntimeError("KF_PAT unset — cannot push to remote repos")

    # Generate run ID (UTC timestamp)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    results: list[dict] = []

    # Loop over repos — continue past conflict/failure (T-03-13, WB-03)
    for repo_name, repo_proposals in sorted(proposals_by_repo.items()):
        record = records_by_name.get(repo_name)
        if record is None:
            print(f"[WARN] No enum record found for repo '{repo_name}' — skipping")
            results.append({
                "repo": repo_name,
                "outcome": "skipped",
                "pushed_sha": None,
                "changes": [],
                "error": f"No enum record found for repo '{repo_name}'",
            })
            continue

        # _write_repo never raises — per-repo error boundary (T-03-13)
        entry = _write_repo(record, repo_proposals, kf_pat, run_id)
        results.append(entry)

    # Write recovery manifest (WB-05) — non-fatal
    _write_manifest(MANIFESTS_DIR, run_id, results)

    # Print tally
    tally = {"succeeded": 0, "failed": 0, "conflict": 0, "skipped": 0}
    for entry in results:
        outcome = entry.get("outcome", "failed")
        if outcome in tally:
            tally[outcome] += 1
    print(
        f"\n[TALLY] {tally['succeeded']} [DONE] / "
        f"{tally['conflict']} [CONFLICT] / "
        f"{tally['skipped']} [SKIP] / "
        f"{tally['failed']} [FAIL]"
    )

    print("Activity Sync — Write-Back — Done!")
    return results


def _confirm_batch_preview(proposals_by_repo: dict) -> None:
    """Print the batch summary table without prompting (used by dry_run path)."""
    total_repos = len(proposals_by_repo)
    total_changes = sum(len(ps) for ps in proposals_by_repo.values())
    print(
        f"\n[INFO] Dry-run preview — {total_repos} repo(s), "
        f"{total_changes} proposed change(s):\n"
    )
    print(f"  {'Repo':<30} {'Task':<40} {'Change'}")
    print(f"  {'-'*30} {'-'*40} {'-'*25}")
    for repo_name in sorted(proposals_by_repo):
        for p in proposals_by_repo[repo_name]:
            change_str = f"{p.old_status} -> {p.new_status}"
            print(f"  {repo_name:<30} {p.task:<40} {change_str}")
    print()


def _enum_records_fallback_writeback() -> list[dict]:
    """Enumerate repos-local/ directly without the clean-tree assertion.

    Mirrors the fallback pattern in reconcile.py for pre-existing GSD state.
    """
    import repo_enum as _re
    repo_names = _re.enumerate_repos(_re.REPOS_LOCAL_DIR)
    if not repo_names:
        return []
    records = []
    for name in repo_names:
        local_path = _re.REPOS_LOCAL_DIR / name
        local_path_str = str(local_path)
        remote_url = _re._get_remote_url(local_path_str)
        if not _re._check_remote_org(remote_url, name):
            continue
        branch = _re._get_default_branch(local_path_str)
        records.append({
            "name": name,
            "local_path": local_path_str,
            "remote_url": remote_url,
            "branch": branch,
        })
    return records


def main() -> int:
    """Parse --dry-run flag and drive reconcile.run() -> writeback.run().

    Mirrors reconcile.py main() pattern: argparse, try/except RuntimeError,
    map to exit codes.

    KF_PAT is read from os.environ inside run() at push time, not here
    (T-03-12: never at import time; dry-run never reads it).

    Returns:
        0 on success, 1 on RuntimeError.
    """
    import argparse
    import reconcile  # noqa: E402

    parser = argparse.ArgumentParser(
        description=(
            "Activity Sync — Write-Back: reconcile task statuses, write and push "
            "to tracked repos. Requires KF_PAT env var for live pushes."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Preview proposed changes without writing or pushing anything. "
            "No KF_PAT required in dry-run mode."
        ),
    )
    args = parser.parse_args()

    if args.dry_run:
        print("[INFO] --dry-run: read-only preview; no files will be written or pushed.")

    try:
        proposals = reconcile.run()
        run(proposals, dry_run=args.dry_run)
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# Frontmatter round-trip (ruamel.yaml, WB-01)
# ---------------------------------------------------------------------------

def split_kanban(content: str) -> tuple[str, str]:
    """Split kanban.md content into (frontmatter_str, body_str).

    Uses _FM_RE to locate the opening '---' block. frontmatter_str is the raw
    YAML text between the delimiters (without the '---' lines themselves).
    body_str is everything after the closing '---\\n'.

    Args:
        content: Full kanban.md file content as a string.

    Returns:
        (frontmatter_str, body_str) tuple.

    Raises:
        ValueError: If content does not start with a YAML frontmatter block.
    """
    match = _FM_RE.match(content)
    if not match:
        raise ValueError(
            "No YAML frontmatter found in kanban.md. "
            "File must start with --- ... --- block."
        )
    frontmatter_str = match.group(1)
    body_str = content[match.end():]
    return frontmatter_str, body_str


def roundtrip_frontmatter(fm_str: str) -> str:
    """Round-trip frontmatter YAML through ruamel, preserving # comments and key order.

    Uses ruamel.YAML() with preserve_quotes=True so quoted string values survive
    the round-trip byte-identical.

    Applies a trailing-newline guard: ruamel may emit extra blank lines in some
    edge cases. We normalize to exactly one trailing newline (Pitfall 5).

    Args:
        fm_str: Raw YAML text extracted by split_kanban() (no '---' delimiters).

    Returns:
        Round-tripped YAML text ending with exactly one '\\n'.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(fm_str)
    stream = StringIO()
    yaml.dump(data, stream)
    # Pitfall 5: normalize to exactly one trailing newline
    return stream.getvalue().rstrip("\n") + "\n"


def reconstruct_kanban(fm_str: str, body_str: str) -> str:
    """Reconstruct a kanban.md string from (possibly edited) frontmatter and body.

    The round-tripped frontmatter preserves # comments, key order, and quoting
    (WB-01). For an unmodified file, reconstruct_kanban(*split_kanban(orig))
    produces a byte-identical string.

    Important: the body is NEVER passed through ruamel. Only the frontmatter is
    round-tripped — the body (table rows, prose, HTML comments) is used verbatim.

    Args:
        fm_str:   Raw frontmatter YAML text (no '---' delimiters).
        body_str: Everything after the closing '---' delimiter (may be edited).

    Returns:
        Complete kanban.md content string with '---\\n' delimiters around the
        round-tripped frontmatter followed by the (possibly edited) body.
    """
    rt_fm = roundtrip_frontmatter(fm_str)
    return "---\n" + rt_fm + "---\n" + body_str


# ---------------------------------------------------------------------------
# Status-cell targeted replacement (Pattern 2 from 03-RESEARCH.md)
# ---------------------------------------------------------------------------

def apply_status_change(
    body_str: str,
    task_name: str,
    new_status: str,
) -> tuple[str, bool]:
    """Replace the Status cell for the first row whose Task cell matches task_name.

    Operates on the raw body_str (pre-sanitize). Works for both 4-col and 6-col
    tables because Status is always the last data column (parts[-2] of a row that
    ends with a trailing '|'). Rows without a trailing '|' are malformed GFM for
    this addressing scheme and are skipped with a [WARN] (CR-02) rather than
    corrupting the Effort cell.

    Rules:
    - Only the FIRST matching row is updated (forward-only, one match per Proposal).
    - If current status already equals new_status, returns (body_str, False) unchanged.
    - If task_name appears on multiple rows, updates only the first and prints [WARN].
    - If task_name is not found, returns (body_str, False) unchanged.

    Args:
        body_str:   Body portion of kanban.md (everything after closing '---').
        task_name:  Exact task name to match (from Proposal.task; matches parts[1].strip()).
        new_status: Target status string (validated TASK_STATUSES member by caller).

    Returns:
        (new_body_str, was_changed) where was_changed is True if any row was modified.
    """
    lines = body_str.splitlines(keepends=True)
    new_lines: list[str] = []
    changed = False
    match_count = 0

    for line in lines:
        stripped = line.rstrip("\n")

        # Only process pipe-table rows
        if not stripped.startswith("|"):
            new_lines.append(line)
            continue

        # CR-02: Status is addressed as parts[-2], which is only the Status cell
        # when the row ends with a trailing '|'. GFM permits trailing-pipe-less
        # rows; for those parts[-2] is the Effort cell and we would overwrite the
        # wrong column while leaving the real status untouched (silent data loss).
        # Require a well-formed row (starts AND ends with '|'); skip otherwise.
        if not stripped.endswith("|"):
            print(f"[WARN] Skipping malformed (no trailing pipe) row: {stripped!r}")
            new_lines.append(line)
            continue

        parts = stripped.split("|")

        # Need at least | task | ... | status | => 4 separator parts minimum
        if len(parts) < 4:
            new_lines.append(line)
            continue

        task_cell = parts[1].strip()
        if task_cell != task_name:
            new_lines.append(line)
            continue

        # Matching row found
        match_count += 1

        if match_count > 1:
            # Duplicate task name — skip this row (first-match-only contract)
            print(
                f"[WARN] Duplicate task name '{task_name}' found in table "
                f"(match #{match_count}). Only the first occurrence is updated."
            )
            new_lines.append(line)
            continue

        # First match: check if status already equals target
        old_status = parts[-2].strip()
        if old_status == new_status:
            # No change needed — idempotent skip
            new_lines.append(line)
            continue

        # Apply the replacement: parts[-2] is the last data cell (Status column)
        parts[-2] = f" {new_status} "
        eol = "\n" if line.endswith("\n") else ""
        new_lines.append("|".join(parts) + eol)
        changed = True

    return "".join(new_lines), changed


# ---------------------------------------------------------------------------
# Idempotency byte-compare gate (Pattern 6 from 03-RESEARCH.md)
# ---------------------------------------------------------------------------

def _content_changed(kanban_path: str, proposed: str) -> bool:
    """True if proposed content differs from the current file bytes.

    Used as an idempotency gate before any file write or git operation.
    Returns False (skip write) when the proposed string is byte-identical
    to the current kanban.md content.

    Args:
        kanban_path: Absolute path to the kanban.md file.
        proposed:    The fully reconstructed kanban.md content string.

    Returns:
        True if content differs (write needed); False if content is identical (skip).
    """
    current = Path(kanban_path).read_bytes()
    return current != proposed.encode("utf-8")
