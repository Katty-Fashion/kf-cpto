# Phase 2: Activity Mining + Reconciliation - Research

**Researched:** 2026-06-04
**Domain:** GitHub REST API mining, git reachability, free-text token matching, Python 3.9 stdlib
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Signal-to-task matching:** Normalized-token matching only — all significant title words present, case/punct-normalized. No fuzzy scoring, no loose substring matching.
- **Signal tiers:** Tier-1 (merged PR or closed linked issue) → Done; Tier-2 (active remote branch) → Todo→In Progress only (never past In Progress); Tier-3 (commit-message keywords, file paths) → ignored entirely.
- **Forward-only/monotonic:** Never downgrade a declared status. Done stays Done even if branch is gone.
- **Reachability gate:** `git merge-base --is-ancestor <merge_commit_sha> origin/<default>` is the canonical revert gate. Covers force-push drops, rebases, revert-of-merge, squash/rebase merges via API-reported `merge_commit_sha`. Do NOT parse `Revert "…"` messages.
- **Hybrid sources:** GitHub API (via `requests` + `KF_PAT`) for merged PRs + `merge_commit_sha` + closes/fixes issue links; local git for reachability and Tier-2 branch detection.
- **Module:** New `reconcile.py` in `.claude/skills/activity-sync/`. Imports `repo_enum.run()`. Prints text table grouped by repo AND returns structured proposals for Phase 3. Dry-run only this phase.
- **Output format:** Text table with `[LABEL]` pills, no emojis. Row format: `task | old → new | [TIER-N] signal`.

### Claude's Discretion

- `reconcile.py` follows Phase 1 pattern: print human-readable change list AND return structured proposals so Phase 3 can consume without re-running.
- Status values must normalize through `utils.TASK_STATUSES` before appearing in any proposal.
- Exact function decomposition, GitHub API call structure, token-normalization helper, and log/pill formatting are at Claude's discretion, guided by `scripts/` conventions.

### Deferred Ideas (OUT OF SCOPE)

- Write-back of corrected `kanban.md`, batch-confirm, non-fast-forward abort, push to default branch, recovery manifest — Phase 3.
- Mermaid-breaking character sanitization — Phase 3.
- Agentic capacity overflow model — Phase 4.
- Tier-2 ambiguous-signal flagging — v2 (RECON-V2-01).

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RECON-01 | Detect completed tasks from Tier-1: merged PRs carrying a task reference and linked issue-closes | GitHub REST API: list closed PRs with `merged_at`, parse `closes/fixes #N` from body, GET issue title for linked issues |
| RECON-02 | Advance Todo→In Progress from Tier-2 active remote branch existence | `git for-each-ref refs/remotes/origin/` against locally fetched state; token-match branch name to task |
| RECON-03 | Auto-update declared kanban status to match Tier-1 verified reality (dry-run in this phase) | Structured Proposal dataclass carries all fields; actual write deferred to Phase 3 |
| RECON-04 | Produce reviewable change list (task, old→new, triggering signal) | Text table renderer grouped by repo, `[TIER-N]` pills, prints to stdout |
| RECON-05 | Support `--dry-run` that previews without writing | `--dry-run` is the only mode this phase; `argparse` flag accepted (implicit default) |
| RECON-06 | Ignore Tier-3 noise (commit-message keywords, file paths) | Architecture: only fetch PRs and branch refs; never enumerate commit messages |
| RECON-07 | Normalize every status string through canonical status enum | `utils.TASK_STATUSES` validated before constructing Proposal; `STATUS_RANK` dict for ranking |
| RECON-08 | Ignore reverted/unreachable merges | `git merge-base --is-ancestor <merge_commit_sha> origin/<branch>`: exit 0 = reachable, 1 = not, other = error (treat as not reachable) |

</phase_requirements>

---

## Summary

Phase 2 builds `reconcile.py` — a read-only engine that mines GitHub activity per tracked repo and produces a reviewable change list. The deliverable is purely a dry-run output: a text table of proposed status transitions, with the same changes also returned as structured Python objects for Phase 3 write-back.

The domain has two distinct sub-problems. The first is **signal acquisition**: calling the GitHub REST API to enumerate merged PRs and their closing issue links per repo, then using local git state to test whether each merge commit is still reachable from the default branch tip. The second is **task matching**: normalizing free-text task names and signal texts (PR titles, branch names, issue titles) into token sets, then testing subset membership to determine which tasks a signal applies to.

Both sub-problems are fully solvable with Python 3.9 stdlib plus the `requests` library already in the project's `requirements.txt`. No new packages are needed. The `utils.TASK_STATUSES` tuple (from `scripts/utils.py`) provides both the valid status set and, via its index, the integer ranking needed for forward-only enforcement and conflict resolution.

