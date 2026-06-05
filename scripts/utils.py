#!/usr/bin/env python3
"""
Shared Utilities for KF Team Git-Native Project Management

Common functions used by aggregator.py and sheets_sync.py
"""

import os
import re
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Single Point of Truth — org name used across all scripts
ORG = "katty-fashion"

# Base directory is the project root (parent of scripts/)
BASE_DIR = Path(__file__).parent.parent
REPOS_DIR = BASE_DIR / "repos"
DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = DOCS_DIR / "_data"
CONFIG_FILE = BASE_DIR / "docs" / "_config.yml"
DISCOVERED_FILE = REPOS_DIR / "discovered.txt"

# Canonical intermediate written by aggregator.py, consumed by sheets_sync.py.
# This is the contract that lets the Sheets export be a strictly downstream consumer.
LOE_DATA_FILE = DATA_DIR / "loe.yml"
GANTT_DATA_FILE = DATA_DIR / "gantt.yml"

# Surfaced on the dashboard via the sidebar badge + index banner.
STATUS_FILE = DATA_DIR / "sync_status.yml"

# GitHub edit URL template — used by aggregator for "Edit Kanban" links
EDIT_URL_TEMPLATE = f"https://github.com/{ORG}/{{repo}}/edit/{{branch}}/kanban.md"

# Per-repo default branch mapping (populated by load_projects())
PROJECT_BRANCHES: dict[str, str] = {}

# Valid task statuses (single source for all status references)
TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")

# Case-folded aliases -> canonical TASK_STATUSES value. Lets the one canonical
# parser self-heal common drift (lowercase "in progress", emoji-prefixed or
# foreign-vocabulary statuses from repos like R3-AAS) instead of leaking invalid
# strings into the kanban diagrams and the LOE intermediate. Unknown statuses are
# left untouched and still warned about (see parse_kanban_tasks).
_STATUS_CANON = {
    "todo": "Todo",
    "to do": "Todo",
    "to-do": "Todo",
    "backlog": "Todo",
    "planned": "Todo",
    "next": "Todo",
    "not started": "Todo",
    "in progress": "In Progress",
    "in-progress": "In Progress",
    "inprogress": "In Progress",
    "in lucru": "In Progress",
    "doing": "In Progress",
    "wip": "In Progress",
    "started": "In Progress",
    "running": "In Progress",
    "testing": "In Progress",
    "near completion": "In Progress",
    "in setup": "In Progress",
    "blocat": "In Progress",
    "blocat extern": "In Progress",
    "blocat de parteneri": "In Progress",
    "blocked": "In Progress",
    "review": "Review",
    "in review": "Review",
    "in-review": "Review",
    "code review": "Review",
    "needs review": "Review",
    "done": "Done",
    "complete": "Done",
    "completed": "Done",
    "finished": "Done",
    "closed": "Done",
    "implemented": "Done",
    "implemented & validated": "Done",
}

# Kanban table column layouts (4-col legacy, 6-col extended with dates)
TASK_COLUMNS_4 = ("Task", "Assignee", "Effort", "Status")
TASK_COLUMNS_6 = ("Task", "Assignee", "Effort", "Start", "End", "Status")

# Header-cell label -> canonical task field. Drives header-driven column mapping
# in parse_kanban_tasks so heterogeneous tables (e.g. an "Owner" column instead
# of "Assignee", a "Deadline" instead of "End") parse correctly and non-task
# tables (no "Task" column) are skipped entirely.
_COLUMN_ALIASES = {
    "task": "task",
    "assignee": "assignee",
    "owner": "assignee",
    "effort": "effort",
    "start": "start",
    "end": "end",
    "deadline": "end",
    "status": "status",
}

# Map from kanban.md status to MermaidJS column name (hyphenated)
STATUS_TO_MERMAID = {s: s.replace(" ", "-") for s in TASK_STATUSES}

# Map task status to MermaidJS kanban priority (colored left border)
STATUS_PRIORITY = {
    "In Progress": "Very High",   # red — active work
    "Review": "High",             # orange — needs attention
    "Todo": "Low",                # blue — queued
}

# Status pill colors — single source for CSS and legend generation
STATUS_COLORS = {
    "In Progress": "#e53e3e",  # red
    "Review": "#ed8936",       # orange
    "Todo": "#3182ce",         # blue
    "Done": "#38a169",         # green
}

# Project type display names
TYPE_DISPLAY = {
    "saas": "SaaS Product",
    "eu-project": "EU Project",
    "internal": "Internal",
}

