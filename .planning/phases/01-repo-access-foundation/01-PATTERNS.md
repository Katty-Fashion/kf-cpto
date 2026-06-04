# Phase 1: Repo Access Foundation - Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 4 new/modified files
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.claude/skills/activity-sync/SKILL.md` | config | — | `.planning/research/STACK.md` frontmatter conventions | partial-match (no prior SKILL.md exists) |
| `.claude/skills/activity-sync/repo_enum.py` | utility | file-I/O + batch | `scripts/discover.py` (enumeration + git) + `scripts/utils.py` (parser callsites) | role-match |
| `.claude/skills/activity-sync/bootstrap.py` | utility | file-I/O + batch | `scripts/discover.py` (clone pattern) | role-match |
| `.gitignore` | config | — | Existing `.gitignore` (lines 1-69, current repo) | exact |

---

## Pattern Assignments

### `.claude/skills/activity-sync/repo_enum.py` (utility, file-I/O + batch)

**Primary analog:** `scripts/discover.py`
**Secondary analog:** `scripts/utils.py` (parser imports + constants)

---

**Imports pattern** — `scripts/discover.py` lines 1-18 + `scripts/aggregator.py` lines 1-35:

```python
#!/usr/bin/env python3
"""
<module docstring — one sentence purpose>

Usage:
    python .claude/skills/activity-sync/repo_enum.py
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

# sys.path injection — 4 levels up from repo_enum.py to repo root
# Chain: repo_enum.py -> activity-sync/ -> skills/ -> .claude/ -> repo_root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils import (
    ORG,
    TASK_STATUSES,
    parse_kanban_frontmatter,
    parse_kanban_tasks,
    normalize_frontmatter,
)
```

**CRITICAL:** `Path(__file__).parent.parent.parent.parent` — exactly 4 `.parent` calls.
3 levels resolves to `.claude/` (wrong); 4 levels resolves to repo root (correct).
[VERIFIED: live shell arithmetic test 2026-06-04]

---

**Module-level constants pattern** — `scripts/utils.py` lines 16-37 + `scripts/aggregator.py` line 37:

```python
# SCREAMING_SNAKE_CASE for all module-level constants (CLAUDE.md convention)
KF_ORG = "Katty-Fashion"          # SSH clone org (capital F — matches actual GitHub org name)
REPOS_LOCAL_DIR = _REPO_ROOT / "repos-local"
SKILL_DIR = Path(__file__).parent
```

Note: `ORG = "katty-fashion"` in `utils.py` (line 16) is the API/directory-name form.
`KF_ORG = "Katty-Fashion"` in the skill is the SSH clone URL org segment — different case.
Both are needed: API uses lowercase, SSH URL uses GitHub's display-name form.

---

**Enumeration pattern** — analog: `scripts/discover.py` lines 21-72 (dir scan adapted from API scan):

```python
def _run_git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    """Internal git subprocess wrapper. Private — prefix underscore per CLAUDE.md."""
    return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)


def _is_git_repo(path: str) -> bool:
    result = _run_git(["-C", path, "rev-parse", "--git-dir"])
    return result.returncode == 0


def enumerate_repos(repos_local: Path) -> list[str]:
    """Return sorted list of repo names present in repos-local/."""
    if not repos_local.exists():
        return []
    return sorted(
        d.name for d in repos_local.iterdir()
        if d.is_dir() and _is_git_repo(str(d))
    )
```

Pattern source: `discover.py` uses `for repo in candidates:` iteration over a list;
here we scan a directory instead of an API response. The skip-silently behavior
matches `discover.py` line 69 (`# 404 = no kanban.md, skip silently`).

---

**git fetch with before/after SHA comparison** — no direct analog in codebase; derived from `discover.py` subprocess pattern (lines 22-71) adapted per RESEARCH.md Pattern 3:

```python
def _get_remote_url(repo_path: str) -> str:
    result = _run_git(["-C", repo_path, "remote", "get-url", "origin"])
    return result.stdout.strip() if result.returncode == 0 else ""


def _get_default_branch(repo_path: str) -> str:
    """Detect current branch from local checkout HEAD. Mix of main/master in org."""
    result = _run_git(["-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode == 0:
        branch = result.stdout.strip()
        if branch and branch != "HEAD":  # HEAD = detached state
            return branch
    return "main"  # safe fallback


def _fetch_repo(repo_path: str, branch: str) -> str:
    """Fetch origin, return 'up-to-date', 'new-commits', or 'fetch-failed'. Non-fatal."""
    tracking_ref = f"origin/{branch}"
    before = _run_git(["-C", repo_path, "rev-parse", tracking_ref])
    before_sha = before.stdout.strip() if before.returncode == 0 else None

    fetch = _run_git(["-C", repo_path, "fetch", "origin"])
    if fetch.returncode != 0:
        print(f"Warning: fetch failed for {repo_path}: {fetch.stderr.strip()}")
        return "fetch-failed"

    after = _run_git(["-C", repo_path, "rev-parse", tracking_ref])
    after_sha = after.stdout.strip() if after.returncode == 0 else None
    return "up-to-date" if before_sha == after_sha else "new-commits"
```

Note: `print(f"Warning: ...")` matches the exact prefix in `utils.py` lines 186-188
and `discover.py` line 37. `[WARN]` pills are for log lines mixed into structured output;
`Warning:` prefix is for standalone warning messages per CLAUDE.md convention.

---

**kanban parse pattern** — analog: `scripts/utils.py` `load_project_kanban()` lines 242-268
(the pattern to follow but with a different path — do NOT call `load_project_kanban()` directly):

```python
# DO NOT call utils.load_project_kanban(name) — it hardcodes REPOS_DIR ("repos/")
# Instead replicate its internal logic with your own path:

def _read_kanban(repo_name: str, repos_local: Path) -> dict[str, Any]:
    """Read and parse kanban.md from repos-local/ checkout."""
    kanban_path = repos_local / repo_name / "kanban.md"
    if not kanban_path.exists():
        return {"exists": False, "meta": normalize_frontmatter({}), "tasks": [], "raw": ""}

    content = kanban_path.read_text(encoding="utf-8")
    meta = normalize_frontmatter(parse_kanban_frontmatter(content))
    tasks = parse_kanban_tasks(content, project=repo_name)
    valid_count = sum(1 for t in tasks if t["status"] in TASK_STATUSES)
    return {
        "exists": True,
        "meta": meta,
        "tasks": tasks,
        "valid_task_count": valid_count,
        "raw": content,
    }
```

Exact model: `utils.load_project_kanban()` lines 251-268 — same shape, same keys,
same `normalize_frontmatter(parse_kanban_frontmatter(content))` chain, but
`kanban_path = repos_local / repo_name / "kanban.md"` instead of `REPOS_DIR / project / "kanban.md"`.

**Parity check logic** — analog: `scripts/aggregator.py` lines 102-109:

```python
# aggregator.py lines 102-109 (exact pattern for valid task count):
for project, project_data in data.items():
    counts = {s: 0 for s in TASK_STATUSES}
    for task in project_data["tasks"]:
        if task["status"] in counts:
            counts[task["status"]] += 1
    total = sum(counts.values())
```

The skill's parity assertion must use `sum(1 for t in tasks if t["status"] in TASK_STATUSES)`
— matching `total = sum(counts.values())` which only sums recognized statuses.
Do NOT use `len(tasks)` — R3-AAS returns 181 total rows but 0 valid-status rows.

---

**Clean-state assertion** — no analog in codebase; new pattern for this skill:

```python
def _assert_kf_cpto_clean(kf_cpto_root: Path) -> None:
    """Assert the kf-cpto working tree is unchanged after skill run."""
    result = _run_git(["-C", str(kf_cpto_root), "status", "--porcelain"])
    if result.stdout.strip():
        raise RuntimeError(
            f"[ERROR] kf-cpto working tree is dirty after skill run:\n{result.stdout}"
        )
    print("[INFO] kf-cpto working tree: CLEAN")
```

---

**Error handling pattern** — analog: `scripts/utils.py` lines 186-188, `scripts/discover.py` lines 37-38 + 69:

```python
# Non-fatal skip with Warning: prefix (matches utils.py line 186-188):
print(f"Warning: repos-local/{name} is not a valid git repo — skipping")

# Structured pill prefix for status lines mixed with tabular output:
print(f"[INFO] {name}: {fetch_status} (branch: {branch})")
print(f"[WARN] {name}: kanban.md missing — seed before enumeration")
print(f"[ERROR] kf-cpto working tree is dirty — investigate before continuing")
```

Convention: bare `Warning:` for inline warnings (matches `utils.py` exactly);
`[INFO]` / `[WARN]` / `[ERROR]` pills for structured run-log lines per user preference.

---

**main() pattern** — analog: `scripts/aggregator.py` lines 536-598, `scripts/discover.py` lines 75-97:

```python
def main() -> int:
    print("Activity Sync — Repo Enum — Starting...")
    # ... body ...
    print("Activity Sync — Repo Enum — Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- `main()` returns `int`, `sys.exit(main())` at module level — exact match with `aggregator.py` pattern (line 536 + caller at CI level).
- Open/close banner: `"KF Aggregator — Starting..."` / `"KF Aggregator — Done!"` (aggregator.py lines 538, end of main) — copy this format with skill-specific prefix.

---

### `.claude/skills/activity-sync/bootstrap.py` (utility, file-I/O + batch)

**Primary analog:** `scripts/discover.py` (clone + file write pattern)

---

**Imports pattern** — same as `repo_enum.py` for sys.path injection; remove parser imports,
add `shutil`:

```python
#!/usr/bin/env python3
"""
Bootstrap helper: clone missing tracked repos into repos-local/ and seed markers.

