# Plan: Adopt Open Knowledge Format (OKF) conventions — additive bundle emitter

## Context

**The question:** Is there value in Google's Open Knowledge Format (OKF), and if so how do we bring it in?

**OKF, briefly** ([spec v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)): an open standard for representing internal knowledge as a *directory of markdown files with YAML frontmatter*, cross-linked into a directed graph, so any agent can consume it without bespoke parsing. Required frontmatter: only `type`. Recommended: `title`, `description`, `resource`, `tags`, `timestamp`. Reserved files `index.md` (progressive disclosure) and `log.md` (change history). Cross-links are ordinary markdown links (absolute bundle-relative `/path.md` preferred); consumers compute backlinks. It is deliberately minimal — "no new runtime, no SDK required."

**Why it's worth doing here:** kf-cpto is *already* an OKF producer in all but name — every input/output is markdown + YAML frontmatter (`kanban.md`, `docs/_projects/*.md`, GSD `STATE.md`), and cross-links already exist (`depends_on` frontmatter drives the dependency graph). The concrete pain this addresses:
1. **Agent context-assembly** — activity-sync (and Claude) re-parse scattered kanban/GSD/plan data every run. OKF is *designed* for exactly this: one shared, cross-linked substrate.
2. **The LOE effort gotcha** (person-days in `kanban.md` vs working-day span in `gantt.yml`) becomes a single `type: Metric` concept that defines the metric once — killing a recurring source of confusion.
3. **Board↔GSD drift** (hand-reconciled earlier) becomes machine-readable: a project concept links its migration tasks to its GSD delivery state.

**Honest limits (why scope is deliberately small):** OKF is a *representation* format, not a sync engine — it will not fix drift by itself (reconcile.py / generate_kanban.py still own that). It is v0.1. The agent-*serving* payoff (Google Cloud Knowledge Catalog / BigQuery) needs GCP infra we don't have.

**Decision (user):** **Bundle only — additive, no third-party dependency (explicitly NO Google Cloud Knowledge Catalog).** Learn from the conventions and emit a conformant bundle as a new generated artifact, consumable by our own agents and the OKF *self-contained* static visualizer, committed to the repo like every other generated doc.

## Recommended approach

Add a new **OKF bundle emitter** to the aggregator stage that transforms *already-parsed* project data + canonical intermediates into a conformant `docs/okf/` bundle. Pure additive: no existing output changes, no new CI step, no runtime dependency, no second parser (per CLAUDE.md).

### Bundle structure (`docs/okf/`)

```
docs/okf/
├── index.md                 # root; only file allowed frontmatter in index: okf_version: "0.1"
├── log.md                   # change history; ISO YYYY-MM-DD headings, **Update** entries
├── projects/
│   ├── index.md             # progressive-disclosure list of project concepts
│   └── {project}.md         # type: Project — one per tracked repo (6)
├── metrics/
│   ├── index.md
│   ├── loe.md               # type: Metric — DEFINES person-days vs working-day span
│   └── status-rag.md        # type: Metric — RAG status colour semantics
└── milestones/
    ├── index.md
    └── {milestone}.md       # type: Milestone — from calendar.yml (M1..M6)
```

- **`projects/{project}.md`** — frontmatter `type: Project`, `title`, `description`, `resource` (GitHub repo / dashboard project-page URL), `tags` (from kanban `tags`), `timestamp` (source `last_updated`, NOT run time — mirrors the auto_blocks no-churn rule). Additive extra keys allowed: `po`, `lead`, `sprint`. Body: LOE rollup table, task table (task/assignee/effort/status), a **Dependencies** section cross-linking `depends_on` targets as `[dep](/projects/dep.md)`, and a link to `/metrics/loe.md` for effort semantics.
- **`metrics/loe.md`** — the highest-value doc: defines LOE = person-days (`Nd`) as declared in kanban, contrasts with `gantt.yml` `effort_days` = inclusive working-day span, and notes the discipline-split "no double-counting" rule.
- **`milestones/{milestone}.md`** — `type: Milestone`, name + date from `calendar.yml`.
- **Conformance:** every non-`index`/`log` file has parseable frontmatter with non-empty `type`; links are absolute bundle-relative; `index.md`/`log.md` carry no frontmatter (except root `okf_version`). Content stays deterministic (no run-timestamps in bodies) to avoid diff churn.

