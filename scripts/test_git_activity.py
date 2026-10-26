#!/usr/bin/env python3
"""
Tests for the git-derived activity input (git_activity.py + aggregator.build_activity_rows).

Runs with plain Python (no pytest dependency):
    python scripts/test_git_activity.py

Exits non-zero on any failed assert.
"""
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import aggregator  # noqa: E402
import git_activity  # noqa: E402

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


print("git_activity.repo_effort:")
# 2026-10-01 12:00 local epoch is irrelevant to totals; use two commits one day, one bot.
EPOCH = 1790856000
LOG = "\n".join([
    f"@@{EPOCH}|Dev One",
    "400\t0\tsrc/app.py",
    "900\t0\t.planning/phases/plan.md",   # excluded path
    "-\t-\tassets/logo.png",              # binary: file counted, 0 added
    f"@@{EPOCH + 60}|Dev One",
    "100\t0\tsrc/util.py",
    f"@@{EPOCH}|KF Bot",
    "5000\t0\tsrc/generated.py",          # bot: ignored entirely
])
res = git_activity.repo_effort(LOG)
check("bot commits are not counted", res["commits"] == 2)
# one contributor-day: 1 + 0.25*2 + 500/500 + 0.03*3 = 2.59h -> 0.3 person-days
check("excluded paths and bots do not inflate churn", res["person_days"] == 0.3)

check("monthly effort is reported and sums to the total",
      set(res["monthly"]) == {"2026-10"} and abs(sum(res["monthly"].values()) - res["person_days"]) < 0.11)

big = "\n".join([f"@@{EPOCH}|Dev One"] + [f"9999\t0\tsrc/f{i}.py" for i in range(50)])
check("one contributor-day is capped at one person-day",
      git_activity.repo_effort(big)["person_days"] == 1.0)

print("aggregator.build_activity_rows:")
activity = {
    "since": "2026-07-25", "until": "2026-10-26",
    "repos": [
        {"repo": "kf-vault", "commits": 6, "person_days": 0.8},
        {"repo": "R3-AAS", "commits": 164, "person_days": 18.1},
        {"repo": "idle", "commits": 0, "person_days": 0},
    ],
}
planned = [{"project": "R3-AAS", "effort_days": 5.0}]
rows = aggregator.build_activity_rows(activity, planned)
check("repo without planned effort gets one Team row",
      len(rows) == 1 and rows[0]["project"] == "kf-vault" and rows[0]["assignee"] == "Team")
check("repo with planned effort is skipped (no double count)",
      all(r["project"] != "R3-AAS" for r in rows))
check("zero-effort repo is skipped", all(r["project"] != "idle" for r in rows))
check("row keeps the canonical LOE contract keys",
      set(rows[0]) == {"project", "sprint", "task", "assignee", "effort_days", "start", "end", "status"})
check("empty activity yields no rows", aggregator.build_activity_rows({}, planned) == [])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
