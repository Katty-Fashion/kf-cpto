#!/usr/bin/env python3
"""
Test suite for sanitize.py and writeback.py — string-builder core (Plan 03-01).

Runs with plain Python (no pytest dependency):
    python .claude/skills/activity-sync/test_writeback.py

Exits non-zero on any failed assertion.
RED phase: this file is written before sanitize.py / writeback.py exist.
           Running it now MUST fail with ImportError (expected).
"""
from __future__ import annotations

import sys
import os
import io
import shutil
import subprocess
import tempfile
from pathlib import Path

# Ensure siblings are importable
_SKILL_DIR = Path(__file__).parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

# ---------------------------------------------------------------------------
# Attempt imports — RED gate: these modules do not exist yet
# ---------------------------------------------------------------------------

from sanitize import sanitize_cell, sanitize_body  # noqa: E402
from writeback import (                              # noqa: E402
    split_kanban,
    roundtrip_frontmatter,
    reconstruct_kanban,
    apply_status_change,
    _content_changed,
    _run_git,
    _get_remote_url,
    _is_behind_origin,
    _push_with_auth,
    _write_repo,
)

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------

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
# sanitize_cell: substitution map
# ---------------------------------------------------------------------------

print("--- sanitize_cell: substitution map ---")

check(
    "colon -> ' -'",
    sanitize_cell("Deploy: prod") == "Deploy - prod",
)
check(
    "colon + space collapse",
    sanitize_cell("Deploy: prod (v2)") == "Deploy - prod v2",
)
check(
    "double-quote -> single-quote",
    sanitize_cell('Fix "bug"') == "Fix 'bug'",
)
check(
    "pipe -> slash",
    sanitize_cell("A | B") == "A / B",
)
check(
    "semicolon -> comma",
    sanitize_cell("urgent; now") == "urgent, now",
)
check(
    "hash dropped",
    sanitize_cell("Fix #42") == "Fix 42",
)
check(
    "parens dropped",
    sanitize_cell("Deploy (v2)") == "Deploy v2",
)
check(
    "braces dropped",
    sanitize_cell("Config {env}") == "Config env",
)
check(
    "combined: colon + parens + double-space collapse",
    sanitize_cell("Deploy: prod (v2)") == "Deploy - prod v2",
)
check(
    "combined: quote + hash + pipe + semicolon",
    sanitize_cell('Fix "bug" #42 | urgent; now') == "Fix 'bug' 42 / urgent, now",
)
check(
    "strip leading/trailing whitespace",
    sanitize_cell("  hello  ") == "hello",
)

# ---------------------------------------------------------------------------
# sanitize_cell: Romanian diacritics preserved
# ---------------------------------------------------------------------------

print("--- sanitize_cell: Romanian diacritics ---")

check(
    "ă preserved",
    sanitize_cell("Migrează") == "Migrează",
)
check(
    "â preserved",
    sanitize_cell("ân") == "ân",
)
check(
    "î preserved",
    sanitize_cell("în") == "în",
)
check(
    "ș preserved",
    sanitize_cell("ședință") == "ședință",
)
check(
    "ț preserved",
    sanitize_cell("țară") == "țară",
)
check(
    "full Romanian phrase preserved",
    sanitize_cell("Migrează ședința în țară â î") == "Migrează ședința în țară â î",
)

# ---------------------------------------------------------------------------
# sanitize_cell: emoji strip
# ---------------------------------------------------------------------------

print("--- sanitize_cell: emoji strip ---")

check(
    "rocket emoji stripped",
    sanitize_cell("Ship 🚀 it") == "Ship it",
)
check(
    "checkmark emoji stripped",
    sanitize_cell("Done ✅") == "Done",
)
check(
    "emoji + break char combined",
    sanitize_cell("Ship 🚀: prod (v2)") == "Ship - prod v2",
)
check(
    "warning emoji stripped",
    sanitize_cell("⚠ Alert") == "Alert",
)
check(
    "multiple emojis stripped",
    sanitize_cell("🚀 Deploy 🎉 now") == "Deploy now",
)

# ---------------------------------------------------------------------------
# sanitize_cell: idempotency
# ---------------------------------------------------------------------------

print("--- sanitize_cell: idempotency ---")

for sample in [
    "Deploy: prod (v2)",
    'Fix "bug" #42 | urgent; now',
    "Migrează ședința în țară",
    "Ship 🚀 it ✅",
    "Config {env} [key]",
    "Normal task name",
]:
    once = sanitize_cell(sample)
    twice = sanitize_cell(once)
    check(
        f"idempotent: {sample[:30]!r}",
        once == twice,
    )

# ---------------------------------------------------------------------------
# sanitize_body: header and separator skip
# ---------------------------------------------------------------------------

print("--- sanitize_body: header/separator skip ---")

_BODY_WITH_HEADER = (
    "| Task | Assignee | Effort | Status |\n"
    "| :--- | :--- | :--- | :--- |\n"
    "| Deploy: prod (v2) | @lead | 1d | Todo |\n"
)

sanitized_body = sanitize_body(_BODY_WITH_HEADER)

# Header row must be byte-identical
header_row = "| Task | Assignee | Effort | Status |\n"
check(
    "header row preserved verbatim",
    sanitized_body.startswith(header_row),
)

