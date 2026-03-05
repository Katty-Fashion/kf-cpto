#!/usr/bin/env python3
"""
Shared Utilities for KF Team Git-Native Project Management

Common functions used by aggregator.py and sheets_sync.py
"""

import re
import yaml
from pathlib import Path
from typing import Any

# Single Point of Truth — org name used across all scripts
ORG = "katty-fashion"

# Base directory is the project root (parent of scripts/)
BASE_DIR = Path(__file__).parent.parent
REPOS_DIR = BASE_DIR / "repos"
DOCS_DIR = BASE_DIR / "docs"
CONFIG_FILE = BASE_DIR / "docs" / "_config.yml"
DISCOVERED_FILE = REPOS_DIR / "discovered.txt"

# GitHub edit URL template — used by aggregator for "Edit Kanban" links
EDIT_URL_TEMPLATE = f"https://github.com/{ORG}/{{repo}}/edit/{{branch}}/kanban.md"

# Per-repo default branch mapping (populated by load_projects())
PROJECT_BRANCHES: dict[str, str] = {}

# Valid task statuses (single source for all status references)
TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")

# Kanban table column layouts (4-col legacy, 6-col extended with dates)
TASK_COLUMNS_4 = ("Task", "Assignee", "Effort", "Status")
TASK_COLUMNS_6 = ("Task", "Assignee", "Effort", "Start", "End", "Status")

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


def parse_kanban_tasks(content: str, project: str = "") -> list[dict[str, str]]:
    """Extract tasks from kanban markdown table.

    Supports both 4-column and 6-column formats:
      4-col: | Task | Assignee | Effort | Status |
      6-col: | Task | Assignee | Effort | Start | End | Status |

    Returns:
        List of task dicts with keys: task, assignee, effort, start, end, status
    """
    tasks = []

    # Detect table format: count pipes in the header row
    header_match = re.search(r"^\|[^\n]+\|", content, re.MULTILINE)
    if not header_match:
        return tasks

    pipe_count = header_match.group().count("|") - 1  # subtract leading pipe
    is_6col = pipe_count >= 6

    if is_6col:
        pattern = r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
    else:
        pattern = r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"

    for match in re.finditer(pattern, content):
        groups = match.groups()
        first = groups[0].strip()

        # Skip header row and separator row
        if first in ("Task", ":---") or first.startswith(":"):
            continue

        if is_6col:
            task_name, assignee, effort, start, end, status = (g.strip() for g in groups)
        else:
            task_name, assignee, effort, status = (g.strip() for g in groups)
            start, end = "", ""

        # Validate status
        if status not in TASK_STATUSES:
            label = f" in {project}" if project else ""
            print(f"Warning: Unknown status '{status}'{label} for task '{task_name}'. "
                  f"Valid: {', '.join(TASK_STATUSES)}")

        tasks.append({
            "task": task_name,
            "assignee": assignee,
            "effort": effort,
            "start": start,
            "end": end,
            "status": status,
        })
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
        data[project] = project_data

    return data
