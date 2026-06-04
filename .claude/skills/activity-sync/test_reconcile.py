#!/usr/bin/env python3
"""
Test suite for reconcile.py — Task 1: Pure helpers and matching/ranking core.

Runs with plain Python (no pytest dependency):
    python .claude/skills/activity-sync/test_reconcile.py

Exits non-zero on any failed assert.
"""

import sys
import io
import os
from pathlib import Path

# Ensure we can import reconcile from this directory
_SKILL_DIR = Path(__file__).parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

# ---------------------------------------------------------------------------
# Attempt import — will fail (RED) if reconcile.py does not exist yet
# ---------------------------------------------------------------------------

import reconcile
from reconcile import (
    task_matches_signal,
    is_advancement,
    most_advanced,
    STATUS_RANK,
    Proposal,
    render_change_list,
    reconcile_repo,
    _build_headers,
    _extract_issue_refs,
    _is_merge_reachable,
)

PASS = 0
FAIL = 0


def check(name: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  PASS: {name}")
        PASS += 1
    else:
        print(f"  FAIL: {name}")
        FAIL += 1


# ---------------------------------------------------------------------------
# STATUS_RANK assertions
# ---------------------------------------------------------------------------

print("--- STATUS_RANK ---")
check("STATUS_RANK['Todo'] == 0", STATUS_RANK == {"Todo": 0, "In Progress": 1, "Review": 2, "Done": 3})
check("STATUS_RANK dict keys match TASK_STATUSES", set(STATUS_RANK.keys()) == {"Todo", "In Progress", "Review", "Done"})

# ---------------------------------------------------------------------------
# task_matches_signal assertions
# ---------------------------------------------------------------------------

print("--- task_matches_signal ---")
check(
    "setup authentication matches feat: setup authentication flow",
    task_matches_signal("Setup authentication", "feat: setup authentication flow") is True,
)
check(
    "setup authentication does NOT match fix: auth token refresh",
    task_matches_signal("Setup authentication", "fix: auth token refresh") is False,
)
check(
    "add login form matches add-login-form component (hyphen to space)",
    task_matches_signal("Add login form", "add-login-form component") is True,
)
check(
    "migrate database schema matches migrate-database-schema-v2",
    task_matches_signal("Migrate database schema", "migrate-database-schema-v2") is True,
)
check(
    "empty signal always returns False",
    task_matches_signal("anything", "") is False,
)
check(
    "empty task name never matches",
    task_matches_signal("", "x") is False,
)
# Additional edge cases
check(
    "single stopword task never matches",
    task_matches_signal("the", "the quick brown fox") is False,
)
check(
    "case-insensitive match: SETUP AUTHENTICATION matches feat: setup authentication flow",
    task_matches_signal("SETUP AUTHENTICATION", "feat: setup authentication flow") is True,
)

# ---------------------------------------------------------------------------
# is_advancement assertions
# ---------------------------------------------------------------------------

print("--- is_advancement ---")
check(
    "Todo -> In Progress is advancement",
    is_advancement("Todo", "In Progress") is True,
)
check(
    "Done -> Todo is NOT advancement",
    is_advancement("Done", "Todo") is False,
)
check(
    "In Progress -> In Progress is NOT advancement (no change)",
    is_advancement("In Progress", "In Progress") is False,
)
check(
    "Todo -> Done is advancement",
    is_advancement("Todo", "Done") is True,
)
check(
    "Review -> Done is advancement",
    is_advancement("Review", "Done") is True,
)
check(
    "Done -> Review is NOT advancement",
    is_advancement("Done", "Review") is False,
)

# ---------------------------------------------------------------------------
# most_advanced assertions
# ---------------------------------------------------------------------------

print("--- most_advanced ---")
check(
    "most_advanced(['In Progress', 'Done']) == 'Done'",
    most_advanced(["In Progress", "Done"]) == "Done",
)
check(
    "most_advanced(['Todo', 'Review']) == 'Review'",
    most_advanced(["Todo", "Review"]) == "Review",
)
check(
    "most_advanced(['Todo']) == 'Todo'",
    most_advanced(["Todo"]) == "Todo",
)
check(
    "most_advanced(['Done', 'Done']) == 'Done'",
    most_advanced(["Done", "Done"]) == "Done",
)

# ---------------------------------------------------------------------------
# Proposal dataclass
# ---------------------------------------------------------------------------

print("--- Proposal dataclass ---")
p = Proposal(
    repo="test-repo",
    task="Setup authentication",
    old_status="Todo",
    new_status="In Progress",
    tier=2,
    signal="branch origin/setup-authentication exists",
)
check("Proposal has repo field", p.repo == "test-repo")
check("Proposal has task field", p.task == "Setup authentication")
check("Proposal has old_status field", p.old_status == "Todo")
check("Proposal has new_status field", p.new_status == "In Progress")
check("Proposal has tier field", p.tier == 2)
check("Proposal has signal field", p.signal == "branch origin/setup-authentication exists")
check("Proposal signal_url defaults to None", p.signal_url is None)

p_with_url = Proposal(
    repo="r", task="t", old_status="Todo", new_status="Done",
    tier=1, signal="PR #1: foo", signal_url="https://github.com/r/pull/1"
)
check("Proposal signal_url accepts value", p_with_url.signal_url == "https://github.com/r/pull/1")

# ---------------------------------------------------------------------------
# reconcile_repo: skip on kanban_exists=False
# ---------------------------------------------------------------------------

print("--- reconcile_repo early-skip ---")
record_no_kanban = {
    "name": "test-repo",
    "local_path": "/fake/path/test-repo",
    "branch": "main",
    "kanban_exists": False,
    "valid_task_count": 0,
    "tasks": [],
}
result = reconcile_repo(record_no_kanban)
check("kanban_exists=False returns empty list", result == [])

record_zero_valid = {
    "name": "test-repo",
    "local_path": "/fake/path/test-repo",
    "branch": "main",
    "kanban_exists": True,
    "valid_task_count": 0,
    "tasks": [],
}
result = reconcile_repo(record_zero_valid)
check("valid_task_count=0 returns empty list", result == [])

# ---------------------------------------------------------------------------
# reconcile_repo: Tier-2 advance Todo -> In Progress (branch match)
# ---------------------------------------------------------------------------

print("--- reconcile_repo Tier-2 advance ---")

class _FakeBranches:
    """Context manager to monkeypatch _list_remote_branches."""
    def __init__(self, branches):
        self.branches = branches
        self._orig = None

    def __enter__(self):
        self._orig = reconcile._list_remote_branches
        reconcile._list_remote_branches = lambda path, default: self.branches
        return self

    def __exit__(self, *args):
        reconcile._list_remote_branches = self._orig


record_with_todo = {
    "name": "some-repo",
    "local_path": "/fake/some-repo",
    "branch": "main",
    "kanban_exists": True,
    "valid_task_count": 1,
    "tasks": [{"task": "Setup authentication", "status": "Todo"}],
}

with _FakeBranches(["setup-authentication"]):
    proposals = reconcile_repo(record_with_todo)

check("Tier-2 match produces 1 proposal", len(proposals) == 1)
if proposals:
    check("Tier-2 proposal old_status is Todo", proposals[0].old_status == "Todo")
    check("Tier-2 proposal new_status is In Progress", proposals[0].new_status == "In Progress")
    check("Tier-2 proposal tier is 2", proposals[0].tier == 2)
    check("Tier-2 proposal signal mentions branch", "branch origin/setup-authentication" in proposals[0].signal)

# Task already In Progress — Tier-2 should NOT advance further
record_in_progress = {
    "name": "some-repo",
    "local_path": "/fake/some-repo",
    "branch": "main",
    "kanban_exists": True,
    "valid_task_count": 1,
    "tasks": [{"task": "Setup authentication", "status": "In Progress"}],
}
with _FakeBranches(["setup-authentication"]):
    proposals_ip = reconcile_repo(record_in_progress)
check("Tier-2 does NOT advance In Progress task", proposals_ip == [])

# Task already Done — Tier-2 should NOT advance
record_done = {
    "name": "some-repo",
    "local_path": "/fake/some-repo",
    "branch": "main",
    "kanban_exists": True,
    "valid_task_count": 1,
    "tasks": [{"task": "Setup authentication", "status": "Done"}],
}
with _FakeBranches(["setup-authentication"]):
    proposals_done = reconcile_repo(record_done)
check("Tier-2 does NOT advance Done task", proposals_done == [])

# ---------------------------------------------------------------------------
# render_change_list: empty case
# ---------------------------------------------------------------------------

print("--- render_change_list ---")
old_stdout = sys.stdout
sys.stdout = io.StringIO()
render_change_list([])
output = sys.stdout.getvalue()
sys.stdout = old_stdout
check(
    "render_change_list([]) prints exactly the [INFO] line",
    "[INFO] No changes proposed — all declared statuses match activity." in output,
)
lines = [l for l in output.splitlines() if l.strip()]
check(
    "render_change_list([]) prints exactly one non-empty line",
    len(lines) == 1,
)

# render_change_list with one proposal
old_stdout = sys.stdout
sys.stdout = io.StringIO()
render_change_list([Proposal(
    repo="test-repo",
    task="Setup authentication",
    old_status="Todo",
    new_status="In Progress",
    tier=2,
    signal="branch origin/setup-authentication exists",
)])
output_with_p = sys.stdout.getvalue()
sys.stdout = old_stdout
check("render_change_list with proposals prints repo name", "test-repo" in output_with_p)
check("render_change_list with proposals prints task name", "Setup authentication" in output_with_p)
check("render_change_list uses [TIER-2] pill", "[TIER-2]" in output_with_p)

# ---------------------------------------------------------------------------
# _extract_issue_refs assertions
# ---------------------------------------------------------------------------

print("--- _extract_issue_refs ---")
check(
    "_extract_issue_refs(None) returns empty list",
    _extract_issue_refs(None) == [],
)
check(
    "_extract_issue_refs('') returns empty list",
    _extract_issue_refs("") == [],
)
check(
    "_extract_issue_refs('closes #12') returns [12]",
    _extract_issue_refs("closes #12") == [12],
)
check(
    "_extract_issue_refs('Closes #12') case-insensitive",
    _extract_issue_refs("Closes #12") == [12],
)
check(
    "_extract_issue_refs('closes #12 and fixes: #34') returns [12, 34]",
    _extract_issue_refs("closes #12 and fixes: #34") == [12, 34],
)
check(
    "_extract_issue_refs('fixed #5') returns [5]",
    _extract_issue_refs("fixed #5") == [5],
)
check(
    "_extract_issue_refs('resolves #99') returns [99]",
    _extract_issue_refs("resolves #99") == [99],
)
check(
    "_extract_issue_refs('see owner/repo#9') returns [] (cross-repo ignored)",
    _extract_issue_refs("see owner/repo#9") == [],
)
check(
    "_extract_issue_refs('no issue references here') returns []",
    _extract_issue_refs("no issue references here") == [],
)
check(
    "_extract_issue_refs with multiple refs extracts all",
    set(_extract_issue_refs("closes #1 fixes #2 resolved #3")) == {1, 2, 3},
)

# ---------------------------------------------------------------------------
# _build_headers assertions
# ---------------------------------------------------------------------------

print("--- _build_headers ---")


class _EnvPatch:
    """Context manager to patch os.environ for tests."""
    def __init__(self, overrides: dict):
        self.overrides = overrides
        self._orig = {}

    def __enter__(self):
        for k, v in self.overrides.items():
            self._orig[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *args):
        for k, orig in self._orig.items():
            if orig is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = orig


with _EnvPatch({"KF_PAT": None, "GITHUB_TOKEN": None}):
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    headers_no_token = _build_headers()
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout

check(
    "_build_headers() without token includes Accept header",
    headers_no_token.get("Accept") == "application/vnd.github+json",
)
check(
    "_build_headers() without token has no Authorization header",
    "Authorization" not in headers_no_token,
)
check(
    "_build_headers() without token prints Warning",
    "Warning" in out,
)

with _EnvPatch({"KF_PAT": "test_token_value", "GITHUB_TOKEN": None}):
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    headers_with_token = _build_headers()
    out_with_token = sys.stdout.getvalue()
    sys.stdout = old_stdout

check(
    "_build_headers() with KF_PAT includes Authorization header",
    "Authorization" in headers_with_token,
)
check(
    "_build_headers() with KF_PAT uses Bearer scheme",
    headers_with_token.get("Authorization", "").startswith("Bearer "),
)
check(
    "_build_headers() with KF_PAT does not print Warning",
    "Warning" not in out_with_token,
)
check(
    "_build_headers() token value is in Authorization (functional check)",
    "test_token_value" in headers_with_token.get("Authorization", ""),
)
# Security: token value must not appear in any print output
check(
    "_build_headers() token value is never printed",
    "test_token_value" not in out_with_token,
)

# GITHUB_TOKEN fallback
with _EnvPatch({"KF_PAT": None, "GITHUB_TOKEN": "gh_fallback_token"}):
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    headers_gh = _build_headers()
    sys.stdout = old_stdout

check(
    "_build_headers() GITHUB_TOKEN fallback adds Authorization",
    "Authorization" in headers_gh,
)
check(
    "_build_headers() GITHUB_TOKEN fallback value present",
    "gh_fallback_token" in headers_gh.get("Authorization", ""),
)

# ---------------------------------------------------------------------------
# _is_merge_reachable assertions (stub _run_git)
# ---------------------------------------------------------------------------

print("--- _is_merge_reachable ---")


class _FakeRunGit:
    """Context manager to monkeypatch reconcile._run_git."""
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self._orig = None

    def __enter__(self):
        self._orig = reconcile._run_git
        rc = self.returncode
        so = self.stdout
        se = self.stderr

        def _fake(args, cwd=None, timeout=60):
            import subprocess as _sp
            return _sp.CompletedProcess(args, rc, so, se)

        reconcile._run_git = _fake
        return self

    def __exit__(self, *args):
        reconcile._run_git = self._orig


with _FakeRunGit(returncode=0):
    result_reachable = _is_merge_reachable("/fake/repo", "abc123", "main")
check(
    "_is_merge_reachable returns True when git exit 0",
    result_reachable is True,
)

with _FakeRunGit(returncode=1):
    result_not_reachable = _is_merge_reachable("/fake/repo", "abc123", "main")
check(
    "_is_merge_reachable returns False when git exit 1",
    result_not_reachable is False,
)

with _FakeRunGit(returncode=128, stderr="unknown revision"):
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    result_error = _is_merge_reachable("/fake/repo", "badsha", "main")
    out_error = sys.stdout.getvalue()
    sys.stdout = old_stdout
check(
    "_is_merge_reachable returns None when git exit 128",
    result_error is None,
)
check(
    "_is_merge_reachable prints Warning on git error",
    "Warning" in out_error or "warning" in out_error.lower(),
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(f"\n--- Results: {PASS} passed, {FAIL} failed ---")
if FAIL > 0:
    sys.exit(1)