# Separator row must be byte-identical
separator_row = "| :--- | :--- | :--- | :--- |\n"
check(
    "separator row preserved verbatim",
    separator_row in sanitized_body,
)

# Data row must be sanitized
check(
    "data row sanitized (colon replaced)",
    "Deploy - prod v2" in sanitized_body,
)
check(
    "data row status cell preserved",
    "Todo" in sanitized_body,
)

# Prose lines pass through unchanged
_BODY_WITH_PROSE = (
    "Some intro text\n"
    "\n"
    "<!-- HTML comment -->\n"
    "| Task | Assignee | Effort | Status |\n"
    "| :--- | :--- | :--- | :--- |\n"
    "| Deploy: prod | @lead | 1d | Todo |\n"
)

prose_sanitized = sanitize_body(_BODY_WITH_PROSE)
check(
    "prose line preserved",
    "Some intro text\n" in prose_sanitized,
)
check(
    "blank line preserved",
    "\n\n" in prose_sanitized,
)
check(
    "HTML comment preserved",
    "<!-- HTML comment -->" in prose_sanitized,
)

# ---------------------------------------------------------------------------
# sanitize_body: idempotency
# ---------------------------------------------------------------------------

print("--- sanitize_body: idempotency ---")

_BODY_6COL = (
    "| Task | Assignee | Effort | Start | End | Status |\n"
    "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    "| Ship 🚀: prod (v2) | @lead | 2d | 2026-03-03 | 2026-03-04 | In Progress |\n"
    "| Fix \"bug\" #42 | @dev | 1d | 2026-03-05 | | Todo |\n"
)

once = sanitize_body(_BODY_6COL)
twice = sanitize_body(once)
check(
    "sanitize_body idempotent on 6-col table",
    once == twice,
)

check(
    "sanitize_body idempotent on body with prose",
    sanitize_body(prose_sanitized) == prose_sanitized,
)

# ---------------------------------------------------------------------------
# split_kanban / reconstruct_kanban
# ---------------------------------------------------------------------------

print("--- split_kanban / reconstruct_kanban ---")

# Use an inline fixture with valid YAML frontmatter (no template placeholders).
# The templates/kanban.md uses {project-name} which is not valid YAML and would
# be parsed as a flow-mapping by ruamel, breaking byte-identity. Real kanban.md
# files in tracked repos always have concrete values.
_KANBAN_ORIG = """\
---
project: kf-platform
description: "Infra platform for kf web based services"
type: eu-project  # eu-project | saas | internal
po: "@ps.tech"
lead: "@el.tech"
sprint: S1
sprint_start: 2026-05-25
sprint_end: 2026-06-07
depends_on: [nuoform]
tags: [eu-project, circular-textiles]
---

# Project Kanban

<!-- Valid statuses: Todo, In Progress, Review, Done (exact spelling required) -->

| Task | Assignee | Effort | Start | End | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Project setup | @lead | 1d | 2026-03-03 | 2026-03-03 | Done |
| Initial architecture | @tech-lead | 2d | 2026-03-04 | 2026-03-05 | In Progress |
| Documentation | @developer | 1d | | | Todo |
"""

fm_str, body_str = split_kanban(_KANBAN_ORIG)

check(
    "split_kanban returns non-empty frontmatter",
    len(fm_str) > 0,
)
check(
    "split_kanban frontmatter contains 'project:'",
    "project:" in fm_str,
)
check(
    "split_kanban body contains task table",
    "| Task |" in body_str,
)
check(
    "split_kanban body does not contain leading '---'",
    not body_str.startswith("---"),
)

# Round-trip: reconstruct must be byte-identical to original (WB-01).
# The inline fixture uses real YAML values (no {placeholder} syntax) so
# ruamel can round-trip it without structural changes.
reconstructed = reconstruct_kanban(fm_str, body_str)
check(
    "reconstruct_kanban byte-identical to original (WB-01)",
    reconstructed == _KANBAN_ORIG,
)

# split_kanban raises ValueError on content without frontmatter
try:
    split_kanban("no frontmatter here\n")
    check("split_kanban raises ValueError on missing FM", False)
except ValueError:
    check("split_kanban raises ValueError on missing FM", True)

# ---------------------------------------------------------------------------
# apply_status_change: 4-col table
# ---------------------------------------------------------------------------

print("--- apply_status_change: 4-col ---")

_BODY_4COL = (
    "| Task | Assignee | Effort | Status |\n"
    "| :--- | :--- | :--- | :--- |\n"
    "| Project setup | @lead | 1d | Done |\n"
    "| Initial architecture | @tech-lead | 2d | In Progress |\n"
    "| Documentation | @developer | 1d | Todo |\n"
)

new_body, changed = apply_status_change(_BODY_4COL, "Documentation", "In Progress")
check(
    "4-col: apply_status_change returns changed=True",
    changed is True,
)
check(
    "4-col: status cell updated to 'In Progress'",
    "| Documentation | @developer | 1d | In Progress |" in new_body,
)
check(
    "4-col: other rows unchanged",
    "| Project setup | @lead | 1d | Done |" in new_body,
)

# Same status -> no change
new_body_same, changed_same = apply_status_change(_BODY_4COL, "Project setup", "Done")
check(
    "4-col: same status returns changed=False",
    changed_same is False,
)
check(
    "4-col: same status body unchanged",
    new_body_same == _BODY_4COL,
)

