#!/usr/bin/env python3
"""
Activity Sync — Write-Back (string builders + git operations)

Consumes reconcile.run() Proposal objects and applies them to kanban.md files
in repos-local/. Plans 02/03 complete the git operations layer.

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

Usage:
    from writeback import split_kanban, reconstruct_kanban, apply_status_change
    from writeback import _write_repo

Phase 3 entry point (plan 03 will add run() / main()):
    from writeback import run
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
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
    tables because Status is always the last data column (parts[-2]).

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
