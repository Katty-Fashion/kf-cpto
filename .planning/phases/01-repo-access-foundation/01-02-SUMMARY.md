---
phase: 01-repo-access-foundation
plan: 02
subsystem: infra
tags: [bootstrap, git-clone, marker-seeding, tracked-repos, python39]

# Dependency graph
requires:
  - 01-01-skill-scaffold
provides:
  - ".claude/skills/activity-sync/bootstrap.py — one-shot clone+seed helper holding the TRACKED_REPOS curated allowlist (the ONLY static list)"
  - "repos-local/ populated with the 6-repo tracked set (full SSH clones, not shallow), each carrying kanban.md + notify-kf-cpto.yml"
affects:
  - 01-03-repo-enum

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "from __future__ import annotations to keep PEP 604 (str | None) annotations valid on the 3.9-pinned venv"
    - "Curated allowlist as a module constant (TRACKED_REPOS) realized as repos-local/ membership; enumeration code never replicates the list"
    - "arg-list subprocess.run (no shell=True) for clone URLs built from hardcoded KF_ORG constant"
    - "Idempotent seed-if-absent marker copy from templates/ into each cloned repo"

key-files:
  created:
    - .claude/skills/activity-sync/bootstrap.py
  modified: []

key-decisions:
  - "Added 'from __future__ import annotations' as first import to defer all annotation evaluation; fixes 'str | None' on the project's Python 3.9 venv without changing the annotation style"
  - "Full SSH clone (no --depth) because Phase 2 activity mining needs git history; URL built from hardcoded KF_ORG=Katty-Fashion constant only"
  - "TRACKED_REPOS lives ONLY in bootstrap.py (REPO-01); the allowlist is realized as repos-local/ membership for the enumerator to read"

patterns-established:
  - "Python 3.9-compat annotation idiom: PEP 604 unions in signatures require 'from __future__ import annotations' on the pinned venv"
  - "Clone+seed bootstrap: skip-if-present clone, non-fatal Warning on failure, seed-if-absent markers"

requirements-completed: [REPO-01]

# Metrics
duration: 8min
completed: 2026-06-04
---

# Phase 1 Plan 02: Bootstrap Tracked Repos and Seed Markers Summary

**bootstrap.py clones the 6-repo curated allowlist (TRACKED_REPOS) into repos-local/ via full SSH clone and seeds missing kanban.md / notify-kf-cpto.yml from templates/; made Python 3.9-compatible via deferred annotations.**

## Performance

- **Duration:** ~8 min (resume + fix + live run)
- **Completed:** 2026-06-04
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint, both now satisfied)
- **Files modified:** 1

## Accomplishments
- Authored `.claude/skills/activity-sync/bootstrap.py` (committed earlier as `304454c`): `TRACKED_REPOS` curated allowlist, `_run_git` arg-list subprocess wrapper, `_clone_repo` (full SSH clone, skip-if-present, non-fatal Warning on failure), `_seed_markers` (seed-if-absent from `templates/`), and `main() -> int` with open/close banner.
- Fixed a real Python 3.9 incompatibility: the `str | None` PEP 604 union annotation in `_run_git` was evaluated at function-definition time and crashed module import on the 3.9-pinned venv. Added `from __future__ import annotations` as the first import to defer all annotation evaluation (commit `b3b356b`).
- Live bootstrap run completed exit 0: cloned all 6 tracked repos (kf-be-platform, kf-fe-platform, kf-platform, R3-AAS, ai-rise-options, tech_brainstorming) into `repos-local/`.
- Markers seeded as expected: ai-rise-options got both kanban.md + notify-kf-cpto.yml; R3-AAS got notify-kf-cpto.yml (kanban.md pre-existed); tech_brainstorming got both.
- Verified all clones are full (not shallow) and the kf-cpto working tree stayed clean (repos-local/ gitignored).

## Task Commits

1. **Task 1: Write bootstrap.py — TRACKED_REPOS allowlist, SSH clone, marker seeding** — `304454c` (feat, committed in the prior execution session)
2. **Python 3.9 compatibility fix** — `b3b356b` (fix) — `from __future__ import annotations`
3. **Task 2: Live bootstrap run** — human-verify checkpoint; no code commit (runtime population of gitignored repos-local/)

**Plan metadata:** docs commit — see below.

## Files Created/Modified
- `.claude/skills/activity-sync/bootstrap.py` — clone+seed helper; `from __future__ import annotations`, `KF_ORG="Katty-Fashion"`, `REPOS_LOCAL_DIR`, `TRACKED_REPOS` (6 repos), `_run_git`, `_clone_repo`, `_seed_markers`, `main()`.

