# Phase 3: Write-Back + Diagram Sanitization — Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 6
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.claude/skills/activity-sync/sanitize.py` | utility | transform | `scripts/utils.py` (`parse_kanban_tasks`) | role-match (transform utility) |
| `.claude/skills/activity-sync/writeback.py` | service | file-I/O + request-response | `.claude/skills/activity-sync/reconcile.py` | exact (same module pattern: `_run_git`, `run()`, `main()`) |
| `.claude/skills/activity-sync/test_writeback.py` | test | batch | `.claude/skills/activity-sync/test_reconcile.py` | exact (same no-pytest harness pattern) |
| `requirements.txt` | config | — | `requirements.txt` | exact (same file; append only) |
| `.gitignore` | config | — | `.gitignore` | exact (same file; append only) |
| `.claude/skills/activity-sync/manifests/.gitkeep` | config | — | n/a (new gitignored dir) | no-analog (new artifact dir) |

---

## Pattern Assignments

### `.claude/skills/activity-sync/sanitize.py` (utility, transform)

**Analog:** `scripts/utils.py` (table-cell parsing and TASK_STATUSES convention)

**Imports pattern** — copy from `reconcile.py` lines 21–40 (sys.path injection + stdlib imports):
```python
from __future__ import annotations

import re
import unicodedata
from typing import Any
```
Note: `sanitize.py` is a pure-function module with no git/subprocess/path dependencies. No sys.path injection needed — it is imported by `writeback.py`, which owns the path setup.

**Module constants pattern** (`SCREAMING_SNAKE_CASE`, from `reconcile.py` lines 43–64 and `utils.py` lines 40–47):
```python
# utils.py lines 40–47
TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")
STATUS_TO_MERMAID = {s: s.replace(" ", "-") for s in TASK_STATUSES}

# reconcile.py lines 63–64 — module-level derived constant
STATUS_RANK: dict[str, int] = {s: i for i, s in enumerate(TASK_STATUSES)}
```
Apply same pattern for `_BREAK_MAP` and `_HEADER_CELLS`:
```python
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
# Frozenset of first-cell values that identify non-data rows (skip sanitization)
_HEADER_CELLS = frozenset({"Task", ":---"})
```

**Core transform pattern** — `parse_kanban_tasks` (utils.py lines 145–198) shows the 4-col/6-col row detection and cell splitting. `sanitize_body` reuses the same `line.startswith("|")` guard and `parts = line.split("|")` split (parts[1] = task cell):
```python
# utils.py lines 157–163 — 4-vs-6-col detection and pipe-split pattern
header_match = re.search(r"^\|[^\n]+\|", content, re.MULTILINE)
pipe_count = header_match.group().count("|") - 1  # subtract leading pipe
is_6col = pipe_count >= 6

# utils.py lines 174–175 — skip header and separator rows
if first in ("Task", ":---") or first.startswith(":"):
    continue
```
`sanitize_body` skips the same set (`first_cell == "Task"` or `":---" in stripped`) — reusing the same guard rather than the regex pattern.

**Warning/print pattern** (from `utils.py` line 186–188 and `reconcile.py` lines 105–106):
```python
# utils.py lines 186–188
print(f"Warning: Unknown status '{status}'{label} for task '{task_name}'. "
      f"Valid: {', '.join(TASK_STATUSES)}")

# reconcile.py lines 105–106
print(f"Warning: git {args[0] if args else ''} timed out after {timeout}s")
```
`sanitize.py` is a pure library — no print statements. Callers (`writeback.py`) emit `[WARN]` pills.

---

### `.claude/skills/activity-sync/writeback.py` (service, file-I/O + request-response)

**Analog:** `.claude/skills/activity-sync/reconcile.py`

**Shebang + module docstring pattern** (reconcile.py lines 1–20):
```python
#!/usr/bin/env python3
"""
Activity Sync — Write-Back

Consumes reconcile.run() Proposals, writes corrected kanban.md back to each tracked
repo, and pushes to trigger the notify-kf-cpto.yml -> kanban-updated -> aggregate.yml
pipeline. Sanitizes Mermaid-breaking characters before write.

Usage:
    python .claude/skills/activity-sync/writeback.py

Phase 3 entry point:
    from writeback import run
    results = run(proposals, dry_run=False)
"""
```

**Imports pattern** (reconcile.py lines 21–40):
```python
from __future__ import annotations

