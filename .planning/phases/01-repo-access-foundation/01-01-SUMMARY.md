---
phase: 01-repo-access-foundation
plan: 01
subsystem: infra
tags: [gitignore, claude-skills, skill-scaffold]

# Dependency graph
requires: []
provides:
  - ".claude/skills/activity-sync/ is git-trackable via .claude/* + !.claude/skills/ in .gitignore"
  - "activity-sync SKILL.md index with name/description/allowed-tools frontmatter and both entry points documented"
  - "repos-local/ excluded from git (runtime-only skill clone dir)"
affects:
  - 01-02-bootstrap
  - 01-03-repo-enum

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ".claude/* + !.claude/skills/ gitignore idiom (child-glob-plus-negation) to un-ignore only skills subdir"
    - "SKILL.md with name/description/allowed-tools frontmatter as Claude Code skill index"

key-files:
  created:
    - .claude/skills/activity-sync/SKILL.md
  modified:
    - .gitignore

key-decisions:
  - "Use .claude/* + !.claude/skills/ (child-glob-plus-negation) rather than listing specific session files; ensures future .claude/ additions default to ignored unless explicitly allowed"
  - "SKILL.md allowed-tools as YAML list (Bash, Read) matching verified field names from existing skill examples"
  - "SKILL.md description includes trigger phrases (activity sync, repo enum, list tracked repos) for Claude Code skill matching"

patterns-established:
  - "Gitignore child-glob-plus-negation: .claude/* then !.claude/skills/ un-ignores one subdir while blocking all others"
  - "Skill SKILL.md index: frontmatter (name, description, allowed-tools) + body with run commands and [LABEL] pills"

requirements-completed: [REPO-01]

# Metrics
duration: 5min
completed: 2026-06-04
---

# Phase 1 Plan 01: Gitignore Skill Unblock and SKILL.md Scaffold Summary

**Child-glob gitignore (.claude/* + !.claude/skills/) enabling activity-sync skill trackability, plus SKILL.md index documenting both entry points (bootstrap.py and repo_enum.py)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-04T07:11:05Z
- **Completed:** 2026-06-04T07:16:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Replaced blanket `.claude/` gitignore exclusion with `.claude/*` + `!.claude/skills/`; verified session files (settings.json, settings.local.json, cache/, memory/) stay ignored and only `.claude/skills/` is un-ignored
- Added `repos-local/` to `.gitignore` (skill's runtime clone dir, mirrors existing `repos/` entry)
- Created `.claude/skills/activity-sync/SKILL.md` with verified frontmatter fields (name, description, allowed-tools) and body documenting bootstrap.py and repo_enum.py entry points; uses `[LABEL]` text pills per CLAUDE.md convention

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace blanket .claude/ exclusion with .claude/* + !.claude/skills/ and add repos-local/** - `e7456c2` (chore)
2. **Task 2: Create the activity-sync SKILL.md index** - `aa852f8` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `.gitignore` — replaced `#Claude / .claude/` blanket entry with `.claude/*` + `!.claude/skills/` block; added `repos-local/` runtime-dirs block
- `.claude/skills/activity-sync/SKILL.md` — Claude Code skill index; YAML frontmatter (name, description, allowed-tools) + body with bootstrap/enum commands, output format, parser constraint note

## Decisions Made
- Used `.claude/*` child-glob-plus-negation pattern rather than listing specific session files explicitly (e.g., `.claude/settings.local.json`, `.claude/cache/`). This ensures any new `.claude/` additions (e.g., `.claude/memory/`) remain ignored by default without requiring a future `.gitignore` update.
- `allowed-tools` written as YAML list (Bash, Read) — verified against existing `.claude/skills/gsd-ultraplan-phase/SKILL.md` on this machine which uses the same format.
- SKILL.md body uses `[LABEL]` text pills (`[BOOTSTRAP]`, `[ENUM]`, `[NOTE]`, `[WARN]`, `[NEVER]`) per CLAUDE.md text pills convention.

## Deviations from Plan

None - plan executed exactly as written.

The SKILL.md frontmatter field names (`name`, `description`, `allowed-tools`) were flagged as [ASSUMED] in RESEARCH.md (Assumption A1). Verified against live SKILL.md examples on this machine before writing:
- `/Users/machina/.local/share/uv/tools/kimi-cli/lib/python3.13/site-packages/kimi_cli/skills/kimi-cli-help/SKILL.md` — uses `name` + `description`
- `/Users/machina/.claude/skills/gsd-ultraplan-phase/SKILL.md` — uses `name`, `description`, `allowed-tools` (YAML list)

Assumption A1 was correct. No field name deviation required.

## Issues Encountered
None.

## Threat Mitigations Applied

| Threat | Mitigation Applied |
|--------|-------------------|
| T-01-01: settings.json/secrets exposed | `.claude/*` blocks all; verified `git add -An` does not stage settings.json, settings.local.json, cache/, memory/ |
| T-01-02: skill code silently dropped | `!.claude/skills/` re-includes; verified probe file under `.claude/skills/activity-sync/` IS staged in dry-run |
| T-01-03: repos-local/ committed | `repos-local/` added to `.gitignore`; verified probe under repos-local/ is NOT staged |

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Known Stubs

None. This plan creates only a `.gitignore` rule change and a `SKILL.md` index; no executable code or data-rendering components.

## Next Phase Readiness
- `.claude/skills/activity-sync/` is git-trackable — Plan 01-02 (bootstrap.py) and 01-03 (repo_enum.py) can commit Python modules there
- `repos-local/` is gitignored — bootstrap.py can populate it at runtime without risk of committing clones
- SKILL.md provides the contract for both entry points; later waves fill in the actual scripts

---
*Phase: 01-repo-access-foundation*
*Completed: 2026-06-04*
