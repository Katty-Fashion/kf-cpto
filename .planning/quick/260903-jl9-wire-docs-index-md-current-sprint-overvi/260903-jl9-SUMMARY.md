---
phase: quick-260903-jl9
plan: 01
subsystem: dashboard
tags: [jekyll, mermaid, auto-blocks, sprint-cadence, python]

# Dependency graph
requires:
  - phase: none
    provides: n/a (quick task, no phase dependency)
provides:
  - "utils.sprint_bounds(cal, idx) / utils.current_sprint_idx(cal, today) — shared sprint cadence math"
  - "auto_blocks.render_current_sprint — AUTO:current-sprint renderer"
  - "docs/index.md as an augmented page with a self-updating Current Sprint Overview gantt"
affects: [dashboard, aggregator, auto-blocks-engine]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sprint cadence math lives in exactly one place (utils.py); both aggregator.py and auto_blocks.py delegate to it via function-level or block-level import"
    - "AUTO:name marker convention extended to docs/index.md (previously only docs/migration-gantt.md)"

key-files:
  created:
    - scripts/test_sprint_cadence.py
  modified:
    - scripts/utils.py
    - scripts/aggregator.py
    - scripts/auto_blocks.py
    - docs/index.md

key-decisions:
  - "Relocated _sprint_bounds/_current_sprint_idx from aggregator.py to utils.py byte-for-byte (no rewrite) to avoid a circular import between aggregator.py and auto_blocks.py"
  - "render_current_sprint mirrors render_calendar's fallback convention: plain italic auto-data text (never a half-formed mermaid fence) when calendar.start_date is missing"
  - "Added scripts/test_sprint_cadence.py following the existing plain-Python test convention (scripts/test_generate_kanban.py) rather than introducing pytest"

patterns-established:
  - "New date-math helpers go in utils.py (stdlib+yaml only) so both aggregator.py and auto_blocks.py can import them without a cycle"

requirements-completed: [QT-260903-JL9]

duration: 12min
completed: 2026-09-03
---

# Quick Task 260903-jl9: Wire docs/index.md Current Sprint Overview to real cadence Summary

**Turned the hardcoded "Sprint 3 / March 2026" gantt on the dashboard landing page into an `AUTO:current-sprint` block, sourced from `docs/_data/calendar.yml` and regenerated on every aggregator run — landing page now correctly shows Sprint S9 (2026-08-24 → 2026-09-04).**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-09-03T13:10:00Z (approx, worktree setup)
- **Completed:** 2026-09-03T13:14:44Z
- **Tasks:** 3 completed (plus 1 TDD RED test commit)
- **Files modified:** 4 (utils.py, aggregator.py, auto_blocks.py, docs/index.md) + 1 new test file

## Accomplishments
- Sprint index/bounds arithmetic (`sprint_bounds`, `current_sprint_idx`) now lives in exactly one place — `scripts/utils.py` — consumed by both `aggregator.py` and `auto_blocks.py`, no circular import
- New `render_current_sprint` renderer registered as `"current-sprint"` in `AUTO_BLOCK_RENDERERS`, matching the previous hand-written gantt style (title, section Scrum, Planning/Active/Demo+Retro bars)
- `docs/index.md` converted to an augmented page (`auto_blocks: [current-sprint]`) with `<!-- AUTO:current-sprint -->` markers wrapping the gantt
- Ran the exact aggregator injection path end to end; regenerated `docs/index.md` now shows the real S9 window and no longer mentions "Sprint 3" or any `2026-03-` date
- Confirmed idempotency: a second consecutive injection run reports no further change
- Both CI gates (`validate_auto_blocks.py`, `validate_mermaid.py`) exit 0

## Task Commits

Each task was committed atomically (TDD flow — Task 1/2 behaviors covered by one upfront RED commit, then per-task GREEN commits):

1. **RED — failing test for shared sprint-cadence math** - `54e6bab` (test)
2. **Task 1: Lift sprint cadence math into utils.py and delegate from aggregator.py** - `50cdcf3` (feat)
3. **Task 2: Add the current-sprint renderer and convert docs/index.md into an augmented page** - `58600c9` (feat)
4. **Task 3: Run the injection path end to end and confirm index.md self-updates** - `e1a367d` (feat)

_TDD gate compliance: `test(...)` commit `54e6bab` precedes all three `feat(...)` commits — RED then GREEN, per plan-level TDD requirement._

## Files Created/Modified
- `scripts/test_sprint_cadence.py` - New plain-Python test file (no pytest) covering `utils.sprint_bounds`/`current_sprint_idx`, `auto_blocks.render_current_sprint`, and `docs/index.md` augmentation invariants; run via `python scripts/test_sprint_cadence.py`
- `scripts/utils.py` - Added public `sprint_bounds(cal, idx)` and `current_sprint_idx(cal, today=None)`, relocated byte-for-byte from `aggregator.py`
- `scripts/aggregator.py` - Removed `_sprint_bounds`/`_current_sprint_idx` bodies; imports and calls the shared `utils` helpers at both call sites in `_gantt_sprint_views`
- `scripts/auto_blocks.py` - Added `render_current_sprint(context)` and registered it as `"current-sprint"`; amended module docstring's determinism note to explain the intentional today-based advancement
- `docs/index.md` - Declares `auto_blocks: [current-sprint]`; hardcoded "Sprint 3 / March 2026" gantt replaced with `<!-- AUTO:current-sprint -->` markers; regenerated content shows S9 (2026-08-24 → 2026-09-04)

## Decisions Made
- Followed the plan's prescribed relocation approach (move, don't rewrite) for `sprint_bounds`/`current_sprint_idx` to guarantee behavior parity
- Used a single test file spanning both TDD tasks' `<behavior>` blocks rather than one file per task, since both tasks share the same sprint-cadence feature and the codebase's existing test convention (`test_generate_kanban.py`) is one file per feature area, not one per plan task

## Deviations from Plan

None — plan executed exactly as written. All verification commands from the plan (Task 1, Task 2, Task 3 automated checks, plus the plan's overall `<verification>` greps) were run and passed.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The dashboard landing page now tells the truth about the current sprint and will continue to do so on every future aggregator run without manual editing
- `scripts/test_sprint_cadence.py` is available for regression coverage if `calendar.yml`'s cadence fields or the renderer's output format change later
- No blockers or concerns for follow-on work

---
*Quick task: 260903-jl9*
*Completed: 2026-09-03*

## Self-Check: PASSED

All created/modified files found on disk; all 4 task commit hashes (`54e6bab`, `50cdcf3`, `58600c9`, `e1a367d`) found in `git log`.
