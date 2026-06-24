---
phase: quick-260624-eqy
plan: "01"
subsystem: aggregator/dashboard
tags: [kanban, html, css, aggregator]
dependency_graph:
  requires: []
  provides: [html-kanban-board]
  affects: [docs/unified-kanban.md, docs/assets/css/custom.css]
tech_stack:
  added: [html.escape (stdlib), _render_kanban_board, _html_escape]
  patterns: [HTML-board-in-markdown, liquid-relative_url-literal-emit]
key_files:
  modified:
    - scripts/aggregator.py
    - docs/assets/css/custom.css
decisions:
  - "Use html.escape(quote=True) via thin _html_escape() wrapper for testability and named intent"
  - "Emit Liquid {{ ... | relative_url }} literally in Python string using .format() with quadruple-brace escaping"
  - "Per-status column accent via border-top on .kanban-col__head rather than column background to keep cards readable on light surface"
  - "_status_legend() kept defined and called in generate_project_page(); only removed from generate_unified_kanban() header"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-24"
  tasks: 2
  files_changed: 2
---

# Phase quick-260624-eqy Plan 01: Replace Unified Kanban Mermaid Diagram Summary

**One-liner:** HTML/CSS 4-column kanban board with Liquid-linked, HTML-escaped cards replaces the Mermaid `kanban` fence in the unified view.

## What Was Built

### Task 1: Render HTML kanban board in aggregator.py (commit 3b55b57)

Added `import html` at the top of `scripts/aggregator.py`. Added two module-level helpers:

- `_html_escape(s: str) -> str` — thin wrapper around `html.escape(s, quote=True)` for named intent and testability.
- `_render_kanban_board(statuses: dict) -> str` — takes the aggregated `statuses` dict (keyed by STATUS_TO_MERMAID names: Todo, In-Progress, Review, Done in TASK_STATUSES order) and returns an HTML string using the `list + "\n".join(lines)` convention. Each column is `div.kanban-col.kanban-col--{slug}` with a `div.kanban-col__head` showing the label and count. Each task is an `<a class="kanban-card">` emitting the Liquid `{{ '/projects/{project}/' | relative_url }}` filter literally for Jekyll baseurl resolution at build time. Card text is `_html_escape()`-ed (quotes included) — no truncation or ellipsis.

In `generate_unified_kanban()`:
- Removed `_status_legend()` from the opening `lines` list (and its trailing blank line).
- Replaced the Mermaid `kanban` fence block with `lines.append(_render_kanban_board(statuses))` + `lines.append("")`.
- The `statuses` aggregation loop, Summary by Project table, and Sprint Timeline gantt are unchanged.
- `_status_legend()` itself remains defined and is still called from `generate_project_page()` (line 367).

### Task 2: Append kanban board styles to custom.css (commit 7c88fa1)

Appended a new `===== Unified Kanban Board =====` section to `docs/assets/css/custom.css`:

- `.kanban-board` — flex container, wrap, 1rem gap, align-items flex-start.
- `.kanban-col` — flex 1 1 200px, card background variable, 8px border-radius, 0.75rem padding.
- `.kanban-col__head` — bold, bottom margin/padding, 3px top border (transparent base overridden per status slug).
- `.kanban-col--todo/in-progress/review/done .kanban-col__head` — reuses existing forest palette: #8a9a7b / #c2682d / #bf9b30 / #3a7d44.
- `.kanban-col__count` — 0.78rem, 60% opacity, small left margin.
- `.kanban-card` — block link, white background, light border, 6px radius, full-text wrap (`word-break: break-word; overflow-wrap: anywhere`), no underline, readable contrast (#1f2a24).
- `.kanban-card:hover` — subtle background shift to #f0f3ee.

All existing `.status-pill` and `.status-legend` rules are retained (per-project pages still use them).

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 3b55b57 | feat | Replace unified kanban mermaid with HTML column board |
| 7c88fa1 | feat | Add HTML kanban board styles to custom.css |

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- AST parse clean: `python -c "import ast; ast.parse(open('scripts/aggregator.py').read())"` — OK
- `_status_legend` defined and still called from `generate_project_page` (line 367) — confirmed
- `_render_kanban_board` defined — confirmed
- `_html_escape` defined — confirmed
- Board renders no mermaid kanban fence, no status-pill/legend in unified output — confirmed
- Cards emit `{{ '/projects/R3-AAS/' | relative_url }}` — confirmed
- HTML escaping: `Build <auth> "core"` -> `Build &lt;auth&gt; &quot;core&quot;` — confirmed
- `.kanban-board`, `.kanban-card`, `.kanban-col__count`, `word-break`/`overflow-wrap`, `.kanban-card:hover`, `#c2682d`, `.status-pill--todo` all present in CSS — confirmed
- Summary by Project table intact in unified kanban output — confirmed

## Self-Check: PASSED

- `scripts/aggregator.py` — modified, committed at 3b55b57
- `docs/assets/css/custom.css` — modified, committed at 7c88fa1
