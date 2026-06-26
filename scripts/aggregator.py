#!/usr/bin/env python3
"""
Aggregator Script for KF Team Git-Native Project Management

Merges kanban.md files from all project repos and generates:
- unified-kanban.md
- unified-calendar.md
- loe-report.md
- docs/_projects/{project}.md (per-project pages — Jekyll collection)
"""

import html
import json
import re
from datetime import datetime, timedelta

import yaml

from auto_blocks import load_context, process_page
from utils import (
    DATA_DIR,
    DOCS_DIR,
    GANTT_DATA_FILE,
    LOE_DATA_FILE,
    ORG,
    EDIT_URL_TEMPLATE,
    PROJECT_BRANCHES,
    TASK_STATUSES,
    STATUS_TO_MERMAID,
    STATUS_COLORS,
    TYPE_DISPLAY,
    TYPE_MERMAID_CLASS,
    TYPE_MERMAID_DEFS,
    load_projects,
    load_all_project_data,
    now_iso,
    parse_effort_days,
    strip_emojis,
    mermaid_label_safe,
    mermaid_node_id,
    mermaid_gantt_label,
    update_sync_status,
    _is_separator_row,
)

PROJECTS = load_projects()

# A gantt date cell must be a real ISO date — repos use placeholders like "—",
# "-", or "TBD" for unknown dates, which are invalid in the gantt date/duration
# position and crash the diagram ("Syntax error in text").
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _html_escape(s: str) -> str:
    """HTML-escape a string including quotes (safe for attribute and text contexts)."""
    return html.escape(s, quote=True)


def _md_cell(value: str) -> str:
    """Escape a free-text value for safe interpolation into a Markdown table cell.

    Coerces to str, then applies (in order):
    - `&` → `&amp;`  (ampersand first, before other replacements introduce &)
    - `<` → `&lt;`
    - `>` → `&gt;`
    - `|` → `\\|`   (pipe is the Markdown column delimiter)
    - `\\r` and `\\n` collapsed to a single space (no multi-line cells)
    """
    s = str(value)
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    s = s.replace("|", "\\|")
    s = s.replace("\r", " ").replace("\n", " ")
    return s