### Implementation

- **New module `scripts/okf_export.py`** with `generate_okf_bundle(all_project_data, loe_rows, calendar_data, base_dir)`. Pure transform of in-memory data — **reuses**, never re-parses:
  - `all_project_data` from `utils.load_all_project_data()` (already parsed frontmatter + tasks)
  - `build_loe_rows()` output for effort/status rollups — [aggregator.py:786](scripts/aggregator.py#L786)
  - `depends_on`, `tags`, `po`, `lead` from `utils.normalize_frontmatter()` — [utils.py:387](scripts/utils.py#L387)
  - milestones from `docs/_data/calendar.yml`
  - status canonicalization via `utils.canonicalize_status()`; reuse project-name slug convention used for `docs/_projects/{project}.md`
- **Emit point:** call it from `aggregator.main()` alongside the other `generate_*` calls (~[aggregator.py:1099](scripts/aggregator.py#L1099)), where all project data and `loe_rows` are already in memory. The existing "commit unified docs" CI step picks up `docs/okf/` automatically — **no new workflow step**.
- **Jekyll:** add `okf/` to the `exclude` list in [docs/_config.yml](docs/_config.yml) so the bundle ships as raw markdown (committed + on gh-pages) without Jekyll processing it as site pages.
- **Health (optional):** record `okf_file_count` on the `aggregator` section via `utils.update_sync_status()` — [utils.py:519](scripts/utils.py#L519).

### Optional enrichments (additive, recommend including #1)

1. **GSD delivery bridge** — if `repos/{project}/.planning/STATE.md` exists, read its frontmatter (`milestone`, `progress.percent`) and add a "Delivery (GSD)" line to the project concept. Small YAML read (not a kanban parser); directly surfaces the board↔GSD drift as machine-readable data. Fully defensive (most repos have none).
2. **Conformance validator `scripts/validate_okf.py`** — asserts every concept file has non-empty `type` and links resolve; wire into CI next to `validate_auto_blocks.py` as a soft gate.

### Explicitly out of scope

- Google Cloud Knowledge Catalog / GCS ingestion, BigQuery, any GCP footprint (would reintroduce the third-party dependency the user rejected).
- Per-task concept files (112 of them) — start at project granularity; revisit only if agents need task-level addressing.
- Replacing the Mermaid dependency graph — the OKF cross-links are *additive*; the existing graph stays.

## Verification

1. Run the aggregator locally against the current clones: `python scripts/aggregator.py`, then inspect the tree: `find docs/okf -name '*.md'`.
2. **Conformance:** every concept file has a `type:` — e.g. `grep -L '^type:' docs/okf/{projects,metrics,milestones}/*.md` returns nothing (excluding index/log); cross-links resolve to existing files; `depends_on` edges appear as links in the relevant `projects/*.md`.
3. **Metric doc:** `docs/okf/metrics/loe.md` clearly states person-days vs working-day span.
4. **No regressions:** existing outputs (`loe.yml`, `unified-kanban.md`, dependency graph, Sheets export) are byte-unchanged except the new `docs/okf/` tree; `bundle exec jekyll build` in `docs/` still succeeds with `okf/` excluded.
5. **Real OKF consumer (read-only eval, no project dependency):** run the reference *self-contained* visualizer from `GoogleCloudPlatform/knowledge-catalog/okf` over `docs/okf/` to confirm the graph + backlinks render — validates conformance against an independent implementation without adding anything to our stack.
