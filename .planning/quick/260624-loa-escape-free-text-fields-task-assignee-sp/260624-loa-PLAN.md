---
phase: quick-260624-loa
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [scripts/aggregator.py]
autonomous: true
requirements: [LOA-01]
must_haves:
  truths:
    - "A task title containing <script> renders as escaped &lt;script&gt; in the Task Summary cell — no raw HTML reaches the page"
    - "A free-text value containing | does not add a column to its Markdown table row (pipe is escaped)"
    - "A description containing an embedded quote and newline produces frontmatter that yaml.safe_load parses and round-trips"
    - "The HTML kanban board still escapes card content via _html_escape (unchanged)"
  artifacts:
    - path: "scripts/aggregator.py"
      provides: "_md_cell helper + escaped free-text interpolations + YAML-safe description frontmatter"
      contains: "def _md_cell"
  key_links:
    - from: "generate_project_page"
      to: "_md_cell"
      via: "wrapped free-text task/assignee/date/meta cells"
      pattern: "_md_cell\\("
    - from: "generate_project_page frontmatter"
      to: "json.dumps"
      via: "YAML-safe description scalar"
      pattern: "description: \\{json.dumps"
---

<objective>
Defensively escape free-text fields rendered into generated Markdown tables, body lines, and YAML frontmatter in `scripts/aggregator.py`, so an odd/malicious value (`<script>`, `|`, `"`, newline) from a tracked repo's `kanban.md` cannot inject HTML, break a table row, or corrupt the project-page frontmatter.

Purpose: Harden the trusted-ish org-repo data path. The aggregator interpolates parsed kanban frontmatter/table values directly into Markdown and YAML with no neutralization at the free-text points (task titles, assignees, descriptions, tags, sprint/PO/lead labels, type/legend displays). One bad value currently breaks a row or the page build.
Output: One new `_md_cell()` helper, free-text interpolation points wrapped, and the `description` frontmatter emitted as a JSON-encoded (YAML-safe) scalar.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

<interfaces>
<!-- Existing helper to model the new one on; do NOT reuse it for Markdown cells. -->
From scripts/aggregator.py (~line 53):
```python
def _html_escape(s: str) -> str:
    """HTML-escape a string including quotes (safe for attribute and text contexts)."""
    return html.escape(s, quote=True)
```

Current frontmatter emission in generate_project_page (~lines 332-340):
```python
lines = [
    "---",
    f"title: {project}",
    f"description: \"{description}\"",   # naive quotes — breaks on embedded " or newline
    f"project: {project}",
    f"type: {type_key}",
    f"edit_url: \"{edit_url}\"",          # constructed URL — leave as-is
    f"generated: {datetime.now().isoformat()}",
    "---",
    ...
]
```

DO NOT TOUCH (intentionally Markdown/Liquid/computed/already-escaped):
- `deps_display` (Markdown links with relative_url), `builder_link`, `edit_url` (URLs)
- numeric/day/effort values, `count_cols`, `header_cols`, totals
- `_render_kanban_board` cards (already escaped via `_html_escape`)
- `mermaid_label_safe`, `mermaid_gantt_label` (own escaping)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add _md_cell helper and wrap free-text Markdown interpolations</name>
  <files>scripts/aggregator.py</files>
  <action>
Add a single new helper `_md_cell(value) -> str` directly after `_html_escape` (~line 56). It must: coerce to str, replace `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;` (in that order, ampersand first), escape the cell delimiter `|`→`\|`, and collapse `\r` and `\n` to a single space each. Use the exact body given in the task detail. snake_case + type hints per CLAUDE.md.

Wrap ONLY the dynamic free-text value at each of these interpolation points (do not touch numeric/computed siblings):
- `generate_unified_kanban` Summary table (~line 151): wrap `{project}` → `{_md_cell(project)}`.
- `generate_loe_report` per-project table (~line 268): wrap `{project}` and `{sprint}`. Assignee table (~line 297): wrap `{assignee}`.
- `generate_project_page` Status table: `{type_display}` (~351), `{po}` (~352), `{lead}` (~353), `{sprint}` (~354). Tags join (~356): escape each tag — `', '.join(_md_cell(t) for t in tags) if tags else '-'`.
- `generate_project_page` body description line `> {description}` (~344): wrap `{description}`.
- `generate_project_page` Task Summary 6-col (~389-390): wrap `{task['task']}`, `{task['assignee']}`, `{task.get('start', '')}`, `{task.get('end', '')}`. Leave `{task['effort']}` and `{task['status']}` (computed/enumerated).
- `generate_project_page` Task Summary 4-col (~395): wrap `{task['task']}` and `{task['assignee']}`.
- `generate_dependency_graph` legend (~557): wrap `{display}` → `{_md_cell(display)}`.

Do NOT modify `deps_display`, `builder_link`, `edit_url`, the kanban board cards, the Mermaid helpers, or any numeric/effort/total cell. This task does not touch frontmatter description (Task 2).
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && python -c "
import ast, re
src = open('scripts/aggregator.py').read()
ast.parse(src)
assert 'def _md_cell' in src, 'helper missing'
# malicious task title must render escaped in a project page; pipe must not add a column
import importlib.util, sys
sys.path.insert(0, 'scripts')
import aggregator as A
data = {'meta': {'description': 'Line1\"quote\nLine2', 'tags': ['a|b'], 'sprint': 's'},
        'tasks': [{'task': 'Pwn <script>alert(1)</script> | & \"q\"', 'assignee': 'x', 'effort': '2d', 'status': 'To Do', 'start': '', 'end': ''}]}