Run once on a fresh machine before using repo_enum.py.

Usage:
    python .claude/skills/activity-sync/bootstrap.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils import ORG  # noqa: E402 — path injection must precede import
```

---

**TRACKED_REPOS constant** — the curated allowlist; `SCREAMING_SNAKE_CASE` per CLAUDE.md:

```python
# Curated allowlist — membership in repos-local/ IS the tracked set.
# "branch" is the remote default branch for this repo.
TRACKED_REPOS: list[dict[str, str]] = [
    {"name": "kf-be-platform",    "branch": "main"},
    {"name": "kf-fe-platform",    "branch": "main"},
    {"name": "kf-platform",       "branch": "master"},
    {"name": "R3-AAS",            "branch": "main"},
    {"name": "ai-rise-options",   "branch": "master"},
    {"name": "tech_brainstorming","branch": "main"},
]
```

Note: This constant lives in `bootstrap.py` only — it is the bootstrap seed list.
`repo_enum.py` does NOT read this constant; it scans `repos-local/` at runtime.
This preserves the REPO-01 "no static project list in enumeration code" principle.

---

**Clone pattern** — analog: `scripts/discover.py` lines 83-85 (HTTPS clone in CI) adapted for SSH full clone in skill:

```python
# CI pattern (discover.py + aggregate.yml) — HTTPS depth-1, not suitable for skill:
# git clone --depth=1 https://<token>@github.com/org/repo.git repos/<name>

