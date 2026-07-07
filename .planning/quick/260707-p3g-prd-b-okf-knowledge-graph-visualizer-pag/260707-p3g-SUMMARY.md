---
phase: "quick"
plan: "260707-p3g"
subsystem: "okf-visualizer"
tags: [okf, cytoscape, knowledge-graph, jekyll, dashboard]
key-files:
  created:
    - scripts/okf_export.py (emit_okf_graph_json function added)
    - docs/okf-graph.md
    - docs/_data/okf_graph.json
  modified:
    - docs/_includes/sidebar.html
decisions:
  - Use Cytoscape UMD build from jsDelivr CDN (same pattern as Mermaid ESM); avoids npm build step
  - Nodes sorted by id, edges by (source, target, kind) — no timestamps; fully deterministic
  - emit_okf_graph_json called from generate_okf_bundle; not counted in OKF .md file count
  - breadthfirst layout (directed) chosen for ~135 nodes; spacingFactor 1.25 avoids overlap
metrics:
  duration: "~45 minutes"
  completed: "2026-07-07"
---

# Quick Task 260707-p3g: PRD B OKF Knowledge-Graph Visualizer

Interactive Cytoscape.js graph on the dashboard consuming an aggregator-emitted `okf_graph.json`; nodes coloured by type/status, searchable, type-filterable, click-to-highlight with external link panel.

## Commits

| Hash | Message | Files |
| --- | --- | --- |
| a62e140 | feat(260707-p3g): add okf_graph.json emitter to okf_export.py | scripts/okf_export.py |
| c5f65a5 | feat(260707-p3g): add okf-graph Jekyll page and sidebar nav link | docs/okf-graph.md, docs/_includes/sidebar.html |
| 4166415 | chore(260707-p3g): generate docs/_data/okf_graph.json | docs/_data/okf_graph.json |

## What Was Built

### 1. scripts/okf_export.py — emit_okf_graph_json()

New function added before `generate_okf_bundle`. Called at the end of `generate_okf_bundle` (after all OKF markdown files are written). Outputs `docs/_data/okf_graph.json`.

- **Nodes:** 135 total — 6 Projects, 121 Tasks, 2 Metrics (loe + status-rag), 6 Milestones
- **Edges:** 126 total — 5 `depends` edges (project→dependency), 121 `contains` edges (project→task)
- **Determinism:** nodes sorted by `id`, edges sorted by `(source, target, kind)`; no run-time timestamps
- **URLs:** Projects → dashboard project page; Tasks/Metrics/Milestones → GitHub blob URL under `docs/okf/`

### 2. docs/okf-graph.md — Jekyll page

- Cytoscape.js 3.30.2 UMD from jsDelivr CDN (`<script src="...cytoscape.umd.js">`)
- Graph data injected at Jekyll build time: `var GRAPH = {{ site.data.okf_graph | jsonify }};`
- Node colours: Project=blue (#2563eb), Metric=purple (#7c3aed), Milestone=teal (#0d9488), Task by status (Done=green, In Progress/Review=amber, other=grey)
- Project nodes rendered 28px, others 18px for visual hierarchy
- `breadthfirst` directed layout with `spacingFactor: 1.25`
- Search: case-insensitive substring filter dims non-matching nodes
- Type checkboxes: hide/show entire node type categories (edges involving hidden nodes also hidden)
- Click node: highlights closed neighbourhood, fades rest, shows label/type/status + external link in `#okf-info`
- Click canvas background: resets highlights
- `<style>` block defines `.okf-legend` colour swatches for the toolbar legend

### 3. docs/_includes/sidebar.html

Added `Knowledge Graph` link pointing to `/okf-graph.html` under the Views `<details>` block, after ALADIN Governance, with `aria-current="page"` when active.

## Verification Results

| Check | Result |
| --- | --- |
| `python scripts/aggregator.py` runs clean | PASS — "135 nodes, 126 edges" printed |
| `python -c "import json;json.load(open('docs/_data/okf_graph.json'))"` | PASS — valid JSON |
| Two aggregator runs byte-identical | PASS — `diff` empty on second run |
| `python scripts/validate_okf.py` exits 0 | PASS — "145 OKF markdown files... conformant" |
| `cd docs && bundle exec jekyll build` | PASS — built in 4.4 seconds, no errors |
| `docs/_site/okf-graph.html` contains Cytoscape CDN ref | PASS — 2 occurrences of "cytoscape" |
| `docs/_site/okf-graph.html` contains `id="okf-cy"` | PASS |

Jekyll warning noted: `faraday-retry` gem not installed (pre-existing; not introduced by this task).

## Deviations from Plan

None. Plan executed exactly as written. The Cytoscape UMD build (not ESM) was chosen upfront as the plan allowed either, and the UMD form works without `type="module"` so is simpler with the existing `<script>` tag pattern.

## Known Stubs

None. The graph JSON is fully populated from real kanban data on each aggregator run.

## Threat Flags

None. The page is a read-only static render of pre-built JSON. `jsonify` is Liquid's built-in escaper. No user input reaches the server; the search/filter is client-side only.

## Note: Visual Confirmation Requires a Browser

The graph interaction (pan/zoom, search highlight, click info panel) requires a real browser to verify. The Jekyll build confirmed the page exists and contains the required script tag and container div. First-load performance with 135 nodes on the `breadthfirst` layout should be fast; if the layout is too crowded the `cose` layout is an easy one-line swap.

## Self-Check: PASSED

- `docs/_data/okf_graph.json` — FOUND
- `docs/okf-graph.md` — FOUND
- `docs/_includes/sidebar.html` updated — FOUND (Knowledge Graph link present)
- Commits a62e140, c5f65a5, 4166415 — FOUND in git log