## Decisions Made
- **Deferred annotations for 3.9 compat:** Rather than rewriting `str | None` to `Optional[str]`, added `from __future__ import annotations` (works on 3.7+) so all annotations become strings and are never evaluated at runtime. This covers the existing union and any future 3.10+ annotation idioms in the file. Audited the file for non-annotation 3.10+ runtime constructs (runtime union expressions, `match` statements) — none present (the module parses and imports cleanly under 3.9.6; 3.9's `ast` has no `Match` node, confirming no match statement exists).
- **Full SSH clone (no --depth):** Phase 2 activity mining needs git history.
- **TRACKED_REPOS lives only here:** the allowlist is realized as `repos-local/` membership for the enumerator (REPO-01).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Python 3.9 incompatibility: PEP 604 union annotation crashed module import**
- **Found during:** Task 2 live run (surfaced at the human-verify checkpoint)
- **Issue:** `_run_git(args: list[str], cwd: str | None = None)` used PEP 604 union syntax (`str | None`), valid only on Python 3.10+. The project venv is pinned to Python 3.9 (CLAUDE.md). The annotation is evaluated at function-definition time, so the module could not even import: `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`, exit 1.
- **Fix:** Added `from __future__ import annotations` as the first import. Verified the module imports under Python 3.9.6 and `TRACKED_REPOS` has 6 entries.
- **Files modified:** `.claude/skills/activity-sync/bootstrap.py`
- **Commit:** `b3b356b`

## Issues Encountered
- The initial bootstrap run failed at module import due to the 3.9 annotation incompatibility above. Fixed inline (Rule 1) and re-run successfully.
- `tech_brainstorming` (flagged in RESEARCH A3 as possibly absent in the org) **does exist** and cloned successfully — the non-fatal Warning path for a missing repo was therefore not exercised in this run, but is implemented and ready.

## Verification Results
- `python .claude/skills/activity-sync/bootstrap.py` → exit 0, "Activity Sync — Bootstrap — Done!" banner.
- `ls repos-local/` → R3-AAS, ai-rise-options, kf-be-platform, kf-fe-platform, kf-platform, tech_brainstorming (all 6).
- ai-rise-options: kanban.md + notify-kf-cpto.yml both present (seeded). R3-AAS: notify-kf-cpto.yml present (seeded); kanban.md pre-existed.
- `git -C repos-local/<repo> rev-parse --is-shallow-repository` → `false` for all 6 (full clones).
- `git -C . status --porcelain` → empty (repos-local/ gitignored; `git check-ignore repos-local/` confirms).
- Plan automated AST check → PASS (TRACKED_REPOS defined; no shell=True; no --depth; no forbidden utils calls; >=4 .parent).

## Threat Mitigations Applied

| Threat | Mitigation Applied |
|--------|-------------------|
| T-02-01: shell injection via repo/branch into argv | `_run_git` uses arg-list `subprocess.run(["git"]+args, ...)`; no `shell=True`. Verified `shell=True` absent. |
| T-02-02: spoofed clone source | Clone URL built from hardcoded `KF_ORG="Katty-Fashion"` constant + curated name only; org segment never parameterized. |
| T-02-03: path traversal in seed/clone targets | Targets are `REPOS_LOCAL_DIR / <name>` where `<name>` comes from the curated allowlist (no `..`, no user input). |
| T-02-04: missing repo DoS | Clone failure is non-fatal (`Warning:` + continue); implemented in `_clone_repo`. Not triggered this run (all 6 cloned). |
| T-02-SC: package-install supply chain | No package installs — stdlib only (shutil, subprocess, sys, pathlib). |

## Threat Flags

None. No new network endpoints beyond the org SSH clone (org segment is a hardcoded constant), no auth paths, no schema changes.

## Known Stubs

None. bootstrap.py is fully functional executable code; live run populated repos-local/ as designed.

## Next Phase Readiness
- `repos-local/` now holds the 6-repo tracked set, each carrying kanban.md + notify-kf-cpto.yml — Plan 01-03 (repo_enum.py) can scan `repos-local/` membership as the realized allowlist (REPO-01 contract).
- Clones are full, so Phase 2 activity mining has git history available.

## Self-Check: PASSED
- FOUND: .claude/skills/activity-sync/bootstrap.py
- FOUND commit: 304454c (bootstrap.py creation)
- FOUND commit: b3b356b (3.9-compat fix)

---
*Phase: 01-repo-access-foundation*
*Completed: 2026-06-04*
