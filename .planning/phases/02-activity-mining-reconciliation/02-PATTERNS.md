# Phase 2: Activity Mining + Reconciliation - Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 1 new file (reconcile.py), 1 update (SKILL.md)
**Analogs found:** 3 / 2 (multiple analogs per file; all strong matches)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.claude/skills/activity-sync/reconcile.py` | service (skill module) | request-response + event-driven | `.claude/skills/activity-sync/repo_enum.py` | exact |
| `.claude/skills/activity-sync/SKILL.md` | config (skill index) | n/a | `.claude/skills/activity-sync/SKILL.md` (current) | exact (extend in-place) |

---

## Pattern Assignments

### `.claude/skills/activity-sync/reconcile.py` (service, request-response + event-driven)

**Primary analog:** `.claude/skills/activity-sync/repo_enum.py`
**Secondary analogs:** `scripts/discover.py` (GitHub REST API pattern), `scripts/utils.py` (status constants)

---

#### Imports and `__future__` block (repo_enum.py lines 30-50)

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

# sys.path injection — 4 .parent levels from skill file to repo root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils import (  # noqa: E402
    ORG,
    TASK_STATUSES,
    ...
)
```

**Note:** `from __future__ import annotations` MUST be the first import. This is the established pattern in every skill module and is required to avoid `TypeError` on Python 3.9 for `Optional[bool]`, `list[dict]`, `dict[str, int]` annotations (Pitfall 3 from RESEARCH.md). The 4-level `parent` chain is the correct path to repo root from `.claude/skills/activity-sync/`.

---

#### Module-level constants (repo_enum.py lines 53-69)

```python
# Module-level constants (SCREAMING_SNAKE_CASE per CLAUDE.md)
REPOS_LOCAL_DIR = _REPO_ROOT / "repos-local"
SKILL_DIR = Path(__file__).parent

GIT_TIMEOUT_SECONDS = 60
GIT_CLONE_TIMEOUT_SECONDS = 300

_ALLOWED_ORG_HOSTS = (
    f"git@github.com:{ORG}/",
    f"https://github.com/{ORG}/",
    ...
)
```

**For reconcile.py:** Replace with constants appropriate to Phase 2:
- `REPOS_LOCAL_DIR` — reuse same path
- `GIT_TIMEOUT_SECONDS` — reuse same value
- `STATUS_RANK: dict[str, int]` — derived from `TASK_STATUSES` index (NOT `STATUS_PRIORITY`)
- `_STOPWORDS` — frozenset for token normalization
- `_CLOSING_KEYWORDS_RE` — compiled regex (module-level, per project convention of `_MARKER_OPEN_RE` pattern in auto_blocks.py)

---

#### `_run_git` subprocess wrapper (repo_enum.py lines 96-103)

```python
def _run_git(args: list[str], cwd: str | None = None, timeout: int = GIT_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    """Internal git subprocess wrapper. Uses arg-list subprocess; never shell-interpolated."""
    try:
        return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"Warning: git {args[0] if args else ''} timed out after {timeout}s")
        return subprocess.CompletedProcess(["git"] + args, returncode=1, stdout="", stderr="git timed out")
```

**Copy this exactly into reconcile.py.** RESEARCH.md confirms `_run_git` is the established pattern; security section confirms arg-list (never shell interpolation) is the shell-injection mitigation. All git calls in reconcile.py (`merge-base --is-ancestor`, `for-each-ref`) must go through this wrapper.

---

#### KF_PAT auth pattern (discover.py lines 22-26, 76-79)

```python
# discover.py — auth header construction
def discover_kanban_repos(org: str = ORG, token: str = None) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
```

```python
# discover.py — token acquisition with graceful degradation
token = os.environ.get("KF_PAT") or os.environ.get("GITHUB_TOKEN")
if not token:
    print("Warning: No KF_PAT or GITHUB_TOKEN set. API rate limits will be very low.")
```

**For reconcile.py:** Copy this exact dual-env-var lookup (`KF_PAT` first, `GITHUB_TOKEN` fallback) and the graceful-degrade `Warning:` pattern. If no token, skip all GitHub API calls and return empty proposals with a `[WARN]` message (Pitfall 7, RESEARCH.md).

---

#### GitHub REST API pagination (discover.py lines 29-50)

```python
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
```

