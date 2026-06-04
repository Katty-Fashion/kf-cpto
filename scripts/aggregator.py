#!/usr/bin/env python3
"""
Aggregator Script for KF Team Git-Native Project Management

Merges kanban.md files from all project repos and generates:
- unified-kanban.md
- unified-calendar.md
- loe-report.md
- docs/_projects/{project}.md (per-project pages — Jekyll collection)
"""

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
    update_sync_status,
)

PROJECTS = load_projects()


def _status_legend() -> str:
    """Generate HTML status legend with colored pills."""
    pills = []
    for status in TASK_STATUSES:
        css_class = f"status-pill--{status.lower().replace(' ', '-')}"
        pills.append(f'<span class="status-pill {css_class}">{status}</span>')
    return '<div class="status-legend">' + "\n".join(pills) + "</div>"



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
        _status_legend(),
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

    # Generate Mermaid kanban (simple format for GitHub compatibility)
    lines.append("```mermaid")
    lines.append("kanban")

    for status, tasks in statuses.items():
        lines.append(f"  {status}")
        for task in tasks:
            task_label = f"{task['project']}: {task['task']}"
            lines.append(f'    {task["id"]}["{task_label}"]')

    lines.append("```")
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
        lines.append(f"| {project} | {count_cols} | {total} |")

    return "\n".join(lines)


def generate_unified_calendar(data: dict) -> str:
    """Generate unified calendar markdown with Gantt chart"""
    lines = [
        "---",
        "title: Unified Calendar",
        f"generated: {datetime.now().isoformat()}",
        "---",
        "",
        "# KF Team — Unified Calendar",
        "",
        "> CPTO 50h Monthly Allocation",
        "",
        "```mermaid",
        "pie title Alocarea Lunara 50 Ore — CPTO KF",
        '    "Sync & Ritm Echipa (Sprint, Retro, All Hands)" : 10',
        '    "Technical Health & Architecture" : 12',
        '    "Pre-Sales & Business Alignment" : 8',
        '    "Proiecte EU (AI-RISE, AIREGIO)" : 10',
        '    "SaaS Products (NuoForm, Waist Mgmt)" : 8',
        '    "Team Events & People" : 2',
        "```",
        "",
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
        if meta.get("sprint_start") and meta.get("sprint_end"):
            sprint = meta.get("sprint", "Sprint")
            lines.append(f"    section {project}")
            lines.append(f"    {sprint} :active, {meta['sprint_start']}, {meta['sprint_end']}")

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
        lines.append(f"| {project} | {sprint} | {project_total}d | {project_completed}d | {remaining}d |")

        total_effort += project_total
        total_completed += project_completed

    lines.append(f"| **Total** | | **{total_effort}d** | **{total_completed}d** | **{total_effort - total_completed}d** |")

    lines.append("")
    lines.append("## Effort by Assignee")
    lines.append("")
    lines.append("| Assignee | Total Effort | In Progress | Completed |")
    lines.append("| :--- | :---: | :---: | :---: |")

    # Aggregate by assignee
    assignee_data = {}
    for project, project_data in data.items():
        for task in project_data["tasks"]:
            assignee = task["assignee"]
            if assignee not in assignee_data:
                assignee_data[assignee] = {"total": 0, "in_progress": 0, "completed": 0}

            days = parse_effort_days(task["effort"])
            assignee_data[assignee]["total"] += days
            if task["status"] == "Done":
                assignee_data[assignee]["completed"] += days
            elif task["status"] == "In Progress":
                assignee_data[assignee]["in_progress"] += days

    for assignee, stats in sorted(assignee_data.items()):
        lines.append(f"| {assignee} | {stats['total']}d | {stats['in_progress']}d | {stats['completed']}d |")

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
        f"[{d}]({{{{ '/projects/{d}/' | relative_url }}}})" for d in depends_on
    ) if depends_on else "None"

    branch = PROJECT_BRANCHES.get(project, "master")
    edit_url = EDIT_URL_TEMPLATE.format(repo=project, branch=branch)

    lines = [
        "---",
        f"title: {project}",
        f"description: \"{description}\"",
        f"project: {project}",
        f"type: {type_key}",
        f"edit_url: \"{edit_url}\"",
        f"generated: {datetime.now().isoformat()}",
        "---",
        "",
        f"# {project}",
        "",
        f"> {description}",
        "",
        "## Status",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        "| Status | Active |",
        f"| Type | {type_display} |",
        f"| PO | {po} |",
        f"| Lead | {lead} |",
        f"| Current Sprint | {sprint} |",
        f"| Sprint Period | {sprint_period} |",
        f"| Tags | {', '.join(tags) if tags else '-'} |",
        f"| Dependencies | {deps_display} |",
        "",
    ]

    # Generate Kanban diagram if tasks exist
    if tasks:
        lines.append(f"## Current Sprint Kanban &nbsp; [Edit Kanban]({edit_url})")
        lines.append("")
        lines.append(_status_legend())
        lines.append("")
        lines.append("```mermaid")
        lines.append("kanban")

        # Group tasks by status with counter for unique IDs
        statuses = {STATUS_TO_MERMAID[s]: [] for s in TASK_STATUSES}

        task_counter = 0
        for task in tasks:
            status = task["status"]
            mermaid_status = STATUS_TO_MERMAID.get(status)
            if mermaid_status and mermaid_status in statuses:
                task_counter += 1
                statuses[mermaid_status].append({**task, "id": f"t{task_counter}"})

        for status, status_tasks in statuses.items():
            lines.append(f"  {status}")
            for task in status_tasks:
                lines.append(f'    {task["id"]}["{task["task"]}"]')

        lines.append("```")
        lines.append("")

        # Task summary table (6-col if any task has dates, 4-col otherwise)
        has_dates = any(task.get("start") or task.get("end") for task in tasks)
        lines.append("## Task Summary")
        lines.append("")
        if has_dates:
            lines.append("| Task | Assignee | Effort | Start | End | Status |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for task in tasks:
                lines.append(f"| {task['task']} | {task['assignee']} | {task['effort']} "
                             f"| {task.get('start', '')} | {task.get('end', '')} | {task['status']} |")
        else:
            lines.append("| Task | Assignee | Effort | Status |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for task in tasks:
                lines.append(f"| {task['task']} | {task['assignee']} | {task['effort']} | {task['status']} |")

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
                t_start = task.get("start", "").strip() or cursor
                t_end = task.get("end", "").strip()
                label = task["task"].replace(":", " ")

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

        # Effort distribution pie chart
        effort_by_status = {}
        for task in tasks:
            days = parse_effort_days(task["effort"])
            if days > 0:
                effort_by_status[task["status"]] = effort_by_status.get(task["status"], 0) + days

        if effort_by_status:
            lines.append("## Effort Distribution")
            lines.append("")
            lines.append("```mermaid")
            lines.append("pie title Effort by Status")
            for status in TASK_STATUSES:
                if status in effort_by_status:
                    lines.append(f'    "{status}" : {effort_by_status[status]}')
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
    lines.append(f"- [Edit Kanban]({edit_url})")
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
        label = project.replace("-", " ").title()
        lines.append(f"    {project}[{label}]{style_class}")

    # Add edges from depends_on
    has_edges = False
    for project, project_data in data.items():
        meta = project_data.get("meta", {})
        for dep in meta.get("depends_on", []):
            if dep in data:
                lines.append(f"    {dep} --> {project}")
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
        lines.append(f"| {legend_colors.get(type_key, '—')} | {display} |")

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

    # Generate individual project pages
    generate_project_pages(data)

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
