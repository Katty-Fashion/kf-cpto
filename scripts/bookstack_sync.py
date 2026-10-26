#!/usr/bin/env python3
"""
Sync project information from the dashboard's canonical data into BookStack.

Local-only (like the activity-sync skill); CI never runs this. Reads the same
sources the GitHub Pages site is built from — docs/_projects/*.md, docs/_data/
loe.yml and git_activity.yml — and publishes them under each project's shelf:

    shelf (e.g. "2601. KF-Platform")
      └─ book "Delivery Dashboard"          (managed by this script)
           ├─ page "Overview"               (roll-up for the shelf's repos)
           ├─ page "Migration Gantt" ...    (org-level charts, where configured)
           └─ chapter "<repo>"
                ├─ page "Status & Kanban"   (the project's Pages content)
                └─ page "Activity"          (git-derived, team-level, conservative)

Mermaid is pre-rendered to PNG (mermaid-cli + local Chrome) and uploaded, since
BookStack has no Mermaid renderer yet.

Safety:
  - every --apply run writes a rollback manifest; undo with --rollback <run_id|latest> (dry-run unless --apply)
  - dry-run by default; --apply performs writes
  - only ever touches the managed book; existing hand-curated books are never edited
  - every managed page carries tags kfcpto-src / kfcpto-md; a page whose current
    markdown no longer matches kfcpto-md was edited by a human -> reported, skipped
  - never deletes pages, chapters or books

Usage:
    python scripts/bookstack_sync.py --shelf "2601. KF-Platform" --repo kf-platform          # dry-run
    python scripts/bookstack_sync.py --shelf "2601. KF-Platform" --repo kf-platform --apply
Credentials: BOOKSTACK_URL / BOOKSTACK_TOKEN_ID / BOOKSTACK_TOKEN_SECRET from .env or env.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from utils import BASE_DIR, DATA_DIR, DOCS_DIR, GIT_ACTIVITY_FILE, LOE_DATA_FILE

BOOK_NAME = "Delivery Dashboard"
PAGES_BASE = "https://katty-fashion.github.io/kf-cpto"
MAP_FILE = DATA_DIR / "bookstack_map.yml"
MANIFEST_DIR = BASE_DIR / ".claude" / "skills" / "activity-sync" / "manifests"  # gitignored
CACHE_DIR = Path(os.environ.get("KF_BOOKSTACK_CACHE", Path.home() / ".cache" / "kf-cpto" / "bookstack"))
CHROME = os.environ.get("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
USER_AGENT = "curl/8.4.0"  # Cloudflare in front of the wiki rejects Python's default UA

_MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.S)


# --------------------------------------------------------------------------- #
# BookStack API client                                                         #
# --------------------------------------------------------------------------- #

def load_env() -> dict:
    """BOOKSTACK_* from the process env, falling back to BASE_DIR/.env (never printed)."""
    keys = ("BOOKSTACK_URL", "BOOKSTACK_TOKEN_ID", "BOOKSTACK_TOKEN_SECRET")
    env = {k: os.environ[k] for k in keys if os.environ.get(k)}
    envfile = BASE_DIR / ".env"
    if len(env) < 3 and envfile.exists():
        for line in envfile.read_text().splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() in keys and k.strip() not in env:
                env[k.strip()] = v.strip().strip("\"'")
    missing = [k for k in keys if k not in env]
    if missing:
        raise SystemExit(f"[ERROR] missing {', '.join(missing)} (set in .env or environment)")
    return env


class BookStack:
    def __init__(self, env: dict):
        self.base = env["BOOKSTACK_URL"].rstrip("/")
        self.auth = f"Token {env['BOOKSTACK_TOKEN_ID']}:{env['BOOKSTACK_TOKEN_SECRET']}"

    def call(self, method: str, path: str, body: dict | None = None, raw: tuple | None = None):
        headers = {"Authorization": self.auth, "User-Agent": USER_AGENT, "Accept": "application/json"}
        data = None
        if body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        elif raw is not None:
            data, headers["Content-Type"] = raw
        req = urllib.request.Request(f"{self.base}/api/{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read()
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {exc.read()[:200]!r}") from None

    def list(self, endpoint: str, **filters) -> list[dict]:
        q = "&".join(f"filter[{k}]={urllib.parse.quote(str(v))}" for k, v in filters.items())
        return self.call("GET", f"{endpoint}?count=500" + (f"&{q}" if q else "")).get("data", [])

    def upload_image(self, page_id: int, name: str, png: bytes) -> str:
        bd = uuid.uuid4().hex
        parts = []
        for k, v in (("type", "gallery"), ("uploaded_to", str(page_id)), ("name", name)):
            parts.append(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{bd}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
                     f"Content-Type: image/png\r\n\r\n".encode() + png + b"\r\n")
        parts.append(f"--{bd}--\r\n".encode())
        res = self.call("POST", "image-gallery", raw=(b"".join(parts), f"multipart/form-data; boundary={bd}"))
        return res["id"], res["url"]


# --------------------------------------------------------------------------- #
# Content builders (pure, no network)                                          #
# --------------------------------------------------------------------------- #

def sha(text: str) -> str:
    """Short content hash; trailing whitespace is ignored (BookStack trims it on save)."""
    return hashlib.sha1(text.strip().encode()).hexdigest()[:12]


def _drop_column(table_lines: list[str], header_name: str) -> list[str]:
    cells = [c.strip() for c in table_lines[0].strip().strip("|").split("|")]
    if header_name not in cells:
        return table_lines
    idx = cells.index(header_name)
    out = []
    for line in table_lines:
        parts = line.strip().strip("|").split("|")
        out.append("| " + " | ".join(c.strip() for i, c in enumerate(parts) if i != idx) + " |")
    return out


def _kanban_table(div_html: str) -> str:
    cols = []
    for m in re.finditer(r'kanban-col__head">(.*?)<span[^>]*>(\d+)</span>(.*?)(?=<div class="kanban-col |\Z)', div_html, re.S):
        cards = [html.unescape(c) for c in re.findall(r'kanban-card[^"]*">(.*?)</div>', m.group(3), re.S)]
        cols.append((f"{m.group(1).strip()} ({m.group(2)})", cards))
    if not cols:
        return ""
    depth = max(len(c[1]) for c in cols)
    lines = ["| " + " | ".join(c[0] for c in cols) + " |", "|" + " --- |" * len(cols)]
    for i in range(depth):
        lines.append("| " + " | ".join(c[1][i] if i < len(c[1]) else "" for c in cols) + " |")
    return "\n".join(lines)


def convert_project_page(text: str) -> str:
    """Jekyll project page -> plain Markdown for BookStack (mermaid blocks left in place)."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"\(\{\{\s*'([^']+)'\s*\|\s*relative_url\s*\}\}([^)]*)\)",
                  lambda m: f"({PAGES_BASE}{m.group(1)}{m.group(2)})", text)
    text = re.sub(r'<div class="kanban-board">.*?\n</div>\n', lambda m: _kanban_table(m.group(0)) + "\n", text, flags=re.S)
    text = re.sub(r"</?sup>|&nbsp;", " ", text)
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):  # drop the Assignee column: output stays team-level
        if lines[i].startswith("|") and i + 1 < len(lines) and re.match(r"\|[\s:|-]+\|?$", lines[i + 1]):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            block = _drop_column(lines[i:j], "Assignee")
            out.extend(html.unescape(b) for b in block)
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out).strip() + "\n"


