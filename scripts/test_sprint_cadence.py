#!/usr/bin/env python3
"""
Tests for the shared sprint-cadence math (utils.sprint_bounds /
utils.current_sprint_idx) and the current-sprint auto-block renderer
(auto_blocks.render_current_sprint).

Runs with plain Python (no pytest dependency):
    python scripts/test_sprint_cadence.py

Exits non-zero on any failed assert.
"""
import sys
from datetime import date
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

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
# utils.sprint_bounds / utils.current_sprint_idx — shared cadence math
# ---------------------------------------------------------------------------
print("utils.sprint_bounds / current_sprint_idx:")

import aggregator  # noqa: E402  (import-cycle smoke check — must not raise)
import auto_blocks  # noqa: E402  (import-cycle smoke check — must not raise)
from utils import sprint_bounds, current_sprint_idx  # noqa: E402

_CAL = {"start_date": "2026-05-04", "sprint_length_weeks": 2}

check(
    "current_sprint_idx(cal, 2026-09-03) == 9",
    current_sprint_idx(_CAL, date(2026, 9, 3)) == 9,
)
check(
    "sprint_bounds(cal, 9) == (2026-08-24, 2026-09-04)",
    sprint_bounds(_CAL, 9) == (date(2026, 8, 24), date(2026, 9, 4)),
)
check(
    "current_sprint_idx({}, ...) == 1 (missing start_date -> safe floor)",
    current_sprint_idx({}, date(2026, 9, 3)) == 1,
)
check(
    "sprint_bounds(cal, 0) == (None, None) (idx < 1 -> unchanged behavior)",
    sprint_bounds({"start_date": "2026-05-04"}, 0) == (None, None),
)

import re  # noqa: E402

_agg_src = (_SCRIPTS_DIR / "aggregator.py").read_text()
check(
    "aggregator.py no longer defines _sprint_bounds/_current_sprint_idx",
    not re.search(r"def _sprint_bounds|def _current_sprint_idx", _agg_src),
)

# ---------------------------------------------------------------------------
# auto_blocks.render_current_sprint — AUTO:current-sprint renderer
# ---------------------------------------------------------------------------
print("auto_blocks.render_current_sprint:")

try:
    from auto_blocks import (  # noqa: E402
        AUTO_BLOCK_RENDERERS,
        render_current_sprint,
        known_block_names,
    )
    _HAS_RENDERER = True
except ImportError:
    _HAS_RENDERER = False

check("render_current_sprint is importable from auto_blocks", _HAS_RENDERER)

if _HAS_RENDERER:
    check("'current-sprint' in known_block_names()", "current-sprint" in known_block_names())
    check(
        "'current-sprint' registered in AUTO_BLOCK_RENDERERS",
        AUTO_BLOCK_RENDERERS.get("current-sprint") is render_current_sprint,
    )

    out = render_current_sprint({"calendar": _CAL})
    for frag in [
        "```mermaid",
        "title Sprint Calendar",
        "section Scrum",
        "Sprint S9 Planning",
        ":crit, 2026-08-24, 1d",
        ":active, 2026-08-25, 9d",
        "Sprint S9 Demo + Retro",
        ":crit, 2026-09-04, 1d",
    ]:
        check(f"render_current_sprint output contains {frag!r}", frag in out)
    check("render_current_sprint output has no 'Sprint 3' leftover", "Sprint 3" not in out)

    bad = render_current_sprint({"calendar": {}})
    check(
        "render_current_sprint({'calendar': {}}) returns italic fallback, no mermaid fence",
        bad.startswith("_(auto-data:") and "mermaid" not in bad,
    )
else:
    print("  SKIP: render_current_sprint checks (renderer not implemented yet)")


# ---------------------------------------------------------------------------
# docs/index.md — augmented page declaring the current-sprint block
# ---------------------------------------------------------------------------
print("docs/index.md augmentation:")

_INDEX_MD = _SCRIPTS_DIR.parent / "docs" / "index.md"
_index_src = _INDEX_MD.read_text() if _INDEX_MD.exists() else ""
check(
    "docs/index.md declares auto_blocks: [current-sprint]",
    "auto_blocks: [current-sprint]" in _index_src or "auto_blocks:\n  - current-sprint" in _index_src,
)
check(
    "docs/index.md has <!-- AUTO:current-sprint --> marker pair",
    "<!-- AUTO:current-sprint -->" in _index_src and "<!-- /AUTO:current-sprint -->" in _index_src,
)
check(
    "docs/index.md no longer hardcodes Sprint 3 / March 2026",
    "Sprint 3 Planning" not in _index_src and "2026-03-" not in _index_src,
)


print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
