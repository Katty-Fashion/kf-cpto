#!/usr/bin/env python3
"""
Lint the generated OKF bundle for conformance.

Asserts for every non-index/log .md under docs/okf/:
  - parseable YAML frontmatter with a non-empty `type` field
  - every absolute bundle-relative link (/...​.md) resolves to an existing file

Exits non-zero on any violation (hard gate); exits 0 if clean.
Mirror of validate_auto_blocks.py idiom.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from utils import DOCS_DIR

OKF_DIR = DOCS_DIR / "okf"

# Index and log files are exempt from the type requirement (per OKF spec)
_EXEMPT_NAMES = {"index.md", "log.md"}

# Matches absolute bundle-relative markdown links: (/path/to/file.md)
_LINK_RE = re.compile(r"\[([^\]]*)\]\((/[^)]+\.md)\)")


def _parse_frontmatter(content: str) -> dict:
    """Return the YAML frontmatter dict, or {} if absent/unparseable."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def check_file(path: Path) -> list[str]:
    """Return a list of error strings (empty if the file is conformant)."""
    errors: list[str] = []
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"{path}: cannot read ({e})"]

    name = path.name
    is_exempt = name in _EXEMPT_NAMES

    if not is_exempt:
        fm = _parse_frontmatter(content)
        if not fm:
            errors.append(
                f"{path}: no parseable YAML frontmatter — every concept file must have "
                f"a `type:` field"
            )
        elif not str(fm.get("type", "")).strip():
            errors.append(
                f"{path}: frontmatter missing non-empty `type` field"
            )

    # Check that all absolute bundle-relative links resolve to existing files
    for match in _LINK_RE.finditer(content):
        link_path = match.group(2)  # e.g. /projects/kf-platform.md
        # Resolve relative to okf_dir: strip leading /
        target = OKF_DIR / link_path.lstrip("/")
        if not target.exists():
            errors.append(
                f"{path}: broken link [{match.group(1)}]({link_path}) "
                f"— target not found: {target}"
            )

    return errors


def main() -> int:
    if not OKF_DIR.exists():
        print(f"warn: {OKF_DIR} does not exist — nothing to lint")
        return 0

    all_errors: list[str] = []
    checked = 0
    concept_count = 0
    exempt_count = 0

    for md_path in sorted(OKF_DIR.rglob("*.md")):
        checked += 1
        if md_path.name in _EXEMPT_NAMES:
            exempt_count += 1
        else:
            concept_count += 1
        errs = check_file(md_path)
        all_errors.extend(errs)

    print(
        f"Checked {checked} OKF markdown files "
        f"({concept_count} concepts, {exempt_count} exempt index/log)."
    )
    if all_errors:
        print(f"\n{len(all_errors)} conformance error(s):")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("OKF bundle is conformant.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
