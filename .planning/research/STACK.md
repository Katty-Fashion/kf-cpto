# Stack Research

**Domain:** Local Claude Code skill — activity-driven kanban reconciliation + agentic capacity model
**Researched:** 2026-06-04
**Confidence:** HIGH

## Context and Constraints

This milestone adds a *local* skill layer on top of an existing Python + Jekyll CI pipeline. The skill never runs in CI — it is the smart input layer that produces corrected `kanban.md` files, which then trigger the existing deterministic `notify → dispatch → aggregate.yml` pipeline.

Constraints that drive every choice below:

- Python 3.9+ minimum (local venv at 3.9; CI at 3.11, but skill runs only locally)
- Existing `requirements.txt` has four deps: `pyyaml>=6.0`, `requests>=2.28`, `google-auth>=2.0`, `google-api-python-client>=2.0`
- `gh` CLI is already installed and used by `sheets_sync.py` (filing issues); version confirmed at 2.87.3
- "One parser, one canonical intermediate" constraint: `utils.parse_kanban_*` and `aggregator.build_loe_rows()` are the only parse path; the skill must not duplicate them
- Exit-0 invariant: any new code that touches the CI path must never block Pages deployment
- No test suite beyond `validate_auto_blocks.py`; keep additions testable without a new test framework

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python stdlib `subprocess` | 3.9+ (stdlib) | Git activity mining from local clones | Already used implicitly across the pipeline. No new dependency. Git's `--format`, `--since`, `--follow` flags produce structured output; `subprocess.run(capture_output=True, text=True)` parses it in 3 lines. Confirmed working for all required operations: `git log`, `git branch -a`, `git status --porcelain`, `git rev-parse --abbrev-ref HEAD`. GitPython wraps this same subprocess and adds object-oriented overhead, resource-leak risk, and a new dep — no benefit for this use case. |
| `gh` CLI (existing) | 2.87.3 (confirmed) | GitHub API queries — merged PRs, open branches, kanban.md commit history per repo | Already in `PATH` and used by `sheets_sync.py`. `gh api`, `gh pr list --json`, `gh api repos/{owner}/{repo}/commits?path=kanban.md` all work and return structured JSON. Only tool that can retrieve merged PR metadata without GitHub API Python client setup on the skill side. |
| `pyyaml` (existing) | `>=6.0` (already in `requirements.txt`) | Kanban frontmatter read/modify/write | Already installed. `yaml.safe_load` + `yaml.dump(allow_unicode=True)` roundtrip confirmed: parses `---` frontmatter, modifies fields, re-serializes without corrupting table body. `allow_unicode=True` is required to preserve non-ASCII project names in Romanian/Romanian-adjacent content. |
| Python stdlib `re` + `unicodedata` | 3.9+ (stdlib) | Mermaid-safe string sanitization | `unicodedata.category()` correctly identifies emoji as `So` (Symbol, other) and variation selectors as `Mn`. Combined with `re.sub` for Mermaid-breaking punctuation (`()`, `:`, `"`, `#`, `;`, `{}`, `\|`), this covers all known failure modes in the existing gantt/kanban/pie diagrams. No new dep needed. Confirmed: all emoji in migration-gantt.md (`🚀`, `✅`, `⚠️` etc.) are category `So` or `Mn` (variation selector). |
| Claude Code skill (`SKILL.md`) | Current (2026-06-04 docs) | Skill invocation and orchestration structure | Official Claude Code skills spec (https://code.claude.com/docs/en/skills). Skill lives at `.claude/skills/reconcile-activity/SKILL.md`. Uses `disable-model-invocation: true` (batch write-back must be explicit, never auto-triggered). Uses `context: fork` for isolation. Dynamic context injection (`` !`command` `` blocks) pre-loads git status and repo list before Claude reads the skill. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `pathlib` | 3.9+ (stdlib) | Resolve symlinked repo paths, kanban.md location, safe path joins | Always. Replaces `os.path` throughout the skill helpers. `Path.resolve()` follows symlinks to real checkout paths. |
| Python stdlib `json` | 3.9+ (stdlib) | Parse `gh` CLI `--json` output | Always. `gh pr list --json` and `gh api` both return JSON. `json.loads()` is the parse step. |
| Python stdlib `datetime` | 3.9+ (stdlib) | Activity window calculations (since X weeks ago), date-string formatting for `--since` git flag | Always. `datetime.now() - timedelta(weeks=4)` → `strftime('%Y-%m-%d')` for `git log --since`. |
| Python stdlib `difflib` | 3.9+ (stdlib) | Generating a human-readable diff of kanban.md changes before batch confirm | For the change-list output shown to the user before batch push confirmation. `unified_diff()` on old vs new content gives a reviewable summary without a third-party diff library. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `gh` CLI | Cross-repo PR/branch API queries | Point at tracked project repos with `--repo owner/name` flag. Auth via existing `KF_PAT` or local `gh auth login`. |
| `git` subprocess | Local clone activity mining | Run against symlinked repo paths. All commands use `cwd=repo_path` parameter. Never mutates the repo until explicit batch-confirmed write-back step. |
| Claude Code skills system | Skill packaging and invocation | `.claude/skills/reconcile-activity/SKILL.md` with `disable-model-invocation: true`. Supporting Python helpers in `.claude/skills/reconcile-activity/scripts/`. |

---

## Installation

```bash
# No new Python dependencies required.
# All tooling is stdlib + already-installed pyyaml + existing gh CLI.

# Verify prerequisites
python3 --version           # must be 3.9+
gh --version                # must be present (2.x+)
python3 -c "import yaml; print(yaml.__version__)"  # must be 6.x+
```

---

## Question-by-Question Decisions

### 1. Git/GitHub Activity Mining

**Use: `subprocess` + `git` for local history; `gh` CLI for remote API (PRs, remote branches)**

`subprocess.run(['git', 'log', '--format=%H|%ae|%s|%aI', '--since=4 weeks ago'], cwd=repo_path)` covers:
- Recent commit timestamps and messages (progress signal)
- File-specific log: `git log --follow -- kanban.md` (was kanban.md updated vs. untouched?)
- Branch list: `git branch -a` (feature branches that imply active work)
- Merge detection: `git log --merges --oneline` (completed work signal)
- Dirty state: `git status --porcelain` (pre-push safety check)

`gh api repos/{owner}/{repo}/pulls?state=closed` + `gh pr list --json number,title,mergedAt,headRefName` covers:
- Merged PR detection with branch names (strongest "task complete" signal)
- Open PR detection (implies task is in Review, not In Progress)

**Why not GitPython 3.1.50:** GitPython wraps the same `git` subprocess internally. It adds `gitdb` dependency, documented resource-leak risk for long-running processes (relevant since skill sessions can span many repos), and `RecursionError` risk on large tree traversals. The object-oriented API gives no benefit over structured `--format` strings for the specific signals we need (commit timestamps, messages, file diffs, branch names). Confirmed not installed; would be a new dep.

**Why not PyGithub:** Would add a new dep and requires a separate token config. `gh` CLI already handles auth and is already in the stack for `sheets_sync.py`.

**Why not `requests` for GitHub API directly:** `requests` is in `requirements.txt` but `gh` CLI handles auth, pagination, rate-limit backoff, and retries automatically. No benefit to reimplementing this.

### 2. Claude Code Skill Structure

**Package as `.claude/skills/reconcile-activity/` with a `SKILL.md` + `scripts/` directory.**

Official Claude Code skills (confirmed at https://code.claude.com/docs/en/skills, 2026-06-04):
- `SKILL.md` is the entrypoint; directory name becomes the `/reconcile-activity` command
- `disable-model-invocation: true` — must be explicit user invocation; never auto-triggered on unrelated prompts
- `context: fork` — runs in a subagent context to isolate the multi-repo write-back from the main session
- `allowed-tools: Bash Read Write` — constrain tool surface to what the skill actually needs
- `` !`command` `` lines in SKILL.md run at load time and inject output into the prompt — use to pre-load the list of symlinked repos and current git status before Claude reads the instructions
- Supporting Python helpers go in `scripts/` alongside `SKILL.md`; referenced from the skill body
- Live file change detection: edits to `SKILL.md` take effect in the current session without restart

Skill orchestrates Python helpers via `Bash` tool calls, not inline Python. The Python scripts in `scripts/` do the heavy lifting (git mining, kanban parsing, sanitization, change-list generation); the skill's `SKILL.md` provides the decision logic and batch-confirm gate.

The existing `.claude/commands/commit.md` pattern (user-invocable, imperative steps) is the right model for this skill's tone.

### 3. Mermaid-Safe String Sanitization

**Use: stdlib `unicodedata` + `re` — no new library.**

Verified emoji Unicode categories in migration-gantt.md context:
- `🚀 ✅ 📌 ⚡ 🔧 🎯 💡 ⚠` → all `So` (Symbol, other) — stripped by category check
- `️` (variation selector-16) → `Mn` (Mark, nonspacing) — stripped by category check

Characters that break Mermaid gantt/kanban/pie syntax (confirmed from mermaid-js issue tracker and existing gantt source):
- `:` — gantt uses `task name :id, date, duration` format; colon in task name breaks parser
- `(` `)` — parentheses in task names cause parse failures in gantt
- `"` — quotes in section/task names break tokenization
- `#` `;` — both break gantt (documented in mermaid-js/mermaid#1981)
- `{` `}` — flowchart/subgraph syntax
- `|` — table/flowchart syntax

Safe sanitization function (all stdlib, no new dep):

```python
import re, unicodedata

def mermaid_safe(text: str) -> str:
    """Strip emoji and chars that break Mermaid gantt/kanban/pie syntax."""
    # 1. Strip emoji and symbol characters by Unicode category
    cleaned = []
    for ch in text:
        cat = unicodedata.category(ch)
        # So=Symbol,other  Mn=Mark,nonspacing (variation selectors)
        # Cs=surrogate  Cf=format (RTL/LTR marks)  Co=private use
        if cat in ('So', 'Mn', 'Cs', 'Cf', 'Co'):
            continue
        cleaned.append(ch)
    s = ''.join(cleaned)
    # 2. Strip Mermaid syntax-breaking punctuation
    s = re.sub(r'[():\"#;{}|]', '', s)
    # 3. Collapse multiple spaces
    s = re.sub(r'  +', ' ', s).strip()
    return s
```

This is sufficient for the existing failure modes. The `regex` module (PyPI) with `\p{So}` would be cleaner but is not installed, not in requirements.txt, and provides no additional coverage for the known emoji categories.

Apply sanitization: to Mermaid block content only, not to `kanban.md` write-back. Kanban content should preserve original emoji (they are data); Mermaid rendering is where they must be stripped.

### 4. Safe Multi-Repo Write-Back + Push

**Pattern: read-only activity mining → generate full change list → single batch confirm → atomic per-repo commit+push.**

Git operations are pure subprocess. Protocol:

1. Pre-flight check per repo:
   - `git rev-parse --abbrev-ref HEAD` → must be on `master` (or configured default branch); abort if detached HEAD or feature branch
   - `git status --porcelain` → must be clean before write-back; abort if dirty (uncommitted changes would be mixed with skill changes)
   - `git remote get-url origin` → verify remote exists before push attempt
2. Write corrected `kanban.md` (Python file write via `pathlib.Path.write_text(content, encoding='utf-8')`)
3. Stage: `git add kanban.md`
4. Commit: `git commit -m "chore: reconcile kanban status [skip ci]"` — `[skip ci]` prevents the `notify-kf-cpto.yml` dispatch from double-triggering; the skill will fire a single explicit `kf-cpto` dispatch after all repos are written
5. Push: `git push origin {branch}`
6. After all repos pushed: trigger `kf-cpto` pipeline manually once (via `gh workflow run aggregate.yml`) rather than relying on N individual `repository_dispatch` events

Batch confirm gate: collect all proposed changes across all repos into a single diff list, print to terminal, prompt once for `y/N`, then execute the commit+push loop. This matches the [NO prompting during org scans] project memory constraint — one confirmation for N repos, never per-repo.

Branch hygiene: the skill never creates branches. It commits directly to the default branch of each tracked repo. Feature branches in tracked repos are a signal (activity mining input), not a target for write-back.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `subprocess` + `git` | GitPython 3.1.50 | Only if you need programmatic access to git object internals (blob/tree traversal for diff analysis). Not needed here — structured `--format` output is sufficient. |
| `gh` CLI for PR/branch data | `requests` + GitHub REST API directly | If `gh` CLI is unavailable or you need batch API calls across hundreds of repos (gh CLI doesn't batch). Neither condition applies here. |
| `unicodedata` + `re` for sanitization | `emoji` library (PyPI 2.x) | If you need to detect emoji by name, replace rather than strip, or map emoji to text descriptions. Not needed — strip-only is correct for Mermaid output. |
| `.claude/skills/` structure | `.claude/commands/` plain file | `.claude/commands/` still works and is simpler. Use `.claude/skills/` because the skill needs supporting Python script files alongside `SKILL.md` and `disable-model-invocation` frontmatter to prevent auto-triggering. |
| `pyyaml` roundtrip for frontmatter | `ruamel.yaml` | `ruamel.yaml` preserves comments and key ordering. Use it if kanban.md frontmatter has hand-written comments that must survive write-back. Current template has inline comments; `pyyaml.dump` will drop them. Evaluate before implementing write-back. |
| stdlib `difflib.unified_diff` | `rich` diff display | `rich` provides colored terminal output. Add it only if the change-list UX proves hard to read in plain text — not a first-pass requirement. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| GitPython | New dependency with documented resource-leak risk and no benefit over `subprocess` for the specific signals needed. The skill runs locally across N repos; resource leaks compound. | `subprocess` + `git --format` |
| `dulwich` (0.24.10 available) | Pure Python git implementation — useful for CI without a git binary, but adds a dep, has incomplete support for porcelain commands, and is slower than subprocess for activity mining. | `subprocess` + `git` |
| PyGithub | Redundant with `gh` CLI, requires separate token management, adds a new dep. | `gh` CLI with `--json` |
| `regex` (PyPI) | Not installed, not needed — `unicodedata.category()` correctly identifies all emoji categories present in this project's content. | stdlib `unicodedata` + `re` |
| Adding a second kanban.md parser in the skill | Violates the "one parser, one canonical intermediate" architectural constraint. Importing `utils.parse_kanban_*` from the existing pipeline is the correct approach. | Import `scripts/utils.py` functions directly |
| `context: fork` without `disable-model-invocation: true` | A forked skill can still be auto-triggered by Claude if the description matches ambient conversation. Multi-repo write-back must never be auto-triggered. | Both flags together |
| `git push --force` in write-back | Tracked repos may have CI protection rules; force-push would override them and destroy remote history. | `git push origin {branch}` (fast-forward only); fail and report if the branch has diverged |
| Per-repo push confirmation prompts | Matches the [NO prompting during org scans] memory constraint — interactive stalls across N repos. | Single batch confirm before any pushes begin |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Python 3.9 (local venv) | `pyyaml>=6.0`, stdlib `unicodedata`, `re`, `pathlib`, `subprocess`, `json`, `difflib`, `datetime` | All stdlib modules used are 3.9-stable. `pyyaml` 6.x requires 3.6+. No compatibility issues. |
| `gh` CLI 2.87.3 | GitHub REST API v3 | `--json` flag and `gh api` are stable features. `gh pr list --json` fields (`number`, `title`, `mergedAt`, `headRefName`) confirmed working. |
| Claude Code skills | Current (2026-06-04 spec) | `disable-model-invocation`, `context: fork`, `allowed-tools`, `!backtick` dynamic injection are all current. `.claude/commands/` files still work but `.claude/skills/` is the recommended path going forward. |
| `pyyaml` `dump(allow_unicode=True)` | kanban.md with Romanian/UTF-8 content | Required. Without `allow_unicode=True`, pyyaml escapes non-ASCII characters as `\uXXXX` sequences, corrupting project names and descriptions in frontmatter. |

---

## Architectural Fit Notes

These choices respect the existing constraints explicitly:

- **One parser rule:** The skill imports `utils.parse_kanban_frontmatter()` and `utils.parse_kanban_tasks()` from `scripts/utils.py` for reading. For writing, it re-serializes only the frontmatter block (pyyaml roundtrip) and leaves the task table body as a raw string, preserving the existing table format.
- **Exit-0 invariant:** The skill is entirely local and never runs in CI. It cannot affect the `sheets_sync.py` exit-0 guarantee.
- **Deterministic CI:** The skill writes corrected `kanban.md` files and pushes to project repos, which triggers the existing `notify-kf-cpto.yml → repository_dispatch → aggregate.yml` pipeline. The pipeline itself is unchanged and remains deterministic.
- **No `repos/` commits:** The skill reads from symlinked sibling checkouts, not from `repos/`. The `repos/` directory remains CI-runtime-only and gitignored.
- **`[skip ci]` on skill commits:** Skill commits to tracked repos use `[skip ci]` to suppress the `notify-kf-cpto.yml` dispatch from each individual repo. A single explicit `gh workflow run` on `kf-cpto` fires one clean pipeline run after all repos are updated.

---

## Sources

- https://code.claude.com/docs/en/skills — Claude Code skills specification (frontmatter fields, `SKILL.md` structure, dynamic context injection, `disable-model-invocation`, `context: fork`). Fetched 2026-06-04. HIGH confidence.
- https://github.com/mermaid-js/mermaid/issues/1981 — Confirmed `#` and `;` break Mermaid gantt parser; escaping not supported in that context. MEDIUM confidence (issue references a PR fix but exact v11 behavior unverified against live instance).
- `pip index versions GitPython` → 3.1.50 (latest); GitPython docs at https://gitpython.readthedocs.io/en/stable/tutorial.html re: resource-leak risk and subprocess-backed implementation. HIGH confidence.
- Local verification: `subprocess` git operations confirmed against `/Users/machina/Dev/kf-cpto`; `gh` CLI JSON output confirmed; `unicodedata.category()` emoji detection confirmed; `pyyaml` roundtrip confirmed. HIGH confidence.
- `.planning/codebase/STACK.md`, `.planning/codebase/ARCHITECTURE.md` — existing stack constraints. HIGH confidence (source-of-truth for this project).

---

*Stack research for: activity-driven kanban reconciliation skill (kf-cpto milestone 2)*
*Researched: 2026-06-04*
