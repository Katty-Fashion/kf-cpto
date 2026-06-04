# kf-cpto — Activity-Driven Migration Dashboard

## What This Is

kf-cpto is the CPTO aggregation hub for the katty-fashion GitHub org: it pulls per-project `kanban.md` files, builds a unified Jekyll dashboard on GitHub Pages (kanban, sprint calendar, LOE report, dependency graph, migration gantt), and exports key LOE data downstream to a Google Workspace `LOE` Sheet. This milestone adds a **local Claude skill** that turns the dashboard from a hand-maintained artifact into an **activity-driven** one — reading real repo activity, reconciling it against the declared plan, writing corrections back to the tracked repos, and modelling over-capacity work as **agentic effort instead of new headcount**.

## Core Value

One command turns *actual repo activity* into an accurate, deployed dashboard and LOE Sheet — with work beyond a person's capacity flowing to a synthetic Agentic assignee instead of a hire recommendation.

## Requirements

### Validated

<!-- Inferred from existing codebase (see .planning/codebase/). These already work and are relied upon. -->

- [DONE] Dynamic org discovery — `discover.py` scans the GitHub org for repos carrying `kanban.md` (`scripts/discover.py`) — existing
- [DONE] kanban.md parsing — frontmatter + 4/6-col task tables, effort strings (`scripts/utils.py`) — existing
- [DONE] Unified dashboard generation — kanban, calendar, LOE report, dependency graph, per-project pages (`scripts/aggregator.py`) — existing
- [DONE] Canonical `loe.yml` intermediate — single parser, single canonical export source — existing
- [DONE] AUTO-block engine — idempotent `<!-- AUTO:name -->` injection into augmented prose pages incl. `migration-gantt.md` (`scripts/auto_blocks.py`) — existing
- [DONE] Google Sheets downstream export — shadow-tab swap into the `LOE` tab, never blocks the pipeline (exit-0 invariant) (`scripts/sheets_sync.py`) — existing
- [DONE] Pages-first deployment — `aggregate.yml` deploys `docs/` to `gh-pages`; canonical dashboard always available — existing
- [DONE] Sync-health surfacing — `sync_status.yml` rendered live on dashboard sidebar + index banner — existing
- [DONE] Push-driven refresh — project repos' `notify-kf-cpto.yml` fires `repository_dispatch` on `kanban.md` push → full pipeline — existing

### Active

<!-- This milestone. Hypotheses until shipped and validated. -->

- [ ] Local Claude skill that accesses the tracked project repos on disk (via symlink to sibling checkouts) — the ones carrying both `kanban.md` and `notify-kf-cpto.yml`
- [ ] Activity gathering — mine each tracked repo's `kanban.md` **and git signals** (commits / PRs / branches) to infer real progress vs. what's declared
- [ ] Reconciliation — auto-update declared status to match observed reality, **and list every change made** for review
- [ ] Write-back — commit the corrected `kanban.md` to each tracked repo and push (batch-confirmed once); rely on the existing `notify → dispatch` pipeline to re-render and deploy
- [ ] Agentic-overflow capacity model — 2 FTE (1 FE, 1 BE); hold each human at 100% capacity and defer only the overflow hours
- [ ] Synthetic **Agentic** assignee — overflow effort appears as its own row/slice in the LOE outputs
- [ ] Replace the "add 0.5 FTE" recommendation (migration-gantt §8.2) with agentic deferral
- [ ] Diagram robustness — sanitize emojis / typos in hand-edited content so Mermaid (gantt, kanban, pie, graph) stops breaking

### Out of Scope

<!-- Explicit boundaries with reasoning. -->

- Net-new dashboard pages — milestone refines the existing views (kanban, gantt, calendar, LOE); no new pages
- Replacing the deterministic CI renderer — the skill is the *smart input layer*; `aggregator.py` + `aggregate.yml` stay the dumb reliable renderer/deployer
- Two-way / real-time Google Sheets sync — Sheets remains a downstream export; Pages stays canonical
- Changing the `sheets_sync.py` exit-0 invariant — Pages must never be blocked by a Sheets failure
- Re-parsing `kanban.md` inside `sheets_sync.py` — keep "one parser, one canonical intermediate"

## Context

- **Master plan as spine:** `docs/migration-gantt.md` is a detailed hand-authored plan for the KF → ALADIN platform migration — 32 weeks, 6 overlapping phases, 16 two-week sprints, tasks tagged with Owner (`FE` / `BE` / `FE+BE`), Size (`S`/`M`/`L`/`XL`), and Type pills. It already carries a Capacity-vs-Demand section (§8.2).
- **The exact pain point:** §8.2 shows Backend Dev at **106%** (~80h over) and currently recommends extending the timeline, adding 0.5 FTE backend, or descoping. This milestone changes that default to agentic deferral.
- **Team:** 2 FTE — 1 Frontend, 1 Backend, full-time. Tasks already encode FE/BE/both, so discipline routing exists in the source.
- **Topology (do not invert):** GitHub Pages is canonical; the `LOE` Google Sheet is a downstream export. Sheets sync runs *after* the `gh-pages` publish in `aggregate.yml`.
- **Existing stack:** Python 3.9+ pipeline scripts, Jekyll 3.10 (github-pages gem) site with Pico CSS + Mermaid v11, deployed via GitHub Actions.
- **No test suite today:** `validate_auto_blocks.py` is the only CI-enforced lint (AUTO marker hygiene).

## Constraints

- **Tech stack**: Python 3.9+ scripts + Jekyll/Ruby site — Keep CI deterministic; the skill produces inputs, CI renders/deploys
- **Execution**: Skill runs locally in Claude Code, reaching sibling repos via symlink — No reliance on the skill at CI time; CI stays self-contained
- **External writes**: Pushes to tracked project repos are batch-confirmed once, never per-repo prompted — Matches the org-scan workflow preference; avoids interactive stalls across N repos
- **Topology**: Pages canonical, Sheets downstream, exit-0 on Sheets failure — Dashboard availability must never depend on the Sheet
- **Parser discipline**: Extend `aggregator.build_loe_rows()` / `write_loe_yaml()` for new fields; never add a second kanban parser — Preserves the canonical-intermediate contract
- **Runtime dirs**: Never commit `repos/` (shallow clones) — gitignored, populated at runtime only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Skill is a local smart layer, not a CI replacement | Keep deterministic rendering/deploy in CI; isolate LLM judgement to a local, reviewable step | [PENDING] |
| Activity = kanban + git signals | Declared status drifts from reality; git is ground truth for what actually moved | [PENDING] |
| Reconcile by auto-update + flag (not silent, not flag-only) | Want the dashboard corrected automatically but with a reviewable change list | [PENDING] |
| Write back to repos and push (vs. PR or local-only) | Reuses the existing `notify → dispatch` loop so CI re-renders deterministically; one batch confirm | [PENDING] |
| Over-capacity overflow → synthetic Agentic assignee | Reframe headcount pressure as agentic effort; human stays pinned at 100% | [PENDING] |
| Agentic shown as its own LOE row/slice | Makes the agentic share legible in reports without distorting per-person lines | [PENDING] |
| Refine existing views, no new pages | Focus the milestone on accuracy + robustness, not surface area | [PENDING] |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-04 after initialization*
