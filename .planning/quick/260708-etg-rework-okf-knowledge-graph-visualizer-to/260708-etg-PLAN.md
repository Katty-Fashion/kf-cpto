---
phase: quick-260708-etg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/okf-graph.md
autonomous: false
requirements: [OKF-VIZ-CONSTELLATION]
must_haves:
  truths:
    - "Graph renders as a force-directed node-link constellation — no compound boxes"
    - "Every project hub has its tasks radiating out via visible `contains` edges"
    - "Task labels are hidden by default and appear on hover, click, or search match"
    - "Project / Metric / Milestone labels are always visible (~14 hubs)"
    - "Hub nodes read larger than task nodes"
    - "Search, 4 type-filter checkboxes, info panel with click-to-open-URL, and layout/repulsion/re-run controls all still work"
  artifacts:
    - path: "docs/okf-graph.md"
      provides: "Force-directed constellation OKF visualizer"
      contains: "show-label"
  key_links:
    - from: "docs/okf-graph.md"
      to: "docs/_data/okf_graph.json"
      via: "Jekyll jsonify injection"
      pattern: "site\\.data\\.okf_graph \\| jsonify"
    - from: "GRAPH.edges contains items"
      to: "cytoscape edges"
      via: "rendered as real edges (no longer skipped)"
      pattern: "kind.*contains"
---

<objective>
Rework the OKF knowledge-graph visualizer at `docs/okf-graph.md` so it renders as a force-directed node-link "constellation" instead of the current fcose COMPOUND-BOX layout. The user rejected the compound-box version as cluttered — boxes with 112 overlapping task labels became unreadable soup.

Purpose: Make the graph legible. Projects become normal hub nodes (not containers), `contains` edges become visible lines so tasks radiate from their hub, and task labels are hidden until hover/click/search (labels-on-demand).

Output: An updated `docs/okf-graph.md`. This is a pure front-end (docs-only) change — the graph JSON and all Python emitters are untouched.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
@docs/okf-graph.md

<data_verified>
Confirmed against `docs/_data/okf_graph.json` (no changes needed to it — commit 6be0a4f already added `parent`):
- 126 nodes: 6 Project + 112 Task + 6 Milestone + 2 Metric.
- ALL 112 Task nodes carry a `parent` field pointing to their project node id (e.g. `/projects/kf-be-platform.md`). r3-aas has the most tasks.
- 117 edges: 112 `contains` (project → task) + 5 `depends` (project → project).
- Always-visible hubs = 6 Project + 6 Milestone + 2 Metric = 14 nodes. The remaining 112 (Task) get labels-on-demand.

This means the rework is docs-only: do NOT edit `okf_graph.json`, `scripts/okf_export.py`, or any Python. Note this verification in the SUMMARY.
</data_verified>

<current_behavior>
The current `docs/okf-graph.md` (the file being reworked):
- Assigns `d.parent = n.parent` so tasks nest inside Project compound containers (`elements` build loop, ~line 137).
- SKIPS `contains` edges entirely: `if (e.kind === 'contains') return;` (~line 144) — only `depends` edges are drawn.
- Has a `node[type = "Project"]` compound-container style block (translucent box, top-aligned label, border-radius, padding) (~lines 214-232).
- Layout select first option reads `fcose (compound)` (~line 37); has a "Nesting factor" range (`#okf-nesting`, ~lines 51-56) wired into `buildLayoutOpts` via `nestingFactor: nest`.
- Base `node` style always shows `label: 'data(label)'` for every node (~line 239).
- Intro prose says "Projects are compound containers; their tasks are nested inside" and "`contains` edges are replaced by compound nesting" (~lines 10, 12).
</current_behavior>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Convert to force-directed constellation — drop compounds, restore contains edges, resize hubs</name>
  <files>docs/okf-graph.md</files>
  <action>
Edit `docs/okf-graph.md` to remove compound nesting and render real `contains` edges:

