# Phase 1: Repo Access Foundation - Research

**Researched:** 2026-06-04
**Domain:** Python skill module — local git enumeration, fetch, and kanban parsing
**Confidence:** HIGH — all findings verified against the live codebase and local git tooling

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Skill lives at `.claude/skills/activity-sync/` with a `SKILL.md` index plus Python modules
- `repo_enum.py` imports `scripts/utils.py` via `sys.path` injection — one-parser constraint
- Tracked sibling checkouts live under a gitignored `repos-local/` at repo root
- Bootstrap helper clones missing tracked repos into `repos-local/` (clone over symlink-only)
- Marker seeding: bootstrap seeds `kanban.md` and `notify-kf-cpto.yml` from `templates/` for repos lacking them
- Tracked set is the curated allowlist realized by `repos-local/` membership (no hardcoded array)
- Initial set: 6 repos — kf-be-platform (main), kf-fe-platform (main), kf-platform (master), R3-AAS (main, has kanban only), ai-rise-options (master, no markers), tech_brainstorming (main, no markers)
- Per-repo default branch must be honored (mix of `main` and `master`)
- Error handling: skip+[WARN] on missing checkout/markers; `git fetch` failure is NON-FATAL; assert `git status` clean post-run

### Claude's Discretion

- Exact module/function decomposition within the skill dir
- Log line formatting
- Structured-return shape for downstream Phase 2 consumption

### Deferred Ideas (OUT OF SCOPE)

- Activity mining / git-signal reconciliation — Phase 2
- Write-back, push, and Mermaid sanitization — Phase 3
- Agentic capacity model — Phase 4
- A richer exclude mechanism beyond `repos-local/` membership

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REPO-01 | Skill enumerates tracked repos by scanning `repos-local/` (curated set, no static project list); markers verified and seeded when absent | `repos-local/` dir scan pattern; bootstrap clone + seed from `templates/`; marker presence check |
| REPO-02 | Skill runs `git fetch` per tracked repo before reading, logs up-to-date vs new commits | Before/after SHA comparison pattern verified; non-fatal fetch error handling |
| REPO-03 | Skill reuses `scripts/utils.py` parsers and status constants; no second kanban parser | sys.path injection pattern verified; direct parser call pattern documented; load_project_kanban() excluded (wrong path) |

</phase_requirements>

---

## Summary

This phase creates the read-only foundation of the `activity-sync` skill. The deliverable is a single Python module (`repo_enum.py`) inside a new Claude Code project skill at `.claude/skills/activity-sync/` that: (1) enumerates repos by scanning `repos-local/`, (2) runs `git fetch origin` per repo before reading, and (3) parses each `kanban.md` through the existing `scripts/utils.py` parsers. Zero writes to the kf-cpto working tree or to any tracked repo.

All technology choices are already resolved by the stack and locked decisions. There are no new external dependencies: the entire implementation uses Python 3.9 stdlib (`subprocess`, `pathlib`, `sys`) plus the project's existing `pyyaml` for the parsers imported from `scripts/utils.py`. The `subprocess` git pattern is verified working against local repos.

There are two structural issues the planner must resolve before writing tasks: (a) a `.gitignore` conflict — `.claude/` is gitignored as a whole, meaning skill code placed there will not be committed; and (b) `utils.load_project_kanban()` is hardwired to `repos/` (CI clone dir), so the skill must call `parse_kanban_frontmatter()` and `parse_kanban_tasks()` directly with its own path, bypassing that convenience function.

**Primary recommendation:** Keep skill at `.claude/skills/activity-sync/` but add `.gitignore` rules that replace the blanket `.claude/` exclusion with fine-grained exclusions that preserve `.claude/skills/`. Alternatively use `.agents/skills/activity-sync/` which is NOT gitignored. Resolve before planning tasks.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Repo enumeration | Local skill script | — | Reads `repos-local/` directory, produces (name, path, remote_url) tuples |
| Bootstrap clone | Local skill script | git subprocess | Clones missing repos into `repos-local/` via SSH |
| Marker seeding | Local skill script | templates/ | Copies kanban.md/notify-kf-cpto.yml template files into cloned repo |
| git fetch | Local skill script (subprocess) | — | Subprocess call per tracked repo; non-fatal on failure |
| kanban parsing | scripts/utils.py (imported) | — | One-parser constraint; skill must not duplicate |
| Clean-state assertion | Local skill script | git subprocess | `git status --porcelain` on kf-cpto confirms no working tree mutation |
| CI pipeline | aggregate.yml | — | Untouched by Phase 1; skill adds no CI dependency |