def activity_page(repo: str, act: dict, activity_meta: dict) -> str:
    window = f"{activity_meta.get('since')} to {activity_meta.get('until')}"
    lines = [
        f"# {repo} — activity", "",
        f"Derived from git history across **all remote branches** ({window}). Conservative floor: "
        "churn-based estimate, capped at one person-day per contributor per day, docs/planning excluded. "
        "Team-level; not tracked time.", "",
        "| Metric | Value |", "| :--- | :--- |",
        f"| Effort (floor) | {act['person_days']} person-days |",
        f"| Commits | {act['commits']} |",
        f"| Last commit | {act.get('last_commit', '—')} |", "",
        "## Effort by month", "", "| Month | Person-days |", "| :--- | ---: |",
    ]
    lines += [f"| {m} | {d} |" for m, d in act.get("monthly", {}).items()]
    branches = act.get("branches", [])
    lines += ["", "## Work in progress (branches ahead of default)", ""]
    if branches:
        lines += ["| Branch | Commits ahead | Last push |", "| :--- | ---: | :--- |"]
        lines += [f"| {b['name']} | {b['ahead']} | {b['last_push']} |" for b in branches]
    else:
        lines.append("No in-flight branches.")
    return "\n".join(lines) + "\n"


def overview_page(shelf: str, repos: list[str], loe_rows: list[dict], act_by_repo: dict, meta: dict) -> str:
    lines = [
        f"# {shelf} — delivery overview", "",
        f"Auto-generated from the kf-cpto dashboard data ({meta.get('since')} to {meta.get('until')} for activity). "
        f"Full dashboard: {PAGES_BASE}/", "",
        "| Repo | Planned (d) | Done (d) | Activity floor (pd) | Commits | In-flight branches | Last commit |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | :--- |",
    ]
    tot = [0.0, 0.0, 0.0]
    for repo in repos:
        planned = [r for r in loe_rows if r["project"] == repo and r.get("sprint") != "Activity"]
        total = sum(r["effort_days"] for r in planned)
        done = sum(r["effort_days"] for r in planned if r["status"] == "Done")
        a = act_by_repo.get(repo, {})
        tot[0] += total; tot[1] += done; tot[2] += a.get("person_days", 0)
        lines.append(f"| {repo} | {total:.1f} | {done:.1f} | {a.get('person_days', '—')} | {a.get('commits', '—')} | "
                     f"{len(a.get('branches', []))} | {a.get('last_commit', '—')} |")
    lines.append(f"| **Total** | **{tot[0]:.1f}** | **{tot[1]:.1f}** | **{tot[2]:.1f}** | | | |")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Mermaid -> PNG                                                               #
