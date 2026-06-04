#!/usr/bin/env bash
# Gap probe for 01-04: proves enumerate_repos() skips marker-less repos
# without regressing the 6 real tracked repos, and leaves the tree CLEAN.
# Run from the kf-cpto repo root.
set -u
cd "$(git rev-parse --show-toplevel)" || exit 1

PROBE="repos-local/__gap_probe__"
git init -q "$PROBE"

python3 - <<'PY'
import sys
sys.path.insert(0, ".claude/skills/activity-sync")
from pathlib import Path
import repo_enum

names = repo_enum.enumerate_repos(Path("repos-local"))
assert "__gap_probe__" not in names, "FAIL: marker-less repo was NOT skipped: %r" % names
real = {"kf-be-platform", "kf-fe-platform", "kf-platform",
        "R3-AAS", "ai-rise-options", "tech_brainstorming"}
present = real & set(names)
assert present == real, "FAIL: expected all 6 real repos, missing %r (got %r)" % (real - present, names)
print("OK skip+noregress:", names)
PY
RC=$?

rm -rf "$PROBE"

if [ "$RC" -ne 0 ]; then
  echo "PROBE FAILED"
  exit 1
fi

# Live run: all 6 enumerate, exit 0, tree stays clean.
python3 .claude/skills/activity-sync/repo_enum.py >/dev/null
if [ $? -ne 0 ]; then
  echo "LIVE RUN FAILED (non-zero exit)"
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "FAIL: kf-cpto tree dirty after live run"
  exit 1
fi

echo "TREE CLEAN — gap probe PASSED"
exit 0