import subprocess
import sys
import os
import re
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
```
Followed by the same sys.path injection block:
```python
# reconcile.py lines 35–40
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils import ORG, TASK_STATUSES  # noqa: E402
```

**Module-level constants** (reconcile.py lines 43–64):
```python
# reconcile.py lines 46–48
REPOS_LOCAL_DIR = _REPO_ROOT / "repos-local"
GIT_TIMEOUT_SECONDS = 60

# writeback.py adds:
MANIFESTS_DIR = Path(__file__).parent / "manifests"
COMMIT_MSG = "chore(kanban): reconcile task statuses from repo activity"
_FM_RE = re.compile(r'^---\n(.*?)\n---\n?', re.DOTALL)
```

**`_run_git` helper** — copy exactly from `reconcile.py` lines 96–106 (identical function):
```python
def _run_git(args: list[str], cwd: str | None = None, timeout: int = GIT_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    """Internal git subprocess wrapper. Uses arg-list subprocess; never shell-interpolated."""
    try:
        return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"Warning: git {args[0] if args else ''} timed out after {timeout}s")
        return subprocess.CompletedProcess(["git"] + args, returncode=1, stdout="", stderr="git timed out")
```

**`_get_remote_url` helper** — copy exactly from `repo_enum.py` lines 111–114:
```python
def _get_remote_url(repo_path: str) -> str:
    """Return the origin remote URL, or empty string if unavailable."""
    result = _run_git(["-C", repo_path, "remote", "get-url", "origin"])
    return result.stdout.strip() if result.returncode == 0 else ""
```

**Push auth pattern** — mirrors `aggregate.yml` lines 49–51 and 62–63 (HTTPS+KF_PAT, git identity, restore in finally):
```yaml
# aggregate.yml lines 49–51 — HTTPS+KF_PAT URL construction
https://${{ secrets.KF_PAT }}@github.com/${{ env.KF_ORG }}/${repo}.git

# aggregate.yml lines 62–63 — git commit identity
git config user.name "KF Bot"
git config user.email "bot@katty-fashion.dev"
```
Python equivalent in `writeback.py` (`_push_with_auth` function):
```python
https_url = f"https://{kf_pat}@github.com/katty-fashion/{repo_name}.git"
# arg-list only; never shell=True; never print https_url
_run_git(["-C", repo_path, "config", "user.name", "KF Bot"])
_run_git(["-C", repo_path, "config", "user.email", "bot@katty-fashion.dev"])
```

**`run()` / `main()` split pattern** (reconcile.py lines 552–639):
```python
# reconcile.py lines 552–598 — run() returns structured result, no sys.exit
def run() -> list[Proposal]:
    """..."""
    print("Activity Sync — Reconcile — Starting...")
    ...
    print("Activity Sync — Reconcile — Done!")
    return all_proposals

# reconcile.py lines 604–639 — main() parses args, delegates, calls sys.exit
def main() -> int:
    """Parse flags and delegate to run(). Map success/failure to exit codes."""
    import argparse
    ...
    try:
        run()
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```
`writeback.py` follows the same split: `run(proposals, dry_run=False) -> list[dict]` returns manifest entries; `main()` calls `reconcile.run()` then `run()`, then `sys.exit`.

**[LABEL] text-pill print pattern** (reconcile.py lines 469–488):
```python
# reconcile.py lines 471–472
print("[INFO] No changes proposed — all declared statuses match activity.")
# reconcile.py lines 509–511 (from _enum_records_fallback)
print(f"[WARN] Fallback: no valid repos found in repos-local/")
# reconcile.py lines 581–585
print(f"[WARN] repo_enum clean-tree check failed ...")
```
`writeback.py` extends the pill set with: `[DONE]`, `[CONFLICT]`, `[SKIP]`, `[FAIL]` — same style, no emojis.

**Error handling pattern** — non-fatal errors use `print(f"Warning: ...")` (utils.py line 186); fatal errors return non-zero from `main()` and print to `sys.stderr` (reconcile.py lines 633–635). `sheets_sync.py` pattern of `except Exception` with `# noqa: BLE001` is NOT used here — `writeback.py` per-repo errors are caught at `_write_repo()` level and recorded in the manifest as `outcome: "failed"`; the overall `run()` continues.

---

### `.claude/skills/activity-sync/test_writeback.py` (test, batch)

