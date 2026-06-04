# Phase 3: Write-Back + Diagram Sanitization — Research

**Researched:** 2026-06-04
**Domain:** Python git automation / ruamel.yaml round-trip / Mermaid sanitization
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **ruamel.yaml**: Add `ruamel.yaml>=0.17` to `requirements.txt`. Round-trip mode preserves inline `#` comments, key order, and quoting. CI self-containment is preserved — CI never imports the skill.
- **Body edits only for status changes**: Task-table Status changes live in the markdown body, not frontmatter. Apply targeted string replacement of the Status cell for each Proposal's matched row.
- **AUTO-block markers do not appear in kanban.md**: validate_auto_blocks.py exit-0 check runs on `docs/` only — it is a post-write sanity assertion on Jekyll pages, not a kanban concern.
- **Re-read kanban.md fresh at write time** from `repos-local/{repo}/kanban.md`; Proposal carries no raw content.
- **Sanitize scope**: emojis + `: ( ) " # ; { } |` in task-table cell text only. Never frontmatter, prose, or HTML comments.
- **Readable substitution map**: `:` → ` -`, `"` → `'`, `|` → `/`, `;` → `,`, `( )` and `{ }` → dropped, `#` → dropped, emojis stripped.
- **Romanian diacritics preserved**: ă/â/î/ș/ț pass through unchanged — only the break-set + emoji ranges are touched.
- **Sanitization skill-side on write path only** this phase; aggregator-side second fence is deferred.
- **Push auth**: reconfigure each repo's origin to HTTPS+KF_PAT at push time, restore SSH URL after push.
- **Natural per-repo dispatch**: no `[skip ci]` on kanban commits — the dispatch is the point.
- **NO live push during autonomous build**: SC-1 (live push → CI → Pages deploy) is human-validated UAT.
- **Commit message**: `chore(kanban): reconcile task statuses from repo activity`
- **Single batch confirmation** before any push; zero per-repo prompts.
- **Conflict detection (WB-03)**: git fetch then behind/diverged check → `[CONFLICT]` abort-and-continue.
- **Recovery manifest (WB-05)**: per-run JSON in `.claude/skills/activity-sync/manifests/` (gitignored).
- **Idempotency (SC-4)**: byte-compare proposed content to current file; skip write+commit+push if identical.
- **New modules**: `writeback.py` (+ `sanitize.py` helper or inline function) in `.claude/skills/activity-sync/`.

### Claude's Discretion

- Module decomposition (separate `sanitize.py` vs inline function), manifest schema details, confirm-prompt wording — follow Phase 1/2 skill patterns.
- Throwaway-remote test harness shape — bare repo under `tempfile.mkdtemp()` or a fixture — at Claude's discretion as long as no live org push occurs.

### Deferred Ideas (OUT OF SCOPE)

- CAP-01..07: Agentic capacity overflow model — Phase 4.
- DIAG-V2-01: Aggregator-side second-fence sanitization — v2 / Phase 5.
- RECON-V2-01: Tier-2 ambiguous-signal human-decision flagging — v2.
- Two-way / real-time Sheets sync.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WB-01 | Write corrected `kanban.md` back to each tracked repo, preserving all non-task content (frontmatter comments, prose) | ruamel.yaml round-trip verified byte-identical for unmodified frontmatter; body edits are targeted string replacements |
| WB-02 | Batch-confirm all writes once before committing (never per-repo prompting) | Confirmed pattern: collect all proposals, print summary table, single y/N prompt, then push all |
| WB-03 | Abort a repo's write on non-fast-forward / divergence rather than clobbering | `git rev-list --count HEAD..origin/<branch>` verified with local bare repo test |
| WB-04 | Commit and push to each repo's correct default branch, triggering existing notify dispatch | Commit with KF Bot identity; push with HTTPS+KF_PAT; restore SSH URL after; branch from `record["branch"]` |
| WB-05 | Record a recovery manifest of what was written so partial-batch failure is recoverable | JSON schema designed; location `.claude/skills/activity-sync/manifests/{run_id}.json` (needs .gitignore entry) |
| DIAG-01 | Sanitize Mermaid-breaking characters from task content on ingest, before write | Substitution map and emoji-detection via unicodedata ranges verified Python 3.9 stdlib |
| DIAG-02 | Scope sanitization to task table only — preserve AUTO-block markers and Romanian diacritics | AUTO blocks not in kanban.md; Romanian U+0103/U+00E2/U+00EE/U+0219/U+021B all Ll category, below emoji ranges |
| DIAG-03 | Dashboard diagrams render without breaking after a skill run | sanitize_cell tested with representative Mermaid break inputs; idempotency verified |
</phase_requirements>

---

## Summary

Phase 3 implements the write-back half of the activity-sync skill: consuming `reconcile.run()` Proposals, writing corrected `kanban.md` files back to tracked repos, and pushing to trigger the existing `notify-kf-cpto.yml` → `kanban-updated` → `aggregate.yml` pipeline that re-renders the dashboard. The implementation requires one new library (ruamel.yaml for comment-preserving YAML round-trip) and two new skill modules (`sanitize.py` and `writeback.py`).

All core technical questions have been answered with working code verified against the actual project files. The ruamel.yaml round-trip is byte-identical for unmodified frontmatter. The status-cell replacement logic works for both 4-col and 6-col tables. Conflict detection via `git rev-list --count HEAD..origin/<branch>` works reliably. The sanitize pass is idempotent. No known blockers.

The live end-to-end push (SC-1) is explicitly deferred to human UAT. The autonomous build produces fully tested modules that exercise commit+push against a throwaway bare git remote.

