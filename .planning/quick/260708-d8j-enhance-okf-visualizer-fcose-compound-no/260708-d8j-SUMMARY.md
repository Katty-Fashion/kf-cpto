---
id: 260708-d8j
title: Enhance OKF Visualizer — fcose Compound Layout + Controls
type: quick
branch: master
completed: 2026-07-08
commits:
  - hash: 6a9fb60
    message: "feat(260708-d8j): add parent field to task nodes in okf graph JSON"
    files: [scripts/okf_export.py]
  - hash: d16469d
    message: "feat(260708-d8j): fcose compound layout, viz selector and repulsion controls"
    files: [docs/okf-graph.md, docs/_data/okf_graph.json]
key-decisions:
  - "Skip 'contains' edges in the visualizer; compound nesting replaces them — avoids duplicate visual relationships"
  - "Compound project node style uses background-color with alpha (rgba) not a separate :parent selector for Cytoscape 3.x compatibility"
  - "Repulsion/nesting sliders update display values live via 'input' events; layout only re-runs on selector change or Re-run button click to avoid thrashing"
---

# Phase 260708-d8j Summary: OKF Visualizer — fcose Compound Layout + Controls

## One-liner

fcose compound layout with project-as-container nesting, adjustable repulsion/nesting sliders, and a six-option layout selector added to the OKF knowledge-graph visualizer.

## What Was Built

### Task 1 — `parent` field in graph JSON (`scripts/okf_export.py`)

Added `"parent": proj_id` to every Task node dict in `emit_okf_graph_json()` (line ~772).
Projects, Metrics, and Milestones remain top-level (no `parent` key). The `contains` edges
are preserved in the JSON for data completeness; the visualizer simply skips them.

### Task 2 — Enhanced visualizer (`docs/okf-graph.md`, `docs/_data/okf_graph.json`)

Three CDN UMD scripts added before the inline script block (mirroring the existing cytoscape.umd.js pattern):

```
https://cdn.jsdelivr.net/npm/layout-base/layout-base.js
https://cdn.jsdelivr.net/npm/cose-base/cose-base.js
https://cdn.jsdelivr.net/npm/cytoscape-fcose/cytoscape-fcose.js
```

A defensive `cytoscape.use(cytoscapeFcose)` call (try/catch) handles both auto-register and
explicit-register modes.

Element building now passes `data.parent` from the node JSON to Cytoscape so project nodes
become compound containers. `kind === "contains"` edges are skipped; only `depends` edges render.

Project compound nodes: `rgba(37,99,235,0.08)` background, `text-valign: top`, `padding: 12px`,
rounded border. Task children keep status colours (Done=green, In-Progress/Review=amber, Todo=grey).

Default layout: `fcose` with `nodeRepulsion: 4500`, `nestingFactor: 0.1`, `numIter: 2500`.

Control bar added above the graph canvas:
- `<select id="okf-layout">` — options: fcose (compound), cose, concentric, breadthfirst, grid, circle
- `<input id="okf-repulsion">` — range 500–20000, step 500, default 4500
- `<input id="okf-nesting">` — range 0–2, step 0.05, default 0.10
- "Re-run layout" button

All existing features preserved: text search, type-filter checkboxes, click-node info panel with external link.

## Verification Results

| Check | Result |
| :--- | :--- |
| `python scripts/aggregator.py` | Clean — 126 nodes, 117 edges |
| All task nodes carry `parent` field | 112 tasks with parent |
| Determinism (two consecutive runs produce identical output) | IDENTICAL |
| `python scripts/validate_okf.py` | Exit 0 — 145 files, bundle conformant |
| `bundle exec jekyll build` | Succeeded in ~3s |
| `layout-base` CDN script in built HTML | Found (1 match) |
| `cose-base` CDN script in built HTML | Found (1 match) |
| `cytoscape-fcose` CDN script in built HTML | Found (1 match) |
| `id="okf-layout"` selector in built HTML | Found (1 match) |
| `id="okf-repulsion"` input in built HTML | Found (1 match) |
| `id="okf-nesting"` input in built HTML | Found (1 match) |

Visual nesting/repulsion feel requires a browser to confirm — the fcose layout renders
compound nesting client-side at page load.

## Deviations from Plan

None. All changes implemented exactly as specified.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary changes. Only client-side CDN
scripts added (the same CDN host, jsdelivr, already used for Cytoscape, Pico CSS, and Mermaid).

## Self-Check

- [x] `scripts/okf_export.py` modified (parent field)
- [x] `docs/okf-graph.md` modified (fcose, controls, compound nesting)
- [x] `docs/_data/okf_graph.json` regenerated (112 tasks with parent)
- [x] Commit 6a9fb60 exists
- [x] Commit d16469d exists