page = A.generate_project_page('demo', data)
assert '<script>' not in page, 'raw script leaked'
assert 'Pwn &lt;script&gt;alert(1)&lt;/script&gt; \\\\| &amp; \"q\"' in page, 'cell not escaped as expected'
# the task-summary row must have correct delimiter count (escaped pipe is not a column break)
row = [l for l in page.splitlines() if l.startswith('| Pwn ')][0]
assert row.count('|') - row.count('\\\\|') == 5, f'wrong column count: {row}'
print('TASK1 OK')
"</automated>
  </verify>
  <done>`_md_cell` exists; all listed free-text cells wrapped; malicious task title renders escaped with no raw `<script>`; escaped pipe does not add a column; numeric/computed/board/Mermaid cells untouched; file parses.</done>
</task>

<task type="auto">
  <name>Task 2: Emit YAML-safe description frontmatter via json.dumps</name>
  <files>scripts/aggregator.py</files>
  <action>
Add `import json` to the import block at the top of `scripts/aggregator.py` if not already present (alongside `import html`, `import re`). In `generate_project_page` frontmatter (~line 335), replace the naive `f"description: \"{description}\""` with a JSON-encoded scalar: `f"description: {json.dumps(description)}"` — a JSON string is a valid YAML flow scalar, so an embedded `"` or newline can no longer break the page build. Optionally apply `json.dumps(title)`/`project` for consistency, but `title`/`project` are repo names and may stay plain. Leave `edit_url` exactly as-is (constructed URL). Do not wrap `description` here with `_md_cell` — the body line uses `_md_cell` (Task 1); frontmatter uses `json.dumps`.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && python -c "
import ast, sys, yaml
sys.path.insert(0, 'scripts')
src = open('scripts/aggregator.py').read()
ast.parse(src)
import aggregator as A
desc = 'Line1\"quote\nLine2'
data = {'meta': {'description': desc, 'tags': [], 'sprint': 's'}, 'tasks': []}
page = A.generate_project_page('demo', data)
# extract frontmatter block between the first two '---' lines
parts = page.split('---')
fm = parts[1]
loaded = yaml.safe_load(fm)
assert loaded['description'] == desc, f'round-trip failed: {loaded[\"description\"]!r}'
assert 'json.dumps(description)' in src or 'description: {json.dumps' in src
print('TASK2 OK')
"</automated>
  </verify>
  <done>`import json` present; `description` frontmatter emitted via `json.dumps`; `yaml.safe_load` of the frontmatter block parses and round-trips a description containing an embedded quote and newline; `edit_url` unchanged.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| org-repo kanban.md → aggregator → generated Markdown/HTML/YAML | Free-text frontmatter/table values cross from tracked (trusted-ish) repos into the generated dashboard, where they are interpolated into Markdown tables, body prose, and YAML frontmatter. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-loa-01 | Tampering | task title / assignee / tags / description rendered into Markdown tables | mitigate | `_md_cell` neutralizes `&<>`, escapes `\|`, collapses CR/LF so a value cannot break a row or inject markup |
| T-loa-02 | Tampering | `description` in project-page YAML frontmatter | mitigate | Emit `json.dumps(description)` (valid YAML flow scalar) so embedded `"`/newline cannot corrupt frontmatter / break Jekyll build |
| T-loa-03 | Information disclosure (HTML injection / stored XSS) | free text reaching the rendered HTML page | mitigate | `_md_cell` escapes `<`/`>` so `<script>` cannot reach the DOM; board cards already escaped via `_html_escape` |
</threat_model>

<verification>
- `python -c "import ast; ast.parse(open('scripts/aggregator.py').read())"` clean.
- A project page built from a task titled `Pwn <script>alert(1)</script> | & "q"`, description `Line1"quote\nLine2`, tag `a|b`: no raw `<script>` anywhere; Task Summary cell shows `Pwn &lt;script&gt;alert(1)&lt;/script&gt; \| &amp; "q"`; the row keeps the correct number of `|` delimiters.
- `yaml.safe_load` of the project-page frontmatter block round-trips the embedded-quote/newline description.
- `generate_unified_kanban` Summary table project cell escaped; HTML board cards unchanged (still via `_html_escape`).
</verification>

<success_criteria>
- ONE new `_md_cell()` helper added near `_html_escape`.
- All listed free-text interpolation points wrapped; DO-NOT-TOUCH set (deps_display, URLs, numeric/effort/totals, board cards, Mermaid helpers) untouched.
- `description` frontmatter is YAML-safe via `json.dumps`; `edit_url` unchanged; `import json` present.
- No second kanban parser; no `loe.yml` change; HTML board behavior unchanged; deterministic output.
- Both task `<automated>` verifications print OK; file parses clean.
</success_criteria>

<output>
Create `.planning/quick/260624-loa-escape-free-text-fields-task-assignee-sp/260624-loa-SUMMARY.md` when done
</output>
