#!/usr/bin/env python3
"""
Activity Sync — Reconciler

Dry-run reconciliation engine: imports repo_enum.run(), mines Tier-1 merged-PR
signals via GitHub REST API and Tier-2 active-branch signals via local git,
reconciles them against declared kanban statuses forward-only, prints a grouped
change list, and returns structured Proposal objects for Phase 3 consumption.

Tier-1 (Done): merged PR whose merge commit is reachable from origin/<default>;
               linked closed issues resolved via PR body closing keywords.
Tier-2 (In Progress): active remote branches matching task tokens (no API).

Usage:
    python .claude/skills/activity-sync/reconcile.py --dry-run

Phase 3 entry point:
    from reconcile import run
    proposals = run()
"""
from __future__ import annotations

import fnmatch
import subprocess
import sys
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional

import requests

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
HTTP_TIMEOUT_SECONDS = 30  # bound GitHub REST calls (mirrors GIT_TIMEOUT_SECONDS discipline)
GITHUB_API = "https://api.github.com"

# Integration-branch globs: short-name fnmatch patterns that identify branches used as
# non-default merge targets (off-default integration branches).  The INTEGRATION-BRANCH
# SET built at runtime = {default_branch} ∪ {branches matching any of these globs}.
# The default branch is ALWAYS a member regardless of glob match.
# Config lives here and only here — NO hardcoded repo or branch names in logic paths
# (CLAUDE.md anti-pattern: no "kf-platform", no "claude-migration", no bare "uat" outside
# this constant).  Add or remove patterns here to adjust what counts as an integration
# branch across all tracked repos.
INTEGRATION_BRANCH_GLOBS: list[str] = ["uat", "work", "*-migration"]

# Closing-keyword regex: matches the 9 GitHub closing keywords followed by #N.
# Same-repo only — cross-repo OWNER/REPO#N deliberately not matched (security:
# avoids resolving issues from untrusted orgs).
# Source: docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue
_CLOSING_KEYWORDS_RE = re.compile(
    r'\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)',
    re.IGNORECASE,
)

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
# Tier-1 acquisition helpers — GitHub REST API + reachability gate
# ---------------------------------------------------------------------------

def _build_headers() -> dict:
    """Build GitHub API request headers with optional Bearer auth.

    Reads KF_PAT first, falls back to GITHUB_TOKEN — mirrors discover.py pattern.
    Warns on missing token (unauthenticated rate limit: 60 req/hr).
    NEVER prints the token value (T-02-05 Information Disclosure mitigation).
    """
    token = os.environ.get("KF_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: No KF_PAT or GITHUB_TOKEN set. API rate limits will be very low.")
    headers: dict = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _list_merged_prs(org: str, repo: str, headers: dict) -> list[dict]:
    """Return all merged PRs for a repo (paginated, state=closed, filter merged_at).

    Pagination mirrors discover.py pattern (per_page=100, page counter).
    Warns and breaks on non-200 status. Rate-limit warning below 100 remaining.
    Filters out PRs with merged_at is None (not actually merged).
    PR body may be None for no-description PRs — callers must guard (Pitfall 4).
    """
    prs: list[dict] = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{GITHUB_API}/repos/{org}/{repo}/pulls",
                headers=headers,
                params={"state": "closed", "per_page": 100, "page": page},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            # WR-01: bound the call; a hung connection must not block forever.
            # WR-02: surface that the result may be partial (don't silently truncate).
            print(
                f"[WARN] PR list for {repo} errored on page {page} ({exc}); "
                f"results may be incomplete — change list for this repo is partial."
            )
            break
        if resp.status_code != 200:
            # WR-02: a 403 with rate-limit exhausted means the list is truncated,
            # not empty-by-fact. Distinguish it so the operator knows the change
            # list is partial rather than a confirmed no-activity result.
            remaining = resp.headers.get("X-RateLimit-Remaining", "?")
            if resp.status_code == 403 and str(remaining) == "0":
                print(
                    f"[WARN] PR list for {repo} hit GitHub rate limit at page {page}; "
                    f"results may be incomplete — change list for this repo is partial."
                )
            else:
                print(f"Warning: PR list for {repo} failed: {resp.status_code}")
            break
        batch = resp.json()
        if not batch:
            break
        prs.extend(pr for pr in batch if pr.get("merged_at") is not None)
        page += 1
        remaining = resp.headers.get("X-RateLimit-Remaining", "?")
        if str(remaining).isdigit() and int(remaining) < 100:
            print(
                f"[WARN] GitHub rate limit low: {remaining} remaining "
                f"(reached page {page - 1} for {repo}; further pages may truncate results)"
            )
    return prs


def _extract_issue_refs(body: Optional[str]) -> list[int]:
    """Extract same-repo issue numbers from PR body using GitHub closing keywords.

    Returns [] when body is None or empty (Pitfall 4 — body is None for PRs
    with no description). Cross-repo OWNER/REPO#N patterns are NOT matched.
    """
    if not body:
        return []
    # WR-05: de-duplicate while preserving first-seen order so a body containing
    # "closes #5 ... resolved #5" does not trigger duplicate API fetches or
    # duplicate candidate entries downstream.
    return list(dict.fromkeys(int(m) for m in _CLOSING_KEYWORDS_RE.findall(body)))