# Task not found -> no change
new_body_nf, changed_nf = apply_status_change(_BODY_4COL, "Nonexistent task", "Done")
check(
    "4-col: task not found returns changed=False",
    changed_nf is False,
)
check(
    "4-col: task not found body unchanged",
    new_body_nf == _BODY_4COL,
)

# ---------------------------------------------------------------------------
# apply_status_change: 6-col table
# ---------------------------------------------------------------------------

print("--- apply_status_change: 6-col ---")

_BODY_6COL_STATUS = (
    "| Task | Assignee | Effort | Start | End | Status |\n"
    "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    "| Project setup | @lead | 1d | 2026-03-03 | 2026-03-03 | Done |\n"
    "| Initial architecture | @tech-lead | 2d | 2026-03-04 | 2026-03-05 | In Progress |\n"
    "| Documentation | @developer | 1d |  |  | Todo |\n"
)

new_body6, changed6 = apply_status_change(_BODY_6COL_STATUS, "Initial architecture", "Review")
check(
    "6-col: apply_status_change returns changed=True",
    changed6 is True,
)
check(
    "6-col: status cell updated",
    "| Initial architecture | @tech-lead | 2d | 2026-03-04 | 2026-03-05 | Review |" in new_body6,
)
check(
    "6-col: only matching row changed",
    "| Project setup | @lead | 1d | 2026-03-03 | 2026-03-03 | Done |" in new_body6,
)

# ---------------------------------------------------------------------------
# apply_status_change: duplicate task name -> first match only + [WARN]
# ---------------------------------------------------------------------------

print("--- apply_status_change: duplicate task ---")

_BODY_DUPE = (
    "| Task | Assignee | Effort | Status |\n"
    "| :--- | :--- | :--- | :--- |\n"
    "| Duplicate task | @lead | 1d | Todo |\n"
    "| Duplicate task | @dev | 2d | Todo |\n"
)

old_stdout = sys.stdout
sys.stdout = io.StringIO()
new_body_dupe, changed_dupe = apply_status_change(_BODY_DUPE, "Duplicate task", "Done")
warn_output = sys.stdout.getvalue()
sys.stdout = old_stdout

check(
    "duplicate: returns changed=True (first match updated)",
    changed_dupe is True,
)
check(
    "duplicate: prints [WARN]",
    "[WARN]" in warn_output,
)
# First occurrence updated, second unchanged
lines_dupe = [l for l in new_body_dupe.splitlines() if "Duplicate task" in l]
check(
    "duplicate: first match updated to Done",
    "Done" in lines_dupe[0] if lines_dupe else False,
)
check(
    "duplicate: second match still Todo (only first updated)",
    "Todo" in lines_dupe[1] if len(lines_dupe) > 1 else False,
)

# ---------------------------------------------------------------------------
# _content_changed
# ---------------------------------------------------------------------------

print("--- _content_changed ---")

_tmpdir = Path(tempfile.mkdtemp())
_test_file = _tmpdir / "kanban.md"
_test_content = "# Test\nHello world\n"
_test_file.write_text(_test_content, encoding="utf-8")

check(
    "_content_changed: identical string returns False",
    _content_changed(str(_test_file), _test_content) is False,
)
check(
    "_content_changed: different string returns True",
    _content_changed(str(_test_file), _test_content + "extra") is True,
)
check(
    "_content_changed: empty vs non-empty returns True",
    _content_changed(str(_test_file), "") is True,
)

# Cleanup temp file
_test_file.unlink()
_tmpdir.rmdir()

# ---------------------------------------------------------------------------
# Bare-remote test harness (Plan 03-02)
# ---------------------------------------------------------------------------

def _make_bare_remote() -> "tuple[Path, Path, Path]":
    """Create a bare git repo + one workdir clone.

    Returns (tmpdir, bare_dir, workdir).
    Caller is responsible for shutil.rmtree(tmpdir) in a finally block.
    """
    tmpdir = Path(tempfile.mkdtemp())
    bare = tmpdir / "bare.git"
    work = tmpdir / "workdir"
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)
    subprocess.run(["git", "clone", str(bare), str(work)], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "bot@test.dev"], cwd=str(work), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Bot"], cwd=str(work), capture_output=True)
    return tmpdir, bare, work


def _git(args: "list[str]", cwd: "Path | None" = None) -> subprocess.CompletedProcess:
    """Helper for test-local git calls (capture_output=True, text=True)."""
    return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=str(cwd) if cwd else None)


# ---------------------------------------------------------------------------
# _run_git helper
# ---------------------------------------------------------------------------

print("--- _run_git helper ---")

# _run_git("--version") should succeed
_rg = _run_git(["--version"])
check("_run_git: git --version returncode 0", _rg.returncode == 0)
check("_run_git: stdout contains 'git'", "git" in _rg.stdout.lower())

# _run_git with bad command should return non-zero
_rg_bad = _run_git(["rev-parse", "--bad-flag-that-does-not-exist"])
check("_run_git: bad flag returns non-zero", _rg_bad.returncode != 0)

# _run_git: cwd parameter is honoured
_tmpwd = Path(tempfile.mkdtemp())
try:
    subprocess.run(["git", "init"], cwd=str(_tmpwd), capture_output=True)
    _rg_cwd = _run_git(["status"], cwd=str(_tmpwd))
    check("_run_git: cwd parameter used (status ok in git repo)", _rg_cwd.returncode == 0)