**Primary recommendation:** Implement `sanitize.py` first (pure function, easily unit-tested), then `writeback.py` consuming it and `reconcile.run()`. Gate the write pass with a byte-comparison idempotency check before any git operation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| YAML frontmatter round-trip | Skill (local Python) | — | Runs only locally; CI never imports skill |
| Status-cell targeted replacement | Skill (local Python) | — | Operates on repos-local/ checkouts |
| Mermaid sanitization | Skill (write path) | — | Phase 3 is first fence; aggregator-side deferred to v2 |
| Conflict detection (fetch + behind check) | Skill (local git) | — | Per-repo, must run before each write |
| Batch-confirm prompt | Skill CLI | — | Single confirm at skill invocation |
| Commit + push | Skill → origin (HTTPS+KF_PAT) | — | Mirrors aggregate.yml pattern |
| Dispatch trigger | notify-kf-cpto.yml (per repo) | aggregate.yml (central) | Existing CI; skill triggers it naturally |
| Recovery manifest write | Skill (local) | .gitignore | Per-run JSON; never committed |
| Post-write sanity | validate_auto_blocks.py (docs/) | — | Checks Jekyll pages only, not kanban.md |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ruamel.yaml | `>=0.17` (0.19.1 current) | YAML round-trip preserving inline `#` comments and key order | Only YAML library that round-trips inline comments; PyPI since 2014, 273 releases [VERIFIED: PyPI registry] |
| subprocess (stdlib) | Python 3.9+ | git operations via arg-list (no shell=True) | Project-established `_run_git` pattern |
| re (stdlib) | Python 3.9+ | Frontmatter split regex; sanitize space collapse | No external regex needed |
| unicodedata (stdlib) | Python 3.9+ | Emoji codepoint range detection | Python 3.9 stdlib; no `regex` package needed |
| json (stdlib) | Python 3.9+ | Recovery manifest serialization | Standard |
| datetime (stdlib) | Python 3.9+ | Run ID timestamp (`strftime('%Y%m%dT%H%M%SZ')`) | Standard |
| tempfile (stdlib) | Python 3.9+ | Throwaway bare git remote for tests | Standard |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path (stdlib) | Python 3.9+ | File I/O, path construction | All file operations in skill modules |
| io.StringIO (stdlib) | Python 3.9+ | In-memory buffer for ruamel.yaml dump | Only needed for ruamel dump API |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ruamel.yaml | pyyaml | pyyaml does NOT preserve inline `#` comments on round-trip — confirmed in CONTEXT.md; not an option for WB-01 |
| ruamel.yaml | In-place string editing of frontmatter | Fragile; would need regex to locate and replace specific key values; breaks on multi-line values or indented structures |
| unicodedata ranges | `regex` package `\p{Emoji}` | `regex` is not stdlib and adds a dependency; unicodedata ranges cover all required emoji blocks verified against real emoji samples |
| `git rev-list --count` | `git merge-base --is-ancestor HEAD origin/<branch>` | Both detect "local behind origin"; `rev-list --count` returns the number of missing commits (more informative for log message) |

**Installation (add to requirements.txt and venv):**
```bash
pip install ruamel.yaml
# requirements.txt: add ruamel.yaml>=0.17
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| ruamel.yaml | PyPI | ~12 yrs (2014) | High (273 releases, widely adopted) | sourceforge.net/p/ruamel-yaml/ | slopcheck unavailable — manual verified | Approved [VERIFIED: PyPI registry] |

**Packages removed due to slopcheck [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** none

**slopcheck availability:** slopcheck was not installable in this environment. Manual verification performed:
- `ruamel.yaml` is a 12-year-old PyPI project with 273 releases, last updated 2026-01-02.
- Author: Anthon van der Neut (a.van.der.neut@ruamel.eu); source hosted on SourceForge.
- No postinstall script. No ecosystem confusion (Python-only package, no npm equivalent).
- `pip show ruamel.yaml` returns correct metadata. [VERIFIED: PyPI registry + manual inspection]

---

## Architecture Patterns

### System Architecture Diagram

```
reconcile.run()
  --> list[Proposal{repo, task, old_status, new_status}]
        |
        v
