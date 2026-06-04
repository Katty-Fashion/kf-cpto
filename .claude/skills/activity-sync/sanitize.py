#!/usr/bin/env python3
"""
Activity Sync — Sanitizer

Pure Mermaid/table break-character sanitization. No git, no I/O, no sys.path
injection — this module is a pure library consumed by writeback.py.

Applies readable substitutions for characters that break Mermaid diagrams or
pipe-table structure (DIAG-01/02/03). Romanian diacritics are preserved verbatim;
emoji codepoints are stripped silently.

Usage (imported by writeback.py):
    from sanitize import sanitize_cell, sanitize_body
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Module constants (SCREAMING_SNAKE_CASE per CLAUDE.md)
# ---------------------------------------------------------------------------

# Readable substitution map for Mermaid/table break characters.
# Choices:
#   : -> ' -'  (colon breaks Mermaid labels; space-dash is readable)
#   " -> '     (double-quote breaks Mermaid string literals)
#   | -> /     (pipe breaks markdown table columns)
#   ; -> ,     (semicolon breaks Mermaid syntax)
#   ( ) { } # -> '' (dropped; these break Mermaid node/edge syntax)
_BREAK_MAP: dict[str, str] = {
    ":": " -",
    '"': "'",
    "|": "/",
    ";": ",",
    "(": "",
    ")": "",
    "{": "",
    "}": "",
    "#": "",
}

# Header/separator cell markers — rows containing these are skipped by sanitize_body.
# "Task" identifies the header row (first data cell of the header).
# ":---" is the canonical alignment marker in every pipe-table separator row.
_HEADER_CELLS = frozenset({"Task", ":---"})

# Structural GFM table-separator cell matcher (CR-01). A separator cell is a run
# of one-or-more dashes optionally fenced by alignment colons:
#   ---  :---  ---:  :--:  :-:  etc.
# This recognises ALL valid GFM separator alignments, not just left-align ':---'.
_SEP_CELL_RE = re.compile(r"^:?-+:?$")


def _is_separator_row(stripped: str) -> bool:
    """True if a pipe-table row is a GFM alignment separator row.

    Detects separators structurally (every non-empty inter-pipe cell matches
    ``^:?-+:?$``) rather than by the literal ':---' marker, so '---', ':--:',
    and '---:' separators are recognised and passed through verbatim (CR-01).

    Requires the row to start AND end with '|' (CR-02): a separator without a
    trailing pipe is malformed and handled by the data-row path's guard.
    """
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    cells = [c.strip() for c in stripped.split("|")[1:-1]]
    return bool(cells) and all(_SEP_CELL_RE.match(c) for c in cells)


# ---------------------------------------------------------------------------
# Emoji detection (stdlib only — no regex package; Python 3.9 compatible)
# ---------------------------------------------------------------------------

def _is_emoji(cp: int) -> bool:
    """True if Unicode codepoint cp falls in a known emoji block.

    Covers all major emoji blocks per Unicode 15.x standard.
    Romanian diacritics (U+0103, U+00E2, U+00EE, U+0219, U+021B) are in the
    Basic Latin + Latin Extended range (0x0000–0x02FF) — well below all blocks
    listed here. They will never be treated as emoji.

    Blocks verified against:
    - https://unicode.org/charts/PDF/U1F600.pdf  (Emoticons)
    - https://unicode.org/charts/PDF/U1F300.pdf  (Misc Symbols and Pictographs)
    - https://unicode.org/charts/PDF/U1F680.pdf  (Transport and Map)
    """
    return (
        0x1F600 <= cp <= 0x1F64F or  # Emoticons (😀–🙏)
        0x1F300 <= cp <= 0x1F5FF or  # Misc Symbols and Pictographs (🌀–🗿)
        0x1F680 <= cp <= 0x1F6FF or  # Transport and Map (🚀–🛿)
        0x1F700 <= cp <= 0x1F9FF or  # Alchemical + Geometric + Supplemental (🜀–🧿)
        0x1FA00 <= cp <= 0x1FA6F or  # Chess Symbols (🨀–🩯)
        0x1FA70 <= cp <= 0x1FAFF or  # Symbols and Pictographs Extended-A (🩰–🫿)
        0x2600  <= cp <= 0x26FF  or  # Misc Symbols (☀–⛿) — includes ⚠ ✅ ⛔
        0x2700  <= cp <= 0x27BF  or  # Dingbats (✀–➿) — includes ✔ ✗ ➡
        0xFE00  <= cp <= 0xFE0F  or  # Variation Selectors (️ modifiers)
        0x1F1E0 <= cp <= 0x1F1FF or  # Regional Indicator Symbols (🇦–🇿, flags)
        cp == 0x200D                  # Zero Width Joiner (emoji sequence combiner)
    )


# ---------------------------------------------------------------------------
# Public transforms
# ---------------------------------------------------------------------------

def sanitize_cell(text: str) -> str:
    """Apply break-char substitution + emoji strip to a single cell value.

    Readable substitutions only (per _BREAK_MAP). Emoji codepoints are dropped
    silently. Romanian diacritics (ă/â/î/ș/ț) pass through unchanged.

    Multiple consecutive spaces collapsed to one; leading/trailing whitespace
    stripped. Idempotent: sanitize_cell(sanitize_cell(x)) == sanitize_cell(x).

    Args:
        text: Raw cell text extracted from a markdown pipe-table row.

    Returns:
        Sanitized cell text safe for Mermaid diagrams and pipe-table structure.
    """
    result: list[str] = []
    for c in text:
        cp = ord(c)
        if _is_emoji(cp):
            continue  # emoji dropped — adds no readable information
        result.append(_BREAK_MAP.get(c, c))
    # Collapse multiple spaces (from dropped chars leaving adjacent spaces)
    return re.sub(r"  +", " ", "".join(result)).strip()


def sanitize_body(body: str) -> str:
    """Apply sanitize_cell to all data cells in task-table rows within body.

    Skips (passes byte-for-byte):
    - Non-pipe lines: prose, blank lines, HTML comments
    - Header row: first cell == 'Task'
    - Separator rows: every cell matches a GFM alignment marker (---, :---,
      ---:, :--:) — detected structurally via _is_separator_row (CR-01)
    - Rows lacking a trailing '|': skipped with a [WARN] (CR-02)

    Sanitizes only data rows (rows that start with '|', are not header, not
    separator). Within data rows, sanitizes parts[1..-2] (all data cells,
    preserving the leading empty part[0] and trailing part[-1] from split('|')).

    Idempotent: sanitize_body(sanitize_body(x)) == sanitize_body(x), because
    sanitize_cell is idempotent and no character in the substitution output is
    in _BREAK_MAP or an emoji codepoint.

    Args:
        body: The non-frontmatter portion of a kanban.md file (everything after
              the closing '---' delimiter).

    Returns:
        Body string with data cell text sanitized; all structural elements intact.
    """
    lines = body.splitlines(keepends=True)
    result: list[str] = []

    for line in lines:
        stripped = line.rstrip("\n")

        # Non-pipe line: prose, blank, HTML comment — pass through unchanged
        if not stripped.startswith("|"):
            result.append(line)
            continue

        # Separator row: any valid GFM alignment markers (---, :---, ---:, :--:)
        # Checked BEFORE the trailing-pipe guard so well-formed separators are
        # always preserved verbatim (CR-01).
        if _is_separator_row(stripped):
            result.append(line)
            continue

        # CR-02: a well-formed data/header row must start AND end with '|'.
        # GFM permits trailing-pipe-less rows, but the cell-index logic below
        # (and apply_status_change's parts[-2] addressing) assumes a trailing
        # pipe. Skip such rows verbatim with a [WARN] rather than corrupting the
        # last cell by sanitizing past the true final column.
        if not stripped.endswith("|"):
            print(f"[WARN] Skipping malformed (no trailing pipe) row: {stripped!r}")
            result.append(line)
            continue

        # Split on pipe to inspect cells
        parts = stripped.split("|")
        first_cell = parts[1].strip() if len(parts) > 1 else ""

        # Header row: first data cell is literally "Task"
        if first_cell == "Task":
            result.append(line)
            continue

        # Data row: sanitize parts[1..-2], preserve parts[0] and parts[-1]
        # parts[0] = '' (before leading |); parts[-1] = '' or '\r' (after trailing |)
        if len(parts) < 4:
            # Malformed row with fewer than 3 pipes — pass through unchanged
            result.append(line)
            continue

        new_parts = [parts[0]]
        for i in range(1, len(parts) - 1):
            new_parts.append(f" {sanitize_cell(parts[i].strip())} ")
        new_parts.append(parts[-1])

        # Preserve original EOL character
        eol = "\n" if line.endswith("\n") else ""
        result.append("|".join(new_parts) + eol)

    return "".join(result)