# MermaidJS graph classDef styles per project type
TYPE_MERMAID_CLASS = {
    "saas": ":::saas",
    "eu-project": ":::eu",
    "internal": ":::internal",
}

TYPE_MERMAID_DEFS = [
    "classDef saas fill:#4CAF50,color:#fff",
    "classDef eu fill:#2196F3,color:#fff",
    "classDef internal fill:#FF9800,color:#fff",
]

# Defaults for optional kanban.md frontmatter fields
FRONTMATTER_DEFAULTS = {
    "description": "",
    "type": "internal",
    "po": "",
    "lead": "",
    "depends_on": [],
    "tags": [],
}


def load_config() -> dict[str, Any]:
    """Load configuration from _config.yml"""
    if CONFIG_FILE.exists():
        return yaml.safe_load(CONFIG_FILE.read_text())
    return {}


def load_projects() -> list[str]:
    """Load project list from discovered repos, falling back to _config.yml for local dev.

    Parses 'name:branch' format from discovered.txt and populates PROJECT_BRANCHES.
    Plain 'name' entries default to 'master'.
    """
    if DISCOVERED_FILE.exists():
        names = []
        for line in DISCOVERED_FILE.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                name, branch = line.split(":", 1)
            else:
                name, branch = line, "master"
            names.append(name)
            PROJECT_BRANCHES[name] = branch
        if names:
            return names
    # Fallback: _config.yml (for local development without running discover.py)
    config = load_config()
    return config.get("kf_projects", [])


def parse_kanban_frontmatter(content: str) -> dict[str, Any]:
    """Extract YAML frontmatter from kanban.md

    Args:
        content: Raw markdown content

    Returns:
        Dictionary of frontmatter key-value pairs
    """
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}
    return {}


def canonicalize_status(status: str) -> Optional[str]:
    """Map a status string to its canonical TASK_STATUSES value, or None if unknown.

    Case-folds and looks up _STATUS_CANON. Caller is responsible for stripping
    emojis first (parse_kanban_tasks does). Returns None — not a default — so
    callers can distinguish a recognized status from genuinely unknown input and
    warn accordingly.
    """
    if not status:
        return None
    return _STATUS_CANON.get(status.strip().lower())


def _is_table_row(line: str) -> bool:
    """True if a line is a GFM pipe-table row (starts with '|' after trim)."""
    return line.strip().startswith("|")


def _is_separator_row(line: str) -> bool:
    """True if a line is a GFM table header separator (e.g. '| :--- | :--- |')."""
    s = line.strip()
    return bool(s) and s.startswith("|") and set(s) <= set("|-: ") and "-" in s


def _split_row(line: str) -> list[str]:
    """Split a pipe-table row into trimmed cells, dropping the leading/trailing pipe."""
    parts = line.strip().split("|")
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [p.strip() for p in parts]


def _map_columns(header_cells: list[str]) -> dict[str, int]:
    """Map a header row's cells to canonical field -> column index via _COLUMN_ALIASES.

    First occurrence of each field wins. Unrecognized columns (Prioritate, Note,
    Blocker, #, Pillar, Component, ...) are ignored.
    """
    colmap: dict[str, int] = {}
    for idx, cell in enumerate(header_cells):
        field = _COLUMN_ALIASES.get(cell.strip().lower())
        if field and field not in colmap:
            colmap[field] = idx
    return colmap


def _cell(cells: list[str], colmap: dict[str, int], field: str) -> str:
    """Return the trimmed value for a mapped field, or '' if absent/out of range."""
    idx = colmap.get(field)
    if idx is None or idx >= len(cells):
        return ""
    return cells[idx]


