#!/usr/bin/env python3
"""
Git-derived activity effort — a conservative, team-level FLOOR per repo.

Local-only producer (run from Claude Code / a dev machine, like the activity-sync
skill). It reads full clones in repos-local/ (all remote branches, so in-flight
work counts) and writes docs/_data/git_activity.yml. CI never runs this; the
aggregator only reads the committed YAML, so CI stays deterministic.

Method (deliberately conservative — report less, deliver more):
  - per contributor per work-day: h = clamp(1 + 0.25*commits + added/500 + 0.03*files, 1, CAP)
  - CAP = 8h per contributor per day (one person cannot exceed a person-day)
  - planning/docs/markdown/generated paths excluded from churn
  - bots excluded; no per-person data is written, only repo totals

Usage:
    python scripts/git_activity.py --since 2026-07-25 --until 2026-10-26
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from utils import BASE_DIR, GIT_ACTIVITY_FILE, now_iso

REPOS_LOCAL_DIR = BASE_DIR / "repos-local"

CAP_HOURS = 8.0
ROLLOVER_HOUR = 6  # activity before 06:00 folds into the previous work-day
HOURS_PER_DAY = 8.0
BOT_RE = re.compile(r"^(KF Bot|root|i\.tech)$", re.IGNORECASE)
EXCLUDE_RE = re.compile(
    r"(^|/)(\.planning|docs|synthetic-test-data|seed-demo|graphs|archive|"
    r"node_modules|dist|build|vendor)/|\.md$|\.json$|\.lock$|package-lock\.json$"
)


def day_hours(commits: int, files: int, added: int) -> float:
    """Churn estimate for one contributor-day, capped at one person-day."""
    return min(CAP_HOURS, max(1.0, 1 + 0.25 * commits + added / 500 + 0.03 * files))


def work_day(epoch: int) -> str:
    return (datetime.fromtimestamp(epoch) - timedelta(hours=ROLLOVER_HOUR)).strftime("%Y-%m-%d")


def _git_log(repo: Path, since: str, until: str) -> str:
    result = subprocess.run(
        ["git", "log", "--remotes", "--no-merges", f"--since={since}", f"--until={until}",
         "--numstat", "--format=@@%at|%aN"],
        cwd=repo, capture_output=True, text=True, timeout=300,
    )
    return result.stdout if result.returncode == 0 else ""


def repo_effort(log: str) -> dict:
    """Parse `git log --numstat` output into {commits, person_days} for one repo."""
    days: dict = defaultdict(lambda: [0, 0, 0])  # (author, day) -> commits, files, added
    commits = 0
    key = None
    for line in log.splitlines():
        if line.startswith("@@"):
            epoch, _, author = line[2:].partition("|")
            if BOT_RE.match(author.strip()):
                key = None
                continue
            key = (author.strip(), work_day(int(epoch)))
            days[key][0] += 1
            commits += 1
        elif key and line.strip():
            parts = line.split("\t")
            if len(parts) != 3 or EXCLUDE_RE.search(parts[2]):
                continue
            added = int(parts[0]) if parts[0].isdigit() else 0  # '-' = binary
            days[key][1] += 1
            days[key][2] += added
    hours = sum(day_hours(c, f, a) for c, f, a in days.values())
    return {"commits": commits, "person_days": round(hours / HOURS_PER_DAY, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    args = ap.parse_args()

    print("Git Activity — Starting...")
    if not REPOS_LOCAL_DIR.exists():
        print("Warning: repos-local/ missing — run activity-sync bootstrap.py first")
        return 1
    repos = []
    for path in sorted(REPOS_LOCAL_DIR.iterdir()):
        if not (path / ".git").exists():
            continue
        stats = repo_effort(_git_log(path, args.since, args.until))
        if stats["commits"]:
            repos.append({"repo": path.name, **stats})
            print(f"[INFO] {path.name}: {stats['commits']} commits, {stats['person_days']} person-days")

    payload = {
        "generated_at": now_iso(),
        "since": args.since,
        "until": args.until,
        "method": "conservative floor: churn estimate, 8h/contributor/day cap, docs excluded",
        "repos": repos,
    }
    GIT_ACTIVITY_FILE.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    print(f"Wrote {len(repos)} repos -> {GIT_ACTIVITY_FILE}")
    print("Git Activity — Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
