---
phase: quick-260708-etg
plan: 01
subsystem: dashboard-viz
tags: [okf, cytoscape, force-directed, constellation, labels-on-demand]
dependency_graph:
  requires: [260708-d8j]
  provides: [OKF-VIZ-CONSTELLATION]
  affects: [docs/okf-graph.md]
tech_stack:
  added: []
  patterns: [labels-on-demand, constellation-layout, contains-edges-as-real-edges]
key_files:
  created: []
  modified:
    - docs/okf-graph.md
decisions:
  - "Constellation over compound: removed compound nesting entirely; contains edges rendered as real cytoscape edges so the radiating-spoke topology is explicit in the graph structure, not inferred from parent-child nesting."
  - "Labels-on-demand via .show-label class: text-opacity:0 on Task nodes by default; class toggled by mouseover/mouseout, click neighbourhood highlight, and search match. Clean CSS class approach avoids style re-application on every event."
  - "Pure front-end rework: okf_graph.json already carried parent on all 112 task nodes and required zero changes. This was confirmed from commit 6be0a4f data — 126 nodes, 117 edges (112 contains + 5 depends). Python emitters untouched."
metrics:
  duration: 12m
  completed: 2026-07-08
---

# Phase quick-260708-etg Plan 01: OKF Graph Constellation Rework Summary

Force-directed constellation OKF visualizer: compound boxes removed, contains edges rendered as real radial lines from hub nodes, task labels hidden until hover/click/search.

## What Was Built

Reworked `docs/okf-graph.md` from a compound-box fcose layout (cluttered, 112 overlapping task labels) into a legible force-directed constellation:

- **Compound nesting removed.** The `d.parent = n.parent` assignment is gone. Task nodes are free-floating in the graph. The `node[type="Project"]` compound-container style block (translucent box, padding, top-valign label) is deleted entirely.
- **`contains` edges now rendered.** The `if (e.kind === 'contains') return;` skip is removed. All 112 project-to-task edges are passed to cytoscape as real edges. A new `edge[kind="contains"]` style makes them thin neutral grey lines (`#d1d5db`, opacity 0.45, no arrow) distinct from the dashed blue `depends` cross-links.
- **Hub nodes enlarged.** Project, Metric and Milestone nodes render at 30px; Task nodes at 14px. Hub font-weight is bold; hub labels are always visible via the base `node` style.
- **Labels-on-demand.** `node[type="Task"]` gets `text-opacity: 0` by default. A `.show-label` class selector forces `text-opacity: 1`. The class is toggled in three places:
  - `mouseover` / `mouseout` on task nodes (hover reveal).
  - `tap node` handler: adds `.show-label` to task nodes in the closed neighbourhood; removes it from nodes outside the neighbourhood.
  - Search handler: adds `.show-label` to matching task nodes; clears it when the query is blank.
  - Background `tap` handler: clears `.show-label` alongside `faded`/`highlighted` reset.
- **Nesting-factor control removed.** The `#okf-nesting` slider label block removed from the toolbar HTML. `nestingSlider`, `nestingVal`, `getNesting()`, and `nestingFactor: nest` removed from JS. The `nest` variable is gone.
- **Layout select first option** updated from `fcose (compound)` to `fcose`.
- **Intro prose updated.** Describes Projects/Metrics/Milestones as hub nodes; `contains` edges as real radial lines; task labels as labels-on-demand.

## Data Verification Note

`docs/_data/okf_graph.json` required **zero changes**. Commit 6be0a4f already added `parent` fields to all 112 task nodes. The JSON carries 126 nodes (6 Project + 112 Task + 6 Milestone + 2 Metric) and 117 edges (112 `contains` + 5 `depends`). This was a pure front-end rework — no Python emitters, no okf_graph.json, no other files were touched.

## Preserved Functionality

All of the following were preserved exactly as-is:
- Jekyll `{{ site.data.okf_graph | jsonify }}` injection
- CDN `<script>` tags (cytoscape 3.30.2, layout-base, cose-base, cytoscape-fcose)
- `minZoom: 0.15` / `maxZoom: 4`
- Info panel click handler with URL, label, type, status display and `escHtml` sanitizer
- Search input with `search-dim` fade behaviour
- 4 type-filter checkboxes (Project, Task, Metric, Milestone)
- Node repulsion slider and "Re-run layout" button
- Full layout option list (fcose, cose, concentric, breadthfirst, grid, circle)
- `nodeColor` and `nodeBorder` colour functions (status colours for tasks, type colours for hubs)

## Automated Verifications

Both plan grep gates passed:

**Task 1 gate:**
- `kind.*contains` present in edges rendering path: PASS
- `if (e.kind === 'contains') return` absent: PASS
- `d.parent = n.parent` absent: PASS
- `selector: node[type = "Project"]` compound style absent: PASS

**Task 2 gate:**
- `show-label` present: PASS
- `mouseover` present: PASS
- `nesting` (case-insensitive) absent: PASS
- `fcose (compound)` absent: PASS
- `compound containers` (case-insensitive) absent: PASS

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 + 2 | Force-directed constellation rework (both tasks committed atomically) | a9373d3 |

## Deviations from Plan

None — plan executed exactly as written. The word "nesting" appeared in an internal comment during drafting and was reworded to "constellation layout" to satisfy the plan's verification gate (which checks the entire file case-insensitively).

## Known Stubs

None.

## Threat Flags

None — pure front-end rendering change; no new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- `docs/okf-graph.md` modified: confirmed (commit a9373d3, 1 file changed, 65 insertions, 46 deletions).
- Commit a9373d3 exists: confirmed.
- `docs/_data/okf_graph.json` unmodified: confirmed (only `docs/okf-graph.md` in the diff).
- No other tracked files staged or committed.

## Status

Stopped at Task 3 (checkpoint:human-verify) — awaiting manual Jekyll preview.