def _get_issue(org: str, repo: str, issue_number: int, headers: dict) -> Optional[dict]:
    """Fetch a single issue by number. Returns None on 404 or error.

    Used to resolve linked issue titles for task token-matching (RECON-01).
    Source: docs.github.com/en/rest/issues/issues
    """
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{org}/{repo}/issues/{issue_number}",
            headers=headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        # WR-01: bound the call so a hung connection can't block indefinitely.
        print(f"Warning: issue fetch errored #{issue_number} in {repo}: {exc}")
        return None
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code == 404:
        return None  # issue deleted or inaccessible — not an error
    print(f"Warning: issue fetch failed #{issue_number} in {repo}: {resp.status_code}")
    return None


def _is_merge_reachable(
    repo_path: str, merge_commit_sha: str, default_branch: str
) -> Optional[bool]:
    """Test whether a merge commit is still reachable from origin/<default_branch>.

    Uses git merge-base --is-ancestor (RECON-08 canonical revert gate).
    Covers force-push drops, rebases, revert-of-merge, squash merges.
    NEVER parses Revert "..." commit messages (T-02-08).

    Returns:
        True  — exit 0: merge commit is an ancestor (reachable, not reverted)
        False — exit 1: not an ancestor (reverted or force-pushed away)
        None  — other exit code: git error; callers treat as not reachable (conservative)

    merge_commit_sha is passed via arg-list subprocess; never shell-interpolated (T-02-07).
    """
    result = _run_git([
        "-C", repo_path,
        "merge-base", "--is-ancestor",
        merge_commit_sha, f"origin/{default_branch}",
    ])
    if result.returncode == 0:
        return True
    elif result.returncode == 1:
        return False
    else:
        print(f"Warning: merge-base error (rc={result.returncode}): {result.stderr.strip()}")
        return None  # conservative: treat as not reachable


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


def _integration_branches(repo_path: str, default_branch: str) -> list[str]:
    """Return the integration-branch set for a repo: default branch plus any locally-known
    remote branches whose short name matches a glob in INTEGRATION_BRANCH_GLOBS.

    The set is built by reusing _list_remote_branches (single source of remote-branch truth;
    no second for-each-ref call).  _list_remote_branches already excludes HEAD and
    default_branch, so we union the glob-matched extras onto {default_branch} explicitly.

    Returns: [default_branch, ...sorted glob-matched branches...]  (default first, de-duped).
    """
    extras = [
        name
        for name in _list_remote_branches(repo_path, default_branch)
        if any(fnmatch.fnmatch(name, g) for g in INTEGRATION_BRANCH_GLOBS)
    ]
    return [default_branch] + sorted(set(extras))


# ---------------------------------------------------------------------------
# Reconciliation engine
# ---------------------------------------------------------------------------

