#!/usr/bin/env python3
"""
Publish the ALADIN WP2 action plan into BookStack as sprint plans and Gantt charts.

Local-only, like bookstack_sync.py (CI never runs this). Inputs are read at run time
from the project folder and are NEVER committed to this repository:

    --plan  ALADIN_WP2_Action_Plan_vX.Y.xlsx   (the tracker; later: the SharePoint copy)
    --ga    ALADIN-who-does-what.md            (grant-agreement working view, optional)

and published under the shelf (default "2605. Aladin"):

    book "ALADIN WP2 · Action Plan"            (managed by this script, KF roles only)
      ├─ page "Overview"                        (version, status mix, overdue, gates)
      ├─ page "Progress & evolution"            (what changed since the previous version)
      ├─ chapter "Sprint plan"                  (previous/current/next + one page per project quarter)
      ├─ chapter "Gantt"                        (GA task windows + gates, actions by task)
      ├─ chapter "Action plan"                  (full rows per task, partner load, notes, version log)
      └─ chapter "Who does what (GA)"           (the working view, one page per section)

Sprints follow the KF cadence in docs/_data/calendar.yml (2-week sprints, S1 = start_date),
so ALADIN work lines up with the KF sprint plan. An action belongs to the sprint that
contains its deadline.

Progress: every imported version is snapshotted (JSON) next to the source workbook in
<plan dir>/.wiki-sync/ — outside this repo. Importing a newer version reports status
changes, moved deadlines and new or retired rows against the previous snapshot.

Safety (inherited from bookstack_sync.Sync): dry-run by default, rollback manifest per
--apply run (undo with `bookstack_sync.py --rollback <run_id>`), pages edited by a human
in BookStack are reported and skipped, nothing is ever deleted. The book's permissions
are set to KF roles only BEFORE any page is written, and checked on every run.

Usage:
    python scripts/aladin_sync.py --plan "<dir>/ALADIN_WP2_Action_Plan_v0.8.xlsx" --ga "<dir>/ALADIN-who-does-what.md"
    python scripts/aladin_sync.py ... --apply
Credentials: BOOKSTACK_URL / BOOKSTACK_TOKEN_ID / BOOKSTACK_TOKEN_SECRET from .env or env.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from bookstack_sync import BookStack, Sync, load_env
from utils import DATA_DIR

SHELF_NAME = "2605. Aladin"
BOOK_NAME = "ALADIN WP2 · Action Plan"
BOOK_DESC = ("ALADIN WP2 (Development of the Aladin Digital Platform services) — action plan, "
             "sprint plan and Gantt charts generated from the WP2 action-plan workbook. "
             "KF internal. Edit the workbook, not these pages.")
CALENDAR_FILE = DATA_DIR / "calendar.yml"
PROJECT_M1 = date(2026, 6, 1)          # ALADIN M1 = June 2026 (workbook 'Notes & open points')
GROUP_ORDER = ["WP2 general", "T2.1", "T2.2", "T2.3", "T2.4", "T2.5", "D2.1", "D2.2"]
STATUS_ORDER = ["Done", "In progress", "Blocked", "Postponed", "Before start"]
# KF-only visibility: role display names that keep access; everything else (Public, partners) gets none.
KF_ROLES = {"Admin": "all", "Editor": "edit", "Viewer": "view"}

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
      "dcterms": "http://purl.org/dc/terms/"}


# --------------------------------------------------------------------------- #
# Workbook reading (stdlib only: an .xlsx is a zip of XML)                     #
# --------------------------------------------------------------------------- #

def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n


def read_xlsx(path: Path) -> tuple[dict[str, list[dict[int, str]]], str | None]:
    """{sheet name: [ {col: text} per non-empty row ]}, plus the workbook's last-modified timestamp."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    sheets = {}
    for s in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS):
        target = rels[s.get(f"{{{NS['r']}}}id")].lstrip("/")
        target = target if target.startswith("xl/") else f"xl/{target}"
        rows = []
        for r in ET.fromstring(z.read(target)).findall(".//m:sheetData/m:row", NS):
            cells = {}
            for c in r.findall("m:c", NS):
                v, t, inline = c.find("m:v", NS), c.get("t"), c.find("m:is", NS)
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr" and inline is not None:
                    val = "".join(x.text or "" for x in inline.iter(f"{{{NS['m']}}}t"))
                else:
                    val = v.text if v is not None else ""
                if val not in ("", None):
                    cells[_col(c.get("r"))] = val.strip()
            if cells:
                rows.append(cells)
        sheets[s.get("name")] = rows
    modified = None
    if "docProps/core.xml" in z.namelist():
        el = ET.fromstring(z.read("docProps/core.xml")).find("dcterms:modified", NS)
        modified = el.text if el is not None else None
    return sheets, modified