def _render_kanban_board(statuses: dict, *, link_project: bool = True) -> str:
    """Render an HTML/CSS column kanban board from the aggregated statuses dict.

    Receives a dict keyed by STATUS_TO_MERMAID names in TASK_STATUSES order
    (Todo, In-Progress, Review, Done). Each value is a list of task dicts
    carrying at least 'project' and 'task' keys.

    When link_project=True (default, unified board): cards are <a> tags with a
    relative_url link to the project page, prefixed "project: task".
    When link_project=False (per-project board): cards are static <div> tags
    with task text only — no href, no project prefix.

    Returns one HTML string built with the list + join convention. Cards emit
    Liquid relative_url literally so Jekyll resolves baseurl at build time.
    """
    lines = ['<div class="kanban-board">']
    for status, tasks in statuses.items():
        slug = status.lower()  # "In-Progress" -> "in-progress", "Todo" -> "todo"
        label = status.replace("-", " ")  # "In-Progress" -> "In Progress"
        lines.append(f'  <div class="kanban-col kanban-col--{slug}">')
        lines.append(
            f'    <div class="kanban-col__head">'
            f'{label} <span class="kanban-col__count">{len(tasks)}</span>'
            f'</div>'
        )
        for task in tasks:
            escaped_task = _html_escape(task["task"])
            if link_project:
                project = task["project"]
                escaped_project = _html_escape(project)
                href = "{{{{ '/projects/{proj}/' | relative_url }}}}".format(proj=project.lower())
                lines.append(
                    f'    <a class="kanban-card" href="{href}">'
                    f'{escaped_project}: {escaped_task}'
                    f'</a>'
                )
            else:
                lines.append(
                    f'    <div class="kanban-card kanban-card--static">{escaped_task}</div>'
                )
        lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def generate_unified_kanban(data: dict) -> str:
    """Generate unified kanban markdown"""
    lines = [
        "---",
        "title: Unified Kanban",
        f"generated: {datetime.now().isoformat()}",
        "---",
        "",
        "# KF Team — Unified Kanban",
        "",
        "> Auto-generated from all project kanbans",
        "",
    ]

    # Aggregate by status (use hyphenated names for MermaidJS)
    statuses = {STATUS_TO_MERMAID[s]: [] for s in TASK_STATUSES}

    task_counter = 0
    for project, project_data in data.items():
        for task in project_data["tasks"]:
            status = task["status"]
            mermaid_status = STATUS_TO_MERMAID.get(status)
            if mermaid_status and mermaid_status in statuses:
                task_counter += 1
                statuses[mermaid_status].append({
                    **task,
                    "project": project,
                    "id": f"task{task_counter}"
                })

    # Generate HTML kanban board (4 columns, linked cards, full-text wrap)
    lines.append(_render_kanban_board(statuses))
    lines.append("")

    # Generate summary table
    lines.append("## Summary by Project")
    lines.append("")
    header_cols = " | ".join(TASK_STATUSES)
    lines.append(f"| Project | {header_cols} | Total |")
    lines.append("| :--- |" + " :---: |" * (len(TASK_STATUSES) + 1))

    for project, project_data in data.items():
        counts = {s: 0 for s in TASK_STATUSES}
        for task in project_data["tasks"]:
            if task["status"] in counts:
                counts[task["status"]] += 1
        total = sum(counts.values())
        count_cols = " | ".join(str(counts[s]) for s in TASK_STATUSES)
        lines.append(f"| {_md_cell(project)} | {count_cols} | {total} |")

    # Sprint Gantt — current sprint window per project (one bar each). Platform
    # repos share a cadence (see generate_kanban.py), so they line up here.
    sprint_rows = []
    for project, project_data in data.items():
        meta = project_data.get("meta", {})
        s_start = str(meta.get("sprint_start", "")).strip()
        s_end = str(meta.get("sprint_end", "")).strip()
        if _ISO_DATE_RE.match(s_start) and _ISO_DATE_RE.match(s_end):
            sprint_rows.append((project, str(meta.get("sprint", "Sprint")), s_start, s_end))

    if sprint_rows:
        lines.append("")
        lines.append("## Sprint Timeline")
        lines.append("")
        lines.append("```mermaid")
        lines.append("gantt")
        lines.append("    title Current Sprint by Project")
        lines.append("    dateFormat YYYY-MM-DD")
        lines.append("    axisFormat %d %b")
        lines.append("    excludes weekends")
        lines.append("")
        for project, sprint, s_start, s_end in sprint_rows:
            lines.append(f"    section {mermaid_gantt_label(project)}")
            lines.append(
                f"    {mermaid_gantt_label(sprint)} :active, {s_start}, {s_end}"
            )
        lines.append("```")

    return "\n".join(lines)


def generate_unified_calendar(data: dict) -> str:
    """Generate unified calendar markdown with Gantt chart"""
    # Compute per-project effort totals for the pie chart
    effort_pairs = []
    for proj, proj_data in data.items():
        total = sum(parse_effort_days(t["effort"]) for t in proj_data["tasks"])
        if total > 0:
            effort_pairs.append((proj, total))
    effort_pairs.sort(key=lambda x: x[1], reverse=True)

    lines = [
        "---",
        "title: Unified Calendar",
        f"generated: {datetime.now().isoformat()}",
        "---",
        "",
        "# KF Team — Unified Calendar",
        "",
        "> Effort by Project (person-days)",
        "",
    ]

    if effort_pairs:
        lines.append("```mermaid")
        lines.append("pie title Effort by Project (person-days)")
        for proj, total in effort_pairs:
            lines.append(f'    "{mermaid_label_safe(proj)}" : {total}')
        lines.append("```")
        lines.append("")

    lines += [
        "## Sprint Calendar",
        "",
        "```mermaid",
        "gantt",
        "    title Calendar Lunar KF",
        "    dateFormat YYYY-MM-DD",
        "    excludes weekends",
        "",
    ]

    # Add sprint sections from project metadata
    for project, project_data in data.items():
        meta = project_data.get("meta", {})
        s_start = str(meta.get("sprint_start", "")).strip()
        s_end = str(meta.get("sprint_end", "")).strip()
        if _ISO_DATE_RE.match(s_start) and _ISO_DATE_RE.match(s_end):
            sprint = meta.get("sprint", "Sprint")
            lines.append(f"    section {mermaid_gantt_label(project)}")
            lines.append(
                f"    {mermaid_gantt_label(str(sprint))} :active, {s_start}, {s_end}"
            )

    lines.append("```")

    return "\n".join(lines)


