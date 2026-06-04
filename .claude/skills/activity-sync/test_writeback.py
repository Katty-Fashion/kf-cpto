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

_REPO_ROOT_DIR = _SKILL_DIR.parent.parent.parent.parent
_KANBAN_TEMPLATE = _REPO_ROOT_DIR / "templates" / "kanban.md"
_KANBAN_ORIG = _KANBAN_TEMPLATE.read_text(encoding="utf-8")

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

# Round-trip: reconstruct must be byte-identical to original (WB-01)
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
# Summary
# ---------------------------------------------------------------------------

print(f"\n--- Results: {PASS} passed, {FAIL} failed ---")
if FAIL > 0:
    sys.exit(1)
