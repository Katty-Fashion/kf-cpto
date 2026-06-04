#!/usr/bin/env python3
"""
Activity Sync — Write-Back (string builders)

Consumes reconcile.run() Proposal objects and applies them to kanban.md files
in repos-local/. This plan (03-01) adds only the pure string builders — git
operations (commit/push), conflict detection, batch confirmation, and manifest
writing land in Plans 02 and 03.

String-builder responsibilities:
- split_kanban()         — split kanban.md into (frontmatter_str, body_str)
- roundtrip_frontmatter() — ruamel.yaml round-trip preserving # comments (WB-01)
- reconstruct_kanban()   — rejoin frontmatter + body into the corrected string
- apply_status_change()  — targeted status-cell replacement by task name
- _content_changed()     — byte-compare idempotency gate

Usage:
    from writeback import split_kanban, reconstruct_kanban, apply_status_change

Phase 3 entry point (plans 02/03 will add run() / main()):
    from writeback import run
"""
from __future__ import annotations

import re
import sys
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

# sys.path injection — 4 .parent levels from writeback.py to repo root
# Chain: writeback.py -> activity-sync/ -> skills/ -> .claude/ -> repo_root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils import ORG, TASK_STATUSES  # noqa: E402

# ---------------------------------------------------------------------------
# Module constants (SCREAMING_SNAKE_CASE per CLAUDE.md)
# ---------------------------------------------------------------------------

# Regex for splitting kanban.md into frontmatter + body.
# Matches the opening '---\n<content>\n---\n' block at the start of the file.
# re.DOTALL allows '.*?' to span newlines.
_FM_RE = re.compile(r'^---\n(.*?)\n---\n?', re.DOTALL)

# Canonical commit message for all write-back commits.
COMMIT_MSG = "chore(kanban): reconcile task statuses from repo activity"


# ---------------------------------------------------------------------------
# Frontmatter round-trip (ruamel.yaml, WB-01)
# ---------------------------------------------------------------------------

def split_kanban(content: str) -> tuple[str, str]:
    """Split kanban.md content into (frontmatter_str, body_str).

    Uses _FM_RE to locate the opening '---' block. frontmatter_str is the raw
    YAML text between the delimiters (without the '---' lines themselves).
    body_str is everything after the closing '---\\n'.

    Args:
        content: Full kanban.md file content as a string.

    Returns:
        (frontmatter_str, body_str) tuple.

    Raises:
        ValueError: If content does not start with a YAML frontmatter block.
    """
    match = _FM_RE.match(content)
    if not match:
        raise ValueError(
            "No YAML frontmatter found in kanban.md. "
            "File must start with --- ... --- block."
        )
    frontmatter_str = match.group(1)
    body_str = content[match.end():]
    return frontmatter_str, body_str


def roundtrip_frontmatter(fm_str: str) -> str:
    """Round-trip frontmatter YAML through ruamel, preserving # comments and key order.

    Uses ruamel.YAML() with preserve_quotes=True so quoted string values survive
    the round-trip byte-identical.

    Applies a trailing-newline guard: ruamel may emit extra blank lines in some
    edge cases. We normalize to exactly one trailing newline (Pitfall 5).

    Args:
        fm_str: Raw YAML text extracted by split_kanban() (no '---' delimiters).

    Returns:
        Round-tripped YAML text ending with exactly one '\\n'.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(fm_str)
    stream = StringIO()
    yaml.dump(data, stream)
    # Pitfall 5: normalize to exactly one trailing newline
    return stream.getvalue().rstrip("\n") + "\n"


def reconstruct_kanban(fm_str: str, body_str: str) -> str:
    """Reconstruct a kanban.md string from (possibly edited) frontmatter and body.

    The round-tripped frontmatter preserves # comments, key order, and quoting
    (WB-01). For an unmodified file, reconstruct_kanban(*split_kanban(orig))
    produces a byte-identical string.

    Important: the body is NEVER passed through ruamel. Only the frontmatter is
    round-tripped — the body (table rows, prose, HTML comments) is used verbatim.

    Args:
        fm_str:   Raw frontmatter YAML text (no '---' delimiters).
        body_str: Everything after the closing '---' delimiter (may be edited).

    Returns:
        Complete kanban.md content string with '---\\n' delimiters around the
        round-tripped frontmatter followed by the (possibly edited) body.
    """
    rt_fm = roundtrip_frontmatter(fm_str)
    return "---\n" + rt_fm + "---\n" + body_str


# ---------------------------------------------------------------------------
# Status-cell targeted replacement (Pattern 2 from 03-RESEARCH.md)
# ---------------------------------------------------------------------------

def apply_status_change(
    body_str: str,
    task_name: str,
    new_status: str,
) -> tuple[str, bool]:
    """Replace the Status cell for the first row whose Task cell matches task_name.

    Operates on the raw body_str (pre-sanitize). Works for both 4-col and 6-col
    tables because Status is always the last data column (parts[-2]).

    Rules:
    - Only the FIRST matching row is updated (forward-only, one match per Proposal).
    - If current status already equals new_status, returns (body_str, False) unchanged.
    - If task_name appears on multiple rows, updates only the first and prints [WARN].
    - If task_name is not found, returns (body_str, False) unchanged.

    Args:
        body_str:   Body portion of kanban.md (everything after closing '---').
        task_name:  Exact task name to match (from Proposal.task; matches parts[1].strip()).
        new_status: Target status string (validated TASK_STATUSES member by caller).

    Returns:
        (new_body_str, was_changed) where was_changed is True if any row was modified.
    """
    lines = body_str.splitlines(keepends=True)
    new_lines: list[str] = []
    changed = False
    match_count = 0

    for line in lines:
        stripped = line.rstrip("\n")

        # Only process pipe-table rows
        if not stripped.startswith("|"):
            new_lines.append(line)
            continue

        parts = stripped.split("|")

        # Need at least | task | ... | status | => 4 separator parts minimum
        if len(parts) < 4:
            new_lines.append(line)
            continue

        task_cell = parts[1].strip()
        if task_cell != task_name:
            new_lines.append(line)
            continue

        # Matching row found
        match_count += 1

        if match_count > 1:
            # Duplicate task name — skip this row (first-match-only contract)
            print(
                f"[WARN] Duplicate task name '{task_name}' found in table "
                f"(match #{match_count}). Only the first occurrence is updated."
            )
            new_lines.append(line)
            continue

        # First match: check if status already equals target
        old_status = parts[-2].strip()
        if old_status == new_status:
            # No change needed — idempotent skip
            new_lines.append(line)
            continue

        # Apply the replacement: parts[-2] is the last data cell (Status column)
        parts[-2] = f" {new_status} "
        eol = "\n" if line.endswith("\n") else ""
        new_lines.append("|".join(parts) + eol)
        changed = True

    return "".join(new_lines), changed


# ---------------------------------------------------------------------------
# Idempotency byte-compare gate (Pattern 6 from 03-RESEARCH.md)
# ---------------------------------------------------------------------------

def _content_changed(kanban_path: str, proposed: str) -> bool:
    """True if proposed content differs from the current file bytes.

    Used as an idempotency gate before any file write or git operation.
    Returns False (skip write) when the proposed string is byte-identical
    to the current kanban.md content.

    Args:
        kanban_path: Absolute path to the kanban.md file.
        proposed:    The fully reconstructed kanban.md content string.

    Returns:
        True if content differs (write needed); False if content is identical (skip).
    """
    current = Path(kanban_path).read_bytes()
    return current != proposed.encode("utf-8")
