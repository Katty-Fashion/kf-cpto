#!/usr/bin/env python3
"""
Discover KF Team repos that contain kanban.md

Scans the GitHub org for repos with a kanban.md file at root,
replacing the static kf_projects list in _config.yml.

Usage:
    KF_PAT=<token> python scripts/discover.py
"""

import os
import sys
from pathlib import Path

import requests

from utils import ORG, DISCOVERED_FILE


def discover_kanban_repos(org: str = ORG, token: str = None) -> list[str]:
    """Return sorted list of repo names in the org that have kanban.md at root."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Fetch all repos in the org (paginated)
    repos = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/orgs/{org}/repos",
            headers=headers,
            params={"per_page": 100, "page": page, "type": "all"},
        )
        if resp.status_code != 200:
            print(f"Error fetching repos: {resp.status_code} {resp.text}")
            break

        batch = resp.json()
        if not batch:
            break

        repos.extend(batch)
        page += 1

        # Log rate limit
        remaining = resp.headers.get("X-RateLimit-Remaining", "?")
        print(f"  Page {page - 1}: {len(batch)} repos (rate limit remaining: {remaining})")

    # Filter: skip archived repos only (forks with kanban.md are valid projects)
    candidates = [
        r["name"] for r in repos
        if not r.get("archived")
    ]
    print(f"Found {len(candidates)} active repos in {org}")

    # Check which repos have kanban.md at root
    discovered = []
    for name in candidates:
        resp = requests.get(
            f"https://api.github.com/repos/{org}/{name}/contents/kanban.md",
            headers=headers,
        )
        if resp.status_code == 200:
            discovered.append(name)
            print(f"  + {name} (has kanban.md)")
        # 404 = no kanban.md, skip silently

    discovered.sort()
    return discovered


def main():
    token = os.environ.get("KF_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: No KF_PAT or GITHUB_TOKEN set. API rate limits will be very low.")

    repos = discover_kanban_repos(token=token)

    # Write discovered repos
    DISCOVERED_FILE.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERED_FILE.write_text("\n".join(repos) + "\n" if repos else "")

    print(f"\nDiscovered {len(repos)} repos with kanban.md")
    print(f"Written to {DISCOVERED_FILE}")

    if not repos:
        print("Warning: No repos found with kanban.md. Dashboard will be empty.")

    return repos


if __name__ == "__main__":
    main()