def excel_date(value: str) -> date | None:
    if not value:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", value):
        return date(1899, 12, 30) + timedelta(days=int(float(value)))
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def parse_plan(path: Path) -> dict:
    sheets, modified = read_xlsx(path)
    rows = sheets.get("Action Plan") or []
    title = rows[0].get(1, "") if rows else ""
    m = re.search(r"\bv(\d+(?:\.\d+)+)", title) or re.search(r"_v(\d+(?:\.\d+)+)", path.name)
    version = f"v{m.group(1)}" if m else "v?"
    header_idx = next(i for i, r in enumerate(rows) if r.get(1) == "ID")
    cols = {name: c for c, name in rows[header_idx].items()}

    def get(r, name):
        return r.get(cols.get(name, -1), "")

    actions = []
    for r in rows[header_idx + 1:]:
        if not re.match(r"W\d+-\d+", get(r, "ID")):
            continue
        deadline = excel_date(get(r, "Deadline"))
        contributors = [p.strip() for p in re.split(r",\s*", get(r, "Main contributors")) if p.strip()]
        actions.append({
            "id": get(r, "ID"), "type": get(r, "Type"), "group": get(r, "Type no") or "WP2 general",
            "action": get(r, "Action"), "dod": get(r, "Definition of done"),
            "contributors": contributors, "owner": contributors[0] if contributors else "",
            "deadline": deadline.isoformat() if deadline else None,
            "month": get(r, "Project month"), "postponed": get(r, "Postponed"),
            "status": get(r, "Status") or "Before start", "comment": get(r, "Comment / output"),
            "rev": get(r, "Rev"),
        })
    return {
        "version": version, "source": path.name, "modified": modified, "title": title,
        "actions": actions,
        "partner_pm": _table(sheets.get("Partner PM & scope"), "Partner"),
        "notes": _table(sheets.get("Notes & open points"), "#"),
        "version_log": _table(sheets.get("Version log"), "Version"),
        "notes_preamble": [r.get(1, "") for r in (sheets.get("Notes & open points") or [])[1:4]],
    }


def _table(rows: list[dict[int, str]] | None, first_header: str) -> list[dict[str, str]]:
    """Rows under the header row whose first cell is `first_header`, as dicts."""
    if not rows:
        return []
    try:
        h = next(i for i, r in enumerate(rows) if r.get(1) == first_header)
    except StopIteration:
        return []
    names = rows[h]
    return [{names[c]: v for c, v in r.items() if c in names} for r in rows[h + 1:] if r.get(1)]


# --------------------------------------------------------------------------- #
# Calendar: KF 2-week sprints, ALADIN project months                           #
# --------------------------------------------------------------------------- #

class Calendar:
    def __init__(self, start: date, weeks: int):
        self.start, self.days = start, weeks * 7

    def sprint(self, d: date) -> int:
        return (d - self.start).days // self.days + 1

    def bounds(self, n: int) -> tuple[date, date]:
        s = self.start + timedelta(days=(n - 1) * self.days)
        return s, s + timedelta(days=self.days - 3)  # Monday .. Friday of the last week


def project_month(d: date) -> int:
    return (d.year - PROJECT_M1.year) * 12 + d.month - PROJECT_M1.month + 1


def load_calendar() -> Calendar:
    cfg = yaml.safe_load(CALENDAR_FILE.read_text()) or {}
    start = cfg["start_date"]
    start = start if isinstance(start, date) else date.fromisoformat(str(start))
    return Calendar(start, int(cfg.get("sprint_length_weeks", 2)))


# --------------------------------------------------------------------------- #
# Rendering helpers                                                            #
# --------------------------------------------------------------------------- #

def cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def fmt(d: date) -> str:
    return d.strftime("%d %b %Y")


def effective_status(a: dict, today: date) -> str:
    """The workbook status, with 'Overdue' for open rows past their deadline."""
    if a["status"] in ("Done", "Postponed", "Blocked"):
        return a["status"]
    if a["deadline"] and date.fromisoformat(a["deadline"]) < today:
        return "Overdue"
    return a["status"]


def status_pill(a: dict, today: date) -> str:
    s = effective_status(a, today)
    return {"Done": "[DONE]", "In progress": "[IN PROGRESS]", "Blocked": "[BLOCKER]",
            "Postponed": "[POSTPONED]", "Overdue": "[OVERDUE]"}.get(s, "[TODO]")


