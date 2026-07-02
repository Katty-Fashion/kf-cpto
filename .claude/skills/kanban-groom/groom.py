#!/usr/bin/env python3
"""kanban-groom — interactive, numbered grooming of a tracked repo's kanban.md.

UAT-list-style numbered table over every parseable task row, plus surgical
by-number edits (set / delete). Reads and writes repos-local/<repo>/kanban.md.
Uses utils.enumerate_kanban_rows (canonical grammar — no second parser).

Usage:
    python .claude/skills/kanban-groom/groom.py list <repo>
    python .claude/skills/kanban-groom/groom.py set <repo> <n> field=value [field=value ...]
    python .claude/skills/kanban-groom/groom.py delete <repo> <n> [<n> ...]

`set` fields: any column present in that row's own table header — canonical
names (task, assignee/owner, effort, start, end, status) or a literal header
label (e.g. note, prioritate, blocker). Status values are validated.
Numbers come from `list` and are re-printed after every mutation (deletes
shift later numbers — always act on the freshest listing).
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE_DIR / "scripts"))

from utils import (  # noqa: E402
    TASK_STATUSES,
    enumerate_kanban_rows,
    strip_emojis,
    parse_effort_days,
)

REPOS_LOCAL = BASE_DIR / "repos-local"

# Boards owned by scripts/generate_kanban.py — groom the plan-of-record instead.
GENERATED_REPOS = {"kf-platform", "kf-fe-platform", "kf-be-platform"}

_STATUS_ALIASES = {
    "todo": "Todo", "in progress": "In Progress", "inprogress": "In Progress",
    "wip": "In Progress", "review": "Review", "in review": "Review",
    "done": "Done", "completed": "Done",
}


def _kanban_path(repo: str) -> Path:
    p = REPOS_LOCAL / repo / "kanban.md"
    if not p.exists():
        sys.exit(f"[ERROR] {p} not found — run bootstrap.py / check the repo name.")
    return p


def _guard_generated(repo: str) -> None:
    if repo in GENERATED_REPOS:
        sys.exit(
            f"[ERROR] {repo}/kanban.md is generated from docs/_data/migration_plan.yml "
            f"(scripts/generate_kanban.py). Groom the plan-of-record, not the board."
        )


def _flags(row: dict, name_counts: dict[str, int]) -> str:
    flags = []
    if row["status"] not in TASK_STATUSES:
        flags.append("[BAD-STATUS]")
    if name_counts.get(row["task"], 0) > 1:
        flags.append("[DUP]")
    colmap = row["colmap"]
    effort = row["cells"][colmap["effort"]] if "effort" in colmap and colmap["effort"] < len(row["cells"]) else ""
    if not effort or parse_effort_days(effort) <= 0:
        flags.append("[NO-EFFORT]")
    start = row["cells"][colmap["start"]] if "start" in colmap and colmap["start"] < len(row["cells"]) else ""
    if not start.strip("—- "):
        flags.append("[NO-DATES]")
    return " ".join(flags)


def _clip(s: str, width: int) -> str:
    s = strip_emojis(s).strip()
    return s if len(s) <= width else s[: width - 1] + "…"


def cmd_list(repo: str) -> int:
    content = _kanban_path(repo).read_text(encoding="utf-8")
    rows = enumerate_kanban_rows(content)
    if not rows:
        print(f"[INFO] {repo}: no parseable task rows.")
        return 0
    name_counts: dict[str, int] = {}
    for r in rows:
        name_counts[r["task"]] = name_counts.get(r["task"], 0) + 1

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = " · ".join(f"{counts.get(s, 0)} {s}" for s in TASK_STATUSES)
    bad = sum(1 for r in rows if r["status"] not in TASK_STATUSES)
    print(f"[INFO] {repo}: {len(rows)} tasks — {summary}"
          + (f" · {bad} BAD-STATUS" if bad else ""))
    print()
    print("| # | Section | Task | Status | Flags |")
    print("|---:|---|---|---|---|")
    for r in rows:
        print(f"| {r['n']} | {_clip(r['section'], 38)} | {_clip(r['task'], 62)} "
              f"| {r['status']} | {_flags(r, name_counts)} |")
    return 0


def _write_row(lines: list[str], row: dict) -> None:
    lines[row["line_no"]] = "| " + " | ".join(row["cells"]) + " |"


def cmd_set(repo: str, n: int, assignments: list[str]) -> int:
    _guard_generated(repo)
    path = _kanban_path(repo)
    content = path.read_text(encoding="utf-8")
    rows = enumerate_kanban_rows(content)
    match = next((r for r in rows if r["n"] == n), None)
    if match is None:
        sys.exit(f"[ERROR] no row #{n} — run `list {repo}` for valid numbers.")

    colmap = dict(match["colmap"])
    # allow literal header labels (Note, Prioritate, Blocker, ...) too
    for idx, label in enumerate(match["header_cells"]):
        key = strip_emojis(label).strip().lower()
        colmap.setdefault(key, idx)

    changed = []
    for a in assignments:
        if "=" not in a:
            sys.exit(f"[ERROR] bad assignment '{a}' — use field=value.")
        field, value = a.split("=", 1)
        field = field.strip().lower()
        if field == "owner":
            field = "assignee" if "assignee" in colmap else "owner"
        if field == "status":
            canon = _STATUS_ALIASES.get(value.strip().lower())
            if canon is None and value.strip() not in TASK_STATUSES:
                sys.exit(f"[ERROR] invalid status '{value}'. Valid: {', '.join(TASK_STATUSES)}")
            value = canon or value.strip()
        if field not in colmap:
            sys.exit(f"[ERROR] row #{n}'s table has no '{field}' column "
                     f"(has: {', '.join(sorted(colmap))}).")
        idx = colmap[field]
        while len(match["cells"]) <= idx:
            match["cells"].append("")
        old = match["cells"][idx]
        match["cells"][idx] = value
        changed.append(f"{field}: '{old.strip()}' -> '{value}'")

    lines = content.splitlines()
    _write_row(lines, match)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[DONE] #{n} {match['task']}")
    for c in changed:
        print(f"       {c}")
    return 0


def cmd_delete(repo: str, ns: list[int]) -> int:
    _guard_generated(repo)
    path = _kanban_path(repo)
    content = path.read_text(encoding="utf-8")
    rows = enumerate_kanban_rows(content)
    by_n = {r["n"]: r for r in rows}
    missing = [n for n in ns if n not in by_n]
    if missing:
        sys.exit(f"[ERROR] no row(s) {missing} — run `list {repo}` for valid numbers.")
    lines = content.splitlines()
    # delete bottom-up so line numbers stay valid
    for n in sorted(set(ns), reverse=True):
        row = by_n[n]
        del lines[row["line_no"]]
        print(f"[DONE] deleted #{n} {row['task']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[WARN] numbers shift after deletion — re-run `list` before further edits.")
    return 0


_CANON_HEADER = "| Task | Owner | Effort | Start | End | Status | Note |"
_CANON_SEP = "|---|---|---|---|---|---|---|"
_CANON_FIELDS = ("task", "owner", "effort", "start", "end", "status", "note")


def cmd_add(repo: str, assignments: list[str]) -> int:
    """Append a task row under `section=...` (section + canonical table created if absent)."""
    _guard_generated(repo)
    path = _kanban_path(repo)
    content = path.read_text(encoding="utf-8")
    fields = {"status": "Todo"}
    for a in assignments:
        if "=" not in a:
            sys.exit(f"[ERROR] bad assignment '{a}' — use field=value.")
        k, v = a.split("=", 1)
        fields[k.strip().lower()] = v
    section = fields.pop("section", None)
    if not section or not fields.get("task"):
        sys.exit("[ERROR] usage: add <repo> section=<title> task=<name> [owner= effort= start= end= status= note=]")
    if fields["status"] not in TASK_STATUSES:
        canon = _STATUS_ALIASES.get(fields["status"].strip().lower())
        if canon is None:
            sys.exit(f"[ERROR] invalid status '{fields['status']}'. Valid: {', '.join(TASK_STATUSES)}")
        fields["status"] = canon

    lines = content.splitlines()
    # locate the section header (any heading level, emoji-insensitive)
    sec_idx = next((i for i, ln in enumerate(lines)
                    if ln.strip().startswith("#")
                    and strip_emojis(ln).lstrip("#").strip().lower() == strip_emojis(section).strip().lower()),
                   None)
    row = "| " + " | ".join(fields.get(f, "—") or "—" for f in _CANON_FIELDS) + " |"

    if sec_idx is None:
        # new section + canonical table at end of file
        lines += ["", "---", "", f"## {section}", "", _CANON_HEADER, _CANON_SEP, row]
        print(f"[DONE] created section '{section}' and added: {fields['task']}")
    else:
        # find the first table under the section; append after its last row
        i = sec_idx + 1
        table_end = None
        while i < len(lines) and not lines[i].strip().startswith("#"):
            if _is_table_row_local(lines[i]):
                j = i
                while j < len(lines) and _is_table_row_local(lines[j]):
                    j += 1
                table_end = j
                break
            i += 1
        if table_end is None:
            insert_at = sec_idx + 1
            while insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            lines[insert_at:insert_at] = [_CANON_HEADER, _CANON_SEP, row, ""]
            print(f"[DONE] created table under '{section}' and added: {fields['task']}")
        else:
            # match the existing table's column layout
            header = lines[table_end - 1]
            existing_rows = enumerate_kanban_rows("\n".join(lines))
            hdr_row = next((r for r in existing_rows if r["line_no"] < table_end and r["line_no"] > sec_idx), None)
            if hdr_row is not None:
                colmap = dict(hdr_row["colmap"])
                for idx, label in enumerate(hdr_row["header_cells"]):
                    colmap.setdefault(strip_emojis(label).strip().lower(), idx)
                width = len(hdr_row["header_cells"])
                cells = ["—"] * width
                for f, v in fields.items():
                    key = "assignee" if f == "owner" and "assignee" in colmap else f
                    if key in colmap and colmap[key] < width:
                        cells[colmap[key]] = v
                row = "| " + " | ".join(cells) + " |"
            lines.insert(table_end, row)
            print(f"[DONE] added under '{section}': {fields['task']}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


def _is_table_row_local(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, repo = argv[1], argv[2]
    if cmd == "list":
        return cmd_list(repo)
    if cmd == "set":
        if len(argv) < 5:
            sys.exit("[ERROR] usage: set <repo> <n> field=value [...]")
        return cmd_set(repo, int(argv[3]), argv[4:])
    if cmd == "delete":
        if len(argv) < 4:
            sys.exit("[ERROR] usage: delete <repo> <n> [<n> ...]")
        return cmd_delete(repo, [int(x) for x in argv[3:]])
    if cmd == "add":
        return cmd_add(repo, argv[3:])
    sys.exit(f"[ERROR] unknown command '{cmd}' (list | set | delete | add)")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
