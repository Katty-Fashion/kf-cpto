#!/usr/bin/env python3
"""
Tests for the pure (no-network) parts of bookstack_sync.py.

Runs with plain Python (no pytest dependency):
    python scripts/test_bookstack_sync.py

Exits non-zero on any failed assert.
"""
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import bookstack_sync as bs  # noqa: E402

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


print("bs.sha:")
check("trailing whitespace is ignored (BookStack trims on save)", bs.sha("abc\n") == bs.sha("abc"))
check("different content hashes differently", bs.sha("abc") != bs.sha("abd"))

print("bs.book_name / is_managed_book_name:")
check("shelf number prefix is dropped from the book title",
      bs.book_name("2601. KF-Platform") == "KF-Platform · Delivery Dashboard")
check("renamed per-shelf books are recognised as managed",
      bs.is_managed_book_name("R3Group · Delivery Dashboard"))
check("legacy plain name is still recognised", bs.is_managed_book_name("Delivery Dashboard"))
check("hand-curated books are never matched", not bs.is_managed_book_name("Module Specifications"))

print("bs.convert_project_page:")
PAGE = """---
title: demo
---

# demo

[dep]({{ '/projects/other/' | relative_url }})

<div class="kanban-board">
  <div class="kanban-col kanban-col--todo">
    <div class="kanban-col__head">Todo <span class="kanban-col__count">1</span></div>
    <div class="kanban-card kanban-card--static">[A &amp; B]</div>
  </div>
  <div class="kanban-col kanban-col--done">
    <div class="kanban-col__head">Done <span class="kanban-col__count">0</span></div>
  </div>
</div>

| Task | Assignee | Effort |
| :--- | :--- | :--- |
| [A &amp; B] | @someone | 2d |

```mermaid
pie
    "x" : 1
```
"""
out = bs.convert_project_page(PAGE)
check("frontmatter stripped", not out.startswith("---") and "title: demo" not in out)
check("liquid links rewritten to Pages URLs", "{{" not in out and f"{bs.PAGES_BASE}/projects/other/" in out)
check("kanban html becomes a markdown table", "<div" not in out and "| Todo (1) | Done (0) |" in out)
check("assignee column dropped (team-level output)", "Assignee" not in out and "@someone" not in out)
check("html entities unescaped", "&amp;" not in out and "[A & B]" in out)
check("mermaid block preserved for rendering", "```mermaid" in out)

print("bs.activity_page / overview_page:")
act = {"person_days": 12.3, "commits": 40, "last_commit": "2026-10-20",
       "monthly": {"2026-10": 12.3}, "branches": [{"name": "work-v2", "ahead": 5, "last_push": "2026-10-20"}]}
page = bs.activity_page("demo", act, {"since": "2026-07-25", "until": "2026-10-26"})
check("activity page lists effort, month and branch", all(x in page for x in ("12.3", "2026-10", "work-v2")))
ov = bs.overview_page("Shelf", ["demo"], [{"project": "demo", "sprint": "S1", "effort_days": 4.0, "status": "Done"},
                                           {"project": "demo", "sprint": "Activity", "effort_days": 9.0, "status": "Activity"}],
                      {"demo": act}, {"since": "a", "until": "b"})
check("overview counts planned effort only (activity row excluded)", "| demo | 4.0 | 4.0 | 12.3 |" in ov)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
