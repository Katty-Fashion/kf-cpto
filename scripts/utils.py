#!/usr/bin/env python3
"""
Shared Utilities for KF Team Git-Native Project Management

Common functions used by aggregator.py and sheets_sync.py
"""

from __future__ import annotations

import os
import re
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Single Point of Truth — org name used across all scripts
ORG = "katty-fashion"

# Base directory is the project root (parent of scripts/)
BASE_DIR = Path(__file__).parent.parent
REPOS_DIR = BASE_DIR / "repos"
DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = DOCS_DIR / "_data"
SCHEMAS_DIR = BASE_DIR / "schemas"
KANBAN_SCHEMA_FILE = SCHEMAS_DIR / "kanban.schema.json"
CONFIG_FILE = BASE_DIR / "docs" / "_config.yml"
DISCOVERED_FILE = REPOS_DIR / "discovered.txt"

# Canonical intermediate written by aggregator.py, consumed by sheets_sync.py.
# This is the contract that lets the Sheets export be a strictly downstream consumer.
LOE_DATA_FILE = DATA_DIR / "loe.yml"

# Surfaced on the dashboard via the sidebar badge + index banner.
STATUS_FILE = DATA_DIR / "sync_status.yml"

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


# --------------------------------------------------------------------------- #
# Validation — used by `python -m scripts.utils validate <path>` and by the    #
# per-repo validate-kanban.yml workflow in project-template.                   #
# --------------------------------------------------------------------------- #

def _stringify_dates(value):
    """Recursively convert datetime.date / datetime.datetime to ISO strings.

    PyYAML deserializes `2026-05-04` as a date object, which trips schemas
    that declare these fields as strings. We normalize at the schema boundary
    so the schema can stay as plain `type: string` + ISO regex.
    """
    from datetime import date, datetime as dt
    if isinstance(value, dt):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _stringify_dates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_stringify_dates(v) for v in value]
    return value


def _load_kanban_schema() -> dict | None:
    if not KANBAN_SCHEMA_FILE.exists():
        return None
    import json
    try:
        return json.loads(KANBAN_SCHEMA_FILE.read_text())
    except (OSError, ValueError):
        return None


def validate_kanban(content: str, schema: dict | None = None) -> list[str]:
    """Validate a kanban.md document against the canonical schema + table rules.

    Returns a list of error strings (empty if the document is valid). Never
    raises — failures are returned so callers can format them.

    Three layers of check:
      1. Frontmatter shape via JSON Schema (`jsonschema` optional dep).
      2. Frontmatter YAML is syntactically valid.
      3. Table has the expected column count (4 or 6) and known statuses.
    """
    errors: list[str] = []

    # --- Layer 1+2: frontmatter ---
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        errors.append("frontmatter: missing or malformed (expected `---\\n…\\n---` block at top)")
    else:
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as e:
            errors.append(f"frontmatter: YAML parse error — {e}")
            meta = None

        if meta is not None and not isinstance(meta, dict):
            errors.append(f"frontmatter: expected a mapping, got {type(meta).__name__}")
            meta = None

        if meta is not None:
            meta = _stringify_dates(meta)
            schema = schema or _load_kanban_schema()
            if schema is None:
                errors.append(
                    "schema: kanban.schema.json not found — structural checks ran "
                    "but JSON Schema validation was skipped"
                )
            else:
                try:
                    import jsonschema
                    validator = jsonschema.Draft202012Validator(schema)
                    for err in sorted(validator.iter_errors(meta), key=lambda e: list(e.absolute_path)):
                        path = "/".join(str(p) for p in err.absolute_path) or "(root)"
                        errors.append(f"frontmatter[{path}]: {err.message}")
                except ImportError:
                    errors.append(
                        "schema: `jsonschema` not installed — structural checks ran "
                        "but JSON Schema validation was skipped. "
                        "Install with `pip install jsonschema` for full validation."
                    )

    # --- Layer 3: table structure & status enum ---
    header_match = re.search(r"^\|[^\n]+\|", content, re.MULTILINE)
    if not header_match:
        errors.append("table: no markdown table found (expected `| Task | Assignee | ... |`)")
    else:
        pipe_count = header_match.group().count("|") - 1
        if pipe_count not in (4, 6):
            errors.append(
                f"table: header has {pipe_count} column(s); expected 4 (Task|Assignee|Effort|Status) "
                f"or 6 (Task|Assignee|Effort|Start|End|Status)"
            )
        else:
            # Status enum check on data rows.
            tasks = parse_kanban_tasks(content)
            for idx, t in enumerate(tasks, 1):
                if t["status"] not in TASK_STATUSES:
                    errors.append(
                        f"table[row {idx}]: status `{t['status']}` is not one of "
                        f"{list(TASK_STATUSES)}"
                    )
                if not t["task"]:
                    errors.append(f"table[row {idx}]: empty Task name")
                # Date format sanity for 6-col rows
                for field in ("start", "end"):
                    val = t.get(field, "")
                    if val and not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
                        errors.append(
                            f"table[row {idx}]: `{field}` value `{val}` is not ISO date YYYY-MM-DD"
                        )

    return errors


def _cli_validate(paths: list[str]) -> int:
    schema = _load_kanban_schema()
    if schema is None:
        print(f"warn: schema not found at {KANBAN_SCHEMA_FILE} — running structural checks only")

    total_errors = 0
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"{path}: not found")
            total_errors += 1
            continue
        errs = validate_kanban(path.read_text(), schema=schema)
        if errs:
            print(f"{path}: {len(errs)} error(s)")
            for e in errs:
                print(f"  - {e}")
            total_errors += len(errs)
        else:
            print(f"{path}: OK")
    return 0 if total_errors == 0 else 1


def main():
    """CLI entry point: `python -m utils validate <path> [<path> ...]`"""
    import sys
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: python -m utils validate <path> [<path> ...]")
        print("       python scripts/utils.py validate <path> [<path> ...]")
        return 0 if args else 1
    cmd, *rest = args
    if cmd == "validate":
        if not rest:
            print("usage: validate <path> [<path> ...]")
            return 1
        return _cli_validate(rest)
    print(f"unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