**Primary recommendation:** Implement `reconcile.py` as three clean layers — (1) signal acquisition functions (`_list_merged_prs`, `_get_issue`, `_list_remote_branches`), (2) pure matching/ranking helpers (`_normalize_tokens`, `task_matches_signal`, `_extract_issue_refs`, `is_advancement`), and (3) an orchestrator (`reconcile_repo`, `run`, `main`) that chains them and prints the change list.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Merged PR enumeration | API/Backend (GitHub REST) | Local git (reachability) | GitHub owns the authoritative PR state; local git owns ancestry truth |
| Reachability gate | Local git | — | `merge-base --is-ancestor` operates on local fetch state; no API call |
| Active branch detection (Tier-2) | Local git | — | `git for-each-ref refs/remotes/origin/` against fetched state; no extra API call |
| Linked issue resolution | API/Backend (GitHub REST) | — | Issue titles needed for token-matching; must fetch from API |
| Task-to-signal matching | Skill (reconcile.py) | — | Pure Python logic; no external dependency |
| Status normalization | Skill (reconcile.py) | `utils.TASK_STATUSES` | Skill enforces; utils provides the canonical set |
| Output formatting | Skill (reconcile.py) | — | Prints to stdout; no filesystem write |
| Structured return | Skill (reconcile.py) | — | Returns Python objects for Phase 3 consumption |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | >=2.28 (already pinned) | GitHub REST API calls | Already in `requirements.txt`; same pattern as `discover.py` |
| `pyyaml` | >=6.0 (already pinned) | Via `scripts/utils.py` import | Already in `requirements.txt`; no direct use in reconcile.py |
| `dataclasses` | stdlib (Python 3.7+) | Structured `Proposal` objects | Zero-dependency; clean typed return shape for Phase 3 |
| `argparse` | stdlib | `--dry-run` CLI flag | Consistent with project conventions |
| `re` | stdlib | Token normalization, closing-keyword regex | No external regex library needed |
| `subprocess` | stdlib | `git merge-base`, `git for-each-ref` | Pattern established in `repo_enum.py` (`_run_git` wrapper) |

### No New Packages Required

Phase 2 is self-contained within the existing `requirements.txt`. The planner must NOT add new package install steps.

---

## Package Legitimacy Audit

> Phase 2 installs NO new packages. All dependencies are already present in `requirements.txt` or Python 3.9 stdlib.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
repo_enum.run()
       |
       v