---

## Standard Stack

### Core

No new packages. All tooling is stdlib + the existing project stack.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `subprocess` | 3.9+ (stdlib) | All git operations: fetch, remote URL, branch, status | Zero new dep; verified working for all needed git commands |
| Python stdlib `pathlib` | 3.9+ (stdlib) | Path resolution for `repos-local/`, kanban.md location | Already the standard across all scripts/ |
| Python stdlib `sys` | 3.9+ (stdlib) | sys.path injection to import scripts/utils.py | Required for one-parser constraint |
| `pyyaml` | 6.0.3 (already installed) | Used by imported utils.parse_kanban_frontmatter() | Pre-existing; no install needed |

[VERIFIED: local codebase] — all packages confirmed present; `python3 -c "import yaml; print(yaml.__version__)"` returns 6.0.3.

### No Package Legitimacy Audit Required

This phase introduces zero new external packages. All tooling is Python 3.9 stdlib or the existing `pyyaml` already in `requirements.txt`. No `npm install`, `pip install`, or any registry interaction is needed.

---

## Architecture Patterns

### System Architecture Diagram

```
User invokes skill
       |
       v
.claude/skills/activity-sync/SKILL.md
       |
       v
repo_enum.py  <-- sys.path injection --> scripts/utils.py (parsers)
       |
       +-- scan repos-local/ --> [dir entries]
       |
       for each repo:
         +-- git -C <path> remote get-url origin
         +-- git -C <path> rev-parse --abbrev-ref HEAD  (default branch)
         +-- [before SHA] git -C <path> rev-parse origin/<branch>
         +-- git -C <path> fetch origin  (non-fatal)
         +-- [after SHA] git -C <path> rev-parse origin/<branch>
         +-- log: up-to-date OR new commits
         +-- check kanban.md exists
         +-- utils.parse_kanban_frontmatter(content)
         +-- utils.parse_kanban_tasks(content, project=name)
         +-- utils.normalize_frontmatter(meta)
         |
         v
       RepoRecord(name, local_path, remote_url, branch,
                  fetch_status, meta, tasks, valid_task_count)
       |
       v
stdout: human-readable (name, path, remote_url) list
return: list[RepoRecord]  <-- Phase 2 input
       |
       v
assert: git -C kf-cpto status --porcelain == ""
```

Bootstrap path (run once or on demand):

```
bootstrap.py
  for each repo in TRACKED_REPOS config:
    if repos-local/<name> absent:
      git clone git@github.com:Katty-Fashion/<name>.git repos-local/<name>
    check kanban.md exists -> if absent: copy from templates/kanban.md
    check .github/workflows/notify-kf-cpto.yml -> if absent: copy from templates/.github/workflows/
```

### Recommended Project Structure

```
.claude/skills/activity-sync/
├── SKILL.md              # Claude Code skill index (frontmatter + instructions)
├── repo_enum.py          # Main enumeration + fetch + parse module
└── bootstrap.py          # One-shot clone + seed helper (run before repo_enum.py)

repos-local/              # gitignored; populated by bootstrap.py
├── kf-be-platform/       # full clone (SSH)
├── kf-fe-platform/
├── kf-platform/
├── R3-AAS/               # already exists at /Users/machina/Dev/R3-AAS (symlink or clone)
├── ai-rise-options/      # already exists at /Users/machina/Dev/ai-rise-options
└── tech_brainstorming/   # missing; bootstrap clones it
```

### Pattern 1: sys.path Injection to Import scripts/utils.py