def parse_kanban_tasks(content: str, project: str = "") -> list[dict[str, str]]:
    """Extract tasks from every well-formed task table in a kanban.md.

    Header-driven (not position/count-driven): each table block is identified by a
    header row immediately followed by a separator row, and its columns are mapped
    by label via _COLUMN_ALIASES. This means:
      - 4-col (| Task | Assignee | Effort | Status |) and 6-col
        (| Task | Assignee | Effort | Start | End | Status |) both parse cleanly;
      - alternative labels map too (Owner -> assignee, Deadline -> end);
      - tables WITHOUT a Task column (e.g. a 'Pillar | Component | Status' summary)
        are skipped entirely, so they never pollute the LOE intermediate;
      - statuses are emoji-stripped and canonicalized (canonicalize_status), so
        'In progress' / emoji-prefixed / foreign-vocabulary values self-heal.

    Returns:
        List of task dicts with keys: task, assignee, effort, start, end, status
    """
    tasks: list[dict[str, str]] = []
    lines = content.splitlines()
    i, n = 0, len(lines)

    while i < n:
        if _is_table_row(lines[i]) and i + 1 < n and _is_separator_row(lines[i + 1]):
            colmap = _map_columns(_split_row(lines[i]))
            i += 2  # consume header + separator
            if "task" not in colmap:
                # Not a task table — skip its data rows without emitting anything.
                while i < n and _is_table_row(lines[i]):
                    i += 1
                continue
            while i < n and _is_table_row(lines[i]):
                cells = _split_row(lines[i])
                task_name = _cell(cells, colmap, "task")
                if task_name:
                    raw_status = strip_emojis(_cell(cells, colmap, "status"))
                    canon = canonicalize_status(raw_status)
                    if canon is not None:
                        status = canon
                    else:
                        status = raw_status
                        if status:
                            label = f" in {project}" if project else ""
                            print(f"Warning: Unknown status '{status}'{label} for "
                                  f"task '{task_name}'. Valid: {', '.join(TASK_STATUSES)}")
                    tasks.append({
                        "task": task_name,
                        "assignee": _cell(cells, colmap, "assignee"),
                        "effort": _cell(cells, colmap, "effort"),
                        "start": _cell(cells, colmap, "start"),
                        "end": _cell(cells, colmap, "end"),
                        "status": status,
                    })
                i += 1
        else:
            i += 1

    return tasks


def normalize_frontmatter(meta: dict) -> dict:
    """Apply defaults to frontmatter, ensuring all expected keys exist.

    Args:
        meta: Raw frontmatter dictionary from parse_kanban_frontmatter()

    Returns:
        Dictionary with all expected keys populated (defaults for missing ones)
    """
    result = dict(FRONTMATTER_DEFAULTS)
    result.update(meta)
    # Normalize type aliases
    type_aliases = {"eu": "eu-project", "saas": "saas", "internal": "internal"}
    result["type"] = type_aliases.get(result["type"], result["type"])
    # Ensure depends_on is always a list
    if isinstance(result["depends_on"], str):
        result["depends_on"] = [result["depends_on"]]
    if isinstance(result["tags"], str):
        result["tags"] = [result["tags"]]
    return result


def parse_effort_days(effort: str) -> float:
    """Parse effort string to float days

    Supports formats like '3d', '2.5d', '1D'

    Args:
        effort: Effort string (e.g., '3d', '2.5d')

    Returns:
        Effort as float days, or 0.0 if parsing fails
    """
    if not effort:
        return 0.0
    match = re.match(r"(\d+(?:\.\d+)?)\s*d", effort.lower())
    if match:
        return float(match.group(1))
    return 0.0


def load_project_kanban(project: str) -> dict[str, Any]:
    """Load kanban data for a single project

    Args:
        project: Project name (e.g., 'nuoform')

    Returns:
        Dictionary with keys: meta, tasks, raw, exists
    """
    kanban_path = REPOS_DIR / project / "kanban.md"

    if kanban_path.exists():
        content = kanban_path.read_text()
        meta = normalize_frontmatter(parse_kanban_frontmatter(content))
        return {
            "meta": meta,
            "tasks": parse_kanban_tasks(content, project=project),
            "raw": content,
            "exists": True
        }

    return {
        "meta": normalize_frontmatter({}),
        "tasks": [],
        "raw": "",
        "exists": False
    }


def now_iso() -> str:
    """UTC timestamp in ISO 8601, second precision, suitable for filenames."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_compact() -> str:
    """UTC timestamp suitable for Google Sheets tab names (no colons)."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


_STATUS_DEFAULTS = {
    "aggregator": {
        "last_run_at": None,
        "last_run_status": "unknown",
        "source_repo_count": 0,
        "task_count": 0,
        "errors": [],
    },
    "sheets_export": {
        "last_run_at": None,
        "last_run_status": "unknown",
        "row_count": 0,
        "duration_seconds": None,
        "last_error": None,
        "last_error_issue": None,
        "recent_failures": [],
    },
}


def load_sync_status() -> dict:
    """Read docs/_data/sync_status.yml, returning defaults if missing/corrupt.

    Each call returns a deep-merged result so callers can safely overwrite
    individual sections without erasing the other.
    """
    result = {k: dict(v) for k, v in _STATUS_DEFAULTS.items()}
    if not STATUS_FILE.exists():
        return result
    try:
        loaded = yaml.safe_load(STATUS_FILE.read_text()) or {}
    except yaml.YAMLError:
        return result
    for section, defaults in _STATUS_DEFAULTS.items():
        section_val = loaded.get(section)
        if isinstance(section_val, dict):
            merged = dict(defaults)
            merged.update(section_val)
            result[section] = merged
    return result


