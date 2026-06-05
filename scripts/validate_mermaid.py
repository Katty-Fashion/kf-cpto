#!/usr/bin/env python3
"""
Validate every ```mermaid``` block in docs/ for the syntax breakers that crash
MermaidJS at render time ("Syntax error in text").

Checks are per diagram type (only DEFINITIVE breakers, to avoid false positives):
  - kanban / graph node labels  id["..."]  -> must hold exactly 2 quote delimiters
  - graph node ids                          -> must be ^[A-Za-z][A-Za-z0-9_]*$
  - gantt task/section titles (before ':')  -> no '"', '[', ']', or stray ':'
  - pie slice rows                          -> 0 or 2 quotes

Exit 1 on any hazard (suitable as a CI gate). Run:
    python scripts/validate_mermaid.py
"""
import re
import sys
from pathlib import Path

DOCS = Path(__file__).parent.parent / "docs"
_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
_GANTT_DIRECTIVES = ("title", "dateFormat", "axisFormat", "excludes",
                     "section", "todayMarker", "%%")
_NODE_ID_RE = re.compile(r"^([^\s\[]+)\[")
_SAFE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DURATION_RE = re.compile(r"^\d+(\.\d+)?[dhwmy]$")
# Gantt metadata tokens that are tags, not dates (mermaid keywords).
_GANTT_TAGS = {"done", "active", "crit", "milestone", "after"}


def _check_block(dtype: str, body_lines: list) -> list:
    issues = []
    for raw in body_lines:
        s = raw.strip()
        if not s or s.startswith("%%"):
            continue
        if dtype == "kanban":
            if '["' in s and s.count('"') != 2:
                issues.append(f"kanban node label not exactly 2 quotes: {s[:80]}")
        elif dtype == "graph" or dtype.startswith("flowchart"):
            m = _NODE_ID_RE.match(s)
            if m and not _SAFE_ID_RE.match(m.group(1)):
                issues.append(f"graph node id not [A-Za-z][A-Za-z0-9_]*: {s[:80]}")
            if '["' in s and s.count('"') != 2:
                issues.append(f"graph node label not exactly 2 quotes: {s[:80]}")
        elif dtype == "gantt":
            if s.startswith(_GANTT_DIRECTIVES) or ":" not in s:
                continue
            title, meta = s.split(":", 1)
            if not title.strip():
                issues.append(f"gantt empty task title: {s[:80]}")
            if re.search(r'["\[\]]', title):
                issues.append(f"gantt title has delimiter char: {s[:80]}")
            # Metadata after ':' is comma-separated tags + date(s)/duration. Every
            # non-tag, non-id token that looks date-ish must be a real ISO date or
            # duration — this is what catches '—' / '-' / 'TBD' in a date cell.
            tokens = [t.strip() for t in meta.split(",") if t.strip()]
            for tok in tokens:
                if tok in _GANTT_TAGS:
                    continue
                if _ISO_DATE_RE.match(tok) or _DURATION_RE.match(tok):
                    continue
                # a bare identifier (task id / 'after X') is allowed; flag the rest
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tok):
                    continue
                issues.append(f"gantt invalid date/duration token {tok!r}: {s[:80]}")
        elif dtype == "pie":
            if s.count('"') not in (0, 2):
                issues.append(f"pie row not 0/2 quotes: {s[:80]}")
    return issues


def main() -> int:
    files = sorted(DOCS.glob("*.md")) + sorted(DOCS.glob("_projects/*.md"))
    total = 0
    for f in files:
        for m in _BLOCK_RE.finditer(f.read_text(encoding="utf-8")):
            lines = [ln for ln in m.group(1).splitlines() if ln.strip()]
            if not lines:
                continue
            dtype = lines[0].strip().split()[0]
            for issue in _check_block(dtype, lines[1:]):
                print(f"  [MERMAID] {f.relative_to(DOCS.parent)}: {issue}")
                total += 1
    if total:
        print(f"\nFAIL: {total} Mermaid syntax hazard(s) found.")
        return 1
    print(f"OK: {len(files)} docs scanned, no Mermaid syntax hazards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
