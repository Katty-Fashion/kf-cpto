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
from utils import (
    canonicalize_status, parse_kanban_tasks, mermaid_label_safe,
    mermaid_node_id, mermaid_gantt_label, TASK_STATUSES,
)
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
# mermaid_label_safe
# ---------------------------------------------------------------------------
print("mermaid_label_safe:")
_lbl = mermaid_label_safe('Ce este „Done" vs „Ready" release')
check("double-quotes replaced (no ASCII \" left)", '"' not in _lbl)
check("typographic quote substituted", "”" in _lbl)
check("square brackets neutralized", mermaid_label_safe("a [x] b") == "a (x) b")
check("newlines flattened", "\n" not in mermaid_label_safe("a\nb"))
check("node label has exactly 2 delimiter quotes",
      f'task1["{mermaid_label_safe(chr(34)+"q"+chr(34))}"]'.count('"') == 2)

print("mermaid_node_id / mermaid_gantt_label:")
check("hyphens -> underscores", mermaid_node_id("kf-be-platform") == "kf_be_platform")
check("leading digit kept safe (starts with letter)", mermaid_node_id("R3-AAS") == "R3_AAS")
check("digit-start gets n_ prefix", mermaid_node_id("3d-thing") == "n_3d_thing")
check("node id is a valid graph id", __import__("re").match(r"^[A-Za-z][A-Za-z0-9_]*$",
      mermaid_node_id("ai-rise-options")) is not None)
check("gantt label drops colon", ":" not in mermaid_gantt_label("a: b: c"))
check("gantt label drops ASCII quotes", '"' not in mermaid_gantt_label('Ce „Done" vs „Ready"'))
check("gantt label collapses whitespace", mermaid_gantt_label("a   b") == "a b")


# ---------------------------------------------------------------------------
# Sprint cadence (platform alignment)
# ---------------------------------------------------------------------------
print("sprint cadence:")
from datetime import date as _date
_cal = {"start_date": "2026-05-04", "sprint_length_weeks": 2, "total_weeks": 32}
check("sprint_bounds S1", gk.sprint_bounds(_cal, 1) == ("2026-05-04", "2026-05-15"))
check("sprint_bounds S3", gk.sprint_bounds(_cal, 3) == ("2026-06-01", "2026-06-12"))
check("current sprint for 2026-06-05 is S3", gk.current_sprint_n(_cal, _date(2026, 6, 5)) == 3)
check("current sprint before start clamps to 1", gk.current_sprint_n(_cal, _date(2026, 1, 1)) == 1)
check("active_sprint_window honors plan override",
      gk.active_sprint_window({"active_sprint": "S5"}, _cal, _date(2026, 6, 5))
      == ("S5", *gk.sprint_bounds(_cal, 5)))
check("active_sprint_window falls back to date",
      gk.active_sprint_window({}, _cal, _date(2026, 6, 5))[0] == "S3")
_fm = "---\nproject: x\nsprint: S1\nsprint_start: 2026-05-11\nsprint_end: 2026-05-22\n---\n"
_ovr = gk._override_sprint_frontmatter(_fm, "S3", "2026-06-01", "2026-06-12")
check("override sets sprint label", "sprint: S3" in _ovr)
check("override sets sprint_start", "sprint_start: 2026-06-01" in _ovr)
check("override sets sprint_end", "sprint_end: 2026-06-12" in _ovr)
check("override leaves other keys", "project: x" in _ovr)


# ---------------------------------------------------------------------------
# Gantt invalid-date fallback (regression: R3-AAS '—' placeholder)
# ---------------------------------------------------------------------------
print("gantt invalid-date fallback:")
import aggregator
_pd = {
    "meta": {"sprint": "S2", "sprint_start": "2026-03-16", "sprint_end": "2026-04-03",
             "type": "eu-project", "description": "", "depends_on": [], "tags": []},
    "tasks": [
        {"task": "Sketch JSON", "assignee": "@x", "effort": "", "start": "", "end": "—", "status": "Done"},
        {"task": "Real dated", "assignee": "@y", "effort": "2d", "start": "2026-03-16", "end": "2026-03-20", "status": "Todo"},
    ],
    "raw": "", "exists": True,
}
_page = aggregator.generate_project_page("demo", _pd)
_gantt = _page.split("```mermaid")
_gantt_lines = [l for blk in _gantt if blk.lstrip().startswith("gantt")
                for l in blk.splitlines() if ":" in l and "dateFormat" not in l and "title" not in l]
check("no '—' placeholder leaks into gantt date cell", all("—" not in l for l in _gantt_lines))
check("invalid end falls back to duration", any(":done, 2026-03-16, 1d" in l for l in _gantt_lines))
check("valid explicit dates preserved", any("2026-03-16, 2026-03-20" in l for l in _gantt_lines))


# ---------------------------------------------------------------------------
print()
print(f"RESULTS: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