**What:** The skill module adds `scripts/` to sys.path at import time, then imports the canonical parsers.

**When to use:** Every skill module that needs kanban parsing.

```python
# Source: verified live against this codebase 2026-06-04
import sys
from pathlib import Path

# repo_enum.py is at: <repo_root>/.claude/skills/activity-sync/repo_enum.py
# Path arithmetic: parent=activity-sync/, x2=skills/, x3=.claude/, x4=repo_root
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

[VERIFIED: local codebase] — `Path(__file__).parent.parent.parent.parent` from `.claude/skills/activity-sync/repo_enum.py` correctly resolves to repo root. Confirmed by shell arithmetic test.

**Critical:** Do NOT use `utils.load_project_kanban(project)` — it is hardwired to `REPOS_DIR` (the CI `repos/` directory, NOT `repos-local/`). Call `parse_kanban_frontmatter(content)` and `parse_kanban_tasks(content, project=name)` directly after reading the file yourself.

### Pattern 2: Reading kanban.md from repos-local/ with the Canonical Parsers

**What:** Read file content from `repos-local/<name>/kanban.md`, then call the canonical parsers directly.

**When to use:** Every kanban read in the skill. Never through `load_project_kanban()`.

```python
# Source: derived from scripts/utils.py parse function signatures (verified)
from pathlib import Path

def read_kanban(repo_name: str, repos_local: Path) -> dict:
    """Read and parse kanban.md from a repos-local checkout."""
    kanban_path = repos_local / repo_name / "kanban.md"
    if not kanban_path.exists():
        return {"exists": False, "meta": normalize_frontmatter({}), "tasks": [], "raw": ""}

    content = kanban_path.read_text(encoding="utf-8")
    meta = normalize_frontmatter(parse_kanban_frontmatter(content))
    tasks = parse_kanban_tasks(content, project=repo_name)
    valid_task_count = sum(1 for t in tasks if t["status"] in TASK_STATUSES)
    return {
        "exists": True,
        "meta": meta,
        "tasks": tasks,
        "valid_task_count": valid_task_count,
        "raw": content,
    }
```

### Pattern 3: git fetch with Before/After SHA Comparison

**What:** Capture the remote tracking SHA before and after fetch to determine if new commits arrived.

**When to use:** Per-repo fetch step in `repo_enum.py`.

```python
# Source: verified against /Users/machina/Dev/R3-AAS (live repo) 2026-06-04
import subprocess

def git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)

def fetch_repo(repo_path: str, branch: str) -> str:
    """Fetch origin and return 'up-to-date' or 'new-commits'. Non-fatal."""
    tracking_ref = f"origin/{branch}"
    before = git(["-C", repo_path, "rev-parse", tracking_ref])
    before_sha = before.stdout.strip() if before.returncode == 0 else None

    fetch = git(["-C", repo_path, "fetch", "origin"])
    if fetch.returncode != 0:
        print(f"[WARN] fetch failed for {repo_path}: {fetch.stderr.strip()}")
        return "fetch-failed"

    after = git(["-C", repo_path, "rev-parse", tracking_ref])
    after_sha = after.stdout.strip() if after.returncode == 0 else None

    if before_sha == after_sha:
        return "up-to-date"
    return "new-commits"