**For reconcile.py `_list_merged_prs`:** Use this pagination structure verbatim, substituting the PR endpoint URL and `merged_at` filter. Preserve the rate-limit logging — use `[WARN]` pill (not bare `Warning:`) when remaining < 100, consistent with CONTEXT.md pill convention.

---

#### Warning / Info print conventions (repo_enum.py lines 87-88, 101, 178-179)

```python
# Non-fatal skip
print(f"Warning: {name} has no origin remote — skipping")

# git subprocess timeout
print(f"Warning: git {args[0] if args else ''} timed out after {timeout}s")

# Structured info pill
print(f"[INFO] kf-cpto working tree: CLEAN")
print(f"[INFO] {name}: {fetch_status} (branch: {branch})")
```

**For reconcile.py:** Use the same mixed pattern:
- `Warning: ...` (bare prefix) for non-fatal issues in helper functions (matches existing scripts convention)
- `[INFO]` / `[WARN]` / `[ERROR]` pills for structured orchestrator-level messages (matches CONTEXT.md output format)
- Never emit emojis (user preference — CLAUDE.md memory)

---

#### `run()` as importable entry point (repo_enum.py lines 254-328)

```python
def run() -> list[dict[str, Any]]:
    """Enumerate repos-local/... Returns structured record list without calling sys.exit.
    main() delegates to this function."""
    print("Activity Sync — Repo Enum — Starting...")
    ...
    print("Activity Sync — Repo Enum — Done!")
    return records
```

**For reconcile.py `run()`:** Follow this exact shape:
- Banner open/close: `"Activity Sync — Reconcile — Starting..."` / `"Activity Sync — Reconcile — Done!"`
- Return type: `list[Proposal]` (structured objects for Phase 3, not `list[dict]`)
- No `sys.exit` in `run()` — that is `main()`'s job
- Consumes `repo_enum.run()` records directly: `from repo_enum import run as enum_run`
- Skip records where `kanban_exists=False` or `valid_task_count == 0` (Pitfall 6, RESEARCH.md)

---

#### `main()` with `sys.exit` and `RuntimeError` catch (repo_enum.py lines 335-346)

```python
def main() -> int:
    """Delegate to run() and map success/failure to exit codes."""
    try:
        run()
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**For reconcile.py `main()`:** Same structure, with `argparse` added for `--dry-run` flag before delegating to `run()`. `argparse` is imported inside `main()` (consistent with RESEARCH.md Pattern CLI example — avoids top-level import cost). Return `int`; call `sys.exit(main())`.

---

#### `TASK_STATUSES` and status ranking (utils.py lines 40-54)

```python
# utils.py lines 40-54
TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")

# Map task status to MermaidJS kanban priority (colored left border)
STATUS_PRIORITY = {
    "In Progress": "Very High",   # red — active work
    "Review": "High",             # orange — needs attention
    "Todo": "Low",                # blue — queued
}
```

**CRITICAL distinction for reconcile.py:**
- Import `TASK_STATUSES` — use its tuple index to derive `STATUS_RANK`
- NEVER import or use `STATUS_PRIORITY` in reconcile.py — it maps to Mermaid label strings, not integers (Pitfall 2, RESEARCH.md)
- Derived constant in reconcile.py: `STATUS_RANK: dict[str, int] = {s: i for i, s in enumerate(TASK_STATUSES)}`
- This gives: `{"Todo": 0, "In Progress": 1, "Review": 2, "Done": 3}`

---

#### Org-guard pattern (repo_enum.py lines 76-89)

```python
def _check_remote_org(remote_url: str, name: str) -> bool:
    if not remote_url:
        print(f"Warning: {name} has no origin remote — skipping")
        return False
    url_lower = remote_url.lower()
    if not any(url_lower.startswith(prefix.lower()) for prefix in _ALLOWED_ORG_HOSTS):
        print(f"Warning: {name} remote URL {remote_url!r} is not in allowed org — skipping")
        return False
    return True
```

**For reconcile.py:** Use `record["local_path"]` from `repo_enum.run()` for all git subprocess calls — it is pre-validated by this org-allowlist check in Phase 1. Do NOT re-validate org membership in reconcile.py (it was already done). This also provides the path-traversal mitigation: only paths from pre-validated records are passed to `_run_git`.

---

## Shared Patterns

### Python 3.9 Compatibility
**Source:** `repo_enum.py` line 30, `sheets_sync.py` line 22
**Apply to:** `reconcile.py` (first line after shebang/docstring)
```python
from __future__ import annotations
```
Required for all type annotations using `list[...]`, `dict[...]`, `Optional[...]`, `bool | None` to work at runtime on Python 3.9 (the venv minimum).

### KF_PAT Token Acquisition
**Source:** `scripts/discover.py` lines 76-79
**Apply to:** `reconcile.py` `run()` or a private `_build_headers()` helper
```python
token = os.environ.get("KF_PAT") or os.environ.get("GITHUB_TOKEN")
if not token:
    print("Warning: No KF_PAT or GITHUB_TOKEN set. API rate limits will be very low.")