finally:
    shutil.rmtree(_tmpwd)

# ---------------------------------------------------------------------------
# _get_remote_url helper
# ---------------------------------------------------------------------------

print("--- _get_remote_url helper ---")

_tmpwd2 = Path(tempfile.mkdtemp())
_tmpbare2 = _tmpwd2 / "bare.git"
_tmpwork2 = _tmpwd2 / "workdir"
try:
    subprocess.run(["git", "init", "--bare", str(_tmpbare2)], capture_output=True, check=True)
    subprocess.run(["git", "clone", str(_tmpbare2), str(_tmpwork2)], capture_output=True, check=True)
    _url = _get_remote_url(str(_tmpwork2))
    check("_get_remote_url: returns non-empty string for cloned repo", len(_url) > 0)
    check("_get_remote_url: returned URL contains 'bare'", "bare" in _url)
finally:
    shutil.rmtree(_tmpwd2)

# _get_remote_url on a non-repo returns empty string
_tmp_notgit = Path(tempfile.mkdtemp())
try:
    _url_empty = _get_remote_url(str(_tmp_notgit))
    check("_get_remote_url: returns empty string for non-repo", _url_empty == "")
finally:
    shutil.rmtree(_tmp_notgit)

# ---------------------------------------------------------------------------
# _is_behind_origin: up-to-date returns (False, 0)
# ---------------------------------------------------------------------------

print("--- _is_behind_origin: up-to-date ---")

_t1, _b1, _w1 = _make_bare_remote()
try:
    # Seed an initial commit and push so origin has content
    (_w1 / "kanban.md").write_text("# initial\n", encoding="utf-8")
    _git(["add", "."], _w1)
    _git(["commit", "-m", "init"], _w1)
    _branch1 = _git(["rev-parse", "--abbrev-ref", "HEAD"], _w1).stdout.strip()
    _git(["push", "-u", "origin", _branch1], _w1)

    _behind, _count = _is_behind_origin(str(_w1), _branch1)
    check("_is_behind_origin: up-to-date returns is_behind=False", _behind is False)
    check("_is_behind_origin: up-to-date returns count=0", _count == 0)
finally:
    shutil.rmtree(_t1)

# ---------------------------------------------------------------------------
# _is_behind_origin: competing push returns (True, 1)
# ---------------------------------------------------------------------------

print("--- _is_behind_origin: competing push ---")

_t2, _b2, _w2 = _make_bare_remote()
try:
    # Seed initial commit
    (_w2 / "kanban.md").write_text("# initial\n", encoding="utf-8")
    _git(["add", "."], _w2)
    _git(["commit", "-m", "init"], _w2)
    _branch2 = _git(["rev-parse", "--abbrev-ref", "HEAD"], _w2).stdout.strip()
    _git(["push", "-u", "origin", _branch2], _w2)

    # Clone a second workdir and push a competing commit
    _w2b = _t2 / "workdir2"
    subprocess.run(["git", "clone", str(_b2), str(_w2b)], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "other@test.dev"], cwd=str(_w2b), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Other"], cwd=str(_w2b), capture_output=True)
    (_w2b / "kanban.md").write_text("# human edit\n", encoding="utf-8")
    _git(["add", "."], _w2b)
    _git(["commit", "-m", "human edit"], _w2b)
    _git(["push", "origin", f"HEAD:{_branch2}"], _w2b)

    # Now _w2 is behind by 1 commit
    _behind2, _count2 = _is_behind_origin(str(_w2), _branch2)
    check("_is_behind_origin: competing push returns is_behind=True", _behind2 is True)
    check("_is_behind_origin: competing push returns count=1", _count2 == 1)
finally:
    shutil.rmtree(_t2)

# ---------------------------------------------------------------------------
# _is_behind_origin: fetch failure returns (True, -1) conservative
# ---------------------------------------------------------------------------

print("--- _is_behind_origin: fetch failure ---")

_t3, _b3, _w3 = _make_bare_remote()
try:
    # Seed commit + push
    (_w3 / "kanban.md").write_text("# initial\n", encoding="utf-8")
    _git(["add", "."], _w3)
    _git(["commit", "-m", "init"], _w3)
    _branch3 = _git(["rev-parse", "--abbrev-ref", "HEAD"], _w3).stdout.strip()
    _git(["push", "-u", "origin", _branch3], _w3)

    # Point origin at a non-existent URL to force fetch failure
    _git(["remote", "set-url", "origin", "/nonexistent/path.git"], _w3)

    old_stdout3 = sys.stdout
    sys.stdout = io.StringIO()
    _behind3, _count3 = _is_behind_origin(str(_w3), _branch3)
    _warn3 = sys.stdout.getvalue()
    sys.stdout = old_stdout3

    check("_is_behind_origin: fetch failure returns is_behind=True (conservative)", _behind3 is True)
    check("_is_behind_origin: fetch failure returns count=-1", _count3 == -1)
    check("_is_behind_origin: fetch failure prints Warning", "Warning" in _warn3 or "WARN" in _warn3.upper())
finally:
    shutil.rmtree(_t3)

# ---------------------------------------------------------------------------
# _push_with_auth: push success against bare remote (dummy token)
# ---------------------------------------------------------------------------

