---
phase: quick-260624-eqy
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/aggregator.py
  - docs/assets/css/custom.css
autonomous: true
requirements: [QUICK-260624-eqy]
must_haves:
  truths:
    - "Unified kanban renders as an HTML/CSS column board (no Mermaid kanban fence)"
    - "Unified kanban has no status-pill legend"
    - "Each card links to its project page via Liquid relative_url"
    - "Card text shows full PROJECT: TASK with no truncation, HTML-escaped"
    - "Summary by Project table and Sprint Timeline gantt still render below the board"
    - "_status_legend() remains defined and still used by project pages"
  artifacts:
    - path: "scripts/aggregator.py"
      provides: "_html_escape and _render_kanban_board helpers; HTML board in generate_unified_kanban"
      contains: "_render_kanban_board"
    - path: "docs/assets/css/custom.css"
      provides: ".kanban-board / .kanban-col / .kanban-card styles"
      contains: ".kanban-card"
  key_links:
    - from: "generate_unified_kanban"
      to: "_render_kanban_board"
      via: "function call replacing the mermaid kanban loop"
      pattern: "_render_kanban_board\\(statuses\\)"
    - from: ".kanban-card href"
      to: "/projects/{project}/"
      via: "Liquid relative_url filter emitted into HTML"
      pattern: "relative_url"
---

<objective>
Replace the unified kanban's Mermaid `kanban` diagram with a deterministic HTML/CSS column board, drop the redundant color-clashing status-pill legend from the unified view only, and make each card a link to its project page.

Purpose: The Mermaid kanban is hard to read at scale and the pill legend duplicates the per-status column colors. An HTML board wraps full text, color-codes columns, and links cards to project pages.
Output: Updated `generate_unified_kanban()` + two new module-level helpers in `scripts/aggregator.py`; new board styles appended to `docs/assets/css/custom.css`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

<interfaces>
<!-- Status constants (scripts/utils.py) — executor uses these directly, no exploration needed. -->

TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")
STATUS_TO_MERMAID = {s: s.replace(" ", "-") for s in TASK_STATUSES}
  # keys produced: "Todo", "In-Progress", "Review", "Done"

In generate_unified_kanban, `statuses` is keyed by STATUS_TO_MERMAID names
in TASK_STATUSES order: {"Todo": [...], "In-Progress": [...], "Review": [...], "Done": [...]}
Each task dict carries at least: task["project"], task["task"].

Existing palette (docs/assets/css/custom.css ~line 223-226):
  todo #8a9a7b · in-progress #c2682d · review #bf9b30 · done #3a7d44

Sidebar link pattern (docs/_includes/sidebar.html:22):
  <a href="{{ proj.url | relative_url }}">   (proj.url == /projects/{name}/)

Config: baseurl "/kf-cpto"; _projects permalink /projects/:name/
</interfaces>

<scope>
ONLY the unified kanban view (generate_unified_kanban, ~line 62).
DO NOT touch the per-project page kanban: the second _status_legend() call
(~line 338) and its Mermaid kanban stay untouched. _status_legend() itself
MUST remain defined (still used by project pages).
Keep "## Summary by Project" table and "## Sprint Timeline" gantt unchanged.
No second parser; no loe.yml change.
</scope>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Render HTML kanban board in aggregator.py</name>
  <files>scripts/aggregator.py</files>
  <action>
Add two module-level helpers near `_status_legend()` (snake_case, type-hinted):

1. Reuse python stdlib for escaping: `import html` at top of file (with the other imports). Define `_html_escape(s: str) -> str` returning `html.escape(s, quote=True)` (a thin wrapper so the intent is named and testable); the executor MAY instead call `html.escape(..., quote=True)` directly inside the board builder — either is acceptable, but quotes MUST be escaped.

2. Define `_render_kanban_board(statuses: dict) -> str`. It receives the existing `statuses` dict (keyed by STATUS_TO_MERMAID names in TASK_STATUSES order) and returns one HTML string built with the list + "\n".join(lines) convention. Structure:
   - Outer `<div class="kanban-board">` … `</div>`.
   - Iterate `statuses.items()` (insertion order already Todo, In-Progress, Review, Done). For each status key, derive `slug = status.lower()` (status keys are already hyphenated, e.g. "In-Progress" -> "in-progress"; "Todo" -> "todo"). Display label = `status.replace("-", " ")` (so "In-Progress" shows as "In Progress").
   - Column: `<div class="kanban-col kanban-col--{slug}">` then head `<div class="kanban-col__head">{label} <span class="kanban-col__count">{len(tasks)}</span></div>`.
   - Each card: `<a class="kanban-card" href="{{ '/projects/{project}/' | relative_url }}">{escaped_project}: {escaped_task}</a>` where `{project}` in the href path is the RAW project key (repo name — ascii/url-safe like R3-AAS, kf-platform; do NOT html-escape the href path). `{escaped_project}` and `{escaped_task}` are `_html_escape()`-ed (quotes included). Emit the `{{ ... | relative_url }}` Liquid literally so Jekyll resolves baseurl at build time.
   - Full text, no truncation/ellipsis/fixed height — that is a CSS concern; emit complete strings.

