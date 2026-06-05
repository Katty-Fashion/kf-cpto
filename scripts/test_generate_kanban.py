#!/usr/bin/env python3
"""
Tests for the header-driven parser + status canonicalization (utils.py) and the
migration-plan kanban generator (generate_kanban.py).

Runs with plain Python (no pytest dependency):
    python scripts/test_generate_kanban.py

Exits non-zero on any failed assert.
"""
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import utils
from utils import canonicalize_status, parse_kanban_tasks, TASK_STATUSES
import generate_kanban as gk

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
# canonicalize_status
# ---------------------------------------------------------------------------
print("canonicalize_status:")
check("lowercase 'in progress' -> 'In Progress'", canonicalize_status("in progress") == "In Progress")
check("'In progress' (typo case) -> 'In Progress'", canonicalize_status("In progress") == "In Progress")
check("'Completed' -> 'Done'", canonicalize_status("Completed") == "Done")
check("'In Review' -> 'Review'", canonicalize_status("In Review") == "Review")
check("'Next' -> 'Todo'", canonicalize_status("Next") == "Todo")
check("'blocat extern' -> 'In Progress'", canonicalize_status("blocat extern") == "In Progress")
check("already-canonical 'Done' -> 'Done'", canonicalize_status("Done") == "Done")
check("unknown -> None", canonicalize_status("Decizie pending") is None)
check("empty -> None", canonicalize_status("") is None)
check("all canonical values round-trip", all(canonicalize_status(s) == s for s in TASK_STATUSES))


# ---------------------------------------------------------------------------
# Header-driven parse_kanban_tasks
# ---------------------------------------------------------------------------
print("parse_kanban_tasks (header-driven):")

SIXCOL = (
    "| Task | Assignee | Effort | Start | End | Status |\n"
    "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    "| Build API | @dev | 3d | 2026-01-01 | 2026-01-03 | In progress |\n"
)
t = parse_kanban_tasks(SIXCOL)
check("6-col: one task parsed", len(t) == 1)
check("6-col: fields mapped", t[0]["task"] == "Build API" and t[0]["assignee"] == "@dev"
      and t[0]["effort"] == "3d" and t[0]["start"] == "2026-01-01" and t[0]["end"] == "2026-01-03")
check("6-col: lowercase status canonicalized", t[0]["status"] == "In Progress")

FOURCOL = (
    "| Task | Assignee | Effort | Status |\n"
    "|:---|:---|:---|:---|\n"
    "| Docs | @dev | 1d | Todo |\n"
)
t = parse_kanban_tasks(FOURCOL)
check("4-col: parsed with empty dates", len(t) == 1 and t[0]["start"] == "" and t[0]["end"] == "")
check("4-col: status Todo", t[0]["status"] == "Todo")

OWNER_DEADLINE = (
    "| Task | Owner | Prioritate | Status | Deadline | Note |\n"
    "|---|---|---|---|---|---|\n"
    "| Ship it | Paul | P1 | 🔄 In Progress | 2026-02-01 | n/a |\n"
)
t = parse_kanban_tasks(OWNER_DEADLINE)
check("Owner -> assignee alias", t[0]["assignee"] == "Paul")
check("Deadline -> end alias", t[0]["end"] == "2026-02-01")
check("emoji-prefixed status healed", t[0]["status"] == "In Progress")
check("unmapped columns (Prioritate/Note) ignored", t[0]["effort"] == "")

NON_TASK_THEN_TASK = (
    "| Pillar | Component | Status |\n"
    "|---|---|---|\n"
    "| WP1 | AAS | 90% |\n"
    "| T2.1 | Nuoform | ✅ Completed |\n"
    "\n"
    "| Task | Owner | Prioritate | Status | Note |\n"
    "|---|---|---|---|---|\n"
    "| Real task | @x | P2 | 📋 Todo | hi |\n"
)
t = parse_kanban_tasks(NON_TASK_THEN_TASK)
check("non-task table (no Task column) skipped entirely", len(t) == 1)
check("real task from second table parsed", t[0]["task"] == "Real task")
check("no '90%' / 'Completed' garbage leaked", all(r["status"] != "90%" for r in t))

MULTI = (
    "| Task | Owner | Prioritate | Status | Note |\n"
    "|---|---|---|---|---|\n"
    "| A | @x | P1 | Done | - |\n"
    "\n"
    "## section\n"
    "\n"
    "| Task | Owner | Prioritate | Status | Note |\n"
    "|---|---|---|---|---|\n"
    "| B | @y | P2 | ⏭ Next | - |\n"
)
t = parse_kanban_tasks(MULTI)
check("multiple task tables both parsed", [x["task"] for x in t] == ["A", "B"])
check("media-emoji status '⏭ Next' -> 'Todo'", t[1]["status"] == "Todo")


# ---------------------------------------------------------------------------
# Generator: classification + partition + status merge
# ---------------------------------------------------------------------------
print("generate_kanban classification/partition:")

check("_email_to_handle local part", gk._email_to_handle("alexandru.bejenari@katty-fashion.ro") == "@alexandru.bejenari")
check("classify FE-only", gk.classify_repo("@alexandru.bejenari", "@alexandru.bejenari", "@ma.tech") == "kf-fe-platform")
check("classify BE-only", gk.classify_repo("@ma.tech", "@alexandru.bejenari", "@ma.tech") == "kf-be-platform")
check("classify FE+BE -> umbrella", gk.classify_repo("@alexandru.bejenari + @ma.tech", "@alexandru.bejenari", "@ma.tech") == "kf-platform")
check("classify unknown -> None", gk.classify_repo("@nobody", "@alexandru.bejenari", "@ma.tech") is None)

PLAN_TASKS = [
    {"task": "A", "assignee": "@fe", "effort": "5d", "start": "", "end": "", "status": "Todo", "repo": "kf-fe-platform"},
    {"task": "B", "assignee": "@be", "effort": "3d", "start": "", "end": "", "status": "Todo", "repo": "kf-be-platform"},
    {"task": "C", "assignee": "@fe + @be", "effort": "2d", "start": "", "end": "", "status": "Todo", "repo": "kf-platform"},
]
buckets = gk.partition(PLAN_TASKS)
check("partition is total (one task per repo)",
      len(buckets["kf-fe-platform"]) == 1 and len(buckets["kf-be-platform"]) == 1 and len(buckets["kf-platform"]) == 1)
check("partition: no task appears twice",
      sum(len(v) for v in buckets.values()) == len(PLAN_TASKS))

# build_body renders a valid, re-parseable 6-col table
body = gk.build_body(PLAN_TASKS, milestone_block="<!-- Milestones x -->")
reparsed = parse_kanban_tasks(body)
check("build_body output re-parses to same task count", len(reparsed) == len(PLAN_TASKS))
check("build_body includes milestone trailer", "Milestones x" in body)

# existing_status_map: only valid statuses, canonicalized
SAMPLE = (
    "---\np: x\n---\n\n| Task | Assignee | Effort | Start | End | Status |\n"
    "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    "| A | @fe | 5d | | | in progress |\n"
    "| B | @be | 3d | | | Decizie pending |\n"
)
m = gk.existing_status_map(SAMPLE)
check("existing_status_map keeps canonicalized valid status", m.get("A") == "In Progress")
check("existing_status_map drops unknown status", "B" not in m)


# ---------------------------------------------------------------------------
print()
print(f"RESULTS: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
