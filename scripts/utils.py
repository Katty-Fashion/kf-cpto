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
EDIT_URL_TEMPLATE = f"https://github.com/{ORG}/{{repo}}/edit/master/kanban.md"

# Valid task statuses (single source for all status references)
TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")

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
    """Load project list from discovered repos, falling back to _config.yml for local dev."""
    if DISCOVERED_FILE.exists():
        projects = [line.strip() for line in DISCOVERED_FILE.read_text().splitlines() if line.strip()]
        if projects:
            return projects
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


def parse_kanban_tasks(content: str) -> list[dict[str, str]]:
    """Extract tasks from kanban markdown table

    Expects table format:
    | Task | Assignee | Effort | Status |
    | :--- | :--- | :--- | :--- |
    | Task name | @user | 3d | Todo |

    Args:
        content: Raw markdown content

    Returns:
        List of task dictionaries with keys: task, assignee, effort, status
    """
    tasks = []
    table_pattern = r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"

    for match in re.finditer(table_pattern, content):
        task, assignee, effort, status = match.groups()
        task_name = task.strip()

        # Skip header row and separator row
        if task_name in ("Task", ":---") or task_name.startswith(":"):
            continue

        tasks.append({
            "task": task_name,
            "assignee": assignee.strip(),
            "effort": effort.strip(),
            "status": status.strip()
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
            "tasks": parse_kanban_tasks(content),
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
