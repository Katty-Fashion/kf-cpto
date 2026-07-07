---
phase: quick
plan: 260707-lrl
subsystem: okf-bundle
tags: [okf, knowledge-format, aggregator, validator, deterministic]
dependency_graph:
  requires: [scripts/aggregator.py, scripts/utils.py, docs/_data/calendar.yml, docs/_data/loe.yml]
  provides: [scripts/okf_export.py, scripts/validate_okf.py, docs/okf/]
  affects: [scripts/aggregator.py, docs/_config.yml, docs/_data/sync_status.yml]
tech_stack:
  added: []
  patterns: [okf-v0.1, pure-transform, gsd-delivery-bridge, defensive-yaml-read]
key_files:
  created:
    - scripts/okf_export.py
    - scripts/validate_okf.py
    - docs/okf/ (19 files)
  modified:
    - scripts/aggregator.py
    - docs/_config.yml
decisions:
  - OKF links to depends_on targets outside tracked repo set rendered as plain text (not broken links)
  - _quote_scalar() handwritten instead of yaml.dump to avoid ... document-end marker churn
  - known_projects set passed into _gen_project_concept to guard cross-links at generation time
metrics:
  duration: ~25 minutes
  completed: "2026-07-07"
  tasks_completed: 3
  files_created: 21
  files_modified: 2
---

# Quick Task 260707-lrl: OKF Bundle Emitter — Summary

OKF v0.1 conformant bundle emitter added as a pure additive output of the aggregator pipeline. 19 markdown files generated at `docs/okf/`, consumed by agents and the OKF self-contained visualizer without any new runtime dependency.

## What Was Built

### scripts/okf_export.py (new)

`generate_okf_bundle(all_project_data, loe_rows, calendar_data, base_dir) -> int`

Pure transform of already-parsed in-memory data. Never re-parses `kanban.md`. Generates:

- `okf/index.md` — root with `okf_version: "0.1"`, effort summary table, section links
- `okf/log.md` — change history derived from source `last_updated` dates (deterministic)
- `okf/projects/index.md` + `okf/projects/{slug}.md` (6 files) — `type: Project` concepts with LOE rollup, task table, dependencies, GSD delivery bridge
- `okf/metrics/index.md` + `okf/metrics/loe.md` + `okf/metrics/status-rag.md` — metric definitions
- `okf/milestones/index.md` + `okf/milestones/{slug}.md` (6 files) — M1-M6 from `calendar.yml`

**GSD delivery bridge:** reads `.planning/STATE.md` YAML frontmatter from each repo defensively; surfaces `milestone` and `progress.percent` in the project concept. Only `kf-platform` has a STATE.md; the other five repos produce no Delivery section (correct fallback).

### scripts/aggregator.py (modified)

Added import of `generate_okf_bundle` and call after `write_gantt_yaml()`. Records `okf_file_count=19` into `update_sync_status("aggregator", ...)`.

### docs/_config.yml (modified)

Added `okf/` to the `exclude:` list so the bundle ships as committed raw markdown without Jekyll processing it as site pages.

### scripts/validate_okf.py (new)

Mirrors `validate_auto_blocks.py` idiom. Asserts:
- Every non-index/log `.md` under `docs/okf/` has parseable YAML frontmatter with non-empty `type`
- Every absolute bundle-relative link (`/...md`) resolves to an existing file

Returns 1 on any violation, 0 when clean.

## Verification Outputs

**Aggregator run:**
```
Generated OKF bundle: 19 files -> docs/okf/
KF Aggregator — Done!
```

**Validator:**
```
Checked 19 OKF markdown files (14 concepts, 5 exempt index/log).
OKF bundle is conformant.
```

**Determinism re-run:** `git status --porcelain docs/okf/` is empty after a second aggregator run. No churn.

**Conformance grep:** `grep -rL '^type:' docs/okf/projects/*.md docs/okf/metrics/*.md docs/okf/milestones/*.md` returns only the three `index.md` files, which are exempt per OKF spec.

**No regressions:** Existing `loe.yml`, `unified-kanban.md`, `dependency-graph.md`, and `_projects/*.md` regenerate normally. `docs/okf/` is the only new untracked tree.

## Commits

| Hash | Type | Description |
| --- | --- | --- |
| dc8e943 | feat | OKF emitter (okf_export.py) + aggregator hook + _config.yml |
| 0c897f1 | feat | OKF conformance validator (validate_okf.py) |
| e5a3059 | chore | Generated initial OKF bundle (19 files) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _safe_yaml_str using yaml.dump caused YAML document-end markers**
- **Found during:** First validator run (all project concept files failed frontmatter parse)
- **Issue:** `yaml.dump()` emits `...` document-end markers for strings containing dots (URLs). This broke YAML frontmatter parsing in validate_okf.py.
- **Fix:** Replaced with `_quote_scalar()` — a hand-written YAML scalar quoter that uses double-quoted form only when needed, never emits `...`.
- **Files modified:** scripts/okf_export.py

**2. [Rule 1 - Bug] projects/index.md linked to /{slug}.md instead of /projects/{slug}.md**
- **Found during:** First validator run (all six project links were broken)
- **Issue:** `_gen_projects_index()` emitted `/{slug}.md` paths, which resolve to `okf/{slug}.md` (non-existent). Files actually live at `okf/projects/{slug}.md`.
- **Fix:** Changed link format to `/projects/{slug}.md` in `_gen_projects_index()`.
- **Files modified:** scripts/okf_export.py

**3. [Rule 2 - Missing critical functionality] depends_on cross-links to untracked repos caused broken links**
- **Found during:** First validator run (`nuoform` dependency not in tracked repo set)
- **Issue:** `kf-platform`, `kf-be-platform`, `kf-fe-platform` declare `depends_on: [nuoform]`, but `nuoform` is not in the tracked repo allowlist and has no concept file.
- **Fix:** Added `known_projects` set parameter to `_gen_project_concept()`. Deps in the set get hyperlinks; deps outside the set render as plain text with `_(not in tracked repo set)_`.
- **Files modified:** scripts/okf_export.py

## CI Wiring Note

`validate_okf.py` is not wired into `aggregate.yml` yet. To add it, insert a step alongside the `validate_auto_blocks.py` step:

```yaml
- name: Validate OKF bundle
  run: python scripts/validate_okf.py
```

The script is CI-ready (hard gate, exits 1 on any conformance violation). Deliberately left for a follow-on commit as the plan notes uncertainty about workflow editing scope.

## Known Stubs

None. All project concepts are wired to real LOE data from `loe_rows`. The `depends_on` untracked-repo case is documented as plain text, not a stub.

## Threat Flags

None. `docs/okf/` is excluded from Jekyll processing and introduces no new network endpoints, auth paths, or trust boundaries. All content is derived from already-public repo data.

## Self-Check

Files created:
- [x] /Users/machina/Dev/kf-cpto/scripts/okf_export.py
- [x] /Users/machina/Dev/kf-cpto/scripts/validate_okf.py
- [x] /Users/machina/Dev/kf-cpto/docs/okf/ (19 files)

Commits:
- [x] dc8e943 feat(260707-lrl): add OKF v0.1 bundle emitter
- [x] 0c897f1 feat(260707-lrl): add OKF conformance validator
- [x] e5a3059 chore(260707-lrl): generate initial OKF bundle (19 files)

## Self-Check: PASSED
