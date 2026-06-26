---
phase: quick-260626-b6m
plan: "01"
subsystem: aggregator
tags: [dashboard, aggregator, mermaid, sidebar]
dependency_graph:
  requires: []
  provides: [agile-sprints.md, lowercase-project-links, effort-by-project-pie]
  affects: [scripts/aggregator.py, docs/_includes/sidebar.html]
tech_stack:
  added: []
  patterns: [list+join line builder, mermaid pie/gantt generators, _md_cell escaping]
key_files:
  modified:
    - scripts/aggregator.py
    - docs/_includes/sidebar.html
decisions:
  - "Per-project effort visibility consolidated to the aggregated Calendar view only (no redundant per-project pie)"
  - "Agile Sprints page uses the same ISO-date gate (_ISO_DATE_RE) as the unified kanban gantt"
  - "Zero-effort projects silently omitted from pie (not an error — placeholder repos with no tasks)"
metrics:
  duration: "~8 min"
  completed: "2026-06-26T00:00:00Z"
  tasks_completed: 4
  files_modified: 2
---

# Phase quick-260626-b6m Plan 01: Dashboard Fixes + Agile Sprints Summary

**One-liner:** Lowercase Jekyll project link hrefs (fix 404s), remove Effort-by-Assignee table, replace static CPTO pie with a computed per-project effort pie, and add a new Agile Sprints page (sprint timeline gantt + summary table with TOTAL row) wired into sidebar nav.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Lowercase /projects/:name/ link paths | ac31fd7 | scripts/aggregator.py |
| 2 | Remove Effort by Assignee from generate_loe_report | ac31fd7 | scripts/aggregator.py |
| 3 | Effort-per-project pie on calendar; drop per-project effort pie | ac31fd7 | scripts/aggregator.py |
| 4 | New Agile Sprints page wired into pipeline + sidebar | ac31fd7 | scripts/aggregator.py, docs/_includes/sidebar.html |

## Changes Made

### T1 — Lowercase project link paths (fix 404s)

- `_render_kanban_board` (line ~108): changed `proj=project` to `proj=project.lower()` in the Liquid href template. Visible card label `escaped_project` keeps original case.
- `generate_project_page` deps_display (line ~342): changed `'/projects/{d}/'` to `'/projects/{d.lower()}/'` using an f-string expression. `[{d}]` visible label stays original case. `builder_link ?project=` unchanged.

### T2 — Remove Effort by Assignee

Deleted the entire block after the `**Total**` row in `generate_loe_report`: blank line, `## Effort by Assignee` header, table header/separator, `assignee_data` aggregation dict+loop, and row-emitting loop (~24 lines removed). Function now returns immediately after the Total row.

### T3 — Computed pie + drop per-project pie

**A — generate_unified_calendar:** Removed the static `> CPTO 50h Monthly Allocation` blurb and the `pie title Alocarea Lunara 50 Ore — CPTO KF` block with 6 hardcoded slices. Replaced with a pre-computation block that sums per-project effort, filters zero-effort projects, sorts descending by total, and emits `pie title Effort by Project (person-days)` with one `"project" : N` slice per non-zero project using `mermaid_label_safe`. The Sprint Calendar gantt section is unchanged.

**B — generate_project_page:** Deleted the `effort_by_status` aggregation dict, `if effort_by_status:` block, `## Effort Distribution` header, and `pie title Effort by Status` fence (~16 lines removed). Sprint Timeline gantt and all other sections intact.

### T4 — generate_agile_sprints + wiring + sidebar

Added `def generate_agile_sprints(data: dict) -> str:` between `generate_loe_report` and `generate_project_page`. Builds:
- YAML frontmatter with `title: Agile Sprints`
- `## Sprint Timeline` mermaid gantt: ISO-date gated per-project sections with `section {mermaid_gantt_label(project)}` + `:active` bar; header always emitted
- `## Sprint Summary` table: per-project row with sprint, window (raw meta values → `_md_cell`), total effort, % done; portfolio TOTAL row with bold formatting

Wired into `main()` after dependency-graph write. Added Agile Sprints `<li>` in `docs/_includes/sidebar.html` after the Migration Gantt entry, mirroring the same indentation and `aria-current="page"` pattern.

## Verification Results

All checks passed:

```
T1 OK   — kanban href /projects/r3-aas/; visible R3-AAS:; deps href /projects/kf-platform/; ?project=R3-AAS unchanged
T2 OK   — Effort by Assignee absent; ## Summary by Project + **Total** present
T3 OK   — pie title Effort by Project present; kf-platform(5) before R3-AAS(3); empty(0) skipped; ## Sprint Calendar intact; no Effort by Status / Effort Distribution
T4 OK   — title: Agile Sprints; mermaid gantt; ## Sprint Summary; **TOTAL**; section R3-AAS
T4 wiring OK — agile-sprints.html in sidebar; DOCS_DIR / "agile-sprints.md" in aggregator
AST parse OK — python -c "import ast; ast.parse(...)" clean
```

## Deviations from Plan

None — plan executed exactly as written. All 4 tasks implemented and verified in one commit (tasks are purely additive/subtractive with no shared state conflicts).

## Known Stubs

None.

## Threat Flags

None. No new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- [x] scripts/aggregator.py modified (2 files changed, 90 insertions, 49 deletions)
- [x] docs/_includes/sidebar.html modified
- [x] Commit ac31fd7 exists on branch worktree-agent-a62a46ec51faf4b79
- [x] All T1/T2/T3/T4 verification snippets return OK
- [x] AST parse clean