def generate_loe_report(data: dict) -> str:
    """Generate Level of Effort report"""
    lines = [
        "---",
        "title: LOE Report",
        f"generated: {datetime.now().isoformat()}",
        "---",
        "",
        "# KF Team — Level of Effort Report",
        "",
        "> Auto-generated LOE aggregation",
        "",
        "## Summary by Project",
        "",
        "| Project | Sprint | Total Effort | Completed | Remaining |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ]

    total_effort = 0
    total_completed = 0

    for project, project_data in data.items():
        meta = project_data.get("meta", {})
        sprint = meta.get("sprint", "-")

        project_total = 0
        project_completed = 0

        for task in project_data["tasks"]:
            days = parse_effort_days(task["effort"])
            project_total += days
            if task["status"] == "Done":
                project_completed += days

        remaining = project_total - project_completed
        lines.append(f"| {_md_cell(project)} | {_md_cell(sprint)} | {project_total}d | {project_completed}d | {remaining}d |")

        total_effort += project_total
        total_completed += project_completed

    lines.append(f"| **Total** | | **{total_effort}d** | **{total_completed}d** | **{total_effort - total_completed}d** |")

    return "\n".join(lines)


def generate_agile_sprints(data: dict) -> str:
    """Generate Agile Sprints page with a sprint timeline gantt and summary table."""
    lines = [
        "---",
        "title: Agile Sprints",
        f"generated: {datetime.now().isoformat()}",
        "---",
        "",
        "# KF Team — Agile Sprints",
        "",
        "## Sprint Timeline",
        "",
        "```mermaid",
        "gantt",
        "    title Sprint Timeline",
        "    dateFormat YYYY-MM-DD",
        "    axisFormat %d %b",
        "    excludes weekends",
        "",
    ]

    for project, project_data in data.items():
        meta = project_data.get("meta", {})
        s_start = str(meta.get("sprint_start", "")).strip()
        s_end = str(meta.get("sprint_end", "")).strip()
        if _ISO_DATE_RE.match(s_start) and _ISO_DATE_RE.match(s_end):
            sprint = str(meta.get("sprint", "Sprint"))
            lines.append(f"    section {mermaid_gantt_label(project)}")
            lines.append(f"    {mermaid_gantt_label(sprint)} :active, {s_start}, {s_end}")

    lines.append("```")
    lines.append("")

    # Sprint Summary table
    lines.append("## Sprint Summary")
    lines.append("")
    lines.append("| Project | Sprint | Window | Total Effort | % Done |")
    lines.append("| :--- | :--- | :--- | :---: | :---: |")

    grand_total = 0.0
    grand_done = 0.0

    for project, project_data in data.items():
        meta = project_data.get("meta", {})
        tasks = project_data.get("tasks", [])
        sprint = meta.get("sprint", "-")
        s_start_raw = str(meta.get("sprint_start", "")).strip()
        s_end_raw = str(meta.get("sprint_end", "")).strip()
        window = f"{s_start_raw} → {s_end_raw}" if s_start_raw and s_end_raw else "-"
        total_days = sum(parse_effort_days(t["effort"]) for t in tasks)
        done_days = sum(parse_effort_days(t["effort"]) for t in tasks if t["status"] == "Done")
        pct = round(done_days / total_days * 100, 1) if total_days else 0
        grand_total += total_days
        grand_done += done_days
        lines.append(
            f"| {_md_cell(project)} | {_md_cell(str(sprint))} | {_md_cell(window)}"
            f" | {total_days}d | {pct}% |"
        )

    overall_pct = round(grand_done / grand_total * 100, 1) if grand_total else 0
    lines.append(f"| **TOTAL** | | | **{grand_total}d** | **{overall_pct}%** |")

    return "\n".join(lines)


def generate_project_page(project: str, project_data: dict) -> str:
    """Generate individual project page markdown"""
    meta = project_data.get("meta", {})
    tasks = project_data.get("tasks", [])

    # Project type from frontmatter (populated by normalize_frontmatter)
    type_key = meta.get("type", "internal")
    type_display = TYPE_DISPLAY.get(type_key, type_key)

    description = meta.get("description", "") or type_display
    po = meta.get("po", "-") or "-"
    lead = meta.get("lead", "-") or "-"
    depends_on = meta.get("depends_on", [])
    tags = meta.get("tags", [])

    sprint = meta.get("sprint", "-")
    sprint_start = meta.get("sprint_start", "")
    sprint_end = meta.get("sprint_end", "")
    sprint_period = f"{sprint_start} to {sprint_end}" if sprint_start and sprint_end else "-"

    deps_display = ", ".join(
        f"[{d}]({{{{ '/projects/{d.lower()}/' | relative_url }}}})" for d in depends_on
    ) if depends_on else "None"

    branch = PROJECT_BRANCHES.get(project, "master")
    edit_url = EDIT_URL_TEMPLATE.format(repo=project, branch=branch)
    # Guided Kanban Builder (validated form → correct kanban.md) with a raw-editor
    # fallback. Liquid relative_url resolves the baseurl at Jekyll build time.
    builder_link = "{{ '/kanban-builder/' | relative_url }}?project=" + project

    lines = [
        "---",
        f"title: {project}",
        f"description: {json.dumps(description)}",
        f"project: {project}",
        f"type: {type_key}",
        f"edit_url: \"{edit_url}\"",
        f"generated: {datetime.now().isoformat()}",
        "---",
        "",
        f"# {project}",
        "",
        f"> {_md_cell(description)}",
        "",
        "## Status",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        "| Status | Active |",
        f"| Type | {_md_cell(type_display)} |",
        f"| PO | {_md_cell(po)} |",
        f"| Lead | {_md_cell(lead)} |",
        f"| Current Sprint | {_md_cell(sprint)} |",
        f"| Sprint Period | {sprint_period} |",
        f"| Tags | {', '.join(_md_cell(t) for t in tags) if tags else '-'} |",
        f"| Dependencies | {deps_display} |",
        "",
    ]

    # Generate Kanban diagram if tasks exist
    if tasks:
        lines.append(
            f"## Current Sprint Kanban &nbsp; [Edit Kanban]({builder_link}) "
            f"<sup>·&nbsp;[raw]({edit_url})</sup>"
        )
        lines.append("")

        # Group tasks by status for the HTML board
        statuses = {STATUS_TO_MERMAID[s]: [] for s in TASK_STATUSES}

        for task in tasks:
            status = task["status"]
            mermaid_status = STATUS_TO_MERMAID.get(status)
            if mermaid_status and mermaid_status in statuses:
                statuses[mermaid_status].append({**task})

        lines.append(_render_kanban_board(statuses, link_project=False))
        lines.append("")

        # Task summary table (6-col if any task has dates, 4-col otherwise)
        has_dates = any(task.get("start") or task.get("end") for task in tasks)
        lines.append("## Task Summary")
        lines.append("")
        if has_dates:
            lines.append("| Task | Assignee | Effort | Start | End | Status |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for task in tasks:
                lines.append(f"| {_md_cell(task['task'])} | {_md_cell(task['assignee'])} | {task['effort']} "
                             f"| {_md_cell(task.get('start', ''))} | {_md_cell(task.get('end', ''))} | {task['status']} |")
        else:
            lines.append("| Task | Assignee | Effort | Status |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for task in tasks:
                lines.append(f"| {_md_cell(task['task'])} | {_md_cell(task['assignee'])} | {task['effort']} | {task['status']} |")

        lines.append("")

        # LOE summary
        total_effort = sum(parse_effort_days(t["effort"]) for t in tasks)
        completed = sum(parse_effort_days(t["effort"]) for t in tasks if t["status"] == "Done")
        in_progress = sum(parse_effort_days(t["effort"]) for t in tasks if t["status"] == "In Progress")
        remaining = total_effort - completed

        lines.append("## LOE Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("| :--- | :--- |")
        lines.append(f"| Total Effort | {total_effort}d |")
        lines.append(f"| In Progress | {in_progress}d |")
        lines.append(f"| Completed | {completed}d |")
        lines.append(f"| Remaining | {remaining}d |")
        lines.append("")

        # Sprint Gantt chart (only if sprint dates are available)
        sprint_start = project_data.get("meta", {}).get("sprint_start")
        sprint_end = project_data.get("meta", {}).get("sprint_end")
        if sprint_start and sprint_end:
            lines.append("## Sprint Timeline")
            lines.append("")
            lines.append("```mermaid")
            lines.append("gantt")
            lines.append(f"    title {sprint} — {project}")
            lines.append("    dateFormat YYYY-MM-DD")
            lines.append("    excludes weekends")
            lines.append("")

            # Schedule tasks: use explicit dates if available, else auto-schedule
            cursor = str(sprint_start)
            status_order = ["Done", "In Progress", "Review", "Todo"]
            sorted_tasks = sorted(tasks, key=lambda t: status_order.index(t["status"])
                                  if t["status"] in status_order else 99)

            for task in sorted_tasks:
                effort_d = parse_effort_days(task["effort"])
                if effort_d <= 0:
                    effort_d = 1
                effort_str = f"{int(effort_d)}d"
                # Only accept real ISO dates; placeholders ("—", "-", "TBD") fall
                # back to the auto-schedule cursor / effort duration.
                start_raw = task.get("start", "").strip()
                end_raw = task.get("end", "").strip()
                t_start = start_raw if _ISO_DATE_RE.match(start_raw) else cursor
                t_end = end_raw if _ISO_DATE_RE.match(end_raw) else ""
                label = mermaid_gantt_label(task["task"])

                if task["status"] == "Done":
                    modifier = "done, "
                elif task["status"] == "In Progress":
                    modifier = "active, "
                else:
                    modifier = ""

                if t_end:
                    lines.append(f"    {label} :{modifier}{t_start}, {t_end}")
                else:
                    lines.append(f"    {label} :{modifier}{t_start}, {effort_str}")

                # Advance cursor for next auto-scheduled task
                try:
                    start_dt = datetime.strptime(t_start, "%Y-%m-%d")
                    cursor = (start_dt + timedelta(days=int(effort_d))).strftime("%Y-%m-%d")
                except ValueError:
                    pass

            lines.append("```")
            lines.append("")

    else:
        lines.append("## Kanban")
        lines.append("")
        lines.append("*No tasks found in kanban.md*")
        lines.append("")

    # Links
    lines.append("## Links")
    lines.append("")
    lines.append(f"- [Edit Kanban]({builder_link}) ·&nbsp;[raw]({edit_url})")
    lines.append(f"- [Repository](https://github.com/{ORG}/{project})")
    lines.append(f"- [Kanban Board](https://github.com/{ORG}/{project}/blob/{branch}/kanban.md)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Auto-generated by KF Aggregator*")

    return "\n".join(lines)


def generate_dependency_graph(data: dict) -> str:
    """Generate dependency graph page with MermaidJS directed graph."""
    lines = [
        "---",
        "title: Dependency Graph",
        f"generated: {datetime.now().isoformat()}",
        "---",
        "",
        "# KF Team — Dependency Graph",
        "",
        "> Inter-project dependencies (auto-generated from kanban.md frontmatter)",
        "",
        "```mermaid",
        "graph LR",
    ]

    # Add nodes with type-based styling
    for project, project_data in data.items():
        meta = project_data.get("meta", {})
        proj_type = meta.get("type", "internal")
        style_class = TYPE_MERMAID_CLASS.get(proj_type, ":::internal")
        label = mermaid_label_safe(project.replace("-", " ").title())
        lines.append(f'    {mermaid_node_id(project)}["{label}"]{style_class}')

    # Add edges from depends_on
    has_edges = False
    for project, project_data in data.items():
        meta = project_data.get("meta", {})
        for dep in meta.get("depends_on", []):
            if dep in data:
                lines.append(f"    {mermaid_node_id(dep)} --> {mermaid_node_id(project)}")
                has_edges = True

    lines.append("")
    for cdef in TYPE_MERMAID_DEFS:
        lines.append(f"    {cdef}")
    lines.append("```")
    lines.append("")

    if not has_edges:
        lines.append("*No inter-project dependencies declared yet. Add `depends_on` to your kanban.md frontmatter.*")
        lines.append("")

    # Legend (colors match TYPE_MERMAID_DEFS order: saas=green, eu=blue, internal=orange)
    legend_colors = {"saas": "Green", "eu-project": "Blue", "internal": "Orange"}
    lines.append("## Legend")
    lines.append("")
    lines.append("| Color | Type |")
    lines.append("| :--- | :--- |")
    for type_key, display in TYPE_DISPLAY.items():
        lines.append(f"| {legend_colors.get(type_key, '—')} | {_md_cell(display)} |")

    return "\n".join(lines)


def build_loe_rows(data: dict) -> list[dict]:
    """Build the canonical LOE row list — the contract for sheets_sync.py.

    Keys mirror the historic Sheets column order (Project, Sprint, Task, Assignee,
    Effort days, Start, End, Status). Sheets sync reads this file rather than
    re-parsing kanban.md. One parser, one canonical intermediate.
    """
    rows = []
    for project, project_data in data.items():
        meta = project_data["meta"]
        sprint = meta.get("sprint", "-")
        for task in project_data["tasks"]:
            # Defensive: never emit a row for an empty task name. The header-driven
            # parser already drops non-task tables, but a malformed row should not
            # leak a blank LOE entry into the Sheet.
            if not task.get("task", "").strip():
                continue
            rows.append({
                "project": project,
                "sprint": sprint,
                "task": task["task"],
                "assignee": task["assignee"],
                "effort_days": parse_effort_days(task["effort"]),
                "start": task.get("start", ""),
                "end": task.get("end", ""),
                "status": task["status"],
            })
    return rows


def write_loe_yaml(rows: list[dict]) -> None:
    """Persist canonical LOE data for downstream consumers (Sheets export, etc.)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": now_iso(),
        "row_count": len(rows),
        "rows": rows,
    }
    LOE_DATA_FILE.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


# ---------------------------------------------------------------------------
# Migration Gantt -> canonical intermediate (gantt.yml) for the Sheets export
# ---------------------------------------------------------------------------

MIGRATION_GANTT_FILE = DOCS_DIR / "migration-gantt.md"

# Mermaid gantt task line: "Task name (FE+BE)   :id, 2026-05-04, 10d"
# or a milestone:          "M1 Infra ready       :milestone, m1, 2026-05-29, 0d"
_GANTT_TASK_RE = re.compile(
    r"^\s*(?P<name>.+?)\s+:(?P<attrs>[^:]+)$"
)
_GANTT_DISCIPLINE_RE = re.compile(r"\(([^)]*)\)\s*$")


def _add_business_days(start: "datetime.date", working_days: int) -> "datetime.date":
    """Return the inclusive end date after `working_days` working days (skips Sat/Sun).

    The Mermaid gantt declares `excludes weekends`, so durations are in working
    days. A 1-day task ends on its start day; an N-day task ends N-1 working
    days later (inclusive span).
    """
    if working_days <= 0:
        return start
    d = start
    remaining = working_days - 1
    while remaining > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:  # Mon-Fri
            remaining -= 1
    return d


def _normalize_discipline(name: str) -> str:
    """Extract FE / BE / FE+BE from a trailing parenthesised tag; '' if none."""
    m = _GANTT_DISCIPLINE_RE.search(name)
    if not m:
        return ""
    raw = m.group(1).upper().replace(" ", "")
    if ("FE" in raw) and ("BE" in raw):
        return "FE+BE"
    if "FE" in raw:
        return "FE"
    if "BE" in raw:
        return "BE"
    return ""


def parse_migration_gantt(md_path=MIGRATION_GANTT_FILE) -> list[dict]:
    """Parse the Mermaid gantt block in migration-gantt.md into structured rows.

    Returns one row per task/milestone:
        {phase, task, discipline, start, end, effort_days, type}
    `type` is 'task' or 'milestone'. Task names are stripped of their trailing
    (FE/BE) discipline tag — that lives in its own column. Source is already
    emoji-free prose; rows are passed through `strip_emojis` defensively anyway.
    """
    if not md_path.exists():
        print(f"Warning: {md_path} not found — gantt.yml will be empty")
        return []

    content = md_path.read_text(encoding="utf-8")
    block = re.search(r"```mermaid\s*\n(.*?)```", content, re.DOTALL)
    if not block:
        print("Warning: no ```mermaid``` gantt block found — gantt.yml will be empty")
        return []

    rows: list[dict] = []
    section = "-"
    for raw_line in block.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("gantt", "title", "dateFormat", "axisFormat", "excludes")):
            continue
        if line.startswith("section "):
            section = line[len("section "):].strip()
            continue
        m = _GANTT_TASK_RE.match(line)
        if not m:
            continue
        name = m.group("name").strip()
        attrs = [a.strip() for a in m.group("attrs").split(",")]
        is_milestone = attrs and attrs[0] == "milestone"
        if is_milestone:
            attrs = attrs[1:]
        # attrs now: [id, start-date, duration]
        if len(attrs) < 3:
            continue
        start_str, dur_str = attrs[1], attrs[2]
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        dur = int(re.sub(r"\D", "", dur_str) or "0")
        end = _add_business_days(start, dur)
        discipline = "" if is_milestone else _normalize_discipline(name)
        task = _GANTT_DISCIPLINE_RE.sub("", name).strip() if discipline else name
        rows.append({
            "phase": strip_emojis(section),
            "task": strip_emojis(task),
            "discipline": discipline,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "effort_days": dur,
            "type": "milestone" if is_milestone else "task",
        })
    return rows


def write_gantt_yaml(rows: list[dict]) -> None:
    """Persist the migration gantt as a canonical intermediate for the Sheets export."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": now_iso(),
        "row_count": len(rows),
        "rows": rows,
    }
    GANTT_DATA_FILE.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


def _generated_repos() -> set:
    """Repos whose kanban.md is generated from the migration plan-of-record.

    Read from docs/_data/migration_plan.yml (the source of the discipline split).
    The Kanban Builder steers edits for these repos to the plan-of-record instead
    of the generated kanban.md (which a regenerate would overwrite).
    """
    plan_path = DATA_DIR / "migration_plan.yml"
    if not plan_path.exists():
        return set()
    try:
        plan = yaml.safe_load(plan_path.read_text()) or {}
    except yaml.YAMLError:
        return set()
    return {t.get("repo") for t in plan.get("tasks", []) if t.get("repo")}


def write_boards_yaml(data: dict) -> None:
    """Persist per-project meta + tasks for the client-side Kanban Builder page.

    The builder (docs/kanban-builder.html) reads this via Jekyll `site.data.boards`
    to seed its validated form — so the editor never has to retype existing data.
    """
    gen = _generated_repos()
    projects = []
    for project, project_data in data.items():
        meta = project_data["meta"]
        branch = PROJECT_BRANCHES.get(project, "master")
        # A board is "simple" (safe to rebuild whole from frontmatter + one table)
        # when its body has exactly one task table. Rich, multi-table boards
        # (e.g. R3-AAS) would lose prose on a full rebuild — the builder falls
        # back to the raw editor for those.
        raw = project_data.get("raw", "")
        table_count = sum(1 for ln in raw.splitlines() if _is_separator_row(ln))
        projects.append({
            "project": project,
            "branch": branch,
            "edit_url": EDIT_URL_TEMPLATE.format(repo=project, branch=branch),
            "generated": project in gen,
            "simple_board": table_count == 1,
            "meta": {
                "description": meta.get("description", ""),
                "type": meta.get("type", "internal"),
                "po": meta.get("po", ""),
                "lead": meta.get("lead", ""),
                "sprint": meta.get("sprint", "-"),
                "sprint_start": str(meta.get("sprint_start", "")),
                "sprint_end": str(meta.get("sprint_end", "")),
                "depends_on": meta.get("depends_on", []) or [],
                "tags": meta.get("tags", []) or [],
                "team": meta.get("team", {}) or {},
            },
            "tasks": [
                {
                    "task": t["task"],
                    "assignee": t["assignee"],
                    "effort": t["effort"],
                    "start": t.get("start", ""),
                    "end": t.get("end", ""),
                    "status": t["status"],
                }
                for t in project_data["tasks"]
            ],
        })
    payload = {"generated_at": now_iso(), "projects": projects}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "boards.yml").write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    )


def generate_project_pages(data: dict):
    """Generate individual project pages"""
    projects_dir = DOCS_DIR / "_projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    for project, project_data in data.items():
        content = generate_project_page(project, project_data)
        (projects_dir / f"{project}.md").write_text(content)
        print(f"Generated _projects/{project}.md")


def main():
    """Main aggregation workflow"""
    print("KF Aggregator — Starting...")

    # Load data from all repos
    data = load_all_project_data()
    print(f"Loaded data from {len(data)} projects")

    # Generate unified docs
    DOCS_DIR.mkdir(exist_ok=True)

    kanban_content = generate_unified_kanban(data)
    (DOCS_DIR / "unified-kanban.md").write_text(kanban_content)
    print("Generated unified-kanban.md")

    calendar_content = generate_unified_calendar(data)
    (DOCS_DIR / "unified-calendar.md").write_text(calendar_content)
    print("Generated unified-calendar.md")

    loe_content = generate_loe_report(data)
    (DOCS_DIR / "loe-report.md").write_text(loe_content)
    print("Generated loe-report.md")

    # Generate dependency graph
    graph_content = generate_dependency_graph(data)
    (DOCS_DIR / "dependency-graph.md").write_text(graph_content)
    print("Generated dependency-graph.md")

    (DOCS_DIR / "agile-sprints.md").write_text(generate_agile_sprints(data))
    print("Generated agile-sprints.md")

    # Generate individual project pages
    generate_project_pages(data)

    # Per-project board data for the client-side Kanban Builder page
    write_boards_yaml(data)
    print("Wrote board data: docs/_data/boards.yml")

    # Inject auto-blocks into every augmented Jekyll page (those declaring
    # `auto_blocks: [...]` in frontmatter). Idempotent — re-runs replace
    # marked sections without touching surrounding prose.
    context = load_context(DATA_DIR)
    augmented_count = 0
    for md_path in sorted(DOCS_DIR.rglob("*.md")):
        try:
            if process_page(md_path, context):
                augmented_count += 1
                print(f"Refreshed auto-blocks: {md_path.relative_to(DOCS_DIR)}")
        except ValueError as e:
            # Surface but don't fail the whole aggregation — the validator
            # script in CI catches these before merge.
            print(f"WARN: auto-block injection failed for {md_path}: {e}")
    if augmented_count:
        print(f"Refreshed {augmented_count} augmented page(s)")

    # Write canonical LOE data for downstream consumers (Sheets export reads this)
    loe_rows = build_loe_rows(data)
    write_loe_yaml(loe_rows)
    print(f"Wrote canonical LOE data: {len(loe_rows)} rows -> {LOE_DATA_FILE}")

    # Write canonical migration-gantt data (downstream: Sheets `Gantt_example` tab)
    gantt_rows = parse_migration_gantt()
    write_gantt_yaml(gantt_rows)
    print(f"Wrote canonical Gantt data: {len(gantt_rows)} rows -> {GANTT_DATA_FILE}")

    # Update aggregator section of sync_status (sheets_export section is written
    # later by sheets_sync.py — it stays as-is from the previous run until then)
    update_sync_status(
        "aggregator",
        last_run_at=now_iso(),
        last_run_status="ok",
        source_repo_count=len(data),
        task_count=len(loe_rows),
        errors=[],
    )

    print("KF Aggregator — Done!")


if __name__ == "__main__":
    main()
