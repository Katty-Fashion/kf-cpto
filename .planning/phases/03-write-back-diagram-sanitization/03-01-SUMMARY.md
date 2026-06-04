---
phase: 03-write-back-diagram-sanitization
plan: "01"
subsystem: skill
tags: [ruamel-yaml, mermaid, sanitization, write-back, tdd, python]

requires:
  - phase: 02-activity-mining-reconciliation
    provides: reconcile.Proposal dataclass; TASK_STATUSES; sys.path injection pattern; test harness style

provides:
  - "sanitize.py: sanitize_cell() + sanitize_body() + _is_emoji() pure transforms"
  - "writeback.py: split_kanban() + roundtrip_frontmatter() + reconstruct_kanban() + apply_status_change() + _content_changed()"
  - "test_writeback.py: 60-assertion no-pytest harness covering all sanitize + string-builder behavior"
  - "requirements.txt: ruamel.yaml>=0.17 added"
  - ".gitignore: manifests/ runtime artifacts excluded"

affects:
  - 03-02 (git operations, conflict detection, manifest writing build on these string builders)
  - 03-03 (batch confirm + run() + main() consume apply_status_change and sanitize_body)

tech-stack:
  added:
    - "ruamel.yaml>=0.17 (comment-preserving YAML round-trip; skill-local only, CI never installs)"
  patterns:
    - "Pure-function library: sanitize.py has no git/IO/print; tested independently"
    - "TDD RED/GREEN: test file written first with failing imports; implementation turns it GREEN"
    - "Inline YAML fixture for round-trip test (real YAML values, not template placeholders)"
    - "apply_status_change first-match-only with [WARN] on duplicates (from RESEARCH.md Pattern 2)"
    - "Trailing-newline guard on ruamel dump: .rstrip('\\n') + '\\n' (RESEARCH.md Pitfall 5)"

key-files:
  created:
    - ".claude/skills/activity-sync/sanitize.py"
    - ".claude/skills/activity-sync/writeback.py"
    - ".claude/skills/activity-sync/test_writeback.py"
    - ".claude/skills/activity-sync/manifests/.gitkeep"
  modified:
    - "requirements.txt (added ruamel.yaml>=0.17)"
    - ".gitignore (added manifests/ exclusion)"

key-decisions:
  - "Test fixture uses inline valid YAML (not templates/kanban.md) — template has {project-name} flow-mapping that ruamel rewrites as {project-name: null}, breaking byte-identity"
  - "sanitize.py is a pure library: no print(), no sys.path injection, no subprocess — writeback.py owns the orchestration"
  - "Status replacement applied BEFORE sanitize pass (anti-pattern from RESEARCH.md: sanitize would alter task name cell, breaking Proposal.task match)"

patterns-established:
  - "Pure-library boundary: sanitize.py has zero side effects; tested in isolation before writeback.py exists"
  - "round-trip-only-frontmatter: body is never passed through ruamel; only frontmatter gets the YAML round-trip"
  - "apply_status_change parts[-2] pattern: works for both 4-col and 6-col tables because Status is always last data column"

requirements-completed: [WB-01, DIAG-01, DIAG-02, DIAG-03]

duration: 5min
completed: "2026-06-04"
---

# Phase 3 Plan 01: Write-Back String Builders + Mermaid Sanitization Summary

**ruamel.yaml comment-preserving frontmatter round-trip + emoji/break-char sanitization producing a corrected kanban.md string with zero git operations — 60/60 tests GREEN**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-04T11:24:57Z
- **Completed:** 2026-06-04T11:29:51Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- `sanitize.py`: pure Mermaid sanitization with `sanitize_cell()` substitution map (_BREAK_MAP), emoji strip via Unicode codepoint ranges, and `sanitize_body()` that scopes strictly to data rows (skips header, separator, prose, HTML comments) — idempotent and Romanian-diacritic-preserving
- `writeback.py`: ruamel.yaml round-trip preserving `#` comments and key order (WB-01); byte-identical reconstruct for unmodified files; targeted `apply_status_change()` working for both 4-col and 6-col tables with first-match-only + [WARN] on duplicates; `_content_changed()` byte-compare gate (SC-4 partial)
- `test_writeback.py`: 60-assertion no-pytest harness covering all DIAG-01/02/03 + WB-01 behaviors — written in RED state before implementation, turned GREEN after Tasks 2 and 3