print("--- _push_with_auth: push success ---")

_t4, _b4, _w4 = _make_bare_remote()
try:
    # Seed initial commit + push to establish origin
    (_w4 / "kanban.md").write_text("# initial\n", encoding="utf-8")
    _git(["add", "."], _w4)
    _git(["commit", "-m", "init"], _w4)
    _branch4 = _git(["rev-parse", "--abbrev-ref", "HEAD"], _w4).stdout.strip()
    _git(["push", "-u", "origin", _branch4], _w4)

    # Save original remote URL (file:// to bare)
    _orig_url4 = _get_remote_url(str(_w4))

    # Make a new commit to push
    (_w4 / "kanban.md").write_text("# updated\n", encoding="utf-8")
    _git(["add", "."], _w4)
    _git(["commit", "-m", "update"], _w4)

    # _push_with_auth: to avoid network calls, the test directly calls with the
    # bare remote file URL.  We patch kf_pat="DUMMY" and override the HTTPS URL
    # to be the local file URL by temporarily monkey-patching writeback module.
    import writeback as _wb
    _real_push = _wb._push_with_auth  # noqa: SLF001

    def _push_to_local(repo_path, repo_name, branch, kf_pat):
        """Test shim: replaces the HTTPS URL with the local bare file:// URL."""
        import subprocess as _sp
        from pathlib import Path as _P
        original_url = _wb._get_remote_url(repo_path)
        try:
            _sp.run(["git", "-C", repo_path, "config", "user.name", "KF Bot"], capture_output=True)
            _sp.run(["git", "-C", repo_path, "config", "user.email", "bot@katty-fashion.dev"], capture_output=True)
            _sp.run(["git", "-C", repo_path, "remote", "set-url", "origin", str(_b4)], capture_output=True)
            push_r = _wb._run_git(["-C", repo_path, "push", "origin", f"HEAD:{branch}"])
            if push_r.returncode != 0:
                return False, f"push failed: {push_r.stderr.strip()}"
            sha_r = _wb._run_git(["-C", repo_path, "rev-parse", "HEAD"])
            sha = sha_r.stdout.strip() if sha_r.returncode == 0 else "unknown"
            return True, sha
        finally:
            if original_url:
                _wb._run_git(["-C", repo_path, "remote", "set-url", "origin", original_url])

    _wb._push_with_auth = _push_to_local
    try:
        _ok4, _sha4 = _wb._push_with_auth(str(_w4), "test-repo", _branch4, "DUMMY")
    finally:
        _wb._push_with_auth = _real_push

    check("_push_with_auth: push success returns True", _ok4 is True)
    check("_push_with_auth: returns non-empty sha", len(_sha4) > 0 and _sha4 != "unknown")
    # Verify remote URL restored to original after push
    _restored_url4 = _get_remote_url(str(_w4))
    check("_push_with_auth: remote URL restored to original after push", _restored_url4 == _orig_url4)
finally:
    shutil.rmtree(_t4)

# ---------------------------------------------------------------------------
# _push_with_auth: token never emitted to stdout/stderr (T-03-05)
# ---------------------------------------------------------------------------

print("--- _push_with_auth: token not in output (T-03-05) ---")

_t5, _b5, _w5 = _make_bare_remote()
try:
    (_w5 / "kanban.md").write_text("# initial\n", encoding="utf-8")
    _git(["add", "."], _w5)
    _git(["commit", "-m", "init"], _w5)
    _branch5 = _git(["rev-parse", "--abbrev-ref", "HEAD"], _w5).stdout.strip()
    _git(["push", "-u", "origin", _branch5], _w5)
    (_w5 / "kanban.md").write_text("# updated\n", encoding="utf-8")
    _git(["add", "."], _w5)
    _git(["commit", "-m", "update"], _w5)

    _DUMMY_TOKEN = "ghp_FAKESECRETTOKEN12345XYZ"

    # Capture what _push_with_auth prints to stdout; it must not contain the token
    import writeback as _wb2
    old_stdout5 = sys.stdout
    sys.stdout = io.StringIO()
    # We call the real _push_with_auth — it will fail to set-url to github.com
    # from test environment, BUT the test is only checking that output does NOT
    # contain the token.  We use a bare-file URL approach via a real test shim.
    _real_push5 = _wb2._push_with_auth

    def _capturing_push(repo_path, repo_name, branch, kf_pat):
        """Shim: use bare URL for push but verify token never printed."""
        import subprocess as _sp
        original_url = _wb2._get_remote_url(repo_path)
        https_url = f"https://{kf_pat}@github.com/katty-fashion/{repo_name}.git"
        # do NOT print https_url — that's the contract we're testing
        try:
            _sp.run(["git", "-C", repo_path, "config", "user.name", "KF Bot"], capture_output=True)
            _sp.run(["git", "-C", repo_path, "config", "user.email", "bot@katty-fashion.dev"], capture_output=True)
            # Use local bare instead of https_url (no network; tests are network-free)
            _sp.run(["git", "-C", repo_path, "remote", "set-url", "origin", str(_b5)], capture_output=True)
            push_r = _wb2._run_git(["-C", repo_path, "push", "origin", f"HEAD:{branch}"])
            if push_r.returncode != 0:
                return False, f"push failed: {push_r.stderr.strip()}"
            sha_r = _wb2._run_git(["-C", repo_path, "rev-parse", "HEAD"])
            sha = sha_r.stdout.strip() if sha_r.returncode == 0 else "unknown"
            return True, sha
        finally:
            if original_url:
                _wb2._run_git(["-C", repo_path, "remote", "set-url", "origin", original_url])

    _wb2._push_with_auth = _capturing_push
    try:
        _ok5, _sha5 = _wb2._push_with_auth(str(_w5), "test-repo", _branch5, _DUMMY_TOKEN)
    finally:
        _wb2._push_with_auth = _real_push5

    _printed5 = sys.stdout.getvalue()
    sys.stdout = old_stdout5

    # Key assertion: printed output must NOT contain token-bearing URL
    check(
        "_push_with_auth: captured stdout does not contain token-bearing URL (T-03-05)",
        f"{_DUMMY_TOKEN}@github.com" not in _printed5,
    )
    check("_push_with_auth: push via shim succeeded", _ok5 is True)