# Skill pattern — SSH full clone (Phase 2 needs git history):
def _clone_repo(name: str, branch: str, repos_local: Path) -> bool:
    """Clone a tracked repo into repos-local/ via SSH. Returns True on success."""
    target = repos_local / name
    if target.exists():
        print(f"[INFO] {name}: already present at {target}")
        return True
    result = subprocess.run(
        ["git", "clone", "-b", branch,
         f"git@github.com:Katty-Fashion/{name}.git", str(target)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Warning: clone failed for {name}: {result.stderr.strip()}")
        return False
    print(f"[INFO] Cloned {name} -> {target}")
    return True
```

---

**Marker seeding pattern** — no direct analog; new pattern. Model after `utils.py`
`save_sync_status()` lines 323-330 for the `mkdir(parents=True, exist_ok=True)` idiom:

```python
def _seed_markers(repo_path: Path, kf_cpto_root: Path) -> None:
    """Copy kanban.md and notify workflow from templates/ into repo if absent."""
    templates_dir = kf_cpto_root / "templates"

    kanban_dest = repo_path / "kanban.md"
    if not kanban_dest.exists():
        shutil.copy(templates_dir / "kanban.md", kanban_dest)
        print(f"[INFO] Seeded kanban.md in {repo_path.name}")

    notify_dest = repo_path / ".github" / "workflows" / "notify-kf-cpto.yml"
    if not notify_dest.exists():
        notify_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            templates_dir / ".github" / "workflows" / "notify-kf-cpto.yml",
            notify_dest
        )
        print(f"[INFO] Seeded notify-kf-cpto.yml in {repo_path.name}")
```

Template source files confirmed present at:
- `/Users/machina/Dev/kf-cpto/templates/kanban.md`
- `/Users/machina/Dev/kf-cpto/templates/.github/workflows/notify-kf-cpto.yml`

---

**main() pattern** — same as repo_enum.py; `return int`, `sys.exit(main())`:

```python
def main() -> int:
    print("Activity Sync — Bootstrap — Starting...")
    repos_local = _REPO_ROOT / "repos-local"
    repos_local.mkdir(exist_ok=True)

    for repo in TRACKED_REPOS:
        cloned = _clone_repo(repo["name"], repo["branch"], repos_local)
        if cloned:
            _seed_markers(repos_local / repo["name"], _REPO_ROOT)

    print("Activity Sync — Bootstrap — Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

### `.claude/skills/activity-sync/SKILL.md` (config)

**No existing analog** — no SKILL.md exists in this repo. Pattern from RESEARCH.md Code Examples:

```markdown
---
name: activity-sync
description: "Read-only enumeration and parsing of tracked sibling repos. Use to
  inspect kanban state across all tracked repos. Triggers on: activity sync, repo
  enum, list tracked repos."
allowed-tools: Bash Read
---

# Activity Sync — Repo Access

Enumerates tracked repos in `repos-local/`, fetches remote state, and parses each
`kanban.md` through the canonical `scripts/utils.py` parsers.

## Usage

Run enumeration:

!`python .claude/skills/activity-sync/repo_enum.py`

Bootstrap (first run on a fresh machine):

!`python .claude/skills/activity-sync/bootstrap.py`
```

[ASSUMED] — `name`, `description`, `allowed-tools` frontmatter field names are from
prior STACK.md research. Verify against current Claude Code skills spec before writing.

---

### `.gitignore` (config, modification)

**Analog:** Existing `.gitignore` (line 68-69 — the `.claude/` blanket exclusion)

**Current state** (`.gitignore` lines 68-69):
```
#Claude
.claude/
```

**Required change** — replace blanket exclusion with fine-grained entries so
`.claude/skills/` is committed but session files remain excluded:

```
# Claude session files (exclude; not skill code)
.claude/settings.local.json
.claude/cache/
.claude/memory/

# Runtime dirs (skill-local; never committed)
repos-local/
```

**Critical:** Git negation (`!.claude/skills/`) does NOT work when the parent
`.claude/` is already excluded. The blanket entry MUST be replaced, not supplemented.
[VERIFIED: live gitignore negation test 2026-06-04]

`repos-local/` must be added separately (mirrors the existing `repos/` entry at line 5).

---

## Shared Patterns

### subprocess git wrapper
**Source:** `scripts/discover.py` lines 22-24 (requests pattern) adapted to subprocess
**Apply to:** Both `repo_enum.py` and `bootstrap.py`

```python
def _run_git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
```

Private helper prefix `_` per CLAUDE.md convention (matches `_status_legend()`,
`_get_sheet_id()` etc. in existing scripts).

### Warning/log message format
**Source:** `scripts/utils.py` lines 186-188; `scripts/discover.py` lines 37, 48, 57, 68
**Apply to:** All skill modules

```python
# Non-fatal issues — bare "Warning:" prefix (matches utils.py exactly):
print(f"Warning: repos-local/{name} is not a valid git repo — skipping")

# Structured run-log lines — pill prefix:
print(f"[INFO] {name}: up-to-date (branch: main)")
print(f"[WARN] {name}: kanban.md absent — run bootstrap.py first")
```

### sys.path injection to import utils
**Source:** Derived from RESEARCH.md Pattern 1 (verified against live codebase)
**Apply to:** Every skill module that calls parser functions

```python
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
```

### main() entry point
**Source:** `scripts/aggregator.py` lines 536-598; `scripts/discover.py` lines 75-97
**Apply to:** Both `repo_enum.py` and `bootstrap.py`

```python
def main() -> int:
    print("<Skill Name> — <Script Name> — Starting...")
    # ... body ...
    print("<Skill Name> — <Script Name> — Done!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### kanban parse call sequence (never via load_project_kanban)
**Source:** `scripts/utils.py` `load_project_kanban()` lines 242-268 (internal call chain)
**Apply to:** `repo_enum.py` `_read_kanban()` function

```python
# Correct sequence — always in this order, with custom path:
content = kanban_path.read_text(encoding="utf-8")
meta = normalize_frontmatter(parse_kanban_frontmatter(content))
tasks = parse_kanban_tasks(content, project=repo_name)
valid_count = sum(1 for t in tasks if t["status"] in TASK_STATUSES)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.claude/skills/activity-sync/SKILL.md` | config | — | No SKILL.md exists in this codebase; pattern from RESEARCH.md assumptions only |
| `assert_kf_cpto_clean()` function | utility | — | No clean-state assertion pattern exists; new pattern for read-only guarantee |

---

## Anti-Pattern Index

The following are explicitly documented in RESEARCH.md and must NOT appear in the plan's implementation tasks:

| Anti-Pattern | Files Affected | Correct Alternative |
|--------------|----------------|---------------------|
| `utils.load_project_kanban(name)` | `repo_enum.py` | Call `parse_kanban_frontmatter()` + `parse_kanban_tasks()` directly with `repos-local/` path |
| `utils.load_projects()` | `repo_enum.py` | Scan `repos-local/` directory at runtime |
| `utils.REPOS_DIR` or `utils.BASE_DIR` | Both skill modules | Use `_REPO_ROOT = Path(__file__).parent.parent.parent.parent` |
| `!.claude/skills/` negation in `.gitignore` | `.gitignore` | Replace blanket `.claude/` exclusion with fine-grained sub-path entries |
| `--depth=1` for `repos-local/` clones | `bootstrap.py` | Full clone (no `--depth`); Phase 2 needs git history |
| `symbolic-ref refs/remotes/origin/HEAD` | `repo_enum.py` | Use `rev-parse --abbrev-ref HEAD` instead |
| `len(tasks)` for parity check | `repo_enum.py` | `sum(1 for t in tasks if t["status"] in TASK_STATUSES)` |

---

## Metadata

**Analog search scope:** `scripts/`, `.gitignore`, `templates/`
**Files scanned:** `scripts/utils.py` (358 lines, full read), `scripts/discover.py` (97 lines, full read), `scripts/aggregator.py` (targeted reads: lines 1-45, 95-111, 489-533, 530-599)
**Pattern extraction date:** 2026-06-04