1. In the elements build loop, DROP the `d.parent` assignment (remove `if (n.parent) d.parent = n.parent;`). Task nodes must no longer nest — they become free-floating nodes. Do not read `n.parent` at all.

2. In the edges build loop, REMOVE the `if (e.kind === 'contains') return;` skip so `contains` edges (project → task) are now rendered as real cytoscape edges alongside `depends` edges. Keep the existing edge `data` shape (id/source/target/kind).

3. DELETE the `node[type = "Project"]` compound-container style block entirely (the translucent-box style with `padding`, `border-radius`, top-valign label). Projects now use the generic node style like every other hub.

4. In the base `node` style, size hubs larger than tasks: set `width`/`height` via a function returning a larger radius (e.g. ~30) for Project/Metric/Milestone and a smaller radius (e.g. ~14) for Task. Keep the existing `nodeColor` / `nodeBorder` colour functions untouched (status colours for tasks, type colours for hubs).

5. Add a style selector for `contains` edges so they read as thin neutral radial lines distinct from the dashed blue `depends` edges — e.g. a solid light-grey line, low opacity, small/no arrow. Keep the existing `edge[kind="depends"]` dashed-blue style.

Do NOT touch: the Jekyll `{{ site.data.okf_graph | jsonify }}` injection, the CDN `<script>` tags (cytoscape + fcose + layout-base + cose-base), `minZoom`/`maxZoom`, the info-panel click handler, the search input, or the 4 type-filter checkboxes. Do NOT edit any file other than `docs/okf-graph.md`.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && grep -qi "kind.*contains" docs/okf-graph.md && ! grep -q "if (e.kind === 'contains') return" docs/okf-graph.md && ! grep -q "d.parent = n.parent" docs/okf-graph.md && ! grep -q 'selector: .node\[type = "Project"\]' docs/okf-graph.md && echo PASS</automated>
  </verify>
  <done>Compound nesting removed (no `d.parent`, no Project compound style), `contains` edges rendered, hub nodes sized larger than task nodes. Graph JSON and Python untouched.</done>
</task>

<task type="auto">
  <name>Task 2: Labels-on-demand + layout controls cleanup + intro prose</name>
  <files>docs/okf-graph.md</files>
  <action>
Continue editing `docs/okf-graph.md` for labels-on-demand and control/prose cleanup:

1. LABELS-ON-DEMAND. In the base `node` style, keep `label: 'data(label)'` ONLY for hubs and hide it for tasks. Implement by:
   - Adding a style selector `node[type = "Task"]` that sets `text-opacity: 0` (task labels hidden by default). Hubs (Project/Metric/Milestone) keep the label visible via the base style.
   - Adding a `.show-label` class selector that forces `text-opacity: 1` (this reveals a task label when toggled).
   - In JS, on cytoscape `mouseover` of a task node, add `.show-label`; on `mouseout`, remove it (only for Task-type nodes — hubs are always shown so no toggle needed).
   - In the existing click/highlight handler: when a node is highlighted, add `.show-label` to its closed neighbourhood's task nodes so clicked constellations reveal their labels; clear `.show-label` on background tap alongside the existing `faded`/`highlighted` reset (except leave hover-driven labels alone by design — the mouseout handler manages those).
   - In the search handler: when a task label matches the query, add `.show-label` to that node; when the search is cleared, remove `.show-label` from task nodes that aren't otherwise revealed. Keep the existing `search-dim` fade behaviour.

2. LAYOUT CONTROLS. Update the layout `<select>` first option text from `fcose (compound)` to just `fcose` (keep `value="fcose"`, keep it `selected` as default). Since compounds are gone, the "Nesting factor" control is inert — REMOVE the `#okf-nesting` slider label block from the toolbar AND remove its wiring: delete `nestingSlider`/`nestingVal`/`getNesting()` references and drop `nestingFactor: nest` (and the `nest` var) from the fcose branch of `buildLayoutOpts`. Keep the "Node repulsion" slider, the "Re-run layout" button, and the full layout option list. fcose stays the default layout and works fine as a plain (non-compound) force-directed layout with `nestingFactor` gone.