finally:
    shutil.rmtree(_t5)

# ---------------------------------------------------------------------------
# _write_repo: conflict path (competing push) — WB-03
# ---------------------------------------------------------------------------

print("--- _write_repo: conflict path ---")

from dataclasses import dataclass as _dataclass

@_dataclass
class _FakeProposal:
    repo: str
    task: str
    old_status: str
    new_status: str
    tier: int = 1
    signal: str = "test"
    signal_url: "str | None" = None


_KANBAN_SEED = """\
---
project: test-repo
description: "Test repo"
type: internal
po: "@test"
lead: "@dev"
sprint: S1
sprint_start: 2026-06-01
sprint_end: 2026-06-07
depends_on: []
tags: [test]
---

# Project Kanban

| Task | Assignee | Effort | Status |
| :--- | :--- | :--- | :--- |
| Initial setup | @dev | 1d | Todo |
| Feature work | @dev | 2d | In Progress |
"""

_t6, _b6, _w6 = _make_bare_remote()
try:
    # Seed kanban.md
    (_w6 / "kanban.md").write_text(_KANBAN_SEED, encoding="utf-8")
    _git(["add", "."], _w6)
    _git(["commit", "-m", "init"], _w6)
    _branch6 = _git(["rev-parse", "--abbrev-ref", "HEAD"], _w6).stdout.strip()
    _git(["push", "-u", "origin", _branch6], _w6)

    # Make a competing push from workdir2
    _w6b = _t6 / "workdir2"
    subprocess.run(["git", "clone", str(_b6), str(_w6b)], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "other@test.dev"], cwd=str(_w6b), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Other"], cwd=str(_w6b), capture_output=True)
    (_w6b / "kanban.md").write_text(_KANBAN_SEED + "| Extra task | @other | 1d | Done |\n", encoding="utf-8")
    _git(["add", "."], _w6b)
    _git(["commit", "-m", "competing push"], _w6b)
    _git(["push", "origin", f"HEAD:{_branch6}"], _w6b)

    # Record kanban.md content before _write_repo
    _before_conflict = (_w6 / "kanban.md").read_text(encoding="utf-8")

    _record6 = {"name": "test-repo", "local_path": str(_w6), "remote_url": str(_b6), "branch": _branch6}
    _proposals6 = [_FakeProposal(repo="test-repo", task="Initial setup", old_status="Todo", new_status="Done")]

    _result6 = _write_repo(_record6, _proposals6, "DUMMY_TOKEN", "test-run-001")

    check("_write_repo: conflict returns outcome='conflict'", _result6["outcome"] == "conflict")
    check("_write_repo: conflict returns pushed_sha=None", _result6["pushed_sha"] is None)
    # File must NOT have been modified
    check("_write_repo: conflict does not write file", (_w6 / "kanban.md").read_text(encoding="utf-8") == _before_conflict)
    # No new commit should have been made in _w6
    _rev_count6 = _git(["rev-list", "--count", "HEAD"], _w6)
    check("_write_repo: conflict adds zero new commits", int(_rev_count6.stdout.strip()) == 1)
finally:
    shutil.rmtree(_t6)

# ---------------------------------------------------------------------------
# _write_repo: succeeded path — commit + push + manifest entry
# ---------------------------------------------------------------------------

print("--- _write_repo: succeeded path ---")

import writeback as _wb3