headers = {"Accept": "application/vnd.github+json"}
if token:
    headers["Authorization"] = f"Bearer {token}"
```

### `_run_git` Subprocess Wrapper
**Source:** `repo_enum.py` lines 96-103
**Apply to:** `reconcile.py` (copy verbatim; all git calls must use this)
- Arg-list only — never `shell=True` (shell injection mitigation)
- `capture_output=True, text=True` — consistent with project subprocess pattern
- Returns `CompletedProcess` with `returncode=1` on timeout (safe default for callers)

### Warning Print Convention
**Source:** `scripts/utils.py` (throughout), `repo_enum.py` (throughout)
**Apply to:** `reconcile.py` helper functions
```python
print(f"Warning: <non-fatal issue description>")
```
Use `Warning:` prefix (bare, no brackets) for non-fatal issues inside private helpers. Use `[INFO]`/`[WARN]`/`[ERROR]` pills only at orchestrator level in `run()` and `render_change_list()`.

### `main() -> int` + `sys.exit(main())` Entry Point
**Source:** `repo_enum.py` lines 335-346; `scripts/aggregator.py` line 536
**Apply to:** `reconcile.py`
```python
def main() -> int:
    try:
        run()
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### `sys.path` Injection for `scripts/utils.py`
**Source:** `repo_enum.py` lines 37-42
**Apply to:** `reconcile.py` (copy verbatim; same directory depth)
```python
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `Proposal` dataclass (inside reconcile.py) | model | n/a | No dataclass-based return shape exists in the project yet; use `dataclasses.dataclass` (stdlib, Python 3.7+) per RESEARCH.md Pattern 8 |
| `task_matches_signal` / `_normalize_tokens` (inside reconcile.py) | utility | transform | No token-matching logic exists in the codebase; implement per RESEARCH.md Pattern 6 |
| `render_change_list` (inside reconcile.py) | utility | transform | No tabular stdout renderer exists; implement per RESEARCH.md Pattern 9 — `[LABEL]` pills, no emojis |

---

## Metadata

**Analog search scope:** `.claude/skills/activity-sync/`, `scripts/`
**Files scanned:** 4 (repo_enum.py, discover.py, utils.py, sheets_sync.py header)
**Pattern extraction date:** 2026-06-04

---

## PATTERN MAPPING COMPLETE

**Phase:** 2 - Activity Mining + Reconciliation
**Files classified:** 2 (reconcile.py new, SKILL.md update)
**Analogs found:** 3 strong matches / 2 files

### Coverage
- Files with exact analog: 1 (reconcile.py — repo_enum.py is exact role+data-flow match)
- Files with role-match analog: 1 (SKILL.md — extend current SKILL.md)
- Files with no analog: 0 (the 3 internal helpers with no analog are sub-components of reconcile.py, not separate files)

### Key Patterns Identified
- All skill modules use `from __future__ import annotations` + 4-level `_REPO_ROOT` path injection + `from utils import ORG, TASK_STATUSES` — copy from repo_enum.py lines 30-50
- `_run_git` wrapper is the canonical subprocess pattern for all git calls — copy verbatim from repo_enum.py lines 96-103; never use `shell=True`
- GitHub REST API auth uses `os.environ.get("KF_PAT") or os.environ.get("GITHUB_TOKEN")` with graceful degrade on missing token — copy from discover.py lines 76-79
- `run() -> list[...]` is the importable Phase-N entry point; `main() -> int` wraps it with `RuntimeError` catch and `sys.exit` — copy structure from repo_enum.py lines 254-346
- `STATUS_RANK` must be derived from `TASK_STATUSES` tuple index; `STATUS_PRIORITY` (Mermaid labels) must NOT be used for numeric comparison

### File Created
`/Users/machina/Dev/kf-cpto/.planning/phases/02-activity-mining-reconciliation/02-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can reference analog patterns in PLAN.md files.