def save_sync_status(status: dict) -> None:
    """Persist sync status to docs/_data/sync_status.yml.

    Always succeeds (creates parent dir as needed). Callers may invoke this
    even when the rest of their workflow is failing — that's the whole point.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(yaml.safe_dump(status, sort_keys=False))


def update_sync_status(section: str, **fields) -> None:
    """Read-modify-write a single section of sync_status.yml."""
    status = load_sync_status()
    if section not in status:
        status[section] = {}
    status[section].update(fields)
    save_sync_status(status)


def _is_emoji(cp: int) -> bool:
    """True if Unicode codepoint cp falls in a known emoji block.

    Romanian diacritics (ă/â/î/ș/ț — U+0103/00E2/00EE/0219/021B) live in the
    Basic Latin + Latin Extended range and are never matched here. Mirrors the
    block list used by the activity-sync skill's sanitizer for consistency.
    """
    return (
        0x1F600 <= cp <= 0x1F64F or  # Emoticons
        0x1F300 <= cp <= 0x1F5FF or  # Misc Symbols and Pictographs
        0x1F680 <= cp <= 0x1F6FF or  # Transport and Map
        0x1F700 <= cp <= 0x1F9FF or  # Alchemical + Geometric + Supplemental
        0x1FA00 <= cp <= 0x1FA6F or  # Chess Symbols
        0x1FA70 <= cp <= 0x1FAFF or  # Symbols and Pictographs Extended-A
        0x231A <= cp <= 0x231B or    # Watch / hourglass (⌚⌛)
        0x23E9 <= cp <= 0x23FA or    # Media control emoji (⏩⏪⏭⏮⏯⏰…)
        0x2600 <= cp <= 0x26FF or    # Misc Symbols (includes ⚠ ✅ ⛔)
        0x2700 <= cp <= 0x27BF or    # Dingbats (includes ✔ ✗ ➡)
        0xFE00 <= cp <= 0xFE0F or    # Variation Selectors
        0x1F1E0 <= cp <= 0x1F1FF or  # Regional Indicator Symbols (flags)
        cp == 0x200D                 # Zero Width Joiner
    )


def strip_emojis(text: str) -> str:
    """Drop emoji codepoints from text; collapse the resulting double spaces.

    Render-time second fence (DIAG-V2-01): guarantees no emojis reach the
    dashboard diagrams or the canonical LOE intermediate / Google Sheet,
    independent of whether the activity-sync skill sanitized a given repo on
    write-back. Romanian diacritics are preserved.
    """
    if not text:
        return text
    cleaned = "".join(c for c in text if not _is_emoji(ord(c)))
    return re.sub(r"  +", " ", cleaned).strip()


def mermaid_label_safe(text: str) -> str:
    """Make text safe to embed inside a Mermaid node label — e.g. `id["<text>"]`.

    The node label is delimited by double quotes and square brackets, so a literal
    `"` / `[` / `]` in the task text terminates the node early and breaks the whole
    diagram with a "Syntax error in text". Replace those delimiters with faithful,
    display-only stand-ins (typographic quote, parentheses) and flatten newlines.
    """
    if not text:
        return text
    return (
        text.replace('"', "”")   # " -> ” (right double quotation mark)
            .replace("[", "(")
            .replace("]", ")")
            .replace("\n", " ")
            .strip()
    )


def _sanitize_task(task: dict[str, str]) -> dict[str, str]:
    """Strip emojis from the human-facing fields of a parsed task dict."""
    for key in ("task", "assignee", "status", "effort"):
        if key in task and isinstance(task[key], str):
            task[key] = strip_emojis(task[key])
    return task


def load_all_project_data() -> dict[str, dict[str, Any]]:
    """Load kanban data from all configured projects

    Returns:
        Dictionary mapping project name to project data
    """
    data = {}
    projects = load_projects()

    for project in projects:
        project_data = load_project_kanban(project)
        if not project_data["exists"]:
            print(f"Warning: repos/{project}/kanban.md not found")
        # Render-time emoji fence (DIAG-V2-01): scrub emojis from every task
        # before they flow into kanban/gantt diagrams and the LOE intermediate.
        for task in project_data.get("tasks", []):
            _sanitize_task(task)
        data[project] = project_data

    return data