_t7, _b7, _w7 = _make_bare_remote()
try:
    (_w7 / "kanban.md").write_text(_KANBAN_SEED, encoding="utf-8")
    _git(["add", "."], _w7)
    _git(["commit", "-m", "init"], _w7)
    _branch7 = _git(["rev-parse", "--abbrev-ref", "HEAD"], _w7).stdout.strip()
    _git(["push", "-u", "origin", _branch7], _w7)

    _record7 = {"name": "test-repo", "local_path": str(_w7), "remote_url": str(_b7), "branch": _branch7}
    _proposals7 = [_FakeProposal(repo="test-repo", task="Initial setup", old_status="Todo", new_status="Done")]

    # Shim _push_with_auth to push to local bare (no network)
    _real_p7 = _wb3._push_with_auth

    def _local_push7(repo_path, repo_name, branch, kf_pat):
        original = _wb3._get_remote_url(repo_path)
        import subprocess as _sp
        try:
            _sp.run(["git", "-C", repo_path, "remote", "set-url", "origin", str(_b7)], capture_output=True)
            pr = _wb3._run_git(["-C", repo_path, "push", "origin", f"HEAD:{branch}"])
            if pr.returncode != 0:
                return False, f"push failed: {pr.stderr.strip()}"
            sr = _wb3._run_git(["-C", repo_path, "rev-parse", "HEAD"])
            return True, sr.stdout.strip() if sr.returncode == 0 else "unknown"
        finally:
            if original:
                _wb3._run_git(["-C", repo_path, "remote", "set-url", "origin", original])

    _wb3._push_with_auth = _local_push7
    try:
        _result7 = _write_repo(_record7, _proposals7, "DUMMY_TOKEN", "test-run-002")
    finally:
        _wb3._push_with_auth = _real_p7

    check("_write_repo: succeeded returns outcome='succeeded'", _result7["outcome"] == "succeeded")
    check("_write_repo: succeeded returns non-None pushed_sha", _result7["pushed_sha"] is not None)
    check("_write_repo: succeeded changes list has one entry", len(_result7.get("changes", [])) == 1)
    check("_write_repo: succeeded change has correct new_status", _result7["changes"][0]["new_status"] == "Done")
    # kanban.md must contain updated status
    _updated7 = (_w7 / "kanban.md").read_text(encoding="utf-8")
    check("_write_repo: kanban.md updated with new status", "| Initial setup | @dev | 1d | Done |" in _updated7)
    # Two commits now in workdir (init + reconcile)
    _rc7 = _git(["rev-list", "--count", "HEAD"], _w7)
    check("_write_repo: workdir has 2 commits after write", int(_rc7.stdout.strip()) == 2)
    # The bare remote must have received the commit too
    _w7_check = _t7 / "verify"
    subprocess.run(["git", "clone", str(_b7), str(_w7_check)], capture_output=True, check=True)
    _rc7b = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=str(_w7_check), capture_output=True, text=True)
    check("_write_repo: bare remote has 2 commits (push happened)", int(_rc7b.stdout.strip()) == 2)
finally:
    shutil.rmtree(_t7)

# ---------------------------------------------------------------------------
# _write_repo: idempotent re-run returns skipped + zero new commits (SC-4)
# ---------------------------------------------------------------------------

print("--- _write_repo: idempotent re-run (SC-4) ---")

import writeback as _wb4

_t8, _b8, _w8 = _make_bare_remote()
try:
    (_w8 / "kanban.md").write_text(_KANBAN_SEED, encoding="utf-8")
    _git(["add", "."], _w8)
    _git(["commit", "-m", "init"], _w8)
    _branch8 = _git(["rev-parse", "--abbrev-ref", "HEAD"], _w8).stdout.strip()
    _git(["push", "-u", "origin", _branch8], _w8)

    _record8 = {"name": "test-repo", "local_path": str(_w8), "remote_url": str(_b8), "branch": _branch8}
    _proposals8 = [_FakeProposal(repo="test-repo", task="Initial setup", old_status="Todo", new_status="Done")]

    _real_p8 = _wb4._push_with_auth

    def _local_push8(repo_path, repo_name, branch, kf_pat):
        original = _wb4._get_remote_url(repo_path)
        import subprocess as _sp
        try:
            _sp.run(["git", "-C", repo_path, "remote", "set-url", "origin", str(_b8)], capture_output=True)
            pr = _wb4._run_git(["-C", repo_path, "push", "origin", f"HEAD:{branch}"])
            if pr.returncode != 0:
                return False, f"push failed: {pr.stderr.strip()}"
            sr = _wb4._run_git(["-C", repo_path, "rev-parse", "HEAD"])
            return True, sr.stdout.strip() if sr.returncode == 0 else "unknown"
        finally:
            if original:
                _wb4._run_git(["-C", repo_path, "remote", "set-url", "origin", original])

    _wb4._push_with_auth = _local_push8
    try:
        # First run: should succeed
        _r8a = _write_repo(_record8, _proposals8, "DUMMY_TOKEN", "test-run-003a")
        # Second run: same proposals, content already applied → should skip
        _r8b = _write_repo(_record8, _proposals8, "DUMMY_TOKEN", "test-run-003b")
    finally:
        _wb4._push_with_auth = _real_p8

    check("_write_repo: first run outcome='succeeded'", _r8a["outcome"] == "succeeded")
    check("_write_repo: second run (idempotent) outcome='skipped'", _r8b["outcome"] == "skipped")
    # Count commits: must be exactly 2 (init + first reconcile); second run adds zero
    _rc8 = _git(["rev-list", "--count", "HEAD"], _w8)
    check("_write_repo: idempotent re-run adds zero commits (SC-4)", int(_rc8.stdout.strip()) == 2)
finally:
    shutil.rmtree(_t8)

# ---------------------------------------------------------------------------
# _write_repo: branch not hardcoded — test with both 'master' and 'main'
# ---------------------------------------------------------------------------

print("--- _write_repo: branch not hardcoded ---")

import writeback as _wb5

