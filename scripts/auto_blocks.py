#!/usr/bin/env python3
"""
Auto-blocks engine for augmented Jekyll pages.

A page declares its auto-blocks in YAML frontmatter:

    ---
    title: Migration Gantt
    layout: default
    auto_blocks: [calendar, meta-header]
    ---

and marks where each block goes with paired HTML comments:

    <!-- AUTO:calendar -->
    (anything between markers is replaced on every aggregator run)
    <!-- /AUTO:calendar -->

This module finds the markers, runs each block's renderer, and writes the
result back. Prose outside the markers is preserved verbatim.

Adding a new block: implement a renderer function, register it in
AUTO_BLOCK_RENDERERS. Renderers must be deterministic for a given context
(no timestamps inside generated content — those live in sync_status.yml).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Iterable

import yaml

# Marker regex — kept loose for readability but anchored to comment form.
# Captures the block name so we can route to the right renderer.
_MARKER_OPEN_RE = re.compile(r"<!--\s*AUTO:([a-z0-9_-]+)\s*-->", re.IGNORECASE)
_MARKER_CLOSE_RE = re.compile(r"<!--\s*/AUTO:([a-z0-9_-]+)\s*-->", re.IGNORECASE)
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


# --------------------------------------------------------------------------- #
# Renderers                                                                    #
# --------------------------------------------------------------------------- #

def _phases_for_week(pw: int, phases: list[dict]) -> str:
    """Return a slash-joined list of phase names that overlap project-week pw."""
    names = []
    for ph in phases:
        if ph.get("start_pw", 1) <= pw <= ph.get("end_pw", 1):
            # Strip "Faza " prefix for compactness in a table cell.
            label = ph["name"].replace("Faza ", "")
            names.append(label)
    return " / ".join(names) if names else "-"


def render_calendar(context: dict) -> str:
    """PW <-> CW <-> Mon/Fri table, derived purely from start_date."""
    cal = context.get("calendar") or {}
    start_str = cal.get("start_date")
    if not start_str:
        return "_(auto-data: calendar.start_date not configured in docs/_data/calendar.yml)_"
    try:
        start = date.fromisoformat(str(start_str))
    except ValueError:
        return f"_(auto-data: invalid start_date `{start_str}` in calendar.yml)_"
    total_weeks = int(cal.get("total_weeks", 32))
    sprint_len = int(cal.get("sprint_length_weeks", 2))
    phases = cal.get("phases", [])

    lines = [
        "",
        "| PW | CW | Mon (start) | Fri (end) | Sprint | Faza |",
        "|---:|---:|---|---|:-:|---|",
    ]
    for i in range(1, total_weeks + 1):
        mon = start + timedelta(weeks=i - 1)
        fri = mon + timedelta(days=4)
        cw = mon.isocalendar()[1]
        sprint = f"S{((i - 1) // sprint_len) + 1}"
        faza = _phases_for_week(i, phases)
        lines.append(
            f"| {i:>2} | {cw:>2} | {mon.isoformat()} | {fri.isoformat()} | {sprint:>3} | {faza} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_meta_header(context: dict) -> str:
    """Compact header summarizing the project span. No timestamps (those live
    in sync_status.yml and would create spurious diffs every run)."""
    cal = context.get("calendar") or {}
    start_str = cal.get("start_date", "?")
    total_weeks = int(cal.get("total_weeks", 0) or 0)
    sprint_len = int(cal.get("sprint_length_weeks", 2) or 2)
    try:
        start = date.fromisoformat(str(start_str))
        end = start + timedelta(weeks=total_weeks, days=-3)  # Friday of last week
        end_str = end.isoformat()
        cw_start = start.isocalendar()[1]
        cw_end = end.isocalendar()[1]
        span = f"**{start_str}** (CW{cw_start}) → **{end_str}** (CW{cw_end})"
    except ValueError:
        span = f"**{start_str}** → (end not computed)"
    sprints = (total_weeks + sprint_len - 1) // sprint_len if total_weeks else 0
    return (
        f"\n> **Project span (auto):** {span} · **{total_weeks}** weeks · "
        f"**{sprints}** sprints of {sprint_len} weeks\n"
    )


AUTO_BLOCK_RENDERERS: dict[str, Callable[[dict], str]] = {
    "calendar": render_calendar,
    "meta-header": render_meta_header,
}


# --------------------------------------------------------------------------- #
# Frontmatter + marker handling                                                #
# --------------------------------------------------------------------------- #

def split_frontmatter(content: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body) — empty dict if no frontmatter."""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    body = content[m.end():]
    return fm, body