In `generate_unified_kanban(data)`:
   - Remove the `_status_legend()` entry from the opening `lines` list (the `_status_legend(),` element ~line 74) and the now-orphan trailing `"",`. Keep the rest of the header.
   - KEEP the existing `statuses` aggregation loop (lines ~79-92) exactly as-is — same grouping semantics and order.
   - Replace the Mermaid kanban emission (the block `lines.append("```mermaid")` / `lines.append("kanban")` / the status+task loop / closing fence, ~lines 94-105) with: `lines.append(_render_kanban_board(statuses))` then `lines.append("")`.
   - Do NOT change "## Summary by Project" or "## Sprint Timeline" sections that follow.
   - Leave the second `_status_legend()` call (~line 338, project pages) and that page's Mermaid kanban untouched.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && venv/bin/python - <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("aggregator", "scripts/aggregator.py")
# import dependencies on path
sys.path.insert(0, "scripts")
import aggregator as a
data = {
    "R3-AAS": {"tasks": [
        {"task": "Build <auth> \"core\"", "status": "Todo", "project": "R3-AAS"},
        {"task": "Wire API", "status": "In Progress", "project": "R3-AAS"},
    ], "meta": {}},
    "kf-platform": {"tasks": [
        {"task": "Review queue", "status": "Review", "project": "kf-platform"},
        {"task": "Ship it", "status": "Done", "project": "kf-platform"},
    ], "meta": {}},
}
out = a.generate_unified_kanban(data)
assert "```mermaid\nkanban" not in out and "kanban\n  Todo" not in out, "mermaid kanban still present"
assert "status-pill" not in out and "status-legend" not in out, "status pill/legend leaked into unified output"
assert 'class="kanban-board"' in out and 'class="kanban-card"' in out, "board/card markup missing"
assert "{{ '/projects/R3-AAS/' | relative_url }}" in out, "relative_url href missing/wrong"
assert "Build &lt;auth&gt; &quot;core&quot;" in out, "task text not html-escaped (quotes included)"
assert 'kanban-col__count">2<' in out, "count wrong/missing"
assert "## Summary by Project" in out and "## Sprint Timeline" not in out  # no sprint dates in sample -> ok
assert callable(a._status_legend), "_status_legend must remain defined"
print("OK task1")
PY</automated>
  </verify>
  <done>Unified kanban output contains an HTML board with linked, escaped, full-text cards and per-status counts; no mermaid kanban fence and no status-pill/legend in the unified output; Summary table still present; _status_legend still defined.</done>
</task>

<task type="auto">
  <name>Task 2: Append kanban board styles to custom.css</name>
  <files>docs/assets/css/custom.css</files>
  <action>
Append a new "===== Unified Kanban Board =====" section to docs/assets/css/custom.css (do NOT remove the existing .status-pill rules — project pages still use them). Add:

   - `.kanban-board` — `display:flex; flex-wrap:wrap; gap:1rem; margin:0.75rem 0 1.5rem; align-items:flex-start;`
   - `.kanban-col` — `flex:1 1 200px; min-width:200px; background:var(--pico-card-background-color, #f6f8f5); border-radius:8px; padding:0.75rem;` (light surface, rounded).
   - `.kanban-col__head` — `font-weight:700; margin-bottom:0.6rem; padding-bottom:0.35rem;` plus a per-status accent via top or left border. Map palette: todo #8a9a7b, in-progress #c2682d, review #bf9b30, done #3a7d44 using `.kanban-col--todo .kanban-col__head { border-top:3px solid #8a9a7b; }` style rules (or a left-border on `.kanban-col--{slug}` — pick one consistently and ensure the accent shows the status color).
   - `.kanban-col__count` — `font-size:0.78rem; font-weight:600; opacity:0.6; margin-left:0.3rem;` (muted small).
   - `.kanban-card` — block link: `display:block; background:#fff; border:1px solid rgba(0,0,0,0.12); border-radius:6px; padding:0.5rem 0.65rem; margin-bottom:0.5rem; color:#1f2a24; text-decoration:none; line-height:1.4; word-break:break-word; overflow-wrap:anywhere;` (NO truncation, full wrap, readable contrast, no underline).
   - `.kanban-card:hover` — subtle shift, e.g. `background:#f0f3ee; border-color:rgba(0,0,0,0.22);`.

Keep deterministic, readable CSS consistent with the existing file style (section comment header, 2-space indent as in current file).
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && grep -q '\.kanban-board' docs/assets/css/custom.css && grep -q '\.kanban-card' docs/assets/css/custom.css && grep -q '\.kanban-col__count' docs/assets/css/custom.css && grep -q 'word-break\|overflow-wrap' docs/assets/css/custom.css && grep -q '\.kanban-card:hover' docs/assets/css/custom.css && grep -q '#c2682d' docs/assets/css/custom.css && grep -q '\.status-pill--todo' docs/assets/css/custom.css && echo OK_task2</automated>
  </verify>
  <done>custom.css contains .kanban-board, .kanban-col(+__head/__count), .kanban-card (with wrap + hover, no truncation) using the existing palette; original .status-pill rules retained.</done>
</task>

</tasks>

<verification>
1. Task 1 inline python harness passes (board markup, escaping, relative_url, counts, no mermaid/pills, _status_legend defined).
2. Task 2 grep gate passes (board/card/count/wrap/hover/palette present; status-pill retained).
3. Spot-check: per-project page generation (generate_project_page) still emits its Mermaid kanban and _status_legend — unchanged by this plan.
</verification>

<success_criteria>
- Unified kanban view renders an HTML column board (4 columns: Todo, In Progress, Review, Done) with full-text, escaped, project-linked cards and per-column counts.
- No status-pill legend and no Mermaid `kanban` fence remain in the unified output.
- Summary by Project table and Sprint Timeline gantt are unchanged.
- _status_legend() remains defined; per-project page kanban untouched.
- Deterministic output; one parser; loe.yml unchanged.
</success_criteria>

<output>
Create `.planning/quick/260624-eqy-replace-unified-kanban-mermaid-diagram-w/260624-eqy-SUMMARY.md` when done.
</output>
