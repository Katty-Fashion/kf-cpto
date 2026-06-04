# Phase 4: Agentic Capacity Model - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning
**Mode:** Auto-generated (fast mode — requirements well-specified; discuss skipped under time constraint)

<domain>
## Phase Boundary

The aggregator computes per-discipline (FE/BE) demand vs. capacity in days, assigns over-capacity overflow to a synthetic `Agentic` assignee (humans stay pinned at 100%), and flows that Agentic overflow through the existing LOE pipeline (`loe.yml` → LOE report → Sheet) as a first-class row — replacing the migration-gantt §8.2 "add 0.5 FTE backend" recommendation with an agentic-deferral view. CAP logic lives in the aggregator (CI-side render), driven by the canonical kanban data; the skill's reconciliation/write-back from Phases 2–3 feeds corrected statuses upstream. Capacity-as-AUTO-block on migration-gantt (CAP-V2-01) is deferred to v2.

</domain>

<decisions>
## Implementation Decisions

### Capacity computation (CAP-01/03/04)
- Per-discipline FE/BE demand vs capacity denominated in **days**. Capacity baseline: raw **40h/week per FTE, no additional buffer**.
- A `FE+BE` shared task splits effort **50/50** across the FE and BE lanes (no double-counting); the sum of per-discipline totals must equal the sum of all task effort-days.
- Estimates already include a 20% buffer — do NOT double-buffer. Add constant `ESTIMATES_INCLUDE_20PCT_BUFFER = True` in `scripts/utils.py`.
- Discipline routing uses the existing kanban Owner/Assignee mapping already encoded in the data (per the out-of-scope rule: never infer FE/BE from branch names or commit metadata). The planner determines the exact discipline-derivation by reading `aggregator.py` / `utils.py`.

### Agentic assignee (CAP-02/05/06)
- Add constant `AGENTIC_ASSIGNEE = "Agentic"` in `scripts/utils.py`.
- Over-capacity overflow is assigned to the synthetic `Agentic` assignee while the human stays pinned at 100% capacity.
- The Agentic overflow appears as its **own row/slice** in the LOE outputs: `docs/_data/loe.yml`, the LOE report page, and (downstream) the Google Sheet LOE tab. When there is **no overflow, the Agentic row is absent**.
- An explicit **agentic ceiling** is a named constant (not a magic number). When overflow exceeds the ceiling, the output contains a visible `[WARN: agentic capacity exceeded — Xd unresolved]` entry.

### §8.2 replacement (CAP-07)
- The `docs/migration-gantt.md` §8.2 section no longer recommends "add 0.5 FTE backend"; it shows the **agentic-deferral view** with computed overflow (days/hours).

### Pipeline discipline (constraints)
- Extend `aggregator.build_loe_rows()` / `write_loe_yaml()` for the new Agentic field/row — never add a second kanban parser. Preserve the canonical-intermediate contract (`loe.yml`).
- `sheets_sync.py` reads `loe.yml` only (no re-parse); the Agentic row flows downstream automatically. Keep the Sheets exit-0 invariant.
- Determinism: CI renders; no dependency on the local skill at CI time.

### Claude's Discretion
- Exact module/function decomposition for the capacity calculator (likely a new function in `aggregator.py` or a small `capacity` helper), the ceiling constant's value, log/pill formatting (`[LABEL]` text pills, no emojis), and the loe.yml schema extension shape.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/aggregator.py` — `build_loe_rows()`, `write_loe_yaml()`, `generate_loe_report()`, `generate_unified_calendar()`; LOE row shape `{project, sprint, task, assignee, effort_days, start, end, status}`. Extend here.
- `scripts/utils.py` — `TASK_STATUSES`, effort parser (`Nd`), constants home for `AGENTIC_ASSIGNEE` and `ESTIMATES_INCLUDE_20PCT_BUFFER`.
- `docs/_data/loe.yml` — canonical intermediate (decouples parser from Sheets exporter).
- `docs/migration-gantt.md` — §8.2 prose to replace; carries AUTO blocks (do not disturb markers).
- `scripts/sheets_sync.py` — reads loe.yml; Agentic row flows downstream with no re-parse.

### Established Patterns
- snake_case, SCREAMING_SNAKE_CASE constants, `[LABEL]` text pills not emojis, type hints, list+join string building.
- LOE is the single canonical intermediate; one parser, one intermediate.

### Integration Points
- Upstream: kanban data (corrected by Phases 2–3). Downstream: LOE report (Pages) + Sheet (exit-0).
- CI renders deterministically; no skill dependency at CI time.

</code_context>

<specifics>
## Specific Ideas

- 50/50 split for FE+BE tasks; per-discipline totals must sum to total effort (no double-count) — verifiable from a logged capacity breakdown.
- Named ceiling constant + `[WARN: agentic capacity exceeded — Xd unresolved]` on breach.
- §8.2 becomes the agentic-deferral view.

</specifics>

<deferred>
## Deferred Ideas

- Capacity rendered as an `AUTO:capacity` block on migration-gantt driven by `docs/_data/capacity.yml` (CAP-V2-01) — v2.
- Aggregator-side second-fence sanitization (DIAG-V2-01) — v2 / Phase 5.

</deferred>