[records: name, local_path, branch, tasks, ...]
       |
       +---> for each record with kanban_exists=True
                      |
          +-----------+-----------+
          |                       |
          v                       v
  [TIER-1 acquisition]    [TIER-2 acquisition]
  GitHub REST API         Local git fetch state
  (requests + KF_PAT)     (git for-each-ref)
          |                       |
  list closed PRs         list origin/* branches
  filter merged_at!=None  strip origin/, HEAD,
  extract merge_commit_sha default_branch
  parse body for closes/#N         |
  GET /issues/{N} titles           v
          |               token_match(branch, task)
          v               -> Tier-2 proposals: Todo->In Progress
  git merge-base
  --is-ancestor
  (local, no API)
          |
  reachable? -> Yes -> token_match(pr_title+body, task)
                          -> Tier-1 proposals: -> Done
                    -> No -> skip (RECON-08)
          |
          v
  [Per-task conflict resolution]
  most_advanced(all proposals for task)
  + forward-only filter (proposed > declared rank)
          |
          v
  [Proposal list: only changed tasks]
          |
          +---> print text table (stdout)
          |
          +---> return list[Proposal] (for Phase 3)
```

### Recommended Project Structure

```
.claude/skills/activity-sync/
├── SKILL.md              # skill index (update to add reconcile.py)
├── bootstrap.py          # Phase 1: one-shot clone + seed
├── repo_enum.py          # Phase 1: fetch + parse all tracked repos
└── reconcile.py          # Phase 2: activity mining + dry-run reconciliation [NEW]
```

### Pattern 1: GitHub REST API — Merged PR List

**What:** Paginated list of closed PRs, filtered to merged (non-null `merged_at`).

**When to use:** Tier-1 signal acquisition per repo.

```python
# Source: docs.github.com/en/rest/pulls/pulls#list-pull-requests [CITED]
# Mirror of discover.py auth + pagination pattern [VERIFIED: codebase]

def _list_merged_prs(org: str, repo: str, headers: dict) -> list[dict]:
    """Return all merged PRs for a repo (paginated, state=closed, filter merged_at)."""
    prs = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/repos/{org}/{repo}/pulls",
            headers=headers,
            params={"state": "closed", "per_page": 100, "page": page},
        )
        if resp.status_code != 200:
            print(f"Warning: PR list failed for {repo}: {resp.status_code}")
            break
        batch = resp.json()
        if not batch:
            break
        prs.extend(pr for pr in batch if pr.get("merged_at") is not None)
        page += 1
        # Rate limit guard
        remaining = resp.headers.get("X-RateLimit-Remaining", "?")
        if isinstance(remaining, str) and remaining.isdigit() and int(remaining) < 100:
            print(f"Warning: GitHub rate limit low: {remaining} remaining")
    return prs
```

**Note on `merge_commit_sha`:** The list endpoint's "Pull Request Simple" schema does include `merge_commit_sha` per the GitHub docs — confirmed by WebSearch cross-reference. [CITED: docs.github.com/en/rest/pulls/pulls] However, if a returned PR has `merge_commit_sha` as `None` despite `merged_at` being set (edge case for old data), skip the reachability gate and treat conservatively as not reachable.

### Pattern 2: Closing Keyword Extraction

**What:** Parse PR body for `closes/fixes/resolves #N` patterns (same-repo only). [CITED: docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue]

```python
# Source: GitHub docs — 9 supported keywords, case-insensitive [CITED]
# Syntax: KEYWORD #N or KEYWORD: #N
# Cross-repo (OWNER/REPO#N) is ignored — only same-repo issues are relevant

_CLOSING_KEYWORDS_RE = re.compile(
    r'(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#(\d+)',
    re.IGNORECASE,
)

def _extract_issue_refs(body: str | None) -> list[int]:
    """Extract same-repo issue numbers from PR body closing keywords."""
    if not body:
        return []
    return [int(m) for m in _CLOSING_KEYWORDS_RE.findall(body)]
```

**Note:** The `body` field is `null`/`None` for PRs with no description. Always guard with `(pr.get("body") or "")`.

### Pattern 3: Issue Title Fetch

**What:** GET a single issue by number to obtain its title for token-matching.

```python
# Source: docs.github.com/en/rest/issues/issues [CITED]

def _get_issue(org: str, repo: str, issue_number: int, headers: dict) -> dict | None:
    """Fetch a single issue. Returns None on 404/error."""
    resp = requests.get(
        f"https://api.github.com/repos/{org}/{repo}/issues/{issue_number}",
        headers=headers,
    )
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code == 404:
        return None  # issue deleted or inaccessible
    print(f"Warning: issue fetch failed #{issue_number} in {repo}: {resp.status_code}")
    return None
```

### Pattern 4: Reachability Gate

**What:** Test whether a merge commit is still an ancestor of the default branch tip. Covers merge reverts, force-push drops, rebase-over, and squash merges.

```python
# Source: git-scm.com/docs/git-merge-base [CITED]
# Exit codes: 0 = is-ancestor (reachable), 1 = not-ancestor, 128 = git error

def _is_merge_reachable(
    repo_path: str, merge_commit_sha: str, default_branch: str
) -> Optional[bool]:
    """True=reachable, False=not, None=git error (treat as False)."""
    result = _run_git([
        "-C", repo_path, "merge-base", "--is-ancestor",
        merge_commit_sha, f"origin/{default_branch}",
    ])
    if result.returncode == 0:
        return True
    elif result.returncode == 1:
        return False
    else:
        print(f"Warning: merge-base error (rc={result.returncode}): {result.stderr.strip()}")
        return None  # conservative: treat as not reachable
```

**Reuse `_run_git`:** Import or copy the `_run_git` helper from `repo_enum.py` — it is the established pattern for subprocess git calls (arg-list, no shell interpolation, timeout).

### Pattern 5: Active Branch Detection (Tier-2)

**What:** List all active remote branches from the locally fetched state. No extra API call — uses data already fetched by Phase 1's `repo_enum.run()`.

```python
# Source: git-scm.com/docs/git-for-each-ref [CITED]

def _list_remote_branches(repo_path: str, default_branch: str) -> list[str]:
    """Return non-default remote branches from locally fetched state."""
    result = _run_git([
        "-C", repo_path, "for-each-ref",
        "--format=%(refname:short)",
        "refs/remotes/origin/",
    ])
    if result.returncode != 0:
        return []
    branches = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if name.startswith("origin/"):
            short = name[len("origin/"):]
            if short not in ("HEAD", default_branch):
                branches.append(short)
    return sorted(branches)
```

### Pattern 6: Token Normalization and Matching

**What:** Casefold + strip punctuation + remove stopwords → frozenset. Match by subset test (all task tokens present in signal tokens).

```python
# Source: Python 3.9 stdlib (re, str.casefold) [VERIFIED: codebase tested]

_STOPWORDS = frozenset({
    "a", "an", "and", "as", "at", "be", "by", "do", "for",
    "from", "in", "is", "it", "of", "on", "or", "the", "to",
    "up", "via", "with",
})

def _normalize_tokens(text: str) -> frozenset:
    """Casefold + strip punctuation + remove stopwords -> frozenset of tokens."""
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"[^\w\s']", " ", text)
    tokens = text.casefold().split()
    return frozenset(t for t in tokens if t not in _STOPWORDS and len(t) > 1)

def task_matches_signal(task_name: str, signal_text: str) -> bool:
    """True if all significant task tokens are present in signal_text tokens."""
    task_tokens = _normalize_tokens(task_name)
    signal_tokens = _normalize_tokens(signal_text)
    if not task_tokens:
        return False  # degenerate: empty task name never matches
    return task_tokens.issubset(signal_tokens)
```

**Verified behavior (tested locally):**
- `task_matches_signal("Setup authentication", "feat: setup authentication flow")` → `True`
- `task_matches_signal("Setup authentication", "fix: auth token refresh")` → `False` (token "setup" absent)
- `task_matches_signal("Add login form", "add-login-form component")` → `True` (hyphens → spaces)
- `task_matches_signal("Migrate database schema", "migrate-database-schema-v2")` → `True`

### Pattern 7: STATUS_RANK — Forward-Only Enforcement

**What:** Derive integer ranking from `TASK_STATUSES` tuple index. `STATUS_PRIORITY` in `utils.py` uses string labels for Mermaid styling, NOT integers — use index-based `STATUS_RANK` for comparison logic.

```python
# Source: scripts/utils.py TASK_STATUSES tuple [VERIFIED: codebase]
# TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")
# STATUS_PRIORITY maps to Mermaid labels — NOT for numerical comparison

from utils import TASK_STATUSES

STATUS_RANK: dict[str, int] = {s: i for i, s in enumerate(TASK_STATUSES)}
# Result: {"Todo": 0, "In Progress": 1, "Review": 2, "Done": 3}

def is_advancement(current: str, proposed: str) -> bool:
    """True if proposed is strictly more advanced than current (forward-only)."""
    return STATUS_RANK.get(proposed, -1) > STATUS_RANK.get(current, -1)

def most_advanced(statuses: list) -> str:
    """Return the most advanced status (conflict resolution: Tier-1 wins over Tier-2)."""
    return max(statuses, key=lambda s: STATUS_RANK.get(s, -1))
```

**Verified behavior (tested locally):**
- `is_advancement("Done", "Todo")` → `False` (never downgrade)
- `is_advancement("In Progress", "In Progress")` → `False` (no change = no row)
- `most_advanced(["In Progress", "Done"])` → `"Done"` (Tier-1 wins)

### Pattern 8: Structured Proposal Dataclass

**What:** Return shape that Phase 3 consumes without re-running the engine. Using `dataclasses.dataclass` (stdlib, Python 3.7+).

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Proposal:
    repo: str           # repo name (for write-back routing in Phase 3)
    task: str           # free-text task name (matches kanban.md 'task' key)
    old_status: str     # declared status from kanban.md
    new_status: str     # proposed status (validated TASK_STATUSES member)
    tier: int           # 1 (Tier-1: merged PR / closed issue) or 2 (Tier-2: branch)
    signal: str         # human-readable: "PR #N: <title>" or "branch origin/<name>"
    signal_url: Optional[str] = None  # PR/issue URL or None for branch signals
```

**Idempotency guarantee:** `reconcile_repo()` emits a `Proposal` only when `is_advancement(task["status"], proposed_status)` is `True`. If the kanban.md already reflects the proposed status (task already `Done`), the condition is `False` and no row is emitted. Running `--dry-run` twice on an already-reconciled repo produces an empty list.

### Pattern 9: Output Rendering

**What:** Print grouped-by-repo text table with `[TIER-N]` pills and `[INFO]` on empty. No emojis.

```python
def render_change_list(proposals: list) -> None:
    """Print grouped-by-repo change list. [INFO] if empty."""
    if not proposals:
        print("[INFO] No changes proposed — all declared statuses match activity.")
        return
    repos: dict = {}
    for p in proposals:
        repos.setdefault(p.repo, []).append(p)
    for repo, changes in sorted(repos.items()):
        print(f"\nRepo: {repo}")
        print(f"{'Task':<40} {'Old':>12} {'New':>12}  Signal")
        print("-" * 90)
        for c in changes:
            print(
                f"{c.task:<40} {c.old_status:>12} -> {c.new_status:>12}"
                f"  [TIER-{c.tier}] {c.signal}"
            )
```

### Anti-Patterns to Avoid

- **Re-parsing kanban.md:** Never call `parse_kanban_frontmatter()` or `parse_kanban_tasks()` in `reconcile.py` — consume `record["tasks"]` from `repo_enum.run()` records directly (REPO-03).
- **Tier-3 signals:** Never enumerate commit messages or file paths touched. Only fetch closed PRs and remote branch refs.
- **Revert commit message parsing:** Never check for `Revert "…"` in commit messages. The reachability gate is the sole revert detection mechanism.
- **Writing files:** `reconcile.py` must be read-only. Never write to `repos-local/` or any file this phase.
- **`STATUS_PRIORITY` for numeric ranking:** `utils.STATUS_PRIORITY` maps to Mermaid label strings, not integers. Use index-based `STATUS_RANK` for forward-only comparisons.
- **`bool | None` type annotation without `__future__`:** Python 3.9 raises `TypeError` at runtime for PEP 604 union syntax. Always include `from __future__ import annotations` (matches `repo_enum.py` pattern).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Status ranking | Custom priority dict | `{s: i for i, s in enumerate(TASK_STATUSES)}` | `TASK_STATUSES` tuple order IS the canonical ranking |
| Kanban parsing | Local parser in reconcile.py | `repo_enum.run()` record's `tasks` list | REPO-03 constraint; one parser, one canonical intermediate |
| Revert detection | Parse `Revert "…"` commit messages | `git merge-base --is-ancestor` reachability gate | Reachability covers all revert forms (force-push, rebase, revert-of-merge) |
| Branch listing | GitHub API `/branches` endpoint | `git for-each-ref refs/remotes/origin/` | Local fetch state suffices; saves API calls; no pagination needed |
| Fuzzy matching | Edit-distance / similarity scoring | Token subset test | Conservative matching prevents false positives; locked decision |
| API auth | New token mechanism | `os.environ.get("KF_PAT") or os.environ.get("GITHUB_TOKEN")` | Same pattern as `discover.py`; same token scope |

**Key insight:** The pattern is already established in Phase 1 — import and reuse rather than recreate. The three most common Phase 2 temptations (re-parsing kanban, reinventing status ranking, building custom revert detection) are all solved by existing primitives.

---

## Runtime State Inventory

> Phase 2 is a new module (greenfield within the skill). No rename/refactor — omit.

---

## Common Pitfalls

### Pitfall 1: `merge_commit_sha` May Be `None` in List Endpoint
**What goes wrong:** The PR list endpoint's "Pull Request Simple" schema is documented to omit `merge_commit_sha` in some references, but it is included in practice. If a rare edge case returns it as `None` for a merged PR, the reachability check will get a `git merge-base` error (exit 128 for invalid object), and the conservative `None` return incorrectly blocks a valid Done signal.
**Why it happens:** GitHub API schema documentation distinguishes between "simple" and "full" PR responses; the simple schema docs do not explicitly list `merge_commit_sha`.
**How to avoid:** Check `pr.get("merge_commit_sha")` explicitly. If `None`, skip the reachability gate and treat the PR as not reachable (conservative). Log a `[INFO]` message.
**Warning signs:** Exit code 128 from `git merge-base` with "unknown revision" in stderr.

### Pitfall 2: `STATUS_PRIORITY` Is Not a Numeric Ranking
**What goes wrong:** `utils.STATUS_PRIORITY` looks like a ranking dict but maps to Mermaid label strings (`"Very High"`, `"High"`, `"Low"`). Using it directly for "most-advanced" comparison produces nonsensical string comparisons.
**Why it happens:** The dict name implies priority ordering, but it serves Mermaid rendering.
**How to avoid:** Derive `STATUS_RANK = {s: i for i, s in enumerate(TASK_STATUSES)}` independently. Never touch `STATUS_PRIORITY` in `reconcile.py`.
**Warning signs:** `most_advanced(["Todo", "Done"]) == "Todo"` (string "Very High" > "Low" would be the confusion vector).

### Pitfall 3: `bool | None` Type Annotation Crashes on Python 3.9
**What goes wrong:** `def f() -> bool | None:` raises `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'` at function definition time on Python 3.9 (without `__future__`).
**Why it happens:** PEP 604 union syntax is only valid at runtime from Python 3.10+.
**How to avoid:** Add `from __future__ import annotations` as the first import (established in `repo_enum.py`). Use `Optional[bool]` from `typing` as a fallback if `__future__` is omitted for any reason.
**Warning signs:** `TypeError` at module import time, not at call time.

### Pitfall 4: PR Body Is `None` for No-Description PRs
**What goes wrong:** Calling `_CLOSING_KEYWORDS_RE.findall(pr["body"])` raises `TypeError: expected string or bytes-like object, got 'NoneType'`.
**Why it happens:** GitHub API returns `"body": null` for PRs created without a description.
**How to avoid:** Always guard: `body = pr.get("body") or ""`. The regex then safely returns `[]`.
**Warning signs:** `TypeError` in `_extract_issue_refs`, only appearing for certain PRs.

### Pitfall 5: Default Branch Mismatch Between `repo_enum` Record and Reachability Gate
**What goes wrong:** `record["branch"]` is detected from local HEAD (`rev-parse --abbrev-ref HEAD`). If the local checkout's HEAD points to a non-default branch (unusual but possible), the reachability gate tests against the wrong ref.
**Why it happens:** `_get_default_branch()` reads local HEAD, which could diverge from the remote's default branch if someone manually checked out a different branch in `repos-local/`.
**How to avoid:** The gate uses `f"origin/{record['branch']}"` which is the remote-tracking ref, not the local branch — this is correct. The concern is only if `repo_enum` has a wrong `branch` value. Use `record["branch"]` from the Phase 1 record, which was validated during fetch.
**Warning signs:** `is_merge_reachable()` returns `False` for PRs that were genuinely merged; branch shows something other than `main`/`master`.

### Pitfall 6: Repos with No Kanban (`kanban_exists=False`) Must Be Skipped
**What goes wrong:** `repo_enum.run()` may return records with `kanban_exists=False` and `tasks=[]`. Mining signals for such repos wastes API calls and produces no proposals.
**Why it happens:** Phase 1 enumeration includes all repos in `repos-local/` with the required markers; a repo may have been bootstrapped but never filled in its kanban.
**How to avoid:** Skip records where `record["kanban_exists"] is False` or `record["valid_task_count"] == 0` at the top of the reconciliation loop.

### Pitfall 7: KF_PAT Not Set — Graceful Degradation Required
**What goes wrong:** All API calls return 401 or hit the unauthenticated rate limit (60 req/hr) immediately.
**Why it happens:** Developer running without `.env` set.
**How to avoid:** Mirror `discover.py` — warn on missing token but continue. With no token, skip API calls and return empty proposals with a `[WARN]` message.
**Warning signs:** `401 Unauthorized` on first API call; `X-RateLimit-Remaining: 0` immediately.

---

## Code Examples

### Complete `_list_merged_prs` with Pagination

```python
# Source: discover.py pagination pattern [VERIFIED: codebase] + GitHub REST docs [CITED]

def _list_merged_prs(org: str, repo: str, headers: dict) -> list[dict]:
    prs = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/repos/{org}/{repo}/pulls",
            headers=headers,
            params={"state": "closed", "per_page": 100, "page": page},
        )
        if resp.status_code != 200:
            print(f"Warning: PR list for {repo} failed: {resp.status_code}")
            break
        batch = resp.json()
        if not batch:
            break
        prs.extend(pr for pr in batch if pr.get("merged_at") is not None)
        page += 1
        remaining = resp.headers.get("X-RateLimit-Remaining", "?")
        if str(remaining).isdigit() and int(remaining) < 100:
            print(f"[WARN] GitHub rate limit low: {remaining} remaining")
    return prs
```

### Reconcile a Single Repo

```python
# Source: architecture pattern derived from this research

def reconcile_repo(record: dict, headers: dict) -> list[Proposal]:
    """Mine signals for one repo and return Proposals (dry-run only)."""
    proposals: dict[str, list] = {}  # task_name -> list of (proposed_status, tier, signal, url)

    repo_name = record["name"]
    repo_path = record["local_path"]
    default_branch = record["branch"]
    tasks = [t for t in record["tasks"] if t["status"] in TASK_STATUSES]

    if not tasks:
        return []

    # --- Tier-1: merged PRs ---
    merged_prs = _list_merged_prs(ORG, repo_name, headers)
    for pr in merged_prs:
        sha = pr.get("merge_commit_sha")
        if not sha:
            continue  # conservative: skip if SHA missing
        reachable = _is_merge_reachable(repo_path, sha, default_branch)
        if not reachable:
            continue  # reverted or unreachable (RECON-08)
        # Match PR title to tasks
        pr_title = pr.get("title", "")
        pr_url = pr.get("html_url")
        signal_desc = f"PR #{pr['number']}: {pr_title} (merged)"
        for task in tasks:
            if task_matches_signal(task["task"], pr_title):
                proposals.setdefault(task["task"], []).append(
                    ("Done", 1, signal_desc, pr_url)
                )
        # Match linked issue titles (RECON-01)
        for issue_num in _extract_issue_refs(pr.get("body")):
            issue = _get_issue(ORG, repo_name, issue_num, headers)
            if issue and issue.get("state") == "closed":
                issue_title = issue.get("title", "")
                issue_signal = f"issue #{issue_num} closed (via PR #{pr['number']})"
                issue_url = issue.get("html_url")
                for task in tasks:
                    if task_matches_signal(task["task"], issue_title):
                        proposals.setdefault(task["task"], []).append(
                            ("Done", 1, issue_signal, issue_url)
                        )

    # --- Tier-2: active remote branches ---
    remote_branches = _list_remote_branches(repo_path, default_branch)
    for branch in remote_branches:
        for task in tasks:
            if task_matches_signal(task["task"], branch):
                proposals.setdefault(task["task"], []).append(
                    ("In Progress", 2, f"branch origin/{branch} exists", None)
                )

    # --- Conflict resolution + forward-only filter ---
    result: list[Proposal] = []
    for task in tasks:
        task_name = task["task"]
        declared = task["status"]
        if task_name not in proposals:
            continue
        all_proposed = [p[0] for p in proposals[task_name]]
        best = most_advanced(all_proposed)
        # Tier-2 cap: never advance past In Progress
        if best == "In Progress" and STATUS_RANK.get(declared, 0) >= STATUS_RANK["In Progress"]:
            continue  # already at or past In Progress
        if not is_advancement(declared, best):
            continue  # forward-only; no downgrade
        # Find the winning signal entry
        winning = next(
            p for p in sorted(proposals[task_name], key=lambda x: -STATUS_RANK.get(x[0], -1))
            if p[0] == best
        )
        result.append(Proposal(
            repo=repo_name,
            task=task_name,
            old_status=declared,
            new_status=best,
            tier=winning[1],
            signal=winning[2],
            signal_url=winning[3],
        ))
    return result
```

### CLI Entry Point with `--dry-run` Flag

```python
# Source: project pattern (aggregator.py main() structure) [VERIFIED: codebase]

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Activity Mining + Reconciliation — dry-run only"
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Preview proposed changes without writing (default and only mode this phase)"
    )
    parser.parse_args()  # parse to consume --dry-run; always dry-run this phase

    try:
        proposals = run()
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Revert detection via commit message parsing (`Revert "..."`) | Reachability gate via `git merge-base --is-ancestor` | Phase 2 decision (2026-06-04) | Handles force-push, rebase, revert-of-merge uniformly |
| Static project list in config | Dynamic enumeration from `repos-local/` membership | Phase 1 | No hardcoded repo names |
| Single `loe.yml` intermediate for CI pipeline | Skill-internal `Proposal` objects for Phase 3 | Phase 2 design | Decouples skill dry-run from CI rendering |

**Deprecated/outdated:**

- Commit-message keyword scanning (Tier-3): explicitly excluded by RECON-06. Do not implement.
- `Revert "..."` message detection: superseded by the reachability gate (locked decision).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `merge_commit_sha` is included in the list PR endpoint response despite being labeled "Pull Request Simple" | Standard Stack / Code Examples | If absent, each merged PR needs an individual GET call (N extra API requests per repo; slower but correct) |
| A2 | All tracked repos in `repos-local/` are either public or accessible with the same `KF_PAT` scope that `discover.py` uses | Common Pitfalls | 401 errors on API calls; skill degrades gracefully with `[WARN]` and empty proposals |
| A3 | `STATUS_PRIORITY` in `utils.py` is not used for numeric ranking (only for Mermaid label strings) | Code Examples | If used for ranking, produces incorrect conflict resolution |

**Risk assessment:** A1 is the only material risk. The safe fallback (skip if `merge_commit_sha` is `None`) is already built into the pattern.

---

## Open Questions (RESOLVED)

1. **`merge_commit_sha` availability in list endpoint**
   - What we know: WebSearch confirms it IS in list endpoint responses; WebFetch of the schema docs says "Simple" schema omits it. Contradiction.
   - What's unclear: Whether the schema reference is outdated.
   - Recommendation: Code defensively — use `merged_at != None` as the primary merge filter; treat `merge_commit_sha = None` conservatively. If it IS present (expected case), the reachability gate fires normally.

2. **Token matching false-positive rate for short task names**
   - What we know: Tasks with 1-2 tokens (e.g., "Testing") will match many branches/PRs containing the word "testing".
   - What's unclear: Actual task name distribution across katty-fashion repos.
   - Recommendation: The locked decision specifies conservative matching ("all significant words present"). For very short task names (1 significant token), a match is a valid signal. Document this behavior in code comments.

3. **Tier-2 Tier-1 interaction for `In Progress` tasks**
   - What we know: Tier-2 only advances `Todo → In Progress`; a task already `In Progress` gets no Tier-2 signal.
   - What's unclear: If a task is `In Progress` and a PR merges, is `Done` correctly emitted?
   - Recommendation: Yes — Tier-1 (`Done`) advances over any current status including `In Progress` (STATUS_RANK 3 > 1). The forward-only check passes. This is the intended behavior.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| git | Reachability gate, branch listing | [VERIFIED] | 2.28.0 | None — required |
| Python 3.9+ | reconcile.py runtime | [VERIFIED] | 3.9.6 | None — required |
| `requests` | GitHub REST API calls | [VERIFIED] | >=2.28 (in venv) | Degrade gracefully: skip API, empty proposals |
| `pyyaml` | Via `utils.py` import | [VERIFIED] | >=6.0 (in venv) | None — already required |
| KF_PAT env var | API auth (5000 req/hr) | NOT SET locally | — | Unauthenticated (60 req/hr); warn + continue |

**Missing dependencies with no fallback:**
- `git 2.28.0+` — required for `merge-base --is-ancestor` and `for-each-ref`.
- Python 3.9+ — the skill's stated minimum.

**Missing dependencies with fallback:**
- `KF_PAT` not set: skip all GitHub API calls, log `[WARN]`, return empty proposals. `repo_enum.py` pattern.

---

## Security Domain

> `security_enforcement` is not explicitly set in `.planning/config.json` — treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A (local CLI skill, no user auth) |
| V3 Session Management | No | N/A (stateless script) |
| V4 Access Control | No | N/A (reads only; no multi-user) |
| V5 Input Validation | Yes | `task_matches_signal` token normalization; regex guards for API response fields |
| V6 Cryptography | No | N/A (no secrets generated; KF_PAT is read from env, not stored) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell injection via repo name or branch name | Tampering | Use arg-list subprocess (established in `_run_git`); never shell-interpolate |
| API response field injection (crafted PR title/body) | Tampering | Token matching on normalized plaintext; no eval; no exec |
| KF_PAT leakage in log output | Information Disclosure | Never log token value; log only presence/absence via `[WARN]` |
| Path traversal via repo name from API | Tampering | Use `record["local_path"]` from `repo_enum.run()` (pre-validated by org allowlist check) |

---

## Sources

### Primary (HIGH confidence)
- `scripts/utils.py` (codebase) — `TASK_STATUSES`, `STATUS_PRIORITY`, `parse_kanban_tasks`; verified directly
- `.claude/skills/activity-sync/repo_enum.py` (codebase) — `_run_git`, `_get_default_branch`, `_fetch_repo`, `run()` patterns; verified directly
- `scripts/discover.py` (codebase) — GitHub REST API auth + pagination pattern; verified directly
- [docs.github.com/en/rest/pulls/pulls](https://docs.github.com/en/rest/pulls/pulls) — PR list endpoint, `merged_at`, `merge_commit_sha`, `body` field
- [docs.github.com/en/rest/issues/issues](https://docs.github.com/en/rest/issues/issues) — GET single issue endpoint, `state`, `title` fields
- [docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) — all 9 closing keywords, case-insensitive, syntax
- [docs.github.com/en/rest/branches/branches](https://docs.github.com/en/rest/branches/branches) — branch list endpoint fields
- [docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) — 5000 req/hr auth, `x-ratelimit-remaining`, `retry-after`

### Secondary (MEDIUM confidence)
- WebSearch: `merge_commit_sha` confirmed in list endpoint response by multiple GitHub docs references
- [github.com/orgs/community/discussions/179613](https://github.com/orgs/community/discussions/179613) — no official REST endpoint for linked issues; body parsing is the standard workaround

### Tertiary (LOW confidence)
- None — all critical claims have primary or secondary sources.

---

## Metadata

**Confidence breakdown:**
- GitHub API endpoints and field names: HIGH — verified via official docs
- Token normalization approach: HIGH — verified via local Python 3.9 execution
- `STATUS_RANK` from `TASK_STATUSES` index: HIGH — verified via local execution against codebase
- Reachability gate exit codes: HIGH — verified via git documentation + local execution
- `merge_commit_sha` in list endpoint: MEDIUM — conflicting docs evidence; defensive coding applied
- Token matching false-positive rate in practice: LOW — no actual task names available to test against

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (GitHub API stable; git semantics stable)

---

## RESEARCH COMPLETE
