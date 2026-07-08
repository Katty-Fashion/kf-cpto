#!/usr/bin/env python3
"""
OKF Bundle Emitter for KF CPTO Dashboard.

Generates a conformant Open Knowledge Format v0.1 bundle at docs/okf/ from
already-parsed in-memory data.  Pure transform — never re-parses kanban.md.

Entry point: generate_okf_bundle(all_project_data, loe_rows, calendar_data, base_dir)
Returns the count of markdown files written.

OKF spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from utils import ORG, REPOS_DIR


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _slug(name: str) -> str:
    """Project-name slug — same convention as docs/_projects/ (lower-case)."""
    return name.lower()


def _milestone_slug(name: str) -> str:
    """Stable slug for a milestone name: lower-case, spaces/special chars -> hyphens."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _task_slug(task_name: str, seen: dict[str, int] | None = None, index: int = 0) -> str:
    """Stable, deterministic, collision-safe slug for a task name.

    Strips surrounding brackets (e.g. ``[F4.S12.QC Module]`` -> ``f4-s12-qc-module``),
    lower-cases, replaces any run of non-alphanumeric characters with a single
    hyphen, and trims leading/trailing hyphens.

    De-duplicates WITHIN a project by appending ``-2``, ``-3``, … to later
    collisions (deterministic by stable input order).  The ``seen`` dict is
    mutated in-place — pass the same dict across all calls for one project.

    An empty or degenerate result falls back to ``task-{index}``.

    Args:
        task_name: Raw task name string from loe_rows.
        seen:      Mutable collision-tracking dict (slug -> next suffix).
                   Pass ``{}`` for the first task in a project; reuse for all.
        index:     Zero-based position of the task in the project's row list.

    Returns:
        A unique, stable slug string.
    """
    if seen is None:
        seen = {}

    # Strip surrounding square brackets (e.g. "[F4.S12.QC Module]")
    s = re.sub(r"^\[|\]$", "", task_name.strip())
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")

    if not s:
        s = f"task-{index}"

    # De-duplicate: if slug already used, append -2, -3, …
    if s not in seen:
        seen[s] = 2  # next suffix for this base slug
        return s

    candidate = f"{s}-{seen[s]}"
    seen[s] += 1
    # Store the candidate as well so a triple-collision also gets a unique suffix
    while candidate in seen:
        candidate = f"{s}-{seen[s]}"
        seen[s] += 1
    seen[candidate] = 2
    return candidate


def _quote_scalar(value: str) -> str:
    """Return a YAML-safe single-line scalar representation.

    Uses double-quoted form when the value contains characters that would
    trigger special YAML parsing (colons, hashes, at-signs leading the value,
    etc.).  Avoids yaml.dump to prevent accidental multi-document output
    (yaml.dump emits '...' separators for strings containing dots).
    """
    # Characters that require quoting in unquoted YAML scalars
    must_quote = any(c in value for c in (':', '#', '"', "'", '\n', '[', ']', '{', '}'))
    # Leading special chars also need quoting
    if not must_quote and value and value[0] in ('-', '?', '&', '*', '!', '|', '>', '@', '`'):
        must_quote = True
    if must_quote:
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _frontmatter(fields: dict[str, Any]) -> str:
    """Render a YAML frontmatter block from ordered key-value pairs."""
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_quote_scalar(str(item))}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        else:
            raw = str(value) if value is not None else ""
            lines.append(f"{key}: {_quote_scalar(raw)}")
    lines.append("---")
    return "\n".join(lines)