```

[VERIFIED: local codebase] — `git fetch --verbose` output shows `= [up to date]` for current repos. The before/after SHA comparison is a cleaner machine-readable approach. Confirmed against `/Users/machina/Dev/R3-AAS` (returns `up-to-date`).

### Pattern 4: Default Branch Detection from Local Checkout

**What:** Detect per-repo default branch from the local checkout's current HEAD branch (not from the remote API).

**When to use:** Required because the org has a mix of `main` and `master`.

```python
# Source: verified against R3-AAS (main) and ai-rise-options (master) 2026-06-04
def get_default_branch(repo_path: str) -> str:
    """Detect current branch from local checkout HEAD."""
    result = git(["-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode == 0:
        branch = result.stdout.strip()
        if branch and branch != "HEAD":  # HEAD = detached state
            return branch
    return "main"  # safe fallback

def get_remote_url(repo_path: str) -> str:
    result = git(["-C", repo_path, "remote", "get-url", "origin"])
    return result.stdout.strip() if result.returncode == 0 else ""
```

[VERIFIED: local codebase] — `git rev-parse --abbrev-ref HEAD` returns `main` for R3-AAS and `master` for ai-rise-options. `symbolic-ref refs/remotes/origin/HEAD` was NOT set in these repos (common for clones without `--set-upstream`), making it unreliable.

### Pattern 5: Clean-State Assertion

**What:** After all reads and fetches, assert the kf-cpto working tree is unchanged.

**When to use:** End of `repo_enum.py` main execution.

```python
# Source: derived from git documentation; verified 2026-06-04
def assert_kf_cpto_clean(kf_cpto_root: str) -> None:
    result = git(["-C", kf_cpto_root, "status", "--porcelain"])
    if result.stdout.strip():
        raise RuntimeError(
            f"[ERROR] kf-cpto working tree is dirty after skill run:\n{result.stdout}"
        )
    print("[INFO] kf-cpto working tree: CLEAN")
```

### Pattern 6: Clone Bootstrap

**What:** Clone a missing tracked repo into `repos-local/` using SSH.

**When to use:** In `bootstrap.py` for repos not yet present locally.

```python
# Source: derived from .github/workflows/aggregate.yml clone pattern (adapted SSH)
import subprocess
from pathlib import Path

def clone_repo(name: str, branch: str, repos_local: Path, org: str = "Katty-Fashion") -> bool:
    """Clone a tracked repo into repos-local/ via SSH. Returns True on success."""
    target = repos_local / name
    if target.exists():
        return True  # already present
    result = subprocess.run(
        ["git", "clone", "-b", branch,
         f"git@github.com:{org}/{name}.git", str(target)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[WARN] Clone failed for {name}: {result.stderr.strip()}")
        return False
    print(f"[INFO] Cloned {name} -> {target}")
    return True
```

Note: CI uses `--depth=1` HTTPS clones with KF_PAT. The skill uses FULL SSH clones (no `--depth=1`) because Phase 2 activity mining needs git log history. Confirmed: existing local checkouts use SSH (`git@github.com:Katty-Fashion/...`). [VERIFIED: local codebase]

### Pattern 7: Marker Seeding

**What:** Copy `kanban.md` and/or `notify-kf-cpto.yml` from `templates/` into a freshly cloned repo that lacks them.

**When to use:** In `bootstrap.py` after clone, for repos like `ai-rise-options` (no markers).

```python
# Source: derived from templates/ directory contents (verified 2026-06-04)
import shutil
from pathlib import Path

def seed_markers(repo_path: Path, kf_cpto_root: Path) -> None:
    """Seed kanban.md and notify workflow from templates/ if absent."""
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

[VERIFIED: local codebase] — `templates/kanban.md` and `templates/.github/workflows/notify-kf-cpto.yml` both exist.

### Pattern 8: Is-Valid-Git-Repo Check

**What:** Confirm a directory under `repos-local/` is an actual git repo before operating on it.

```python
def is_git_repo(path: str) -> bool:
    result = git(["-C", path, "rev-parse", "--git-dir"])
    return result.returncode == 0
```

[VERIFIED: local codebase] — `git -C <valid-repo> rev-parse --git-dir` exits 0 and returns `.git`; exits non-zero for non-git dirs.

### Anti-Patterns to Avoid

- **Calling `utils.load_project_kanban()`:** It resolves paths against `REPOS_DIR` (`repos/`), which is the CI runtime dir, NOT `repos-local/`. Always call `parse_kanban_frontmatter()` and `parse_kanban_tasks()` directly with your own path. [VERIFIED: live code inspection]
- **Calling `utils.load_projects()`:** It reads `repos/discovered.txt` (CI artifact). The skill enumerates by scanning `repos-local/` at runtime, not from `discovered.txt`.
- **Using `utils.REPOS_DIR` or `utils.BASE_DIR`:** These constants point at paths relative to `scripts/utils.py`'s location (repo root). Use `_REPO_ROOT` derived from `Path(__file__)` in the skill module instead.
- **Relying on `symbolic-ref refs/remotes/origin/HEAD`:** Not set in locally cloned repos that were not cloned with `--set-upstream-to`. Use `rev-parse --abbrev-ref HEAD` instead.
- **Shallow clone for `repos-local/`:** CI uses `--depth=1` because it only needs the latest file content. Phase 2 needs git log history for activity mining — do not shallow-clone.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| kanban.md parsing | A new regex/table parser in the skill | `utils.parse_kanban_frontmatter()` and `utils.parse_kanban_tasks()` | One-parser constraint; two parsers diverge on edge cases (pipe-count detection, separator rows) |
| Task status validation | A local TASK_STATUSES tuple | `utils.TASK_STATUSES` (imported) | Single source of truth; skill and aggregator must agree |
| Git operations | GitPython or dulwich | `subprocess` + `git` | Zero new deps; all required operations (fetch, rev-parse, remote, status) are simple subprocess calls |

**Key insight:** The entire skill is "don't hand-roll" — every reusable component already exists in `scripts/utils.py`. The skill's job is to wire them together with the right paths.

---

## Common Pitfalls

### Pitfall 1: load_project_kanban() Uses Wrong Directory

**What goes wrong:** Developer calls `utils.load_project_kanban(repo_name)` from the skill. It constructs path as `REPOS_DIR / repo_name / "kanban.md"` which resolves to `repos/<name>/kanban.md` (the CI clone dir), not `repos-local/<name>/kanban.md`. File not found; returns `exists: False` silently.

**Why it happens:** `load_project_kanban()` looks like the right function name. The path hardcoding inside it is non-obvious until you read the source.

**How to avoid:** Never call `load_project_kanban()` from the skill. Always call `parse_kanban_frontmatter(content)` and `parse_kanban_tasks(content, project=name)` after reading the file yourself from `repos-local/<name>/kanban.md`.

**Warning signs:** `repo_enum.py` reports `exists: False` for repos that have a readable `kanban.md` in `repos-local/`.

---

### Pitfall 2: Wrong Path Arithmetic for sys.path

**What goes wrong:** Developer uses 3 levels of `.parent` instead of 4. `Path(__file__).parent.parent.parent` from `repo_enum.py` resolves to `.claude/` (not the repo root). `scripts/` is not found; `ImportError: No module named 'utils'`.

**Why it happens:** The skill is nested 4 levels deep: `<repo_root>/.claude/skills/activity-sync/repo_enum.py`.

**How to avoid:** `_REPO_ROOT = Path(__file__).parent.parent.parent.parent` — exactly 4 levels. The path chain is: `repo_enum.py` → `activity-sync/` → `skills/` → `.claude/` → repo root. [VERIFIED: shell arithmetic]

**Warning signs:** `ModuleNotFoundError: No module named 'utils'` at import time.

---

### Pitfall 3: .gitignore Swallows the Skill Code

**What goes wrong:** `.claude/` is gitignored by line 69 of `.gitignore` (`#Claude / .claude/`). All files under `.claude/skills/activity-sync/` are invisible to git. After creating the skill, `git status` shows nothing new; `git add -A` adds nothing; code is never committed.

**Why it happens:** The existing `.gitignore` entry was added to exclude Claude session files (memory, settings) — not skill code. The blanket pattern catches everything.

**How to avoid:** The planner must add a Wave 0 task to modify `.gitignore` before any skill files are created. Two approaches:

Option A (preferred): Replace the blanket exclusion with fine-grained entries:
```
# Claude session files (not skills)
.claude/settings.local.json
.claude/cache/
```

Option B: Use `.agents/skills/activity-sync/` instead (NOT gitignored — confirmed). Then update CLAUDE.md's "Project Skills" discovery path to match.

**Warning signs:** After creating `.claude/skills/activity-sync/repo_enum.py`, running `git status` shows no new files.

---

### Pitfall 4: Negated .gitignore Pattern Does Not Un-Ignore Subdirectory of Excluded Parent

**What goes wrong:** Developer adds `!.claude/skills/` to `.gitignore`, expecting it to make `.claude/skills/` trackable. It does not. Git's rule: negation cannot re-include a file if its parent directory was excluded by a preceding pattern. The `.claude/` parent is excluded; `!.claude/skills/` is silently ignored.

**Why it happens:** This is a well-known git gotcha. Negation with `!` only works when the parent directory is not itself excluded.

**How to avoid:** To make `.claude/skills/` tracked, the blanket `.claude/` entry must be removed or replaced with specific sub-path patterns (see Pitfall 3 fix). [VERIFIED: live gitignore negation test]

---

### Pitfall 5: Parse-Parity Metric is Valid-Status Count, Not Total Row Count

**What goes wrong:** Developer compares `len(parse_kanban_tasks(content))` from the skill against what the aggregator "would produce." The aggregator's summary table counts only tasks with status in TASK_STATUSES, not all parsed rows. R3-AAS returns 181 rows from the parser but 0 valid-status rows — a parity check based on total row count would show 181 vs 0 (false failure).

**Why it happens:** `parse_kanban_tasks()` returns every row that matches the table regex, including separator rows, header rows, and non-standard tables. The aggregator filters to `TASK_STATUSES` in its summary table logic (aggregator.py lines 102-109).

**How to avoid:** The parity check in the skill must compare `sum(1 for t in tasks if t["status"] in TASK_STATUSES)` — matching the aggregator's count logic exactly. [VERIFIED: live code inspection + test against R3-AAS]

**Warning signs:** Parity check fails for repos with non-standard kanban.md format (like R3-AAS), even though the skill is running the exact same parser.

---

### Pitfall 6: R3-AAS kanban.md Is Non-Standard Format

**What goes wrong:** R3-AAS uses emoji statuses (`✅ Done`, `🔄 In Progress`, `⏭️ Next`) and multiple non-standard Markdown tables. The canonical parser returns 181 rows, all with unrecognized statuses — valid-status count is 0. This is expected behavior for this repo in its current state.

**Why it happens:** R3-AAS predates the kanban template. Its `kanban.md` is a project document, not a structured task table.

**How to avoid:** The skill must accept 0 valid tasks as a valid parse result (not an error). Log `[INFO] R3-AAS: 0 valid-status tasks (non-standard kanban format)` and continue. Do not fail or skip the repo on account of parse result. [VERIFIED: live parser run against /Users/machina/Dev/R3-AAS]

---

### Pitfall 7: Stale Local Clone Produces Wrong Read

**What goes wrong:** Developer skips the `git fetch` step, reads from local HEAD. The local checkout may be hours or days behind `origin`. The task count and status distribution reflect old state.

**How to avoid:** Always fetch before read (REPO-02). The fetch is non-fatal — if it fails (offline), fall back to local state and log `[WARN] fetch failed — reading local state`. Never skip the attempt.

---

## Code Examples

### Enumerating repos-local/

```python
# Source: derived from project conventions (verified 2026-06-04)
from pathlib import Path

def enumerate_repos(repos_local: Path) -> list[str]:
    """Return sorted list of repo names present in repos-local/."""
    if not repos_local.exists():
        return []
    return sorted(
        d.name for d in repos_local.iterdir()
        if d.is_dir() and is_git_repo(str(d))
    )
```

### Parity Check Function

```python
# Source: derived from aggregator.py lines 102-109 (verified)
def valid_task_count(tasks: list[dict]) -> int:
    """Count tasks with status in TASK_STATUSES — matches aggregator summary table logic."""
    return sum(1 for t in tasks if t["status"] in TASK_STATUSES)
```

### SKILL.md Minimal Frontmatter

```markdown
---
name: activity-sync
description: "Read-only enumeration and parsing of tracked sibling repos. Use to inspect kanban state across all tracked repos. Triggers on: activity sync, repo enum, list tracked repos."
allowed-tools: Bash Read
---

# Activity Sync — Repo Access

Run `python .claude/skills/activity-sync/repo_enum.py` to enumerate all tracked repos,
fetch remote state, and parse each kanban.md.

## Usage

!`python .claude/skills/activity-sync/repo_enum.py`
```

[ASSUMED] — SKILL.md frontmatter field names (`name`, `description`, `allowed-tools`) are based on the prior project stack research referencing Claude Code skills spec. Confirm field names match the current spec before writing the file.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `utils.load_project_kanban()` for any kanban read | Call `parse_kanban_frontmatter()` + `parse_kanban_tasks()` directly with custom path | Phase 1 design | `load_project_kanban()` is hardwired to `repos/`; skill uses `repos-local/` |
| CI `--depth=1` HTTPS clone | Full SSH clone for `repos-local/` | Phase 1 design | Phase 2 needs full git history for activity mining |
| `repos/` (CI runtime, gitignored) | `repos-local/` (skill runtime, also gitignored) | Phase 1 design | Both dirs gitignored; `repos-local/` must be added to `.gitignore` |

**Deprecated/outdated:**

- `utils.load_all_project_data()`: Reads from `repos/discovered.txt` + `repos/` — both CI artifacts. Not usable from the skill.
- `utils.load_projects()`: Reads `repos/discovered.txt`. Not relevant; skill enumerates `repos-local/` directly.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SKILL.md frontmatter fields (`name`, `description`, `allowed-tools`) match the current Claude Code skills spec | Code Examples — SKILL.md | SKILL.md may not be recognized or may trigger incorrectly; verify against official docs before writing |
| A2 | SSH auth to `git@github.com:Katty-Fashion/` works without a passphrase for bootstrap clone | Pattern 6 — Clone Bootstrap | `git clone` hangs or fails; user must configure SSH key |
| A3 | `tech_brainstorming` repo exists in the `katty-fashion` org on GitHub (not found locally, not in discovered.txt) | Tracked Set | Bootstrap clone fails; planner needs a fallback [WARN] path |

---

## Open Questions

1. **Skill placement: `.claude/skills/` vs `.agents/skills/`**
   - What we know: `.claude/` is gitignored at line 69. `.agents/` does NOT exist yet and is NOT gitignored. Both are valid project skill discovery paths per the GSD system.
   - What's unclear: Which path the user prefers. Option A (`.claude/`) requires modifying `.gitignore`. Option B (`.agents/`) requires no gitignore change but the dir doesn't match the CONTEXT.md locked decision.
   - Recommendation: The planner should default to Option A (`.claude/` per the locked decision) and include a Wave 0 task to update `.gitignore` to fine-grained exclusions before creating any skill files.

2. **Already-present local repos (R3-AAS, ai-rise-options) vs. `repos-local/`**
   - What we know: R3-AAS at `/Users/machina/Dev/R3-AAS` and ai-rise-options at `/Users/machina/Dev/ai-rise-options` are existing full clones with SSH remotes. They are NOT under `repos-local/`.
   - What's unclear: Should bootstrap symlink these into `repos-local/` (fast, no duplication) or clone them fresh (consistent, self-contained)?
   - Recommendation: Clone fresh into `repos-local/` per the locked decision. The existing checkouts at `~/Dev/R3-AAS` etc. remain untouched; `repos-local/` is the skill's private space.

3. **`tech_brainstorming` org existence**
   - What we know: Not found locally; not in `repos/discovered.txt` snapshot on disk.
   - What's unclear: Whether it exists in `katty-fashion` org on GitHub.
   - Recommendation: Bootstrap should [WARN] gracefully on clone failure for any missing repo. The plan must include this skip path.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | repo_enum.py, bootstrap.py | YES | 3.9.6 | — |
| pyyaml | utils.py import (parsers) | YES | 6.0.3 | — |
| git | All git subprocess calls | YES | 2.28.0 | — |
| SSH to github.com | Bootstrap clone | [ASSUMED] | — | Provide clone URL as HTTPS + KF_PAT if SSH fails |
| R3-AAS local clone | repos-local/ seed (existing checkout at ~/Dev/R3-AAS) | YES | main branch | Clone fresh if not using existing |
| ai-rise-options local clone | repos-local/ seed (existing checkout at ~/Dev/ai-rise-options) | YES | master branch | Clone fresh |
| kf-be-platform local clone | repos-local/ — NOT present locally | NO | — | Bootstrap clones |
| kf-fe-platform local clone | repos-local/ — NOT present locally | NO | — | Bootstrap clones |
| kf-platform local clone | repos-local/ — NOT present locally | NO | — | Bootstrap clones |
| tech_brainstorming local clone | repos-local/ — NOT found locally or in discovered.txt | [ASSUMED MISSING] | — | Bootstrap attempts clone; [WARN] on failure |

**Missing dependencies with no fallback:** None — all git ops are non-fatal; bootstrap [WARN]s on clone failure.

**Missing dependencies with fallback:** kf-be-platform, kf-fe-platform, kf-platform, tech_brainstorming — bootstrap clones them.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 1 |
|-----------|-------------------|
| Python 3.9+ | All skill code targets 3.9; type hints use `list[dict]` not `List[dict]` (3.9+ native) |
| `snake_case.py` for scripts | Skill modules: `repo_enum.py`, `bootstrap.py` |
| `print(f"Warning: ...")` for non-fatal issues | All skip/warn paths use this prefix format |
| `[LABEL]` text pills, no emojis | Log lines use `[INFO]`, `[WARN]`, `[ERROR]` pills |
| Never add a second kanban parser | Enforced by one-parser constraint; import `utils.parse_kanban_*` only |
| Never commit `repos/` | `repos-local/` must be added to `.gitignore` before any content goes there |
| Skill runs locally; CI stays self-contained | Phase 1 adds zero CI dependency; no edits to `aggregate.yml` |
| External writes batch-confirmed once | Not applicable Phase 1 (read-only); noted for Phases 3+ |
| `SCREAMING_SNAKE_CASE` for module-level constants | e.g., `REPOS_LOCAL_DIR`, `SKILL_DIR`, `KF_ORG` |
| `_` prefix for private helpers | Internal git wrapper function: `_run_git()` |

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: local codebase] `scripts/utils.py` — Full source read; all exported functions and constants documented; path arithmetic verified by shell test 2026-06-04
- [VERIFIED: local codebase] `scripts/aggregator.py` lines 102-109 — Task count logic verified; parity check semantics confirmed
- [VERIFIED: local codebase] `scripts/discover.py` — Clone pattern reference; HTTPS vs SSH comparison
- [VERIFIED: local codebase] `.gitignore` line 69 — `.claude/` blanket exclusion confirmed; negation limitation verified by live test
- [VERIFIED: local codebase] `templates/kanban.md` and `templates/.github/workflows/notify-kf-cpto.yml` — Both exist; used by bootstrap seeding
- [VERIFIED: local codebase] `.planning/config.json` — `nyquist_validation: false`; no Validation Architecture section needed

### Secondary (MEDIUM confidence)

- [VERIFIED: local codebase] Live git operations against `/Users/machina/Dev/R3-AAS` and `/Users/machina/Dev/ai-rise-options` — Remote URL format, branch detection, fetch mechanics all tested 2026-06-04
- [CITED: .planning/research/STACK.md] Claude Code skills structure: SKILL.md frontmatter, `allowed-tools`, `disable-model-invocation`, `context: fork` — prior research from 2026-06-04 referencing official docs

### Tertiary (LOW confidence)

- [ASSUMED] `tech_brainstorming` repo exists in katty-fashion org — not found locally; needs verification via `gh repo view katty-fashion/tech_brainstorming`
- [ASSUMED] SSH auth works without passphrase for bootstrap clone — typical for development machines but not verified programmatically

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib; no new deps; pyyaml version confirmed live
- Architecture: HIGH — all patterns verified against live codebase and actual git repos
- Pitfalls: HIGH — all derived from live code inspection and verified experiments
- Gitignore: HIGH — negation behavior verified by live test

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (stable domain — gitignore behavior, subprocess git, utils.py API all highly stable)
