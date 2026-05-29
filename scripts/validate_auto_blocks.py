#!/usr/bin/env python3
"""
Lint augmented Jekyll pages for auto-block marker hygiene.

Walks docs/ looking for pages whose frontmatter declares `auto_blocks: [...]`,
and verifies:
  - every declared block has a matching `<!-- AUTO:name -->` / `<!-- /AUTO:name -->` pair;
  - every marker pair in the body is declared in `auto_blocks`;
  - every declared block name corresponds to a registered renderer.

Exits non-zero on any failure so the workflow blocks bad PRs.
"""

from __future__ import annotations

import sys
from pathlib import Path

from auto_blocks import (
    find_marker_pairs,
    known_block_names,
    split_frontmatter,
)
from utils import DOCS_DIR


def check_page(path: Path) -> list[str]:
    """Return a list of error strings (empty if the page is clean)."""
    errors: list[str] = []
    try:
        content = path.read_text()
    except OSError as e:
        return [f"{path}: cannot read ({e})"]

    fm, body = split_frontmatter(content)
    declared = fm.get("auto_blocks") or []
    if not declared:
        return errors  # not an augmented page — nothing to lint

    if not isinstance(declared, list):
        return [f"{path}: `auto_blocks:` must be a YAML list, got {type(declared).__name__}"]

    try:
        pairs = find_marker_pairs(body)
    except ValueError as e:
        return [f"{path}: {e}"]
    marker_names = {p[0] for p in pairs}
    declared_set = {str(n).lower() for n in declared}
    known = set(known_block_names())

    missing = declared_set - marker_names
    if missing:
        errors.append(
            f"{path}: declared auto_blocks {sorted(missing)} have no markers in body"
        )
    orphan = marker_names - declared_set
    if orphan:
        errors.append(
            f"{path}: markers {sorted(orphan)} not listed in `auto_blocks:` frontmatter"
        )
    unknown = declared_set - known
    if unknown:
        errors.append(
            f"{path}: unknown auto_blocks {sorted(unknown)} — known: {sorted(known)}"
        )

    return errors


def main() -> int:
    if not DOCS_DIR.exists():
        print(f"warn: {DOCS_DIR} does not exist — nothing to lint")
        return 0

    all_errors: list[str] = []
    checked = 0
    augmented = 0

    for md_path in sorted(DOCS_DIR.rglob("*.md")):
        checked += 1
        content = md_path.read_text()
        fm, _ = split_frontmatter(content)
        if not fm.get("auto_blocks"):
            continue
        augmented += 1
        errs = check_page(md_path)
        all_errors.extend(errs)

    print(f"Checked {checked} markdown files; {augmented} declared auto_blocks.")
    if all_errors:
        print(f"\n{len(all_errors)} error(s):")
        for e in all_errors:
            print(f"  - {e}")
        return 1
    print("All augmented pages are clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