def gantt_tag(a: dict, today: date) -> str:
    s = effective_status(a, today)
    return {"Done": "done, ", "In progress": "active, ", "Blocked": "crit, ", "Overdue": "crit, "}.get(s, "")


def mm_label(text: str, limit: int = 58) -> str:
    """Mermaid gantt task names cannot contain ':' ';' or '#'."""
    text = re.sub(r"[:;#]", " -", text).replace("  ", " ").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def mm_id(action_id: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", action_id.lower())


def short(text: str, limit: int = 110) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def action_table(actions: list[dict], today: date, full: bool = False) -> list[str]:
    if full:
        lines = ["| ID | Action | Definition of done | Owner | With | Deadline | Status | Comment |",
                 "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
    else:
        lines = ["| ID | Action | Owner | With | Deadline | Status |",
                 "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for a in actions:
        dl = date.fromisoformat(a["deadline"]) if a["deadline"] else None
        dls = f"{fmt(dl)} ({a['month']})" if dl else "—"
        with_ = ", ".join(a["contributors"][1:])
        if full:
            lines.append(f"| {a['id']} | {cell(a['action'])} | {cell(a['dod'])} | {cell(a['owner'])} | "
                         f"{cell(with_)} | {dls} | {status_pill(a, today)} | {cell(a['comment'])} |")
        else:
            lines.append(f"| {a['id']} | {cell(short(a['action']))} | {cell(a['owner'])} | {cell(with_)} | "
                         f"{dls} | {status_pill(a, today)} |")
    return lines


def legend() -> str:
    return ("Status pills: `[DONE]` · `[IN PROGRESS]` · `[TODO]` (before start) · `[OVERDUE]` (open, past its "
            "deadline) · `[BLOCKER]` · `[POSTPONED]`. In the Gantt charts: grey = done, blue = in progress, "
            "red = overdue or blocked.")


def as_of(plan: dict) -> str:
    mod = plan.get("modified")
    when = f", workbook saved {mod[:10]}" if mod else ""
    return f"Source: `{plan['source']}` ({plan['version']}{when})."


# --------------------------------------------------------------------------- #
# Pages                                                                        #
# --------------------------------------------------------------------------- #

def overview_page(plan: dict, cal: Calendar, today: date) -> str:
    acts = plan["actions"]
    eff = Counter(effective_status(a, today) for a in acts)
    cur = cal.sprint(today)
    s, e = cal.bounds(cur)
    lines = [f"**ALADIN WP2 — action plan {plan['version']}**", "",
             f"{as_of(plan)} Generated {today.isoformat()} by kf-cpto `aladin_sync.py`. "
             "The workbook is the source of truth: edit it (or the SharePoint copy) and re-run the sync, "
             "not these pages.", "",
             f"**Today:** {fmt(today)} — KF sprint **S{cur}** ({fmt(s)} → {fmt(e)}), ALADIN **M{project_month(today)}**.", "",
             "## Status", "", "```mermaid", "pie showData", "    title Actions by status"]
    for k in ["Done", "In progress", "Overdue", "Blocked", "Postponed", "Before start"]:
        if eff.get(k):
            lines.append(f'    "{k}" : {eff[k]}')
    lines += ["```", "", "| Status | Rows |", "| :--- | ---: |"]
    for k in ["Done", "In progress", "Overdue", "Blocked", "Postponed", "Before start"]:
        lines.append(f"| {k} | {eff.get(k, 0)} |")
    lines.append(f"| **Total** | **{len(acts)}** |")

    overdue = [a for a in acts if effective_status(a, today) in ("Overdue", "Blocked")]
    lines += ["", f"## Needs attention — overdue or blocked ({len(overdue)})", ""]
    lines += action_table(sorted(overdue, key=lambda a: a["deadline"] or ""), today) if overdue else ["Nothing overdue."]

    gates = [a for a in acts if a["type"] in ("Deliverable", "Milestone")]
    lines += ["", "## Gates and deliverables", ""] + action_table(gates, today)
    nxt = [a for a in acts if a["deadline"] and cal.sprint(date.fromisoformat(a["deadline"])) in (cur, cur + 1, cur + 2)
           and a["status"] != "Done"]
    lines += ["", f"## Due in the next three sprints (S{cur}–S{cur + 2})", ""]
    lines += action_table(nxt, today) if nxt else ["Nothing due."]
    lines += ["", legend()]
    return "\n".join(lines) + "\n"


def sprint_views_page(plan: dict, cal: Calendar, today: date) -> str:
    cur = cal.sprint(today)
    by_sprint = defaultdict(list)
    for a in plan["actions"]:
        if a["deadline"]:
            by_sprint[cal.sprint(date.fromisoformat(a["deadline"]))].append(a)
    carry = [a for a in plan["actions"] if a["deadline"] and cal.sprint(date.fromisoformat(a["deadline"])) < cur
             and a["status"] not in ("Done", "Postponed")]
    lines = ["# Sprints — previous / current / next", "",
             f"{as_of(plan)} KF sprint cadence (2 weeks). An action sits in the sprint that contains its deadline.", ""]
    for n, label in ((cur - 1, "previous"), (cur, "current"), (cur + 1, "next")):
        s, e = cal.bounds(n)
        lines += [f"## Sprint S{n} ({label}) — {fmt(s)} → {fmt(e)} · M{project_month(e)}", ""]
        lines += action_table(by_sprint.get(n, []), today) if by_sprint.get(n) else ["No ALADIN WP2 deadlines in this sprint."]
        lines.append("")
    lines += [f"## Carried over — still open from earlier sprints ({len(carry)})", "",
              "Rows whose deadline sprint has passed and that are not Done or Postponed in the workbook. "
              "They stay on their original sprint page too.", ""]
    lines += action_table(sorted(carry, key=lambda a: a["deadline"]), today) if carry else ["None."]
    lines += ["", legend()]
    return "\n".join(lines) + "\n"


def quarter_pages(plan: dict, cal: Calendar, today: date) -> list[tuple[str, str]]:
    """One page per project quarter (M1–M3, M4–M6, ...), each sprint with its actions and a small Gantt."""
    by_sprint = defaultdict(list)
    for a in plan["actions"]:
        if a["deadline"]:
            by_sprint[cal.sprint(date.fromisoformat(a["deadline"]))].append(a)
    last_m = max(project_month(date.fromisoformat(a["deadline"])) for a in plan["actions"] if a["deadline"])
    pages = []
    for q in range(1, (last_m + 2) // 3 + 1):
        m_lo, m_hi = 3 * q - 2, 3 * q
        sprints = sorted(n for n in by_sprint if m_lo <= project_month(cal.bounds(n)[1]) <= m_hi)
        q_start = date(PROJECT_M1.year + (PROJECT_M1.month - 1 + m_lo - 1) // 12, (PROJECT_M1.month - 1 + m_lo - 1) % 12 + 1, 1)
        q_end = date(PROJECT_M1.year + (PROJECT_M1.month - 1 + m_hi) // 12, (PROJECT_M1.month - 1 + m_hi) % 12 + 1, 1) - timedelta(days=1)
        name = f"Q{q} · M{m_lo}–M{m_hi} ({q_start.strftime('%b %Y')} – {q_end.strftime('%b %Y')})"
        lines = [f"# Sprint plan — {name}", "", as_of(plan), ""]
        n_actions = sum(len(by_sprint[n]) for n in sprints)
        if not sprints:
            lines.append("No ALADIN WP2 deadlines in this quarter.")
            pages.append((name, "\n".join(lines) + "\n"))
            continue
        lines += ["```mermaid", "gantt", f"    title {name} — {n_actions} actions by sprint", "    dateFormat YYYY-MM-DD",
                  "    axisFormat %d %b", "    excludes weekends"]
        for n in sprints:
            s, e = cal.bounds(n)
            lines.append(f"    section S{n} · {s.strftime('%d %b')}")
            for a in by_sprint[n]:
                lines.append(f"    {mm_label(a['id'] + ' ' + a['owner'] + ' - ' + a['action'], 52)} :"
                             f"{gantt_tag(a, today)}{mm_id(a['id'])}_q, {s.isoformat()}, {(e + timedelta(days=1)).isoformat()}")
        lines += ["```", ""]
        for n in sprints:
            s, e = cal.bounds(n)
            lines += [f"## S{n} — {fmt(s)} → {fmt(e)} · M{project_month(e)}", ""] + action_table(by_sprint[n], today) + [""]
        lines.append(legend())
        pages.append((name, "\n".join(lines) + "\n"))
    return pages


def ga_windows(ga_md: str | None) -> list[tuple[str, str, int, int]]:
    """(task id, title, from month, to month) from '### T2.1 — Title *(M4–M12)*' headings."""
    out = []
    for m in re.finditer(r"^### (T2\.\d) — (.+?) \*\(M(\d+)[–-]M(\d+)\)\*", ga_md or "", re.M):
        out.append((m.group(1), m.group(2), int(m.group(3)), int(m.group(4))))
    return out


def month_start(m: int) -> date:
    y, mo = divmod(PROJECT_M1.month - 1 + m - 1, 12)
    return date(PROJECT_M1.year + y, mo + 1, 1)


def gantt_ga_page(plan: dict, ga_md: str | None, today: date) -> str:
    lines = ["# Gantt — grant task windows and gates", "",
             f"{as_of(plan)} Task windows from the Grant Agreement (who-does-what §4); gates are the plan's "
             "Deliverable, Milestone and Decision rows, placed on their deadline. M1 = June 2026.", "",
             "```mermaid", "gantt", "    title ALADIN WP2 — GA task windows, decisions and gates (M1–M18)",
             "    dateFormat YYYY-MM-DD", "    axisFormat %b %y"]
    windows = ga_windows(ga_md)
    if windows:
        lines.append("    section GA task windows")
        for tid, title, a, b in windows:
            lines.append(f"    {mm_label(tid + ' ' + title, 50)} :{tid.replace('.', '')}w, "
                         f"{month_start(a).isoformat()}, {month_start(b + 1).isoformat()}")
    for typ, section in (("Decision", "Decisions"), ("Milestone", "Milestones"), ("Deliverable", "Deliverables")):
        rows = [a for a in plan["actions"] if a["type"] == typ and a["deadline"]]
        if rows:
            lines.append(f"    section {section}")
            for a in rows:
                tag = gantt_tag(a, today)
                lines.append(f"    {mm_label(a['id'] + ' ' + a['action'], 50)} :{tag}milestone, {mm_id(a['id'])}_g, {a['deadline']}, 0d")
    lines += ["```", "", legend()]
    return "\n".join(lines) + "\n"


def gantt_tasks_page(plan: dict, cal: Calendar, today: date) -> str:
    groups = defaultdict(list)
    for a in plan["actions"]:
        if a["deadline"]:
            groups[a["group"]].append(a)
    order = [g for g in GROUP_ORDER if g in groups] + sorted(g for g in groups if g not in GROUP_ORDER)
    lines = ["# Gantt — every action, by task", "",
             f"{as_of(plan)} Each bar is the KF sprint that contains the action's deadline.", "",
             "```mermaid", "gantt", f"    title ALADIN WP2 — {len(plan['actions'])} actions by task, on KF sprints",
             "    dateFormat YYYY-MM-DD", "    axisFormat %b %y", "    excludes weekends"]
    for g in order:
        lines.append(f"    section {g}")
        for a in sorted(groups[g], key=lambda x: x["deadline"]):
            s, e = cal.bounds(cal.sprint(date.fromisoformat(a["deadline"])))
            lines.append(f"    {mm_label(a['id'] + ' ' + a['owner'] + ' - ' + a['action'], 46)} :"
                         f"{gantt_tag(a, today)}{mm_id(a['id'])}_t, {s.isoformat()}, {(e + timedelta(days=1)).isoformat()}")
    lines += ["```", "", legend()]
    return "\n".join(lines) + "\n"


def group_pages(plan: dict, today: date) -> list[tuple[str, str]]:
    groups = defaultdict(list)
    for a in plan["actions"]:
        groups[a["group"]].append(a)
    order = [g for g in GROUP_ORDER if g in groups] + sorted(g for g in groups if g not in GROUP_ORDER)
    pages = []
    for g in order:
        rows = sorted(groups[g], key=lambda a: (a["deadline"] or "9999", a["id"]))
        lines = [f"# {g} — actions", "", as_of(plan), ""] + action_table(rows, today, full=True) + ["", legend()]
        pages.append((f"Actions · {g}", "\n".join(lines) + "\n"))
    return pages


def partner_load_page(plan: dict, today: date) -> str:
    acts = [a for a in plan["actions"] if a["deadline"]]
    months = sorted({project_month(date.fromisoformat(a["deadline"])) for a in acts})
    owns = defaultdict(Counter)
    named = defaultdict(Counter)
    for a in acts:
        m = project_month(date.fromisoformat(a["deadline"]))
        owner = "All partners" if a["owner"] == "All partners" else a["owner"]
        owns[owner][m] += 1
        for p in a["contributors"][1:]:
            named[p][m] += 1
    partners = sorted(set(owns) | set(named), key=lambda p: (-sum(owns[p].values()), p))
    lines = ["# Partner load — who owes what, month by month", "",
             f"{as_of(plan)} Number = items the partner **owns** that month (the first partner named on a row owns it); "
             "`·` = named on someone else's item. Same convention as the workbook's Timeline tab.", "",
             "| Partner | Owns | " + " | ".join(f"M{m}" for m in months) + " |",
             "| :--- | ---: | " + " | ".join(":---:" for _ in months) + " |"]
    for p in partners:
        cells = [str(owns[p][m]) if owns[p][m] else ("·" if named[p][m] else "") for m in months]
        lines.append(f"| {p} | {sum(owns[p].values())} | " + " | ".join(cells) + " |")
    if plan["partner_pm"]:
        lines += ["", "## WP2 person-months against what WP2 asks", "",
                  "| Partner | WP2 PM | Share | Read on whether the PM matches the ask | What has to happen |",
                  "| :--- | ---: | ---: | :--- | :--- |"]
        for r in plan["partner_pm"]:
            share = r.get("Share of WP2", "")
            try:
                share = f"{float(share) * 100:.1f}%"
            except ValueError:
                pass
            lines.append(f"| {cell(r.get('Partner', ''))} | {cell(r.get('WP2 PM', ''))} | {share} | "
                         f"{cell(r.get('Read on whether the PM matches the ask', ''))} | {cell(r.get('What has to happen', ''))} |")
    return "\n".join(lines) + "\n"


def notes_page(plan: dict) -> str:
    lines = ["# Notes, assumptions and open points", "", as_of(plan), ""]
    lines += [p for p in plan["notes_preamble"] if p] + [""]
    lines += ["| # | Open point | How the plan handles it | Owner | Rows affected |", "| ---: | :--- | :--- | :--- | :--- |"]
    for r in plan["notes"]:
        lines.append(f"| {cell(r.get('#', ''))} | **{cell(r.get('Discrepancy / open point', ''))}** — "
                     f"{cell(r.get('What the sources say', ''))} | {cell(r.get('How this plan handles it', ''))} | "
                     f"{cell(r.get('Owner', ''))} | {cell(r.get('Rows affected', ''))} |")
    return "\n".join(lines) + "\n"


def version_log_page(plan: dict) -> str:
    lines = ["# Workbook version log", "", as_of(plan), "",
             "| Version | Date | Issued by | Summary | What changed |", "| :--- | :--- | :--- | :--- | :--- |"]
    for r in plan["version_log"]:
        lines.append(f"| {cell(r.get('Version', ''))} | {cell(r.get('Date', ''))} | {cell(r.get('Issued by', ''))} | "
                     f"{cell(r.get('Summary', ''))} | {cell(r.get('What changed', ''))} |")
    return "\n".join(lines) + "\n"


def progress_page(plan: dict, history: list[dict], today: date) -> str:
    """Evolution across imported versions: status mix per version, and the diff to the previous one."""
    lines = ["# Progress & evolution", "",
             f"{as_of(plan)} Every imported workbook version is snapshotted outside the repo; this page compares them. "
             "When the SharePoint copy is imported, its statuses, moved deadlines and new rows show up here.", "",
             "## Status by imported version", "",
             "| Version | Saved | Rows | " + " | ".join(STATUS_ORDER) + " |",
             "| :--- | :--- | ---: | " + " | ".join("---:" for _ in STATUS_ORDER) + " |"]
    for h in history:
        c = Counter(a["status"] for a in h["actions"])
        lines.append(f"| {h['version']} | {(h.get('modified') or '')[:10]} | {len(h['actions'])} | "
                     + " | ".join(str(c.get(s, 0)) for s in STATUS_ORDER) + " |")
    prev = history[-2] if len(history) > 1 else None
    if not prev:
        lines += ["", "## Changes since the previous version", "",
                  f"{plan['version']} is the first imported version — nothing to compare yet. "
                  "Import the next workbook (e.g. the SharePoint copy) and this section lists what moved."]
        return "\n".join(lines) + "\n"
    old = {a["id"]: a for a in prev["actions"]}
    new = {a["id"]: a for a in plan["actions"]}
    status_ch = [(i, old[i]["status"], new[i]["status"]) for i in new if i in old and old[i]["status"] != new[i]["status"]]
    moved = [(i, old[i]["deadline"], new[i]["deadline"]) for i in new if i in old and old[i]["deadline"] != new[i]["deadline"]]
    added = [i for i in new if i not in old]
    gone = [i for i in old if i not in new]
    lines += ["", f"## Changes {prev['version']} → {plan['version']}", "",
              f"{len(status_ch)} status changes · {len(moved)} moved deadlines · {len(added)} new rows · {len(gone)} rows no longer present", ""]
    if status_ch:
        lines += ["### Status changes", "", "| ID | Action | From | To |", "| :--- | :--- | :--- | :--- |"]
        lines += [f"| {i} | {cell(short(new[i]['action'], 90))} | {a} | {b} |" for i, a, b in status_ch] + [""]
    if moved:
        lines += ["### Deadlines moved", "", "| ID | Action | From | To | Shift |", "| :--- | :--- | :--- | :--- | ---: |"]
        for i, a, b in moved:
            shift = (date.fromisoformat(b) - date.fromisoformat(a)).days if a and b else ""
            lines.append(f"| {i} | {cell(short(new[i]['action'], 90))} | {a or '—'} | {b or '—'} | "
                         f"{(f'{shift:+d} d' if shift != '' else '')} |")
        lines.append("")
    if added:
        lines += ["### New rows", ""] + action_table([new[i] for i in added], today) + [""]
    if gone:
        lines += ["### Rows no longer in the workbook", "", "| ID | Action (as last seen) |", "| :--- | :--- |"]
        lines += [f"| {i} | {cell(short(old[i]['action'], 110))} |" for i in gone]
    return "\n".join(lines) + "\n"


def ga_pages(ga_md: str, today: date) -> list[tuple[str, str]]:
    """Split the who-does-what working view on '## n. Title' into one page per section."""
    head, *parts = re.split(r"^## (?=\d+\. )", ga_md, flags=re.M)
    pages = []
    intro = re.sub(r"^# .*\n", "", head).strip()
    for part in parts:
        title, _, body = part.partition("\n")
        name = re.sub(r"^\d+\.\s*", "", title).strip()
        body = body.strip().rstrip("-").strip()
        extra = ""
        if name.lower().startswith("project overview"):
            extra = "\n\n" + wp_gantt(body)
        md = f"# {name}\n\n_From the KF working view of the Grant Agreement (who-does-what)._\n\n{body}{extra}\n"
        if intro and not pages:
            md = md.replace("\n\n", f"\n\n{intro}\n\n", 1)
        pages.append((f"GA · {name}", md))
    return pages


def wp_gantt(overview_md: str) -> str:
    rows = re.findall(r"^\|\s*\**(WP\d+)\**\s*\|\s*\**(.+?)\**\s*\|\s*\**(\w+)\**\s*\|\s*M(\d+)[–-]M(\d+)\s*\|", overview_md, re.M)
    if not rows:
        return ""
    lines = ["## All work packages on one timeline", "", "```mermaid", "gantt",
             "    title ALADIN — 15 work packages, M1–M48 (M1 = June 2026)", "    dateFormat YYYY-MM-DD", "    axisFormat %b %y"]
    current = None
    for wp, name, lead, a, b in rows:
        if lead != current:
            lines.append(f"    section Lead {lead}")
            current = lead
        tag = "active, " if lead == "KF" else ""
        lines.append(f"    {mm_label(wp + ' ' + name, 48)} :{tag}{wp.lower()}, {month_start(int(a)).isoformat()}, "
                     f"{month_start(int(b) + 1).isoformat()}")
    lines += ["```", "", "Highlighted bars are the work packages KF leads."]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Snapshots (outside the repo) and permissions                                 #
# --------------------------------------------------------------------------- #

def save_snapshot(plan: dict, plan_path: Path) -> list[dict]:
    """Store this version's rows next to the workbook; return all snapshots, oldest first."""
    folder = plan_path.parent / ".wiki-sync"
    folder.mkdir(exist_ok=True)
    keep = {k: plan[k] for k in ("version", "source", "modified", "actions")}
    (folder / f"plan-{plan['version']}.json").write_text(json.dumps(keep, indent=1))

    def key(p: Path):
        return [int(x) for x in re.findall(r"\d+", p.stem)]
    return [json.loads(p.read_text()) for p in sorted(folder.glob("plan-v*.json"), key=key)]


def kf_only_permissions(api: BookStack) -> dict:
    roles = {r["display_name"]: r["id"] for r in api.list("roles")}
    missing = [n for n in KF_ROLES if n not in roles]
    if missing:
        raise SystemExit(f"[ERROR] roles not found: {missing} — refusing to publish without KF-only permissions")
    perms = []
    for name, level in KF_ROLES.items():
        perms.append({"role_id": roles[name], "view": True, "create": level in ("all", "edit"),
                      "update": level in ("all", "edit"), "delete": level == "all"})
    return {"role_permissions": perms,
            "fallback_permissions": {"inheriting": False, "view": False, "create": False, "update": False, "delete": False}}


def ensure_private_book(sync: Sync, shelf: dict) -> dict | None:
    api = sync.api
    books = api.call("GET", f"shelves/{shelf['id']}").get("books", [])
    book = next((b for b in books if b["name"] == BOOK_NAME), None)
    wanted = kf_only_permissions(api)
    if book is None:
        print(f"[PLAN] create book '{BOOK_NAME}' on shelf '{shelf['name']}' (KF roles only)")
        if not sync.apply:
            return None
        book = api.call("POST", "books", {"name": BOOK_NAME, "description": BOOK_DESC})
        sync.manifest["created"]["books"].append({"id": book["id"], "name": book["name"]})
        api.call("PUT", f"content-permissions/book/{book['id']}", wanted)  # before any page exists
        ids = [b["id"] for b in books]
        sync.manifest["shelves_before"][str(shelf["id"])] = sorted(ids)
        api.call("PUT", f"shelves/{shelf['id']}", {"books": ids + [book["id"]]})
    current = api.call("GET", f"content-permissions/book/{book['id']}") if book.get("id") else {}
    fb = current.get("fallback_permissions", {})
    if fb.get("inheriting", True) or fb.get("view"):
        print("[PLAN] (re)apply KF-only permissions on the book")
        if sync.apply:
            api.call("PUT", f"content-permissions/book/{book['id']}", wanted)
            current = api.call("GET", f"content-permissions/book/{book['id']}")
            fb = current.get("fallback_permissions", {})
            if fb.get("inheriting", True) or fb.get("view"):
                raise SystemExit("[ERROR] could not restrict the book to KF roles — aborting before writing pages")
    return book


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #

def publish(sync: Sync, book, chapter, name: str, markdown: str) -> None:
    """BookStack shows the page name as the title, so a leading '# ...' line would repeat it."""
    markdown = re.sub(r"\A# [^\n]*\n+", "", markdown)
    sync.sync_page(book, chapter, name, markdown)


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish the ALADIN WP2 action plan to BookStack (dry-run by default).")
    ap.add_argument("--plan", required=True, type=Path, help="ALADIN_WP2_Action_Plan_vX.Y.xlsx")
    ap.add_argument("--ga", type=Path, help="ALADIN-who-does-what.md (GA working view)")
    ap.add_argument("--shelf", default=SHELF_NAME)
    ap.add_argument("--today", type=date.fromisoformat, help="override today's date (testing)")
    ap.add_argument("--apply", action="store_true", help="perform writes (default: dry-run)")
    args = ap.parse_args()

    today = args.today or datetime.now(timezone.utc).date()
    plan = parse_plan(args.plan)
    ga_md = args.ga.read_text() if args.ga else None
    cal = load_calendar()
    print(f"ALADIN Sync — {plan['version']} ({len(plan['actions'])} actions) — {'APPLY' if args.apply else 'dry-run'}")
    undated = [a["id"] for a in plan["actions"] if not a["deadline"]]
    if undated:
        print(f"[WARN] rows without a deadline (left out of sprints and Gantt): {', '.join(undated)}")
    history = save_snapshot(plan, args.plan) if args.apply else [plan]
    if not args.apply:
        folder = args.plan.parent / ".wiki-sync"
        prior = sorted(folder.glob("plan-v*.json")) if folder.exists() else []
        history = [json.loads(p.read_text()) for p in prior if p.stem != f"plan-{plan['version']}"] + [plan]

    api = BookStack(load_env())
    sync = Sync(api, args.apply)
    shelf = sync.find("shelves", args.shelf, name=args.shelf)
    if not shelf:
        print(f"[ERROR] shelf '{args.shelf}' does not exist in BookStack")
        return 1
    try:
        book = ensure_private_book(sync, shelf)
        publish(sync, book, None, "Overview", overview_page(plan, cal, today))
        publish(sync, book, None, "Progress & evolution", progress_page(plan, history, today))

        ch = sync.ensure_chapter(book, "Sprint plan")
        publish(sync, book, ch, "Sprints — previous, current, next", sprint_views_page(plan, cal, today))
        for name, md in quarter_pages(plan, cal, today):
            publish(sync, book, ch, name, md)

        ch = sync.ensure_chapter(book, "Gantt")
        publish(sync, book, ch, "Gantt — GA task windows and gates", gantt_ga_page(plan, ga_md, today))
        publish(sync, book, ch, "Gantt — every action by task", gantt_tasks_page(plan, cal, today))

        ch = sync.ensure_chapter(book, "Action plan")
        for name, md in group_pages(plan, today):
            publish(sync, book, ch, name, md)
        publish(sync, book, ch, "Partner load", partner_load_page(plan, today))
        publish(sync, book, ch, "Notes and open points", notes_page(plan))
        publish(sync, book, ch, "Workbook version log", version_log_page(plan))

        if ga_md:
            ch = sync.ensure_chapter(book, "Who does what (GA)")
            for name, md in ga_pages(ga_md, today):
                publish(sync, book, ch, name, md)
    finally:
        sync.save_manifest()
    print(f"[TALLY] {sync.tally['create']} create / {sync.tally['update']} update / "
          f"{sync.tally['skip']} skip / {sync.tally['conflict']} conflict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