**Analog:** `.claude/skills/activity-sync/test_reconcile.py`

**File header + import block** (test_reconcile.py lines 1–37):
```python
#!/usr/bin/env python3
"""
Test suite for writeback.py — sanitize and write-back core.

Runs with plain Python (no pytest dependency):
    python .claude/skills/activity-sync/test_writeback.py

Exits non-zero on any failed assert.
"""
import sys
import io
import os
import shutil
import tempfile
import subprocess
from pathlib import Path

_SKILL_DIR = Path(__file__).parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

import sanitize
import writeback
from sanitize import sanitize_cell, sanitize_body
from writeback import (
    split_kanban,
    reconstruct_kanban,
    _is_behind_origin,
    _content_changed,
    _write_manifest,
)
```

**`check()` helper + PASS/FAIL counters** (test_reconcile.py lines 39–51):
```python
PASS = 0
FAIL = 0

def check(name: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  PASS: {name}")
        PASS += 1
    else:
        print(f"  FAIL: {name}")
        FAIL += 1
```

**Context-manager monkeypatching pattern** (test_reconcile.py lines 216–249, 509–533):
```python
class _FakeRunGit:
    """Context manager to monkeypatch reconcile._run_git."""
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        ...
    def __enter__(self):
        self._orig = reconcile._run_git
        reconcile._run_git = lambda args, cwd=None, timeout=60: ...
        return self
    def __exit__(self, *args):
        reconcile._run_git = self._orig
```
Apply same pattern for `writeback._run_git` in test_writeback.py.

**`_EnvPatch` context manager** (test_reconcile.py lines 413–435):
```python
class _EnvPatch:
    """Context manager to patch os.environ for tests."""
    def __init__(self, overrides: dict):
        ...
    def __enter__(self):
        for k, v in self.overrides.items():
            self._orig[k] = os.environ.get(k)
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
    def __exit__(self, *args):
        for k, orig in self._orig.items():
            if orig is None: os.environ.pop(k, None)
            else: os.environ[k] = orig
```
Reuse directly for `KF_PAT` env tests in test_writeback.py.

**Summary block** (test_reconcile.py lines 731–735):
```python
print(f"\n--- Results: {PASS} passed, {FAIL} failed ---")
if FAIL > 0:
    sys.exit(1)
```

**Throwaway bare repo pattern** — new for Phase 3; no exact analog in test_reconcile.py (which uses only stubs). From RESEARCH.md Pattern 8 (verified by researcher):
```python
def _make_bare_remote() -> tuple[Path, Path, Path]:
    """Create bare repo + workdir. Returns (tmpdir, bare_dir, workdir)."""
    tmpdir = Path(tempfile.mkdtemp())
    bare = tmpdir / "bare.git"
    work = tmpdir / "workdir"
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)
    subprocess.run(["git", "clone", str(bare), str(work)], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "bot@test.dev"], cwd=work, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Bot"], cwd=work, capture_output=True)
    return tmpdir, bare, work
# Usage: try: ... finally: shutil.rmtree(tmpdir)
```

---

### `requirements.txt` (config, append-only)

**Analog:** `requirements.txt` (current file)

**Current file pattern** (requirements.txt lines 1–12):
```
# KF-CPTO Dependencies
# Python 3.9+ required

# Core dependencies
pyyaml>=6.0

# Google Sheets integration (optional - scripts fallback gracefully)
google-auth>=2.0
google-api-python-client>=2.0

# HTTP requests (optional)
requests>=2.28
```
**Change:** append a new section after line 12:
```
# Skill-local dependency (skill only; CI never installs this)
ruamel.yaml>=0.17
```

---

### `.gitignore` (config, append-only)

**Analog:** `.gitignore` (current file)

**Existing skill-exclusion pattern** (`.gitignore` lines 69–74):
```gitignore
# Claude: ignore everything under .claude/ EXCEPT the skills dir
.claude/*
!.claude/skills/

# Runtime dirs (skill-local; never committed)
repos-local/
```
**Problem:** The `!.claude/skills/` negation makes ALL content under `.claude/skills/` trackable by git, including the new `manifests/` runtime artifacts.

**Change:** append after line 74:
```gitignore
# Skill runtime artifacts (per-run manifests; never committed)
.claude/skills/activity-sync/manifests/
```

---

## Shared Patterns

