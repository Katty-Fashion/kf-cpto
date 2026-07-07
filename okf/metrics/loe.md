---
type: Metric
title: Level of Effort (LOE)
description: Person-days of work as declared in kanban.md, distinct from gantt working-day spans
tags:
  - loe
  - effort
  - person-days
  - metrics
---

# Level of Effort (LOE)

## Definition

**LOE = person-days (`Nd`)** as declared in each project's `kanban.md` task table
(e.g. `5d`, `10d`).  It represents the *estimated work* one person needs to
complete a task, regardless of calendar span.

## Distinction from `gantt.yml` effort_days

The migration Gantt chart (`docs/migration-gantt.md`) uses a separate field
`effort_days` that represents the **inclusive working-day span** of a bar on
the chart — how many working days the bar occupies on the timeline.  This is
a *scheduling* quantity, not a *capacity* quantity.

| Concept | Field | Semantics | Source |
| :--- | :--- | :--- | :--- |
| LOE | `kanban.md` effort column (`Nd`) | Person-days of work | Per-project `kanban.md` |
| Gantt span | `gantt.yml` `effort_days` | Inclusive working-day calendar span | `docs/migration-gantt.md` |

## Discipline-split no-double-counting rule

When a migration task spans both FE and BE disciplines (e.g. `(FE+BE)` tag in
the gantt), the task's effort is **split across two separate task rows** —
one per discipline.  Summing LOE across both rows gives the total capacity
required.  Do NOT add a combined row on top of the split rows.

## Usage in this bundle

Each project concept file (under [/projects/](/projects/index.md)) shows a
**LOE rollup** computed from the canonical `docs/_data/loe.yml` intermediate,
which is written by `scripts/aggregator.py` after parsing all `kanban.md` files.
Downstream consumers (Google Sheets export) read `loe.yml` — they never
re-parse `kanban.md` directly.