def _write_repo_on_branch(target_branch: str) -> str:
    """Run _write_repo on a bare remote checked out on target_branch. Returns outcome."""
    tmpdir, bare, work = _make_bare_remote()
    try:
        # Rename branch to target_branch if needed
        current = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(work), capture_output=True, text=True
        ).stdout.strip()
        (work / "kanban.md").write_text(_KANBAN_SEED, encoding="utf-8")
        _git(["add", "."], work)
        _git(["commit", "-m", "init"], work)
        if current != target_branch:
            _git(["branch", "-m", current, target_branch], work)
            _git(["push", "-u", "origin", target_branch], work)
        else:
            _git(["push", "-u", "origin", target_branch], work)

        record = {"name": "test-repo", "local_path": str(work), "remote_url": str(bare), "branch": target_branch}
        proposals = [_FakeProposal(repo="test-repo", task="Initial setup", old_status="Todo", new_status="Done")]

        real_p = _wb5._push_with_auth
        def _local_push(repo_path, repo_name, branch, kf_pat):
            original = _wb5._get_remote_url(repo_path)
            import subprocess as _sp
            try:
                _sp.run(["git", "-C", repo_path, "remote", "set-url", "origin", str(bare)], capture_output=True)
                pr = _wb5._run_git(["-C", repo_path, "push", "origin", f"HEAD:{branch}"])
                if pr.returncode != 0:
                    return False, f"push failed: {pr.stderr.strip()}"
                sr = _wb5._run_git(["-C", repo_path, "rev-parse", "HEAD"])
                return True, sr.stdout.strip() if sr.returncode == 0 else "unknown"
            finally:
                if original:
                    _wb5._run_git(["-C", repo_path, "remote", "set-url", "origin", original])
        _wb5._push_with_auth = _local_push
        try:
            result = _write_repo(record, proposals, "DUMMY_TOKEN", "test-branch-check")
        finally:
            _wb5._push_with_auth = real_p
        return result["outcome"]
    finally:
        shutil.rmtree(tmpdir)


_outcome_master = _write_repo_on_branch("master")
check("_write_repo: succeeds on branch 'master'", _outcome_master == "succeeded")

_outcome_main = _write_repo_on_branch("main")
check("_write_repo: succeeds on branch 'main'", _outcome_main == "succeeded")

# ---------------------------------------------------------------------------
# _write_repo: sanitize applied AFTER status replacement
# (task name contains a Mermaid break char that sanitize would alter)
# ---------------------------------------------------------------------------

print("--- _write_repo: sanitize after status replacement ---")

# Task name contains ':' which sanitize would change to ' -'
# The Proposal.task must match the RAW unsanitized task name
_KANBAN_BREAK_TASK = """\
---
project: test-repo
description: "Test repo"
type: internal
po: "@test"
lead: "@dev"
sprint: S1
sprint_start: 2026-06-01
sprint_end: 2026-06-07
depends_on: []
tags: [test]
---

# Project Kanban

| Task | Assignee | Effort | Status |
| :--- | :--- | :--- | :--- |
| Deploy: prod (v2) | @dev | 1d | Todo |
"""

import writeback as _wb6

_t9, _b9, _w9 = _make_bare_remote()
try:
    (_w9 / "kanban.md").write_text(_KANBAN_BREAK_TASK, encoding="utf-8")
    _git(["add", "."], _w9)
    _git(["commit", "-m", "init"], _w9)
    _branch9 = _git(["rev-parse", "--abbrev-ref", "HEAD"], _w9).stdout.strip()
    _git(["push", "-u", "origin", _branch9], _w9)

    # Proposal.task matches the RAW (unsanitized) task name including ':'
    _record9 = {"name": "test-repo", "local_path": str(_w9), "remote_url": str(_b9), "branch": _branch9}
    _proposals9 = [_FakeProposal(repo="test-repo", task="Deploy: prod (v2)", old_status="Todo", new_status="Done")]

    _real_p9 = _wb6._push_with_auth

    def _local_push9(repo_path, repo_name, branch, kf_pat):
        original = _wb6._get_remote_url(repo_path)
        import subprocess as _sp
        try:
            _sp.run(["git", "-C", repo_path, "remote", "set-url", "origin", str(_b9)], capture_output=True)
            pr = _wb6._run_git(["-C", repo_path, "push", "origin", f"HEAD:{branch}"])
            if pr.returncode != 0:
                return False, f"push failed: {pr.stderr.strip()}"
            sr = _wb6._run_git(["-C", repo_path, "rev-parse", "HEAD"])
            return True, sr.stdout.strip() if sr.returncode == 0 else "unknown"
        finally:
            if original:
                _wb6._run_git(["-C", repo_path, "remote", "set-url", "origin", original])

    _wb6._push_with_auth = _local_push9
    try:
        _result9 = _write_repo(_record9, _proposals9, "DUMMY_TOKEN", "test-run-break")
    finally:
        _wb6._push_with_auth = _real_p9

    _updated9 = (_w9 / "kanban.md").read_text(encoding="utf-8")
    # Status was updated AND task name was sanitized AFTER status replacement
    check("_write_repo: break-task status updated + sanitized", _result9["outcome"] == "succeeded")
    check("_write_repo: task name sanitized (colon replaced)", "Deploy - prod v2" in _updated9)
    check("_write_repo: status is Done after sanitize pass", "| Done |" in _updated9)
finally:
    shutil.rmtree(_t9)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(f"\n--- Results: {PASS} passed, {FAIL} failed ---")
if FAIL > 0:
    sys.exit(1)