def find_marker_pairs(body: str) -> list[tuple[str, int, int, int, int]]:
    """Find AUTO marker pairs in body.

    Returns a list of (name, open_start, open_end, close_start, close_end)
    tuples in document order. Raises ValueError on mismatched/nested markers.
    """
    opens = [(m.group(1).lower(), m.start(), m.end()) for m in _MARKER_OPEN_RE.finditer(body)]
    closes = [(m.group(1).lower(), m.start(), m.end()) for m in _MARKER_CLOSE_RE.finditer(body)]
    if len(opens) != len(closes):
        raise ValueError(
            f"AUTO marker count mismatch: {len(opens)} open vs {len(closes)} close"
        )
    pairs = []
    # Markers must be sibling pairs (no nesting). We pair by document order.
    open_iter = iter(opens)
    close_iter = iter(closes)
    for (oname, os_, oe), (cname, cs, ce) in zip(open_iter, close_iter):
        if oname != cname:
            raise ValueError(
                f"AUTO marker mismatch: opened with `{oname}`, closed with `{cname}`"
            )
        if cs < oe:
            raise ValueError(
                f"AUTO marker `{oname}` close precedes its own open — nested/overlapping markers are not supported"
            )
        pairs.append((oname, os_, oe, cs, ce))
    return pairs


# --------------------------------------------------------------------------- #
# Injection                                                                    #
# --------------------------------------------------------------------------- #

def inject_auto_blocks(content: str, context: dict, page_label: str = "") -> str:
    """Run all AUTO renderers declared in `auto_blocks:` frontmatter, replacing
    content between paired markers. Prose outside markers is untouched.

    If `auto_blocks` is missing/empty, returns content unchanged.
    Raises ValueError if a declared block has no renderer or no markers.
    """
    fm, body = split_frontmatter(content)
    declared = fm.get("auto_blocks") or []
    if not declared:
        return content

    pairs = find_marker_pairs(body)
    marker_names = {p[0] for p in pairs}

    # Surface mismatches early — these are config bugs the linter will catch
    # too, but we don't want to silently render half the page.
    missing_markers = set(declared) - marker_names
    if missing_markers:
        raise ValueError(
            f"{page_label}: declared auto_blocks {sorted(missing_markers)} "
            f"have no <!-- AUTO:... --> markers in body"
        )
    orphan_markers = marker_names - set(declared)
    if orphan_markers:
        raise ValueError(
            f"{page_label}: markers {sorted(orphan_markers)} not declared in "
            f"`auto_blocks:` frontmatter"
        )
    unknown = set(declared) - set(AUTO_BLOCK_RENDERERS)
    if unknown:
        raise ValueError(
            f"{page_label}: unknown auto_blocks {sorted(unknown)} — "
            f"known: {sorted(AUTO_BLOCK_RENDERERS)}"
        )

    # Replace in reverse document order so offsets stay valid.
    new_body = body
    for name, os_, oe, cs, ce in reversed(pairs):
        rendered = AUTO_BLOCK_RENDERERS[name](context)
        # Preserve the markers themselves; replace only the interior.
        new_body = new_body[:oe] + "\n" + rendered.strip("\n") + "\n" + new_body[cs:]

    # Reassemble with original frontmatter.
    head_match = _FRONTMATTER_RE.match(content)
    head = head_match.group(0) if head_match else ""
    return head + new_body


def process_page(path: Path, context: dict) -> bool:
    """Inject auto-blocks into a single page. Returns True if content changed."""
    original = path.read_text()
    updated = inject_auto_blocks(original, context, page_label=str(path))
    if updated != original:
        path.write_text(updated)
        return True
    return False


# --------------------------------------------------------------------------- #
# Context loaders                                                              #
# --------------------------------------------------------------------------- #

def load_context(data_dir: Path) -> dict:
    """Load every `_data/*.yml` file by its stem into a context dict so
    renderers can reference e.g. context['calendar']['start_date']."""
    ctx: dict = {}
    if not data_dir.exists():
        return ctx
    for yml in sorted(data_dir.glob("*.yml")):
        try:
            ctx[yml.stem] = yaml.safe_load(yml.read_text()) or {}
        except yaml.YAMLError as e:
            print(f"Warning: failed to load {yml}: {e}")
    return ctx


def known_block_names() -> Iterable[str]:
    """Exposed for the validator script."""
    return tuple(AUTO_BLOCK_RENDERERS.keys())