### `_run_git` Subprocess Wrapper
**Source:** `.claude/skills/activity-sync/reconcile.py` lines 96–106 and `repo_enum.py` lines 96–102 (identical functions)
**Apply to:** `writeback.py`
```python
def _run_git(args: list[str], cwd: str | None = None, timeout: int = GIT_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"Warning: git {args[0] if args else ''} timed out after {timeout}s")
        return subprocess.CompletedProcess(["git"] + args, returncode=1, stdout="", stderr="git timed out")
```
Rule: arg-list only, never `shell=True`, never f-string a user value into a shell command.

### `run()` / `main()` Module Entry-Point Split
**Source:** `.claude/skills/activity-sync/reconcile.py` lines 552–598 (`run`) and 604–639 (`main`)
**Apply to:** `writeback.py`
- `run(proposals, dry_run)` — does the work, returns structured result, never calls `sys.exit`
- `main()` — parses CLI args via `argparse`, calls `reconcile.run()` then `writeback.run()`, calls `sys.exit(main())`
- Module ends with `if __name__ == "__main__": sys.exit(main())`

### `[LABEL]` Text Pills
**Source:** `.claude/skills/activity-sync/reconcile.py` lines 471, 509, 529, 581 etc.
**Apply to:** `writeback.py` output
```python
print("[INFO] No changes proposed — all declared statuses match activity.")
print(f"[WARN] {repo_name}: fetch failed — skipping")
print(f"[CONFLICT] {repo_name}: local is {n} commit(s) behind origin/{branch} — skipping write")
print(f"[SKIP] {repo_name}: content unchanged (idempotent no-op)")
print(f"[DONE] {repo_name}: pushed {sha[:8]} (branch: {branch})")
print(f"[FAIL] {repo_name}: {error}")
```
No emojis. No colon-preceded pill variants. Caps pills only.

### `sys.path` Injection for `scripts/` Imports
**Source:** `.claude/skills/activity-sync/reconcile.py` lines 35–40 and `repo_enum.py` lines 39–43
**Apply to:** `writeback.py`
```python
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils import ORG, TASK_STATUSES  # noqa: E402
```
`sanitize.py` does NOT need this injection (pure stdlib functions; `writeback.py` imports it as a sibling).

### `from __future__ import annotations`
**Source:** `reconcile.py` line 21, `repo_enum.py` line 31
**Apply to:** `writeback.py`, `sanitize.py`
Required for `str | None` union syntax on Python 3.9.

### Warning / Non-Fatal Error Printing
**Source:** `scripts/utils.py` lines 186–188, `repo_enum.py` lines 83–84
**Apply to:** `writeback.py`
```python
# Non-fatal: print Warning: prefix (utils convention)
print(f"Warning: {repo_name}: fetch failed for {repo_path}: {fetch.stderr.strip()}")
# Structured non-fatal: [WARN] pill (reconcile convention; used in writeback for consistency)
print(f"[WARN] {repo_name}: ...")
```

### Test Module Structure (no-pytest)
**Source:** `.claude/skills/activity-sync/test_reconcile.py`
**Apply to:** `test_writeback.py`
- Top-level `check(name, condition)` helper with global `PASS`/`FAIL` counters
- Test sections delimited by `print("--- SECTION ---")`
- Context-manager stubs (`class _FakeXxx`) for isolating dependencies
- `_EnvPatch` for env var isolation
- Summary at end: `print(f"\n--- Results: {PASS} passed, {FAIL} failed ---"); if FAIL > 0: sys.exit(1)`

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.claude/skills/activity-sync/manifests/.gitkeep` | config | — | No existing gitignored runtime-artifact sentinel in the codebase; pattern is standard but novel to this skill |

The throwaway bare-repo test harness (Pattern 8 in RESEARCH.md) has no existing analog in `test_reconcile.py` (which uses only in-process stubs). The `_make_bare_remote()` helper pattern is drawn from verified research rather than the codebase.

---

## Metadata

**Analog search scope:** `.claude/skills/activity-sync/`, `scripts/`, `.github/workflows/aggregate.yml`, `requirements.txt`, `.gitignore`
**Files scanned:** 8 (`reconcile.py`, `repo_enum.py`, `test_reconcile.py`, `utils.py`, `aggregate.yml`, `requirements.txt`, `.gitignore`, `SKILL.md`)
**Pattern extraction date:** 2026-06-04