def _write(path: Path, content: str) -> None:
    """Write content to path, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# GSD delivery bridge — optional enrichment #1
# ---------------------------------------------------------------------------

def _read_gsd_state(project: str) -> dict[str, Any]:
    """Read .planning/STATE.md YAML frontmatter for a project repo.

    Fully defensive: returns {} if the file doesn't exist or fails to parse.
    Never fails — most repos have no .planning directory.
    """
    state_path = REPOS_DIR / project / ".planning" / "STATE.md"
    if not state_path.exists():
        return {}
    try:
        text = state_path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return {}
        return yaml.safe_load(match.group(1)) or {}
    except Exception:  # noqa: BLE001
        return {}


# ---------------------------------------------------------------------------
# Per-project LOE rollup from loe_rows
# ---------------------------------------------------------------------------

def _project_loe(project: str, loe_rows: list[dict]) -> dict[str, float]:
    """Compute total / done / remaining effort_days for a project."""
    rows = [r for r in loe_rows if r.get("project") == project]
    total = sum(r.get("effort_days", 0) for r in rows)
    done = sum(r.get("effort_days", 0) for r in rows if r.get("status") == "Done")
    return {"total": total, "done": done, "remaining": total - done}


# ---------------------------------------------------------------------------
# File generators
# ---------------------------------------------------------------------------

def _gen_root_index(
    okf_dir: Path,
    all_project_data: dict,
    loe_rows: list[dict],
    task_count: int = 0,
) -> str:
    """docs/okf/index.md — root with progressive-disclosure links."""
    project_count = len(all_project_data)
    total_effort = sum(r.get("effort_days", 0) for r in loe_rows)
    done_effort = sum(r.get("effort_days", 0) for r in loe_rows if r.get("status") == "Done")
    remaining = total_effort - done_effort

    lines = [
        "---",
        'okf_version: "0.1"',
        "---",
        "",
        "# KF CPTO — Open Knowledge Bundle",
        "",
        "This directory is a conformant OKF v0.1 bundle: a directed graph of markdown",
        "concepts cross-linked by absolute bundle-relative paths.  It is generated by",
        "`scripts/okf_export.py` from already-parsed kanban and calendar data — never",
        "re-parse individual repo files; consume this bundle instead.",
        "",
        "## Sections",
        "",
        f"- [Projects](/projects/index.md) — {project_count} tracked repos",
        f"- [Tasks](/tasks/index.md) — {task_count} task concepts",
        "- [Metrics](/metrics/index.md) — LOE and RAG status definitions",
        "- [Milestones](/milestones/index.md) — Migration calendar milestones",
        "- [log.md](/log.md) — Change history",
        "",
        "## Effort Summary",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Total declared effort | {total_effort:.0f}d |",
        f"| Done | {done_effort:.0f}d |",
        f"| Remaining | {remaining:.0f}d |",
        "",
        "> **Effort semantics:** `Nd` = person-days as declared in each `kanban.md`.",
        "> See [/metrics/loe.md](/metrics/loe.md) for the full definition and the",
        "> distinction from `gantt.yml` working-day spans.",
    ]
    return "\n".join(lines) + "\n"


def _gen_log(all_project_data: dict) -> str:
    """docs/okf/log.md — deterministic change history from source last_updated dates."""
    # Collect dated entries from project metadata
    entries: list[tuple[str, str]] = []  # (date, description)
    for project, project_data in all_project_data.items():
        meta = project_data.get("meta", {})
        lu = str(meta.get("last_updated", "")).strip()
        # Only use real ISO dates to stay deterministic
        if _ISO_DATE_RE.match(lu):
            entries.append((lu, f"**Update** `{project}` kanban last_updated: {lu}"))

    # Sort by date descending, then project name for stable ordering
    entries.sort(key=lambda e: e[0], reverse=True)

    # Group by date
    by_date: dict[str, list[str]] = {}
    for date, desc in entries:
        by_date.setdefault(date, []).append(desc)

    lines = [
        "# OKF Bundle — Change Log",
        "",
        "> Entries are derived from `last_updated` frontmatter in tracked `kanban.md`",
        "> files.  Dates reflect source data, not aggregator run time.",
        "",
    ]

    if by_date:
        for date in sorted(by_date.keys(), reverse=True):
            lines.append(f"## {date}")
            lines.append("")
            for entry in sorted(by_date[date]):
                lines.append(f"- {entry}")
            lines.append("")
    else:
        lines.append("_No `last_updated` dates found in tracked kanban files._")
        lines.append("")

    return "\n".join(lines)


def _gen_projects_index(all_project_data: dict) -> str:
    """docs/okf/projects/index.md — progressive-disclosure project list."""
    lines = [
        "# Projects",
        "",
        "> One concept file per tracked repository.  Each file carries a LOE rollup,",
        "> task table, dependency cross-links, and an optional GSD delivery bridge.",
        "",
    ]
    for project in sorted(all_project_data.keys()):
        meta = all_project_data[project].get("meta", {})
        desc = str(meta.get("description", "") or "").strip()
        slug = _slug(project)
        lines.append(f"- [{project}](/projects/{slug}.md){' — ' + desc if desc else ''}")
    lines.append("")
    return "\n".join(lines)


def _gen_project_concept(
    project: str,
    project_data: dict,
    loe_rows: list[dict],
    known_projects: set[str] | None = None,
    has_task_concepts: bool = False,
) -> str:
    """docs/okf/projects/{slug}.md — OKF Project concept."""
    meta = project_data.get("meta", {})
    tasks = project_data.get("tasks", [])

    description = str(meta.get("description", "") or "").strip()
    po = str(meta.get("po", "") or "").strip()
    lead = str(meta.get("lead", "") or "").strip()
    sprint = str(meta.get("sprint", "") or "").strip()
    tags = [str(t) for t in (meta.get("tags") or [])]
    depends_on = [str(d) for d in (meta.get("depends_on") or [])]
    last_updated = str(meta.get("last_updated", "") or "").strip()

    # Use source last_updated as timestamp (deterministic; not run time)
    timestamp = last_updated if _ISO_DATE_RE.match(last_updated) else ""

    # Resource links
    branch = meta.get("branch", "master") or "master"
    repo_url = f"https://github.com/{ORG}/{project}"
    dashboard_url = f"https://katty-fashion.github.io/kf-cpto/projects/{_slug(project)}/"

    # Build frontmatter
    fm_fields: dict[str, Any] = {
        "type": "Project",
        "title": project,
    }
    if description:
        fm_fields["description"] = description
    fm_fields["resource"] = [repo_url, dashboard_url]
    if tags:
        fm_fields["tags"] = tags
    if timestamp:
        fm_fields["timestamp"] = timestamp
    if po:
        fm_fields["po"] = po
    if lead:
        fm_fields["lead"] = lead
    if sprint:
        fm_fields["sprint"] = sprint

    loe = _project_loe(project, loe_rows)

    # GSD delivery bridge
    gsd = _read_gsd_state(project)
    gsd_milestone = str(gsd.get("milestone", "") or "").strip()
    gsd_percent = gsd.get("progress", {})
    if isinstance(gsd_percent, dict):
        gsd_percent = gsd_percent.get("percent", None)
    else:
        gsd_percent = None

    lines = [
        _frontmatter(fm_fields),
        "",
        f"# {project}",
        "",
    ]
    if description:
        lines += [f"> {description}", ""]

    # LOE rollup
    lines += [
        "## LOE Rollup",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Total effort | {loe['total']:.0f}d |",
        f"| Done | {loe['done']:.0f}d |",
        f"| Remaining | {loe['remaining']:.0f}d |",
        "",
        "> Effort is person-days (`Nd`) as declared in `kanban.md`.",
        "> See [/metrics/loe.md](/metrics/loe.md) for semantics.",
        "",
    ]

    # GSD delivery bridge (only shown when STATE.md exists and has data)
    if gsd_milestone or gsd_percent is not None:
        lines += ["## Delivery (GSD)", ""]
        if gsd_milestone:
            lines.append(f"- Milestone: `{gsd_milestone}`")
        if gsd_percent is not None:
            lines.append(f"- Progress: {gsd_percent}%")
        lines.append("")

    # Task table
    if tasks:
        lines += [
            "## Tasks",
            "",
            "| Task | Assignee | Effort | Status |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for t in tasks:
            task_name = str(t.get("task", "")).replace("|", "\\|")
            assignee = str(t.get("assignee", "")).replace("|", "\\|")
            effort = str(t.get("effort", ""))
            status = str(t.get("status", ""))
            lines.append(f"| {task_name} | {assignee} | {effort} | {status} |")
        lines.append("")
        # Down-link to addressable task concepts when they exist
        if has_task_concepts:
            task_slug = _slug(project)
            lines.append(
                f"See task concepts: [/tasks/{task_slug}/index.md](/tasks/{task_slug}/index.md)"
            )
            lines.append("")

    # Dependencies — only cross-link to projects that exist in this bundle.
    # Deps referencing repos outside the tracked set (e.g. 'nuoform' not yet
    # in the allowlist) are listed as plain text to avoid broken links.
    if depends_on:
        lines += ["## Dependencies", ""]
        for dep in depends_on:
            dep_slug = _slug(dep)
            if known_projects is None or dep in known_projects:
                lines.append(f"- [{dep}](/projects/{dep_slug}.md)")
            else:
                lines.append(f"- {dep} _(not in tracked repo set)_")
        lines.append("")
    else:
        lines += ["## Dependencies", "", "None declared.", ""]

    return "\n".join(lines)


def _gen_metrics_index() -> str:
    """docs/okf/metrics/index.md — progressive-disclosure metrics list."""
    lines = [
        "# Metrics",
        "",
        "> Metric concepts define the measurement vocabulary used across this bundle.",
        "",
        "- [/metrics/loe.md](/metrics/loe.md) — Level of Effort (person-days vs working-day span)",
        "- [/metrics/status-rag.md](/metrics/status-rag.md) — RAG status colour semantics",
        "",
    ]
    return "\n".join(lines)


def _gen_loe_metric() -> str:
    """docs/okf/metrics/loe.md — LOE metric concept."""
    fm_fields = {
        "type": "Metric",
        "title": "Level of Effort (LOE)",
        "description": "Person-days of work as declared in kanban.md, distinct from gantt working-day spans",
        "tags": ["loe", "effort", "person-days", "metrics"],
    }
    lines = [
        _frontmatter(fm_fields),
        "",
        "# Level of Effort (LOE)",
        "",
        "## Definition",
        "",
        "**LOE = person-days (`Nd`)** as declared in each project's `kanban.md` task table",
        "(e.g. `5d`, `10d`).  It represents the *estimated work* one person needs to",
        "complete a task, regardless of calendar span.",
        "",
        "## Distinction from `gantt.yml` effort_days",
        "",
        "The migration Gantt chart (`docs/migration-gantt.md`) uses a separate field",
        "`effort_days` that represents the **inclusive working-day span** of a bar on",
        "the chart — how many working days the bar occupies on the timeline.  This is",
        "a *scheduling* quantity, not a *capacity* quantity.",
        "",
        "| Concept | Field | Semantics | Source |",
        "| :--- | :--- | :--- | :--- |",
        "| LOE | `kanban.md` effort column (`Nd`) | Person-days of work | Per-project `kanban.md` |",
        "| Gantt span | `gantt.yml` `effort_days` | Inclusive working-day calendar span | `docs/migration-gantt.md` |",
        "",
        "## Discipline-split no-double-counting rule",
        "",
        "When a migration task spans both FE and BE disciplines (e.g. `(FE+BE)` tag in",
        "the gantt), the task's effort is **split across two separate task rows** —",
        "one per discipline.  Summing LOE across both rows gives the total capacity",
        "required.  Do NOT add a combined row on top of the split rows.",
        "",
        "## Usage in this bundle",
        "",
        "Each project concept file (under [/projects/](/projects/index.md)) shows a",
        "**LOE rollup** computed from the canonical `docs/_data/loe.yml` intermediate,",
        "which is written by `scripts/aggregator.py` after parsing all `kanban.md` files.",
        "Downstream consumers (Google Sheets export) read `loe.yml` — they never",
        "re-parse `kanban.md` directly.",
    ]
    return "\n".join(lines) + "\n"


def _gen_status_rag_metric() -> str:
    """docs/okf/metrics/status-rag.md — RAG status colour semantics."""
    fm_fields = {
        "type": "Metric",
        "title": "RAG Status Colours",
        "description": "Red-Amber-Green task status colour semantics for kanban and gantt views",
        "tags": ["rag", "status", "colours", "kanban", "gantt"],
    }
    lines = [
        _frontmatter(fm_fields),
        "",
        "# RAG Status Colours",
        "",
        "## Definition",
        "",
        "Tasks and gantt bars are coloured by a Red-Amber-Green (RAG) scheme that",
        "combines the declared `status` field with start/end dates relative to today.",
        "",
        "| Colour | Mermaid modifier | Condition |",
        "| :--- | :--- | :--- |",
        "| Green (Done) | `done,` | `status == Done` |",
        "| Amber (In work) | `active,` | `status In Progress` or `Review` |",
        "| Red (Late / At risk) | `crit,` | overdue (`end < today` and not Done), or should-have-started (`status Todo` and `start < today`) |",
        "| Grey (Planned) | _(none)_ | `status Todo` and start is in the future or undated |",
        "",
        "## Source of truth",
        "",
        "The `utils.rag_modifier(status, start_iso, end_iso, today)` function in",
        "`scripts/utils.py` is the single source of truth for this logic.  All gantt",
        "charts in the dashboard use it; this document mirrors that definition.",
        "",
        "## Colour mapping",
        "",
        "Colours are applied via Mermaid `themeVariables` in `docs/_layouts/default.html`,",
        "not via external CSS.  The legend in every gantt page (`GANTT_LEGEND_HTML`)",
        "must stay in sync with this table.",
    ]
    return "\n".join(lines) + "\n"


def _gen_task_concept(project: str, row: dict, project_meta: dict) -> str:
    """docs/okf/tasks/{project_slug}/{task_slug}.md — OKF Task concept.

    Uses the project's ``last_updated`` as the concept timestamp so the output
    is deterministic across aggregator runs (never uses run time).

    Args:
        project:      Canonical project name (matches loe_rows ``project`` key).
        row:          Single loe_rows entry for this task.
        project_meta: ``project_data["meta"]`` dict for the owning project.

    Returns:
        Markdown string for the task concept file.
    """
    task_name = str(row.get("task", "")).strip()
    status = str(row.get("status", "")).strip()
    assignee = str(row.get("assignee", "")).strip()
    effort_days = row.get("effort_days", 0)
    sprint = str(row.get("sprint", "")).strip()

    # Deterministic timestamp: project's last_updated, not run time
    last_updated = str(project_meta.get("last_updated", "") or "").strip()
    timestamp = last_updated if _ISO_DATE_RE.match(last_updated) else ""

    # Effort as a readable string (e.g. "5d"); omit decimal for whole numbers
    if isinstance(effort_days, float) and effort_days == int(effort_days):
        effort_str = f"{int(effort_days)}d"
    else:
        effort_str = f"{effort_days}d"

    # Resource: dashboard project page (canonical, always-available)
    dashboard_url = f"https://katty-fashion.github.io/kf-cpto/projects/{_slug(project)}/"

    fm_fields: dict[str, Any] = {
        "type": "Task",
        "title": task_name,
        "status": status,
        "assignee": assignee,
        "effort": effort_str,
        "sprint": sprint,
    }
    if timestamp:
        fm_fields["timestamp"] = timestamp
    fm_fields["resource"] = dashboard_url

    project_slug = _slug(project)

    lines = [
        _frontmatter(fm_fields),
        "",
        f"# {task_name}",
        "",
        f"**Status:** {status} | **Effort:** {effort_str} | **Assignee:** {assignee}",
        "",
        "## Links",
        "",
        f"- [Project: {project}](/projects/{project_slug}.md)",
        "- [LOE metric definition](/metrics/loe.md)",
    ]
    return "\n".join(lines) + "\n"


def _gen_tasks_project_index(project: str, task_entries: list[tuple[str, str]]) -> str:
    """docs/okf/tasks/{project_slug}/index.md — per-project task listing.

    No frontmatter (index files are exempt from the ``type`` requirement).

    Args:
        project:      Canonical project name.
        task_entries: Ordered list of (task_slug, task_title) for this project.

    Returns:
        Markdown string for the per-project task index file.
    """
    project_slug = _slug(project)
    lines = [
        f"# Tasks — {project}",
        "",
        f"> Task concepts for [{project}](/projects/{project_slug}.md).",
        f"> Each file is an addressable OKF ``type: Task`` concept.",
        "",
    ]
    for slug, title in task_entries:
        lines.append(f"- [{title}](/tasks/{project_slug}/{slug}.md)")
    lines.append("")
    return "\n".join(lines)


def _gen_tasks_root_index(project_task_counts: list[tuple[str, int]]) -> str:
    """docs/okf/tasks/index.md — tasks grouped by project with counts.

    No frontmatter (index file).

    Args:
        project_task_counts: Ordered list of (project_name, task_count).

    Returns:
        Markdown string for the root tasks index file.
    """
    total = sum(count for _, count in project_task_counts)
    lines = [
        "# Tasks",
        "",
        f"> {total} task concepts across {len(project_task_counts)} projects.",
        "> Each concept is an addressable OKF node cross-linked to its project.",
        "",
    ]
    for project, count in project_task_counts:
        project_slug = _slug(project)
        lines.append(
            f"- [{project}](/tasks/{project_slug}/index.md) — {count} tasks"
        )
    lines.append("")
    return "\n".join(lines)


def _gen_milestones_index(milestones: list[dict]) -> str:
    """docs/okf/milestones/index.md — progressive-disclosure milestone list."""
    lines = [
        "# Milestones",
        "",
        "> Migration calendar milestones from `docs/_data/calendar.yml`.",
        "",
    ]
    for ms in milestones:
        name = str(ms.get("name", ""))
        date = str(ms.get("date", ""))
        slug = _milestone_slug(name)
        lines.append(f"- [{name}](/milestones/{slug}.md) — {date}")
    lines.append("")
    return "\n".join(lines)


def _gen_milestone_concept(ms: dict) -> str:
    """docs/okf/milestones/{slug}.md — OKF Milestone concept."""
    name = str(ms.get("name", ""))
    date = str(ms.get("date", ""))
    date_str = str(date).strip()

    fm_fields: dict[str, Any] = {
        "type": "Milestone",
        "title": name,
        "description": f"Migration milestone: {name}",
        "tags": ["milestone", "migration"],
    }
    if _ISO_DATE_RE.match(date_str):
        fm_fields["timestamp"] = date_str

    lines = [
        _frontmatter(fm_fields),
        "",
        f"# {name}",
        "",
        f"**Target date:** {date_str}",
        "",
        "## Context",
        "",
        "This milestone is part of the KF CPTO migration calendar defined in",
        "`docs/_data/calendar.yml`.  The calendar drives the AUTO-injected migration",
        "Gantt table in `docs/migration-gantt.md`.",
        "",
        "## Links",
        "",
        "- [All milestones](/milestones/index.md)",
        "- [LOE metric definition](/metrics/loe.md)",
        "- [Projects](/projects/index.md)",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Graph JSON emitter — docs/_data/okf_graph.json
# ---------------------------------------------------------------------------

_GITHUB_BLOB_BASE = f"https://github.com/{ORG}/kf-cpto/blob/master/docs/okf"
_DASHBOARD_BASE = "https://katty-fashion.github.io/kf-cpto"


def emit_okf_graph_json(
    all_project_data: dict[str, Any],
    loe_rows: list[dict],
    calendar_data: dict,
    base_dir: Path,
) -> tuple[int, int]:
    """Emit docs/_data/okf_graph.json — a Cytoscape-ready node/edge graph.

    Builds from the SAME in-memory relationships the OKF bundle uses.
    Never re-parses kanban.md or any bundle files on disk.

    Node types: Project, Task, Metric, Milestone.
    Edge kinds:
      - ``depends``: project -> project it depends on (same direction as the
        Mermaid dep -> dependent graph).
      - ``contains``: project -> each of its task concepts.

    Output is fully deterministic: nodes sorted by id, edges sorted by
    (source, target, kind).  No run-time timestamps in the JSON.

    Args:
        all_project_data: Output of utils.load_all_project_data()
        loe_rows:         Output of aggregator.build_loe_rows()
        calendar_data:    Loaded docs/_data/calendar.yml (dict)
        base_dir:         docs/ directory (Path)

    Returns:
        Tuple of (node_count, edge_count).
    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []

    # --- Project nodes & dependency edges -----------------------------------
    for project, project_data in all_project_data.items():
        proj_slug = _slug(project)
        proj_id = f"/projects/{proj_slug}.md"
        nodes.append({
            "id": proj_id,
            "label": project,
            "type": "Project",
            "status": None,
            "url": f"{_DASHBOARD_BASE}/projects/{proj_slug}/",
        })

        meta = project_data.get("meta", {})
        depends_on = [str(d) for d in (meta.get("depends_on") or [])]
        for dep in depends_on:
            dep_id = f"/projects/{_slug(dep)}.md"
            edges.append({
                "source": proj_id,
                "target": dep_id,
                "kind": "depends",
            })

    # --- Task nodes & contains edges ----------------------------------------
    # Group rows by project to compute per-project slugs (collision-safe).
    rows_by_project: dict[str, list[dict]] = {}
    for row in loe_rows:
        proj = str(row.get("project", "")).strip()
        if proj:
            rows_by_project.setdefault(proj, []).append(row)

    for project, rows in rows_by_project.items():
        proj_slug = _slug(project)
        proj_id = f"/projects/{proj_slug}.md"
        seen_slugs: dict[str, int] = {}
        for idx, row in enumerate(rows):
            task_name = str(row.get("task", "")).strip()
            task_slug = _task_slug(task_name, seen_slugs, idx)
            task_id = f"/tasks/{proj_slug}/{task_slug}.md"
            task_status = str(row.get("status", "")).strip() or None
            nodes.append({
                "id": task_id,
                "label": task_name,
                "type": "Task",
                "status": task_status,
                "parent": proj_id,
                "url": f"{_GITHUB_BLOB_BASE}/tasks/{proj_slug}/{task_slug}.md",
            })
            edges.append({
                "source": proj_id,
                "target": task_id,
                "kind": "contains",
            })

    # --- Metric nodes --------------------------------------------------------
    _metric_defs = [
        ("loe", "Level of Effort", "metrics/loe.md"),
        ("status-rag", "RAG Status Colours", "metrics/status-rag.md"),
    ]
    for metric_slug, metric_label, metric_rel in _metric_defs:
        metric_id = f"/metrics/{metric_slug}.md"
        nodes.append({
            "id": metric_id,
            "label": metric_label,
            "type": "Metric",
            "status": None,
            "url": f"{_GITHUB_BLOB_BASE}/{metric_rel}",
        })

    # --- Milestone nodes -----------------------------------------------------
    milestones = calendar_data.get("milestones", []) or []
    for ms in milestones:
        name = str(ms.get("name", ""))
        if not name:
            continue
        ms_slug = _milestone_slug(name)
        ms_id = f"/milestones/{ms_slug}.md"
        nodes.append({
            "id": ms_id,
            "label": name,
            "type": "Milestone",
            "status": None,
            "url": f"{_GITHUB_BLOB_BASE}/milestones/{ms_slug}.md",
        })

    # --- Sort for determinism ------------------------------------------------
    nodes.sort(key=lambda n: n["id"])
    edges.sort(key=lambda e: (e["source"], e["target"], e["kind"]))

    graph: dict[str, Any] = {
        "nodes": nodes,
        "edges": edges,
    }

    out_path = base_dir / "_data" / "okf_graph.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph, indent=2, sort_keys=False), encoding="utf-8")

    return len(nodes), len(edges)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_okf_bundle(
    all_project_data: dict[str, Any],
    loe_rows: list[dict],
    calendar_data: dict,
    base_dir: Path,
) -> int:
    """Generate the OKF v0.1 bundle at base_dir/okf/.

    Pure transform of in-memory data — never re-parses kanban.md.

    Args:
        all_project_data: Output of utils.load_all_project_data()
        loe_rows:         Output of aggregator.build_loe_rows()
        calendar_data:    Loaded docs/_data/calendar.yml (dict)
        base_dir:         docs/ directory (Path)

    Returns:
        Number of markdown files written.
    """
    okf_dir = base_dir / "okf"
    files_written = 0

    def write(rel: str, content: str) -> None:
        nonlocal files_written
        _write(okf_dir / rel, content)
        files_written += 1

    # Pre-compute task data grouped by project so we know which projects have
    # task concepts before generating project pages (needed for the down-link).
    # Group loe_rows by project; preserve stable input order.
    rows_by_project: dict[str, list[dict]] = {}
    for row in loe_rows:
        project = str(row.get("project", "")).strip()
        if project:
            rows_by_project.setdefault(project, []).append(row)

    # Projects that have at least one loe row get task concept files.
    projects_with_tasks: set[str] = {p for p, rows in rows_by_project.items() if rows}

    # Build per-project slug → [(task_slug, task_title)] map (deterministic order).
    project_task_entries: dict[str, list[tuple[str, str]]] = {}
    for project, rows in rows_by_project.items():
        if not rows:
            continue
        seen_slugs: dict[str, int] = {}
        entries: list[tuple[str, str]] = []
        for idx, row in enumerate(rows):
            task_name = str(row.get("task", "")).strip()
            slug = _task_slug(task_name, seen_slugs, idx)
            entries.append((slug, task_name))
        project_task_entries[project] = entries

    # Total task concept count (for root index)
    total_task_concepts = sum(
        len(entries) for entries in project_task_entries.values()
    )

    # Root
    write("index.md", _gen_root_index(okf_dir, all_project_data, loe_rows, total_task_concepts))
    write("log.md", _gen_log(all_project_data))

    # Projects section
    known_projects: set[str] = set(all_project_data.keys())
    write("projects/index.md", _gen_projects_index(all_project_data))
    for project, project_data in all_project_data.items():
        slug = _slug(project)
        has_task_concepts = project in projects_with_tasks
        write(
            f"projects/{slug}.md",
            _gen_project_concept(
                project, project_data, loe_rows, known_projects, has_task_concepts
            ),
        )

    # Tasks section — one file per task, per-project index, root index.
    # Only emit for projects that actually have loe_rows (skip 0-task repos).
    project_task_counts: list[tuple[str, int]] = []
    for project, entries in sorted(project_task_entries.items()):
        project_slug = _slug(project)
        meta = all_project_data.get(project, {}).get("meta", {})
        project_task_counts.append((project, len(entries)))

        # Per-task concept files
        for (task_slug, task_name), row in zip(entries, rows_by_project[project]):
            write(
                f"tasks/{project_slug}/{task_slug}.md",
                _gen_task_concept(project, row, meta),
            )

        # Per-project task index
        write(
            f"tasks/{project_slug}/index.md",
            _gen_tasks_project_index(project, entries),
        )

    # Root tasks index
    write("tasks/index.md", _gen_tasks_root_index(project_task_counts))

    # Metrics section
    write("metrics/index.md", _gen_metrics_index())
    write("metrics/loe.md", _gen_loe_metric())
    write("metrics/status-rag.md", _gen_status_rag_metric())

    # Milestones section
    milestones = calendar_data.get("milestones", []) or []
    write("milestones/index.md", _gen_milestones_index(milestones))
    for ms in milestones:
        name = str(ms.get("name", ""))
        if not name:
            continue
        slug = _milestone_slug(name)
        write(f"milestones/{slug}.md", _gen_milestone_concept(ms))

    # Emit Cytoscape graph JSON to docs/_data/ (consumed by okf-graph.md).
    # Not counted in files_written (it's a JSON data file, not an OKF .md file).
    node_count, edge_count = emit_okf_graph_json(
        all_project_data, loe_rows, calendar_data, base_dir
    )
    print(f"Generated OKF graph JSON: {node_count} nodes, {edge_count} edges -> docs/_data/okf_graph.json")

    return files_written
