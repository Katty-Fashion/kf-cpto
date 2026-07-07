---
type: Metric
title: RAG Status Colours
description: Red-Amber-Green task status colour semantics for kanban and gantt views
tags:
  - rag
  - status
  - colours
  - kanban
  - gantt
---

# RAG Status Colours

## Definition

Tasks and gantt bars are coloured by a Red-Amber-Green (RAG) scheme that
combines the declared `status` field with start/end dates relative to today.

| Colour | Mermaid modifier | Condition |
| :--- | :--- | :--- |
| Green (Done) | `done,` | `status == Done` |
| Amber (In work) | `active,` | `status In Progress` or `Review` |
| Red (Late / At risk) | `crit,` | overdue (`end < today` and not Done), or should-have-started (`status Todo` and `start < today`) |
| Grey (Planned) | _(none)_ | `status Todo` and start is in the future or undated |

## Source of truth

The `utils.rag_modifier(status, start_iso, end_iso, today)` function in
`scripts/utils.py` is the single source of truth for this logic.  All gantt
charts in the dashboard use it; this document mirrors that definition.

## Colour mapping

Colours are applied via Mermaid `themeVariables` in `docs/_layouts/default.html`,
not via external CSS.  The legend in every gantt page (`GANTT_LEGEND_HTML`)
must stay in sync with this table.