writeback.run(proposals, dry_run)
  |
  +-- batch confirm prompt (single y/N)
  |
  +-- for each repo with proposals:
  |     |
  |     +-- git fetch origin
  |     +-- conflict check: rev-list --count HEAD..origin/<branch>
  |     |     +-- count > 0 --> [CONFLICT] skip repo, record in manifest
  |     |
  |     +-- read fresh repos-local/{repo}/kanban.md
  |     +-- split_kanban() -> (frontmatter_str, body_str)
  |     +-- ruamel round-trip frontmatter (preserves # comments)
  |     +-- apply_status_changes(body_str, proposals_for_repo)
  |     +-- sanitize_body(body_str)  <-- sanitize.py
  |     +-- compare bytes to current file
  |     |     +-- identical --> [SKIP] record in manifest (idempotent)
  |     |
  |     +-- write file
  |     +-- git add kanban.md
  |     +-- git commit -m "chore(kanban): reconcile task statuses from repo activity"
  |     +-- save original_url = _get_remote_url()
  |     +-- git remote set-url origin https://<KF_PAT>@github.com/katty-fashion/{repo}.git
  |     +-- git push origin HEAD:<branch>
  |     +-- git remote set-url origin <original_url>  (restore, in finally)
  |     +-- record manifest: {repo, outcome, pushed_sha, changes, error}
  |
  +-- write manifests/{run_id}.json
  +-- print summary table [DONE/CONFLICT/SKIP counts]

pushed commit in repo
  --> notify-kf-cpto.yml fires (path: kanban.md, branch: main/master)
  --> repository_dispatch{event_type: kanban-updated}
  --> aggregate.yml re-renders full dashboard
  --> GitHub Pages deploy
```

### Recommended Project Structure

```
.claude/skills/activity-sync/
├── bootstrap.py        # Phase 1 (existing)
├── repo_enum.py        # Phase 1 (existing)
├── reconcile.py        # Phase 2 (existing)
├── sanitize.py         # [NEW Phase 3] sanitize_cell(), sanitize_body()
├── writeback.py        # [NEW Phase 3] run(), main(), _write_repo(), _confirm_batch()
└── manifests/          # [NEW Phase 3] gitignored; per-run JSON manifests
    └── .gitkeep        # optional sentinel (gitignore by pattern)
```

### Pattern 1: ruamel.yaml Frontmatter Round-Trip

**What:** Split kanban.md into frontmatter + body using regex, round-trip only the frontmatter YAML through ruamel, rejoin with the (edited) body.

**When to use:** Any time writeback.py reconstructs kanban.md to ensure inline `#` comments, key order, and quoted strings survive.

**Example:**
```python
# Source: verified against templates/kanban.md in this session
from ruamel.yaml import YAML
from io import StringIO
import re

_FM_RE = re.compile(r'^---\n(.*?)\n---\n?', re.DOTALL)

def split_kanban(content: str) -> tuple[str, str]:
    """Split kanban.md into (frontmatter_str, body_str). Raises ValueError if no FM."""
    match = _FM_RE.match(content)
    if not match:
        raise ValueError("No YAML frontmatter found")
    return match.group(1), content[match.end():]

def roundtrip_frontmatter(fm_str: str) -> str:
    """Round-trip frontmatter YAML through ruamel, preserving # comments and key order."""
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(fm_str)
    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()  # ends with single \n

def reconstruct_kanban(fm_str: str, body_str: str) -> str:
    """Reconstruct kanban.md from (possibly edited) frontmatter and body."""
    rt_fm = roundtrip_frontmatter(fm_str)
    return "---\n" + rt_fm + "---\n" + body_str
```

**Key insight:** `yaml.dump()` produces a trailing `\n` but no document-end `---` marker, so the rejoin is exactly `"---\n" + rt_fm + "---\n" + body_str`. This was verified byte-identical for unmodified frontmatter.

### Pattern 2: Status-Cell Targeted Replacement

**What:** For each Proposal, locate the table row by matching the raw task name (parts[1].strip()), replace parts[-2] (the last data cell = Status) with the new status value.

**When to use:** Body pass before sanitization; operates on the raw (pre-sanitize) body lines.

**Example:**
```python
# Source: verified against both 4-col and 6-col table layouts in this session
def replace_status_cell(line: str, task_name: str, new_status: str) -> tuple[str, bool]:
    """Replace Status cell in a pipe-table row matching task_name.
    Returns (new_line, was_changed).
    Works for both 4-col and 6-col tables (status is always the last data column).
    """
    if not line.startswith("|"):
        return line, False
    parts = line.split("|")
    # parts[0] = '' (before leading |); parts[-1] = '' (after trailing |)
    # Need at least | task | ... | status |  => 4 parts minimum
    if len(parts) < 4:
        return line, False
    task_cell = parts[1].strip()
    if task_cell != task_name:
        return line, False
    old_status = parts[-2].strip()
    if old_status == new_status:
        return line, False
    parts[-2] = f" {new_status} "
    return "|".join(parts), True
```

**Duplicate task name edge case:** If multiple rows share the same task name, update only the first match and log `[WARN]`. The reconcile engine emits one Proposal per unique task name, so the second match is a kanban authoring error in the source repo.

### Pattern 3: Emoji and Break-Character Sanitization

**What:** Strip emoji codepoints, apply readable substitutions for Mermaid/table break characters, preserve all Latin characters including Romanian diacritics.

**When to use:** After status replacements, applied to ALL data cells in task-table rows (skip header row where `parts[1].strip() == "Task"` and separator rows containing `:---`).

**Example:**
```python
# Source: verified in this session — Romanian diacritics preserved, emoji stripped
import re, unicodedata

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

def _is_emoji(cp: int) -> bool:
    """True if Unicode codepoint is in an emoji block (stdlib, Python 3.9 compat)."""
    return (
        0x1F600 <= cp <= 0x1F64F or  # Emoticons
        0x1F300 <= cp <= 0x1F5FF or  # Misc Symbols and Pictographs
        0x1F680 <= cp <= 0x1F6FF or  # Transport and Map
        0x1F700 <= cp <= 0x1F9FF or  # Alchemical + Geometric + Arrows + Supplemental
        0x1FA00 <= cp <= 0x1FA6F or  # Chess Symbols
        0x1FA70 <= cp <= 0x1FAFF or  # Symbols and Pictographs Extended-A
        0x2600  <= cp <= 0x26FF  or  # Misc Symbols (⚠✅⛔ etc.)
        0x2700  <= cp <= 0x27BF  or  # Dingbats (✔✗➡ etc.)
        0xFE00  <= cp <= 0xFE0F  or  # Variation Selectors
        0x1F1E0 <= cp <= 0x1F1FF or  # Regional Indicator Symbols (flags)
        cp == 0x200D                  # Zero Width Joiner (emoji sequences)
    )

def sanitize_cell(text: str) -> str:
    """Apply break-char substitution + emoji strip to a single cell value.
    
    Readable substitutions only (never silent drop for visible text chars).
    Romanian diacritics (ă U+0103, â U+00E2, î U+00EE, ș U+0219, ț U+021B)
    are category Ll -- below all emoji ranges -- preserved verbatim.
    """
    result: list[str] = []
    for c in text:
        if _is_emoji(ord(c)):
            continue
        result.append(_BREAK_MAP.get(c, c))
    return re.sub(r"  +", " ", "".join(result)).strip()

def sanitize_body(body: str) -> str:
    """Apply sanitize_cell to all data cells in task-table rows.
    
    Skips: header row (first cell == 'Task'), separator rows (':---'),
    prose lines, HTML comments, blank lines.
    Idempotent: second pass produces identical output.
    """
    lines = body.splitlines(keepends=True)
    result: list[str] = []
    for line in lines:
        stripped = line.rstrip("\n")
        if not stripped.startswith("|"):
            result.append(line)
            continue
        parts = stripped.split("|")
        first_cell = parts[1].strip() if len(parts) > 1 else ""
        # Skip header and separator rows
        if first_cell == "Task" or ":---" in stripped:
            result.append(line)
            continue
        # Sanitize data cells: parts[1..-2]
        new_parts = [parts[0]]
        for i in range(1, len(parts) - 1):
            new_parts.append(f" {sanitize_cell(parts[i].strip())} ")
        new_parts.append(parts[-1])
        eol = "\n" if line.endswith("\n") else ""
        result.append("|".join(new_parts) + eol)
    return "".join(result)
```

**Romanian diacritics codepoints (verified):**
- ă: U+0103 (LATIN SMALL LETTER A WITH BREVE) — category Ll
- â: U+00E2 (LATIN SMALL LETTER A WITH CIRCUMFLEX) — category Ll
- î: U+00EE (LATIN SMALL LETTER I WITH CIRCUMFLEX) — category Ll
- ș: U+0219 (LATIN SMALL LETTER S WITH COMMA BELOW) — category Ll
- ț: U+021B (LATIN SMALL LETTER T WITH COMMA BELOW) — category Ll

All are in the 0x0000–0x02FF Basic Latin + Latin Extended range, well below all emoji blocks. The `_is_emoji()` range check will never touch them.

### Pattern 4: Conflict Detection Gate

**What:** `git fetch origin` then count commits in `origin/<branch>` that are not in `HEAD`.

**When to use:** Before every write, immediately after fetch. Count > 0 means local is behind remote (non-fast-forward); abort with `[CONFLICT]` and continue to next repo.

**Example:**
```python
# Source: verified with throwaway bare git repo in this session
def _is_behind_origin(repo_path: str, branch: str) -> tuple[bool, int]:
    """Return (is_behind, behind_count) for the local checkout vs origin/<branch>.
    
    Fetches first to get fresh remote state.
    Returns (True, N) if local is behind by N commits.
    Returns (False, 0) if up-to-date.
    Returns (True, -1) on git error (conservative: treat as conflict to avoid clobber).
    """
    fetch = _run_git(["-C", repo_path, "fetch", "origin"])
    if fetch.returncode != 0:
        print(f"Warning: fetch failed for {repo_path}: {fetch.stderr.strip()}")
        return True, -1  # conservative: treat fetch failure as conflict
    
    result = _run_git([
        "-C", repo_path, "rev-list", "--count",
        f"HEAD..origin/{branch}"
    ])
    if result.returncode != 0:
        return True, -1  # conservative
    
    count = int(result.stdout.strip() or "0")
    return count > 0, count
```

### Pattern 5: Push with HTTPS Auth + URL Restore

**What:** Save original SSH URL, temporarily set HTTPS+token URL for push, restore SSH URL in a `finally` block.

**When to use:** Every push in `writeback.py`. Token never printed or logged.

**Example:**
```python
# Source: mirrors aggregate.yml pattern; verified with local bare repo
def _push_with_auth(
    repo_path: str,
    repo_name: str,
    branch: str,
    kf_pat: str,
) -> tuple[bool, str]:
    """Push HEAD to origin/<branch> using HTTPS+KF_PAT auth.
    
    Saves and restores original remote URL in a finally block so the token
    is never permanently stored in .git/config (T-02-05).
    Returns (success, pushed_sha_or_error).
    Never logs or prints the HTTPS URL (T-02-05 Information Disclosure).
    """
    original_url = _get_remote_url(repo_path)
    # Build HTTPS URL with token -- arg-list only, never shell=True
    https_url = f"https://{kf_pat}@github.com/katty-fashion/{repo_name}.git"
    try:
        set_r = _run_git(["-C", repo_path, "remote", "set-url", "origin", https_url])
        if set_r.returncode != 0:
            return False, f"remote set-url failed: {set_r.stderr.strip()}"
        
        push_r = _run_git(["-C", repo_path, "push", "origin", f"HEAD:{branch}"])
        if push_r.returncode != 0:
            return False, f"push failed: {push_r.stderr.strip()}"
        
        sha_r = _run_git(["-C", repo_path, "rev-parse", "HEAD"])
        sha = sha_r.stdout.strip() if sha_r.returncode == 0 else "unknown"
        return True, sha
    finally:
        # Always restore original URL -- token must not persist in .git/config
        if original_url:
            _run_git(["-C", repo_path, "remote", "set-url", "origin", original_url])
```

### Pattern 6: Idempotency Byte-Compare

**What:** Compare the proposed kanban.md bytes to the current file bytes. Skip write+commit+push if identical.

**When to use:** After computing the full reconstructed content, before any file write or git operation.

**Example:**
```python
def _content_changed(kanban_path: str, proposed: str) -> bool:
    """True if proposed content differs from current file bytes."""
    current = Path(kanban_path).read_bytes()
    return current != proposed.encode("utf-8")
```

### Pattern 7: Recovery Manifest

**What:** Write a per-run JSON file recording outcome for every repo.

**Example:**
```python
# Source: designed in this session; follows utils.now_iso() convention
import json
from datetime import datetime, timezone

def _write_manifest(manifests_dir: Path, run_id: str, repos_results: list[dict]) -> None:
    """Write per-run JSON manifest to manifests_dir/{run_id}.json.
    
    manifests_dir is gitignored (.claude/skills/activity-sync/manifests/).
    Never raises -- manifest write failure must not abort the write-back run.
    """
    manifests_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_repos": len(repos_results),
        "summary": {
            "succeeded": sum(1 for r in repos_results if r["outcome"] == "succeeded"),
            "failed":    sum(1 for r in repos_results if r["outcome"] == "failed"),
            "conflict":  sum(1 for r in repos_results if r["outcome"] == "conflict"),
            "skipped":   sum(1 for r in repos_results if r["outcome"] == "skipped"),
        },
        "repos": repos_results,
    }
    path = manifests_dir / f"{run_id}.json"
    try:
        path.write_text(json.dumps(manifest, indent=2))
        print(f"[INFO] Manifest written: {path}")
    except OSError as exc:
        print(f"Warning: could not write manifest: {exc}")
```

**Manifest per-repo entry schema:**
```json
{
  "repo":        "kf-be-platform",
  "outcome":     "succeeded",
  "pushed_sha":  "abc123def456",
  "changes":     [{"task": "...", "old_status": "Todo", "new_status": "Done"}],
  "error":       null
}
```

**Outcome enum:** `succeeded` | `failed` | `conflict` | `skipped`

### Pattern 8: Throwaway Bare Repo Test Harness

**What:** Create a bare git repo in a `tempfile.mkdtemp()` directory as a throw-away remote for testing commit+push+conflict logic without any network access.

**When to use:** Unit tests in a `test_writeback.py` file. Teardown with `shutil.rmtree(tmpdir)`.

**Example:**
```python
# Source: verified in this session; pattern established from conflict detection tests
import tempfile, shutil, subprocess
from pathlib import Path

def _make_bare_remote() -> tuple[Path, Path, Path]:
    """Create bare repo + two workdirs. Returns (tmpdir, bare_dir, workdir)."""
    tmpdir = Path(tempfile.mkdtemp())
    bare = tmpdir / "bare.git"
    work = tmpdir / "workdir"
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)
    subprocess.run(["git", "clone", str(bare), str(work)], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "bot@test.dev"], cwd=work, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Bot"], cwd=work, capture_output=True)
    return tmpdir, bare, work

# Usage in test:
# tmpdir, bare, work = _make_bare_remote()
# try:
#     ... test logic ...
# finally:
#     shutil.rmtree(tmpdir)
```

### Anti-Patterns to Avoid

- **Never use `shell=True` for git subprocess calls**: token interpolation risk; all git calls must use arg-list form.
- **Never print or log the HTTPS remote URL**: it contains the KF_PAT token. Use `[INFO] push ok` not the URL.
- **Never call `git remote -v` in writeback.py**: output would print the token. If remote URL is needed for logging, use the saved `original_url` (SSH form) before set-url.
- **Never round-trip the markdown body through ruamel.yaml**: ruamel is for frontmatter only. Table rows, HTML comments, and prose must pass through unchanged.
- **Never sanitize the header row or separator row**: only data rows (not `| Task | Assignee |...` or `| :--- | :--- |...`).
- **Never run sanitize before status replacements**: sanitize may alter the task name cell, breaking the Proposal.task match. Apply status replacements first on raw cell values, then sanitize.
- **Never add `[skip ci]` to kanban commits**: the dispatch is intentional; the CI should run.
- **Never use `pyyaml.safe_load` + `yaml.safe_dump` for the frontmatter round-trip**: this loses inline `#` comments (confirmed in Phase 2 research).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML round-trip with comment preservation | Custom frontmatter string editor | `ruamel.yaml` round-trip mode | Inline comments, key order, quoting edge cases are all handled; custom regex fragile on multi-line values |
| Emoji detection | Unicode category lookup or external list | Codepoint range check via `unicodedata` stdlib | No external dependency; emoji blocks are stable Unicode ranges; verified against common emoji chars |
| kanban.md parsing | Second regex parser in writeback.py | `scripts/utils.parse_kanban_tasks()` | REPO-03 constraint; single parser ensures status validation stays consistent |
| Git token auth | Custom HTTP client or credential helper | `git remote set-url` + restore pattern | Mirrors aggregate.yml; portable; no SSH key assumption |

**Key insight:** The write-back path is intentionally minimal — it only edits the Status cell and optionally sanitizes cell text. Any deeper kanban manipulation belongs in the kanban format itself, not the skill.

---

## Runtime State Inventory

Not applicable — this phase does not rename or migrate stored data. The write-back modifies `kanban.md` files in place (tracked repos, not kf-cpto itself). No OS-registered state, no stored data records, no build artifacts affected.

**repos-local/ runtime dir:** Already gitignored. Phase 3 writes to repos-local/{repo}/kanban.md, then pushes the change to the tracked repo. repos-local/ itself is never committed.

**manifests/ directory:** New gitignored directory at `.claude/skills/activity-sync/manifests/`. Must be added to `.gitignore` — the `!.claude/skills/` negation currently makes all content under skills/ trackable by git.

---

## Common Pitfalls

### Pitfall 1: Token in .git/config After Failed Push

**What goes wrong:** `git remote set-url` writes the HTTPS+token URL to `.git/config`. If the push fails and the finally-block URL restore also fails, the token persists on disk in plaintext.

**Why it happens:** `_run_git` swallows exceptions; a finally-block restore that ignores errors could silently fail.

**How to avoid:** The finally block must always attempt the URL restore. Log a `[WARN]` if restore fails but do not re-raise. Accept that on restore failure the .git/config contains a token (not committed, local only), but log clearly so the operator knows to run `git remote set-url origin <ssh_url>` manually.

**Warning signs:** `git remote -v` in the tracked repo shows an HTTPS URL after writeback.py ran.

### Pitfall 2: Proposal.task Mismatch After Prior Sanitization Run

**What goes wrong:** `reconcile.run()` calls `parse_kanban_tasks()` on the current file. If the file was already sanitized (e.g. by a prior writeback run), task names in the file are the sanitized forms. The Proposal.task field will match the sanitized name. Status replacement will work correctly because we re-read the file fresh.

**Why it happens:** The Proposal is built from the CURRENT file state, not from any cached state. This is self-consistent.

**How to avoid:** Always call `reconcile.run()` immediately before `writeback.run()` within the same skill invocation (or pass the proposals from the same session). Do NOT cache proposals across separate sessions.

### Pitfall 3: Pipe Character in Task Name Breaking Table at Read Time

**What goes wrong:** A task name containing `|` (e.g. `"A | B"`) causes `parse_kanban_tasks()` to split the row incorrectly — the task cell is truncated at the first `|`. `Proposal.task` will contain the truncated name. After writeback.py's sanitize pass, `|` → `/` in the file, so subsequent reads are clean. But the FIRST write attempt must still locate the row.

**Why it happens:** Both markdown table syntax and `parse_kanban_tasks()` split on `|`. A raw `|` in a task name is already a broken row.

**How to avoid:** In `replace_status_cell()`, match against `parts[1].strip()` (the truncated task name from the broken row), exactly as `parse_kanban_tasks()` parsed it. This is already how the code works — the Proposal.task field matches what `parse_kanban_tasks()` returned, including any truncation. After sanitization writes `/` instead of `|`, the row is well-formed and subsequent reconcile runs will read the full corrected name.

**Warning signs:** Proposal.task contains `|` characters — this is unusual and signals a broken row in the source file that sanitization will fix.

### Pitfall 4: Behind-Count Returns 0 Before Fetch

**What goes wrong:** Calling `git rev-list --count HEAD..origin/<branch>` WITHOUT a prior `git fetch origin` will use stale remote tracking refs. A competing push that happened since the last fetch will not be detected.

**Why it happens:** Remote tracking refs (`origin/<branch>`) are only updated by `git fetch`.

**How to avoid:** Always run `git fetch origin` as the first step of conflict detection in `_is_behind_origin()`. The `_fetch_repo()` helper from Phase 1 already does this correctly.

### Pitfall 5: ruamel.yaml Dumps Extra Trailing Newlines on Python 3.9

**What goes wrong:** In some edge cases, `yaml.dump()` may emit a blank line at the end of the document for multi-document YAML. This would shift the `---\n` separator.

**Why it happens:** ruamel default behavior; version-dependent.

**How to avoid:** After `stream.getvalue()`, strip trailing blank lines if any:
```python
rt_fm = stream.getvalue().rstrip("\n") + "\n"
```
Our testing confirmed ruamel 0.19.1 on Python 3.9 emits exactly one trailing `\n`, but the `.rstrip("\n") + "\n"` guard is cheap and defensive.

### Pitfall 6: .gitignore Does Not Cover manifests/

**What goes wrong:** The `.gitignore` has `.claude/*` + `!.claude/skills/` which means everything under `.claude/skills/` is tracked. A `git add -A` in kf-cpto would commit manifests JSON files into the repo.

**Why it happens:** The skills exemption was added for skill source files, not runtime artifacts.

**How to avoid:** Add `.claude/skills/activity-sync/manifests/` to `.gitignore` as part of Phase 3 Wave 0. Verify with `git status` after creating the directory.

### Pitfall 7: Empty Status Cell Produces Incorrect Replacement

**What goes wrong:** If the Status cell in the file is empty (`| |`), `parts[-2].strip()` returns `""`, which is not in `TASK_STATUSES`. `replace_status_cell()` would still replace it (old != new), producing a valid row. This is correct behavior — an empty status should be corrected.

**Why it happens:** Rarely occurs in practice; parse_kanban_tasks already prints a `Warning:` for unknown statuses.

**How to avoid:** No special handling needed. The replacement is valid. The `[WARN]` from `parse_kanban_tasks()` at Phase 2 read time already surfaces this.

---

## Code Examples

### Full Write-Back Sequence (Pseudo-code)

```python
# Source: synthesized from verified patterns in this session
def _write_repo(
    record: dict,
    proposals_for_repo: list[Proposal],
    kf_pat: str,
    run_id: str,
) -> dict:
    """Apply proposals to one repo. Returns manifest entry dict."""
    repo_name = record["name"]
    repo_path = record["local_path"]
    branch = record["branch"]
    kanban_path = Path(repo_path) / "kanban.md"
    
    # Step 1: Conflict check
    is_behind, behind_count = _is_behind_origin(repo_path, branch)
    if is_behind:
        msg = (f"local checkout is {behind_count} commit(s) behind origin/{branch}"
               if behind_count >= 0 else "fetch failed")
        print(f"[CONFLICT] {repo_name}: {msg} — skipping write")
        return {"repo": repo_name, "outcome": "conflict", "pushed_sha": None,
                "changes": [], "error": msg}
    
    # Step 2: Read fresh kanban.md
    content = kanban_path.read_text(encoding="utf-8")
    fm_str, body_str = split_kanban(content)
    
    # Step 3: Apply status replacements (by raw task name)
    for proposal in proposals_for_repo:
        body_str, _ = apply_status_change(body_str, proposal.task, proposal.new_status)
    
    # Step 4: Sanitize all task-table data cells
    body_str = sanitize_body(body_str)
    
    # Step 5: Reconstruct
    new_content = reconstruct_kanban(fm_str, body_str)
    
    # Step 6: Idempotency check
    if not _content_changed(str(kanban_path), new_content):
        print(f"[SKIP] {repo_name}: content unchanged (idempotent no-op)")
        return {"repo": repo_name, "outcome": "skipped", "pushed_sha": None,
                "changes": [], "error": None}
    
    # Step 7: Write + commit
    kanban_path.write_text(new_content, encoding="utf-8")
    _run_git(["-C", repo_path, "config", "user.name", "KF Bot"])
    _run_git(["-C", repo_path, "config", "user.email", "bot@katty-fashion.dev"])
    _run_git(["-C", repo_path, "add", "kanban.md"])
    commit_r = _run_git(["-C", repo_path, "commit", "-m",
                          "chore(kanban): reconcile task statuses from repo activity"])
    if commit_r.returncode != 0:
        return {"repo": repo_name, "outcome": "failed", "pushed_sha": None,
                "changes": [], "error": f"commit failed: {commit_r.stderr.strip()}"}
    
    # Step 8: Push with token + restore URL
    ok, sha_or_err = _push_with_auth(repo_path, repo_name, branch, kf_pat)
    if not ok:
        return {"repo": repo_name, "outcome": "failed", "pushed_sha": None,
                "changes": [], "error": sha_or_err}
    
    changes = [{"task": p.task, "old_status": p.old_status, "new_status": p.new_status}
               for p in proposals_for_repo]
    print(f"[DONE] {repo_name}: pushed {sha_or_err[:8]} (branch: {branch})")
    return {"repo": repo_name, "outcome": "succeeded", "pushed_sha": sha_or_err,
            "changes": changes, "error": None}
```

### Test Harness for Conflict Detection

```python
# Source: verified in this session
import tempfile, shutil, subprocess
from pathlib import Path

def test_conflict_detection():
    tmpdir = Path(tempfile.mkdtemp())
    bare = tmpdir / "bare.git"
    work1 = tmpdir / "workdir1"
    work2 = tmpdir / "workdir2"
    
    def git(args, cwd=None):
        return subprocess.run(["git"] + args, capture_output=True, text=True, cwd=str(cwd))
    
    git(["init", "--bare", str(bare)])
    git(["clone", str(bare), str(work1)])
    git(["config", "user.email", "bot@test.dev"], work1)
    git(["config", "user.name", "Bot"], work1)
    
    # Initial commit
    (work1 / "kanban.md").write_text("# test\n")
    git(["add", "."], work1)
    git(["commit", "-m", "init"], work1)
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], work1).stdout.strip()
    git(["push", "-u", "origin", branch], work1)
    
    # Competing push from work2
    git(["clone", str(bare), str(work2)])
    git(["config", "user.email", "bot@test.dev"], work2)
    git(["config", "user.name", "Bot"], work2)
    (work2 / "kanban.md").write_text("# human edit\n")
    git(["add", "."], work2)
    git(["commit", "-m", "human edit"], work2)
    git(["push", "origin", f"HEAD:{branch}"], work2)
    
    # work1 fetches and checks
    git(["fetch", "origin"], work1)
    r = git(["rev-list", "--count", f"HEAD..origin/{branch}"], work1)
    behind = int(r.stdout.strip())
    assert behind == 1, f"Expected 1, got {behind}"
    
    shutil.rmtree(tmpdir)
    print("Conflict detection test: PASS")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pyyaml round-trip (loses comments) | ruamel.yaml round-trip (preserves comments) | Phase 3 decision | WB-01 compliance; hand-authored kanban.md metadata survives writes |
| No sanitization (raw task names in Mermaid) | Skill-side sanitize on write path | Phase 3 | DIAG-01/02/03 compliance; diagrams render cleanly after first writeback run |
| SSH remote only for skill | HTTPS+KF_PAT at push time, restore SSH after | Phase 3 decision | CI-parity auth; no assumption about SSH key presence |

**Deprecated/outdated:**
- Dependency on `repos/` CI runtime dir: the skill uses `repos-local/` and never touches `repos/`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All tracked repos' `notify-kf-cpto.yml` is configured to fire `kanban-updated` on push to main/master | Architecture Patterns (dispatch chain) | Natural dispatch would not fire; CI would not re-render. Risk LOW — template is managed by bootstrap.py |
| A2 | `KF_PAT` token has `repo` scope (push access to tracked repos) | Pattern 5 (push auth) | Push fails with 403. Risk LOW — same token used by CI `aggregate.yml` for cloning |
| A3 | All tracked repos use either `main` or `master` as default branch | Pattern 2 / conflict detection | Wrong branch push would fail silently or push to wrong branch. Risk LOW — `record["branch"]` from Phase 1 detects actual default branch per-repo |
| A4 | ruamel.yaml 0.19.1 is Python 3.9 compatible | Standard Stack | Round-trip breaks at runtime. Risk LOW — verified by installing in the project venv (Python 3.9.6) |

**If this table is empty of HIGH-risk items:** All core claims were verified in this session. The four assumptions above are LOW risk based on existing Phase 1/2 infrastructure.

---

## Open Questions (RESOLVED)

1. **pyyaml vs ruamel.yaml** (from STATE.md)
   - RESOLVED: Use ruamel.yaml. Round-trip verified byte-identical for unmodified frontmatter including inline `#` comments. See Pattern 1.

2. **skip-ci dispatch strategy** (from STATE.md)
   - RESOLVED: Natural per-repo dispatch (no `[skip ci]`). N pushes → N aggregate runs; each run re-clones all repos so any run produces the full corrected dashboard.

3. **ruamel.yaml Python 3.9 compatibility**
   - RESOLVED: Installed and verified in project venv (Python 3.9.6). `from ruamel.yaml import YAML; YAML()` works. Round-trip with `preserve_quotes=True` confirmed.

4. **How to detect local-behind-origin**
   - RESOLVED: `git rev-list --count HEAD..origin/<branch>` after `git fetch origin`. Verified with throwaway bare repo.

5. **Idempotency implementation**
   - RESOLVED: Byte-compare `Path(kanban_path).read_bytes()` vs `proposed.encode("utf-8")`. Skip write if identical. Sanitize pass is idempotent on second run.

6. **Token masking**
   - RESOLVED: Save + restore pattern. `git remote set-url` (arg-list, never shell=True). Never print HTTPS URL. Restore in `finally` block.

7. **Romanian diacritics codepoints**
   - RESOLVED: ă (U+0103), â (U+00E2), î (U+00EE), ș (U+0219), ț (U+021B). All Ll category, below all emoji ranges. Not touched by `_is_emoji()` or `_BREAK_MAP`.

8. **manifests/ gitignore**
   - RESOLVED: Must add `.claude/skills/activity-sync/manifests/` to `.gitignore` (the `!.claude/skills/` negation makes it currently trackable). Wave 0 task.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | All skill modules | Yes | 3.9.6 (venv) | — |
| ruamel.yaml | writeback.py frontmatter round-trip | Yes (installed in venv) | 0.19.1 | None — required for WB-01 |
| git | Conflict detect, commit, push | Yes | system git | — |
| KF_PAT env var | Push auth | Must be set by operator | — | None — push fails without it |
| scripts/utils.py | parse_kanban_tasks, TASK_STATUSES | Yes | — | — (already imported in Phase 1/2) |

**Missing dependencies with no fallback:**
- `KF_PAT`: must be set in the shell environment before running writeback.py with live push. The skill should fail-fast with a clear error message if unset at push time (not at import time).

---

## Validation Architecture

> `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json` — this section is omitted per configuration.

---

## Security Domain

> No `security_enforcement` key in config; treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — skill is local; no user auth |
| V3 Session Management | No | N/A — no sessions |
| V4 Access Control | Yes | Org-allowlist guard from Phase 1 (`_check_remote_org`); only katty-fashion repos |
| V5 Input Validation | Yes | Arg-list subprocess; task names from parse_kanban_tasks only (never eval/exec) |
| V6 Cryptography | No | Token handled as env var; no custom crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token disclosure via log | Information Disclosure | Never print HTTPS URL; restore SSH URL after push; arg-list subprocess prevents shell expansion |
| Path traversal via repo name | Tampering | Org-allowlist guard (`_check_remote_org`); path constructed from `record["local_path"]` (org-verified in Phase 1) |
| Shell injection via task name / branch | Tampering | Arg-list `_run_git`; never `shell=True`; task names from parsed YAML, never exec'd |
| Clobber concurrent human edit | Tampering | WB-03 conflict detection gate (`rev-list --count`); aborts and logs `[CONFLICT]` |

---

## Sources

### Primary (HIGH confidence)
- Verified in this session against project source code: `reconcile.py`, `repo_enum.py`, `bootstrap.py`, `scripts/utils.py`, `templates/kanban.md`, `.github/workflows/aggregate.yml`, `templates/.github/workflows/notify-kf-cpto.yml`, `scripts/validate_auto_blocks.py`
- ruamel.yaml 0.19.1 installed and tested in project venv (Python 3.9.6)
- PyPI registry: `https://pypi.org/pypi/ruamel.yaml/json` — 12-year history, 273 releases, Anthon van der Neut

### Secondary (MEDIUM confidence)
- Python stdlib unicodedata: `unicodedata.category()` for Romanian diacritics (Ll), verified against actual codepoints
- Unicode emoji block ranges: cross-referenced against Unicode standard block assignments

### Tertiary (LOW confidence)
- Mermaid character break analysis: based on Mermaid kanban/gantt syntax knowledge [ASSUMED]; specific break behavior not tested against live Mermaid renderer — but the substitution set is conservative (only known-problematic chars)

---

## Project Constraints (from CLAUDE.md)

All directives from `./CLAUDE.md` that apply to this phase:

- Python 3.9+ (venv pinned to 3.9) — all new modules must be compatible; use `from __future__ import annotations` for PEP 604 union types
- `snake_case.py` for new module filenames: `sanitize.py`, `writeback.py`
- `snake_case` for all functions: `sanitize_cell`, `sanitize_body`, `split_kanban`, `roundtrip_frontmatter`, `reconstruct_kanban`, `run`, `main`
- Module-level constants in `SCREAMING_SNAKE_CASE`: `_BREAK_MAP`, `MANIFESTS_DIR`, `COMMIT_MSG`
- `_run_git` arg-list subprocess — no `shell=True`, ever
- `run()` / `main()` split — `main()` delegates to `run()`; `run()` returns structured result without `sys.exit`
- `[LABEL]` text pills in output (`[DONE]`, `[CONFLICT]`, `[SKIP]`, `[WARN]`, `[INFO]`); no emojis
- Never commit `repos-local/` or runtime artifacts
- Never import skill modules from CI (`aggregate.yml` installs only its four packages)
- Extend existing `requirements.txt` (add `ruamel.yaml>=0.17`); never add a second kanban parser
- Parser discipline: `reconcile.run()` is the only caller; `writeback.py` imports reconcile, not utils parsers directly
- No static project list in the skill (repos-local/ membership is the tracked set)
- `KF_PAT` read from env; never printed; never hardcoded

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — ruamel.yaml installed, tested, PyPI-verified
- Architecture: HIGH — all patterns verified with working code against real project files
- Pitfalls: HIGH — most pitfalls discovered through active code testing in this session
- Mermaid break analysis: MEDIUM — character set is well-known; specific Mermaid renderer behavior not live-tested

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (ruamel.yaml stable; Python 3.9 stdlib stable)
