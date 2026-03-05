#!/usr/bin/env python3
"""
Aggregator Script for KF Team Git-Native Project Management

Merges kanban.md files from all project repos and generates:
- unified-kanban.md
- unified-calendar.md
- loe-report.md
- docs/_projects/{project}.md (per-project pages — Jekyll collection)
"""

from datetime import datetime

from utils import (
    DOCS_DIR,
    ORG,
    EDIT_URL_TEMPLATE,
    TASK_STATUSES,
    STATUS_TO_MERMAID,
    STATUS_PRIORITY,
    STATUS_COLORS,
    TYPE_DISPLAY,
    TYPE_MERMAID_CLASS,
    TYPE_MERMAID_DEFS,
    load_projects,
    load_all_project_data,
    parse_effort_days,
)

PROJECTS = load_projects()


def _status_legend() -> str:
    """Generate HTML status legend with colored pills."""
    pills = []
    for status in TASK_STATUSES:
        css_class = f"status-pill--{status.lower().replace(' ', '-')}"
        pills.append(f'<span class="status-pill {css_class}">{status}</span>')
    return '<div class="status-legend">' + "\n".join(pills) + "</div>"


def _task_metadata(task: dict) -> str:
    """Build MermaidJS @{} metadata string for a kanban task."""
    parts = []
    priority = STATUS_PRIORITY.get(task.get("status"))
    if priority:
        parts.append(f"priority: '{priority}'")
    assignee = task.get("assignee", "").lstrip("@")
    if assignee:
        parts.append(f"assigned: '{assignee}'")
    return f"@{{ {', '.join(parts)} }}" if parts else ""


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
            meta = _task_metadata(task)
            lines.append(f"    {task['id']}[{task_label}]{meta}")

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

    edit_url = EDIT_URL_TEMPLATE.format(repo=project)

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
        edit_url = EDIT_URL_TEMPLATE.format(repo=project)
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
                meta = _task_metadata(task)
                lines.append(f"    {task['id']}[{task['task']}]{meta}")

        lines.append("```")
        lines.append("")

        # Task summary table
        lines.append("## Task Summary")
        lines.append("")
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
    lines.append(f"- [Kanban Board](https://github.com/{ORG}/{project}/blob/master/kanban.md)")
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

    print("KF Aggregator — Done!")


if __name__ == "__main__":
    main()