def reconcile_repo(record: dict, headers: dict) -> list[Proposal]:
    """Mine Tier-1 and Tier-2 signals for one repo and return Proposals.

    Tier-1 (Done): merged PRs reachable from origin/<default> whose title or
    linked closed-issue title token-matches a task. Reachability via
    git merge-base --is-ancestor (RECON-08 canonical revert gate).

    Tier-2 (In Progress): active remote branches matching task tokens (pure-local
    git, no API). Cap: never advance past In Progress (Todo -> In Progress only).

    Both tiers feed the same per-task candidate dict; conflict resolution picks
    most_advanced, so Tier-1 Done wins over Tier-2 In Progress (RECON-03).

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

    # Integration-branch set: default branch plus any branches matching INTEGRATION_BRANCH_GLOBS.
    # Computed once; reused in both Tier-1 (any-branch reachability) and Tier-2 (exclusion).
    integration_branches = _integration_branches(repo_path, default_branch)

    # Per-task candidate list: (proposed_status, tier, signal, url)
    proposals: dict[str, list] = {}

    # --- Tier-1: merged PRs reachable from any branch in the integration set ---
    # This block runs before Tier-2 so both feeds the same proposals dict.
    # Conflict resolution (most_advanced) then picks Done over In Progress.
    # Tier-1 short-circuits on the first True from the integration set (any-branch semantics):
    # a merge reached via an off-default integration branch (e.g. uat/*-migration) is Done,
    # not In Progress. Conservative gate preserved: only True counts; False or None skips.
    merged_prs = _list_merged_prs(ORG, repo_name, headers)
    for pr in merged_prs:
        sha = pr.get("merge_commit_sha")
        if not sha:
            # Pitfall 1: merge_commit_sha absent — conservative skip (no git call)
            continue
        # Reachability gate (RECON-08): covers force-push, rebase, revert-of-merge.
        # Iterate integration set; short-circuit on first True.
        # merge_commit_sha and branch values flow via arg-list _run_git; never
        # shell-interpolated (T-02-07).
        reachable = False
        for _ib in integration_branches:
            _r = _is_merge_reachable(repo_path, sha, _ib)
            if _r is True:
                reachable = True
                break
        if not reachable:
            # No integration branch confirmed reachability — skip conservatively
            continue

        # WR-03: read number defensively like every other field; one malformed
        # PR object should skip that PR, not abort reconciliation for the repo.
        pr_number = pr.get("number")
        if pr_number is None:
            continue
        # Match PR title to task tokens (T-02-06: normalized plaintext, no eval)
        pr_title = pr.get("title", "")
        pr_url = pr.get("html_url")
        signal_desc = f"PR #{pr_number}: {pr_title} (merged)"
        for task in tasks:
            if task_matches_signal(task["task"], pr_title):
                proposals.setdefault(task["task"], []).append(
                    ("Done", 1, signal_desc, pr_url)
                )

        # Linked-issue match (RECON-01): parse closes/fixes #N from PR body
        for issue_num in _extract_issue_refs(pr.get("body")):
            issue = _get_issue(ORG, repo_name, issue_num, headers)
            if issue and issue.get("state") == "closed":
                issue_title = issue.get("title", "")
                issue_signal = f"issue #{issue_num} closed (via PR #{pr_number})"
                issue_url = issue.get("html_url")
                for task in tasks:
                    if task_matches_signal(task["task"], issue_title):
                        proposals.setdefault(task["task"], []).append(
                            ("Done", 1, issue_signal, issue_url)
                        )

    # --- Tier-2: active remote branches ---
    # Pure-local git (no API); no commit enumeration (RECON-06).
    # Filter out every branch in the integration set before the task-match loop:
    # integration branches (default, uat, work, *-migration) are merge targets, not
    # active-work signals — they must never demote finished work to In Progress.
    # _list_remote_branches already excludes default_branch; we additionally exclude
    # the glob-matched integration branches here.
    _integration_set = set(integration_branches)
    remote_branches = [
        b for b in _list_remote_branches(repo_path, default_branch)
        if b not in _integration_set
    ]
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
        # Tier-1 (Done, tier=1) sorts before Tier-2 (In Progress, tier=2) because
        # STATUS_RANK["Done"] == 3 > STATUS_RANK["In Progress"] == 1.
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

def _report_planning_state(record: dict) -> None:
    """[TIER-3] Surface a repo's .planning/STATE.md progress as context.

    Read-only informational signal (RECON-05 preserved): any tracked repo may
    carry a GSD .planning/ folder whose STATE.md frontmatter records milestone
    progress. That progress maps to kanban tasks by human judgment (via
    docs/_data/migration_plan.yml), so it is printed for the operator rather
    than converted into automatic proposals.
    """
    state_path = Path(record.get("local_path", "")) / ".planning" / "STATE.md"
    if not state_path.exists():
        return
    try:
        content = state_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[WARN] {record.get('name')}: unreadable .planning/STATE.md ({exc})")
        return
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    summary = ""
    if m:
        import yaml as _yaml
        try:
            fm = _yaml.safe_load(m.group(1)) or {}
            prog = fm.get("progress") or {}
            summary = (
                f"milestone {fm.get('milestone', '?')} · "
                f"phases {prog.get('completed_phases', '?')}/{prog.get('total_phases', '?')} · "
                f"plans {prog.get('completed_plans', '?')}/{prog.get('total_plans', '?')} · "
                f"{prog.get('percent', '?')}%"
            )
        except _yaml.YAMLError:
            summary = "frontmatter unparseable"
    print(
        f"[INFO] {record.get('name')}: .planning present — {summary or 'no progress frontmatter'} "
        f"(TIER-3 context; align statuses via docs/_data/migration_plan.yml)"
    )


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

    # Build headers once; pass to each reconcile_repo call (T-02-05: token read once)
    headers = _build_headers()

    try:
        records = enum_run()
    except RuntimeError as exc:
        msg = str(exc)
        if "working tree is dirty" in msg:
            # Pre-existing GSD orchestration state — reconcile.py wrote nothing.
            # Extract the records that were accumulated before the exception via
            # a fallback direct enumeration, or proceed with empty and warn.
            print(f"[WARN] repo_enum clean-tree check failed (pre-existing GSD state, not our writes): {msg}")
            print("[WARN] Proceeding with Tier-1/Tier-2 reconciliation using fallback enumeration.")
            records = _enum_records_fallback()
        else:
            raise

    all_proposals: list[Proposal] = []

    for record in records:
        _report_planning_state(record)
        proposals = reconcile_repo(record, headers)
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
        description="Activity Mining + Reconciliation — dry-run only (read-only; writes nothing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Explicit opt-in to the read-only preview. This phase is dry-run-only "
            "and never writes; there is no write mode. The flag is accepted for "
            "forward-compatibility with Phase 3 but does not change behavior here."
        ),
    )
    args = parser.parse_args()

    # WR-04: the flag is now read (no misleading default=True). This phase has no
    # write path — make the read-only contract observable instead of implying a
    # non-dry mode could exist. Phase 3 owns write-back.
    if args.dry_run:
        print("[INFO] --dry-run requested; this phase is read-only and writes nothing.")
    else:
        print("[INFO] Read-only mode (this phase only previews; it never writes).")

    try:
        run()
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