# --------------------------------------------------------------------------- #

def render_png(block: str) -> bytes | None:
    """Render one mermaid block to PNG via mermaid-cli; cached by content hash."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / f"{sha(block)}.png"
    if cached.exists():
        return cached.read_bytes()
    if not Path(CHROME).exists():
        print(f"[WARN] Chrome not found at {CHROME}; diagram left as source")
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src, cfg = Path(tmp, "d.mmd"), Path(tmp, "pp.json")
        src.write_text(block)
        cfg.write_text(json.dumps({"executablePath": CHROME, "args": ["--no-sandbox"]}))
        res = subprocess.run(
            ["npx", "-y", "@mermaid-js/mermaid-cli@11", "-p", str(cfg), "-i", str(src), "-o", str(cached),
             "-s", "2", "-b", "white", "-t", "forest"],
            capture_output=True, text=True, timeout=240, env={**os.environ, "PUPPETEER_SKIP_DOWNLOAD": "1"})
    if res.returncode != 0 or not cached.exists():
        print(f"[WARN] mermaid render failed: {res.stderr.strip()[-160:]}")
        return None
    return cached.read_bytes()


# --------------------------------------------------------------------------- #
# Sync                                                                         #
# --------------------------------------------------------------------------- #

class Sync:
    def __init__(self, api: BookStack, apply: bool):
        self.api, self.apply = api, apply
        self.tally = {"create": 0, "update": 0, "skip": 0, "conflict": 0}
        self.manifest = {
            "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "shelves_before": {},
            "created": {"shelves": [], "books": [], "chapters": [], "pages": [], "images": []},
            "updated": [],
        }

    def save_manifest(self) -> None:
        m = self.manifest
        if not self.apply or not (any(m["created"].values()) or m["updated"]):
            return
        MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        path = MANIFEST_DIR / f"bookstack-{m['run_id']}.json"
        path.write_text(json.dumps(m, indent=2))
        print(f"[INFO] rollback manifest: {path.name}  (undo: --rollback {m['run_id']})")

    def find(self, endpoint: str, target: str, **filters) -> dict | None:
        for item in self.api.list(endpoint, **filters):
            if item["name"] == target:
                return item
        return None

    def ensure_book(self, shelf: dict) -> dict | None:
        """The managed book on THIS shelf (never a same-named book on another shelf)."""
        if shelf["id"] is None:  # dry-run: shelf not created yet
            print(f"[PLAN] create book '{BOOK_NAME}' on new shelf '{shelf['name']}'")
            return None
        shelf_books = self.api.call("GET", f"shelves/{shelf['id']}").get("books", [])
        on_shelf = {b["id"] for b in shelf_books}
        for b in shelf_books:
            if b["name"] == BOOK_NAME:
                return b
        print(f"[PLAN] create book '{BOOK_NAME}' on shelf '{shelf['name']}'")
        if not self.apply:
            return None
        book = self.api.call("POST", "books", {"name": BOOK_NAME,
                             "description": "Auto-generated by kf-cpto from repo activity and kanban data. Edit the source, not this page."})
        self.manifest["created"]["books"].append({"id": book["id"], "name": book["name"]})
        self.manifest["shelves_before"][str(shelf["id"])] = sorted(on_shelf)
        self.api.call("PUT", f"shelves/{shelf['id']}", {"books": sorted(on_shelf | {book["id"]})})
        return book

    def ensure_chapter(self, book: dict | None, name: str) -> dict | None:
        pending = {"id": None, "name": name}  # dry-run stand-in: its pages do not exist yet
        if book is None:
            print(f"[PLAN] create chapter '{name}'")
            return pending
        ch = self.find("chapters", name, book_id=book["id"])
        if ch:
            return ch
        print(f"[PLAN] create chapter '{name}'")
        if not self.apply:
            return pending
        ch = self.api.call("POST", "chapters", {"book_id": book["id"], "name": name})
        self.manifest["created"]["chapters"].append({"id": ch["id"], "name": ch["name"]})
        return ch

    def sync_page(self, book: dict | None, chapter: dict | None, name: str, markdown: str) -> None:
        blocks = _MERMAID_RE.findall(markdown)
        src_hash = sha(markdown)
        if chapter and chapter["id"] is None:
            existing = None
        elif chapter:
            existing = self.find("pages", name, chapter_id=chapter["id"])
        else:
            existing = self.find("pages", name, book_id=book["id"]) if book else None
        if existing:
            page = self.api.call("GET", f"pages/{existing['id']}")
            tags = {t["name"]: t["value"] for t in page.get("tags", [])}
            if tags.get("kfcpto-md") and sha(page.get("markdown", "")) != tags["kfcpto-md"]:
                print(f"[CONFLICT] '{name}' was edited in BookStack since the last sync — skipped")
                self.tally["conflict"] += 1
                return
            if tags.get("kfcpto-src") == src_hash:
                print(f"[SKIP] '{name}' unchanged")
                self.tally["skip"] += 1
                return
        action = "update" if existing else "create"
        print(f"[PLAN] {action} page '{name}' ({len(blocks)} diagram(s))")
        self.tally[action] += 1
        if not self.apply:
            return
        if existing:
            page_id = existing["id"]  # old images are kept so a rollback can restore the previous markdown
            self.manifest["updated"].append({"id": page_id, "name": name, "prev": {
                "markdown": page.get("markdown", ""), "tags": page.get("tags", [])}})
        else:
            payload = {"book_id": book["id"], "name": name, "markdown": "Rendering…"}
            if chapter:
                payload = {"chapter_id": chapter["id"], "name": name, "markdown": "Rendering…"}
            page_id = self.api.call("POST", "pages", payload)["id"]
            self.manifest["created"]["pages"].append({"id": page_id, "name": name})
        final = markdown
        for n, block in enumerate(blocks, 1):
            png = render_png(block)
            if png:
                img_id, url = self.api.upload_image(page_id, f"{name}-{n}.png", png)
                self.manifest["created"]["images"].append(img_id)
                final = final.replace(f"```mermaid\n{block}```", f"![{name} diagram {n}]({url})", 1)
        self.api.call("PUT", f"pages/{page_id}", {
            "name": name, "markdown": final,
            "tags": [{"name": "managed", "value": "kf-cpto"},
                     {"name": "kfcpto-src", "value": src_hash},
                     {"name": "kfcpto-md", "value": sha(final)}]})


# --------------------------------------------------------------------------- #
# Rollback                                                                     #
# --------------------------------------------------------------------------- #

def list_manifests() -> list[Path]:
    return sorted(MANIFEST_DIR.glob("bookstack-*.json")) if MANIFEST_DIR.exists() else []


def _edited_since_sync(api: BookStack, page_id: int) -> bool:
    page = api.call("GET", f"pages/{page_id}")
    tags = {t["name"]: t["value"] for t in page.get("tags", [])}
    return bool(tags.get("kfcpto-md")) and sha(page.get("markdown", "")) != tags["kfcpto-md"]


def rollback(api: BookStack, run_id: str, apply: bool, force: bool) -> int:
    """Undo one sync run from its manifest: restore updated pages, delete what it created.

    Deletes go to BookStack's recycle bin (admin-recoverable). A page edited by a human
    since the sync is left alone unless --force.
    """
    files = list_manifests()
    if run_id == "latest":
        open_runs = [f for f in files if not json.loads(f.read_text()).get("rolled_back_at")]
        path = open_runs[-1] if open_runs else None
    else:
        path = MANIFEST_DIR / f"bookstack-{run_id}.json"
    if not path or not path.exists():
        print(f"[ERROR] no rollback manifest for '{run_id}' (see --rollback-list)")
        return 1
    m = json.loads(path.read_text())
    if m.get("rolled_back_at"):
        print(f"[INFO] {path.name} was already rolled back at {m['rolled_back_at']}")
        return 0
    created, tag = m["created"], ("APPLY" if apply else "dry-run")
    print(f"BookStack Rollback — {path.name} ({tag})")
    done = {"restored": 0, "deleted": 0, "skipped": 0}

    def act(label: str, fn) -> None:
        print(f"[PLAN] {label}")
        if apply:
            try:
                fn()
                done["deleted" if label.startswith("delete") else "restored"] += 1
            except RuntimeError as exc:
                print(f"[WARN] {exc}")
                done["skipped"] += 1

    for u in reversed(m["updated"]):
        if _edited_since_sync(api, u["id"]) and not force:
            print(f"[CONFLICT] page '{u['name']}' edited since sync — not restored (use --force)")
            done["skipped"] += 1
            continue
        act(f"restore page '{u['name']}' to its previous content", lambda u=u: api.call(
            "PUT", f"pages/{u['id']}", {"markdown": u["prev"]["markdown"], "tags": u["prev"]["tags"]}))
    for pg in reversed(created["pages"]):
        if _edited_since_sync(api, pg["id"]) and not force:
            print(f"[CONFLICT] page '{pg['name']}' edited since sync — not deleted (use --force)")
            done["skipped"] += 1
            continue
        act(f"delete page '{pg['name']}'", lambda pg=pg: api.call("DELETE", f"pages/{pg['id']}"))
    for img_id in created["images"]:
        act(f"delete image #{img_id}", lambda i=img_id: api.call("DELETE", f"image-gallery/{i}"))
    for ch in created["chapters"]:
        left = api.list("pages", chapter_id=ch["id"]) if apply else []
        if left:
            print(f"[SKIP] chapter '{ch['name']}' still has {len(left)} page(s)")
            done["skipped"] += 1
            continue
        act(f"delete chapter '{ch['name']}'", lambda ch=ch: api.call("DELETE", f"chapters/{ch['id']}"))
    for bk in created["books"]:
        left = (api.list("pages", book_id=bk["id"]) + api.list("chapters", book_id=bk["id"])) if apply else []
        if left:
            print(f"[SKIP] book '{bk['name']}' still has content — not deleted")
            done["skipped"] += 1
            continue
        act(f"delete book '{bk['name']}'", lambda bk=bk: api.call("DELETE", f"books/{bk['id']}"))
    for shelf_id, before in m["shelves_before"].items():  # detach only what this run attached
        current = api.call("GET", f"shelves/{shelf_id}").get("books", [])
        keep = [b["id"] for b in current if b["id"] in before or b["name"] != BOOK_NAME]
        if len(keep) != len(current):
            act(f"restore shelf #{shelf_id} book list", lambda s=shelf_id, k=keep: api.call(
                "PUT", f"shelves/{s}", {"books": k}))
    for sh in created.get("shelves", []):
        left = api.call("GET", f"shelves/{sh['id']}").get("books", []) if apply else []
        if left:
            print(f"[SKIP] shelf '{sh['name']}' still has {len(left)} book(s)")
            done["skipped"] += 1
            continue
        act(f"delete shelf '{sh['name']}'", lambda sh=sh: api.call("DELETE", f"shelves/{sh['id']}"))
    if apply and not done["skipped"]:
        m["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(m, indent=2))
    print(f"[TALLY] {done['restored']} restored / {done['deleted']} deleted / {done['skipped']} skipped"
          + ("" if apply else "  (dry-run; add --apply to execute)"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync dashboard data into BookStack (dry-run by default).")
    ap.add_argument("--shelf", help='exact BookStack shelf name, e.g. "2601. KF-Platform"')
    ap.add_argument("--repo", action="append", help="limit to these repos (default: all mapped to the shelf)")
    ap.add_argument("--apply", action="store_true", help="perform writes (default: dry-run)")
    ap.add_argument("--rollback", metavar="RUN_ID", help='undo a run from its manifest ("latest" = newest open run)')
    ap.add_argument("--rollback-list", action="store_true", help="list rollback manifests")
    ap.add_argument("--create-shelves", action="store_true", help="create the shelf if it does not exist yet")
    ap.add_argument("--force", action="store_true", help="rollback even pages edited in BookStack since the sync")
    args = ap.parse_args()

    if args.rollback_list:
        for f in list_manifests():
            m = json.loads(f.read_text())
            c = m["created"]
            print(f"{m['run_id']}  created: {len(c['books'])} book / {len(c['chapters'])} ch / {len(c['pages'])} pages / "
                  f"{len(c['images'])} img{', ' + str(len(c.get('shelves', []))) + ' shelf' if c.get('shelves') else ''}, updated: {len(m['updated'])}  {'ROLLED BACK' if m.get('rolled_back_at') else 'open'}")
        return 0
    if args.rollback:
        return rollback(BookStack(load_env()), args.rollback, args.apply, args.force)
    if not args.shelf:
        ap.error("--shelf is required for a sync")

    print(f"BookStack Sync — Starting... ({'APPLY' if args.apply else 'dry-run'})")
    mapping = yaml.safe_load(MAP_FILE.read_text()) or {}
    cfg = mapping.get("shelves", {}).get(args.shelf)
    if not cfg:
        print(f"[ERROR] shelf '{args.shelf}' not in {MAP_FILE.name}")
        return 1
    repos = [r for r in cfg["repos"] if not args.repo or r in args.repo]
    loe_rows = (yaml.safe_load(LOE_DATA_FILE.read_text()) or {}).get("rows", [])
    activity = yaml.safe_load(GIT_ACTIVITY_FILE.read_text()) or {}
    act_by_repo = {r["repo"]: r for r in activity.get("repos", [])}

    api = BookStack(load_env())
    shelf = Sync(api, args.apply).find("shelves", args.shelf, name=args.shelf)
    sync = Sync(api, args.apply)
    if not shelf:
        if not args.create_shelves:
            print(f"[ERROR] shelf '{args.shelf}' does not exist in BookStack (use --create-shelves)")
            return 1
        print(f"[PLAN] create shelf '{args.shelf}'")
        shelf = {"id": None, "name": args.shelf}
        if args.apply:
            shelf = api.call("POST", "shelves", {"name": args.shelf, "description": cfg.get("description", "")})
            sync.manifest["created"]["shelves"].append({"id": shelf["id"], "name": shelf["name"]})
    try:
        _run(sync, args, cfg, repos, loe_rows, activity, act_by_repo, shelf)
    finally:
        sync.save_manifest()

    print(f"[TALLY] {sync.tally['create']} create / {sync.tally['update']} update / "
          f"{sync.tally['skip']} skip / {sync.tally['conflict']} conflict")
    print("BookStack Sync — Done!")
    return 0


def _run(sync, args, cfg, repos, loe_rows, activity, act_by_repo, shelf) -> None:
    book = sync.ensure_book(shelf)

    sync.sync_page(book, None, "Overview", overview_page(args.shelf, cfg["repos"], loe_rows, act_by_repo, activity))
    for page in cfg.get("org_pages", []):  # org-level charts rendered from existing dashboard pages
        src = (DOCS_DIR / page["source"]).read_text()
        blocks = _MERMAID_RE.findall(src)
        if len(blocks) > page.get("block", 0):
            body = f"# {page['name']}\n\nSource: {PAGES_BASE}/{page['source'].removesuffix('.md')}/\n\n```mermaid\n{blocks[page.get('block', 0)]}```\n"
            sync.sync_page(book, None, page["name"], body)

    for repo in repos:
        chapter = sync.ensure_chapter(book, repo)
        proj = DOCS_DIR / "_projects" / f"{repo}.md"
        if proj.exists():
            sync.sync_page(book, chapter, "Status & Kanban", convert_project_page(proj.read_text()))
        if repo in act_by_repo:
            sync.sync_page(book, chapter, "Activity", activity_page(repo, act_by_repo[repo], activity))


if __name__ == "__main__":
    sys.exit(main())