## Task Commits

1. **Task 1: Config groundwork + RED test scaffold** - `eee771c` (chore)
2. **Task 2: sanitize.py pure Mermaid sanitization** - `4057e3f` (feat)
3. **Task 3: writeback.py string builders + GREEN test suite** - `1280808` (feat)

**Plan metadata:** (docs commit follows this SUMMARY)

## Files Created/Modified

- `.claude/skills/activity-sync/sanitize.py` - Pure sanitization library: `_BREAK_MAP`, `_is_emoji()`, `sanitize_cell()`, `sanitize_body()`
- `.claude/skills/activity-sync/writeback.py` - String builders: `split_kanban()`, `roundtrip_frontmatter()`, `reconstruct_kanban()`, `apply_status_change()`, `_content_changed()`
- `.claude/skills/activity-sync/test_writeback.py` - 60-assertion no-pytest test harness (RED at Task 1, GREEN at Task 3)
- `.claude/skills/activity-sync/manifests/.gitkeep` - Sentinel for gitignored runtime artifact directory
- `requirements.txt` - Added `ruamel.yaml>=0.17` (skill-local; CI never installs)
- `.gitignore` - Added `.claude/skills/activity-sync/manifests/` exclusion

## Decisions Made

- **Inline YAML fixture instead of templates/kanban.md**: The template file uses `{project-name}` which ruamel.yaml parses as a YAML flow mapping and dumps as `{project-name: null}`, breaking byte-identity. Real tracked-repo kanban.md files always have concrete values and round-trip cleanly. Test fixture uses an inline fixture matching real repo structure.
- **sanitize.py has no print/sys.path/subprocess**: Kept as a pure library with zero side effects. writeback.py owns orchestration and sys.path injection.
- **Status replacement before sanitize**: Per RESEARCH.md anti-pattern note — sanitize_body must run AFTER apply_status_change so the Proposal.task match operates on raw (unsanitized) task names.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Round-trip test fixture replaced from templates/kanban.md to inline YAML**
- **Found during:** Task 3 (writeback.py string builders)
- **Issue:** `templates/kanban.md` contains `{project-name}` as a YAML value — ruamel parses this as a flow mapping `{project-name: null}` and dumps it differently, causing `reconstruct_kanban(*split_kanban(orig)) != orig`. The test would permanently FAIL against the template.
- **Fix:** Replace `_KANBAN_ORIG = _KANBAN_TEMPLATE.read_text()` with an inline fixture containing real YAML values (same structure as actual tracked-repo kanban.md files). The round-trip is byte-identical for real YAML.
- **Files modified:** `.claude/skills/activity-sync/test_writeback.py`
- **Verification:** `python test_writeback.py` — 60/60 PASS including the byte-identity assertion
- **Committed in:** `1280808` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test fixture)
**Impact on plan:** Required for the WB-01 byte-identity criterion to be meaningful. No scope creep. The fix also accurately models real usage (skill only runs against real repos, never template files).

## Issues Encountered

None beyond the test fixture deviation documented above.

## Known Stubs

None. All functions are fully implemented and verified. The plan explicitly defers git operations (commit/push), conflict detection, batch confirmation, and manifest writing to Plans 02 and 03 — these are planned future work, not stubs.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced in this plan. `sanitize.py` and `writeback.py` are pure string-transform libraries with no I/O in this plan.

## Next Phase Readiness

- Plans 02 and 03 can now import `split_kanban`, `reconstruct_kanban`, `apply_status_change`, `sanitize_body` and build the git operations on top
- The string-builder contract is fully tested — any breakage from Plan 02 edits will surface immediately
- `manifests/` directory is created, gitignored, and ready for per-run JSON manifests

---
*Phase: 03-write-back-diagram-sanitization*
*Completed: 2026-06-04*