3. INTRO PROSE. Update the two intro lines near the top:
   - "**Node types:**" — remove "compound containers / nested inside"; describe Projects/Metrics/Milestones as hub nodes and tasks as nodes connected to their project hub. Mention that task labels appear on hover/click/search (labels-on-demand), while hub labels are always shown. Use `[LABEL]`-style text pills only if introducing new pill terms — otherwise plain prose per project no-emoji convention.
   - "**Edge kinds:**" — state that `contains` edges (project → task) are now rendered as real edges radiating from each hub, and `depends` edges (project → project) are dashed cross-links. Remove "replaced by compound nesting".

Do NOT edit any file other than `docs/okf-graph.md`.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && grep -q "show-label" docs/okf-graph.md && grep -q "mouseover" docs/okf-graph.md && ! grep -qi "nesting" docs/okf-graph.md && ! grep -q "fcose (compound)" docs/okf-graph.md && ! grep -qi "compound containers" docs/okf-graph.md && echo PASS</automated>
  </verify>
  <done>Task labels hidden by default, revealed on hover/click/search via `.show-label`; hubs always labelled. Nesting-factor control fully removed. Layout label reads "fcose". Intro prose updated to describe real `contains` edges and labels-on-demand.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
Reworked `docs/okf-graph.md` into a force-directed constellation: compound boxes removed, `contains` edges rendered as real radial lines, hubs enlarged, and task labels hidden until hover/click/search. Nesting-factor control removed; intro prose updated. Graph JSON and Python emitters untouched (verified: all 112 tasks already carry `parent`, 112 `contains` + 5 `depends` edges).
  </what-built>
  <how-to-verify>
Preview the Jekyll site locally and inspect the graph:

1. From the repo, serve the site: `cd docs && bundle exec jekyll serve` (or your usual preview command), then open the "Knowledge Graph" page (`/kf-cpto/okf-graph/`).
2. Confirm the graph renders as a force-directed constellation of dots — NO translucent project boxes. Each project hub should have its tasks radiating out via visible thin lines (`contains` edges).
3. Confirm only ~14 labels are visible at rest (the 6 Project + 6 Milestone + 2 Metric hubs). Task dots should have NO labels by default — the "label soup" is gone.
4. Hover a task dot: its label should appear, then disappear on mouse-out.
5. Click a hub (e.g. r3-aas): its neighbourhood highlights, the surrounding task labels appear, and the info panel opens with a working external link.
6. Type in the search box: matching nodes stay bright, others dim, and matching task labels appear.
7. Confirm controls: Layout select first option reads "fcose" (not "fcose (compound)"), there is NO "Nesting factor" slider, and "Node repulsion" + "Re-run layout" still work.
  </how-to-verify>
  <resume-signal>Type "approved" if the constellation renders and labels-on-demand work, or describe what still looks wrong.</resume-signal>
</task>

</tasks>

<verification>
- `grep` gates in Task 1 and Task 2 pass (no compound artifacts, `contains` rendered, labels-on-demand present, nesting control removed).
- `docs/_data/okf_graph.json` unchanged (git diff shows no modification to it or any `scripts/*.py`).
- Human verification confirms the constellation renders legibly with labels-on-demand.
</verification>

<success_criteria>
- Graph renders as a force-directed constellation; no compound project boxes.
- `contains` edges visible; tasks radiate from their project hub.
- Task labels hidden by default; shown on hover, click-highlight, and search match.
- 14 hub labels always visible; hubs sized larger than tasks.
- Nesting-factor control gone; layout label reads "fcose"; repulsion + re-run + search + filters + info panel preserved.
- Only `docs/okf-graph.md` changed.
</success_criteria>

<output>
Create `.planning/quick/260708-etg-rework-okf-knowledge-graph-visualizer-to/260708-etg-SUMMARY.md` when done. Note in it that the graph JSON already contained `parent` on all task nodes and required no changes (pure front-end rework).
</output>
