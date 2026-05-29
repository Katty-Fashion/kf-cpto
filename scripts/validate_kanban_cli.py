#!/usr/bin/env python3
"""
Standalone kanban.md validator — usable from any repo.

The per-repo `validate-kanban.yml` workflow in project-template curls this
file (and the schema) at runtime, so it must have **no relative imports**
and only stdlib + pyyaml + jsonschema dependencies.

Usage:
  python validate_kanban_cli.py <path> [<path> ...] --schema <schema.json>

Exits 0 if every path is valid, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _stringify_dates(value):
    """Recursively convert datetime.date / datetime.datetime to ISO strings."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _stringify_dates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_stringify_dates(v) for v in value]
    return value


def _parse_table_rows(content: str, is_6col: bool) -> list[dict]:
    if is_6col:
        pattern = r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
    else:
        pattern = r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
    rows = []
    for m in re.finditer(pattern, content):
        groups = [g.strip() for g in m.groups()]
        first = groups[0]
        if first in ("Task", ":---") or first.startswith(":"):
            continue
        if is_6col:
            task, assignee, effort, start, end, status = groups
        else:
            task, assignee, effort, status = groups
            start = end = ""
        rows.append({
            "task": task, "assignee": assignee, "effort": effort,
            "start": start, "end": end, "status": status,
        })
    return rows


def validate_kanban(content: str, schema: dict | None) -> list[str]:
    errors: list[str] = []

    # Frontmatter shape
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        errors.append("frontmatter: missing or malformed (expected `---\\n…\\n---` at top)")
        meta = None
    else:
        try:
            meta = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError as e:
            errors.append(f"frontmatter: YAML parse error — {e}")
            meta = None
        if meta is not None and not isinstance(meta, dict):
            errors.append(f"frontmatter: expected a mapping, got {type(meta).__name__}")
            meta = None

    if meta is not None and schema is not None:
        try:
            import jsonschema
            meta = _stringify_dates(meta)
            validator = jsonschema.Draft202012Validator(schema)
            for err in sorted(validator.iter_errors(meta), key=lambda e: list(e.absolute_path)):
                path = "/".join(str(p) for p in err.absolute_path) or "(root)"
                errors.append(f"frontmatter[{path}]: {err.message}")
        except ImportError:
            errors.append("schema: `jsonschema` not installed — install with `pip install jsonschema`")

    # Table structure
    header_match = re.search(r"^\|[^\n]+\|", content, re.MULTILINE)
    if not header_match:
        errors.append("table: no markdown table found (expected `| Task | Assignee | ... |`)")
        return errors

    pipe_count = header_match.group().count("|") - 1
    if pipe_count not in (4, 6):
        errors.append(
            f"table: header has {pipe_count} column(s); expected 4 "
            f"(Task|Assignee|Effort|Status) or 6 (Task|Assignee|Effort|Start|End|Status)"
        )
        return errors

    rows = _parse_table_rows(content, is_6col=(pipe_count == 6))
    for idx, t in enumerate(rows, 1):
        if not t["task"]:
            errors.append(f"table[row {idx}]: empty Task name")
        if t["status"] not in TASK_STATUSES:
            errors.append(
                f"table[row {idx}]: status `{t['status']}` is not one of {list(TASK_STATUSES)}"
            )
        for field in ("start", "end"):
            val = t.get(field, "")
            if val and not _ISO_DATE_RE.match(val):
                errors.append(
                    f"table[row {idx}]: `{field}` value `{val}` is not ISO date YYYY-MM-DD"
                )

    return errors


def _load_schema(schema_path: Path | None) -> dict | None:
    if schema_path is None:
        return None
    if not schema_path.exists():
        print(f"warn: schema not found at {schema_path} — structural checks only", file=sys.stderr)
        return None
    try:
        return json.loads(schema_path.read_text())
    except (OSError, ValueError) as e:
        print(f"warn: failed to load schema {schema_path}: {e}", file=sys.stderr)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="kanban.md file(s) to validate")
    parser.add_argument("--schema", type=Path, default=None,
                        help="Path to kanban.schema.json (optional but recommended)")
    args = parser.parse_args()

    schema = _load_schema(args.schema)
    total = 0
    for p in args.paths:
        path = Path(p)
        if not path.exists():
            print(f"{path}: not found")
            total += 1
            continue
        errs = validate_kanban(path.read_text(), schema)
        if errs:
            print(f"{path}: {len(errs)} error(s)")
            for e in errs:
                print(f"  - {e}")
            total += len(errs)
        else:
            print(f"{path}: OK")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
