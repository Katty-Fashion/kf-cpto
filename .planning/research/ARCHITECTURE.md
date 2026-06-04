# Architecture Research

**Domain:** Agentic-capacity activity-driven migration dashboard (local Claude skill + existing Python/Jekyll CI pipeline)
**Researched:** 2026-06-04
**Confidence:** HIGH — based on direct codebase analysis, not speculation

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        LOCAL ENVIRONMENT (developer machine)                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    CLAUDE SKILL (new, this milestone)                   │ │
│  │                                                                         │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────────┐ │ │
│  │  │ repo_enum.py │  │ activity.py   │  │ reconcile.py                 │ │ │
│  │  │              │  │               │  │                              │ │ │
│  │  │ Enumerate    │  │ Mine git +    │  │ Diff declared vs observed;   │ │ │
│  │  │ tracked repos│  │ kanban signals│  │ compute agentic overflow;    │ │ │
│  │  │ (symlink-    │  │ per repo      │  │ emit change list             │ │ │
│  │  │  aware)      │  │               │  │                              │ │ │
│  │  └──────┬───────┘  └──────┬────────┘  └──────────────┬───────────────┘ │ │
│  │         │                 │                           │                 │ │
│  │         └─────────────────┴───────────┬───────────────┘                 │ │
│  │                                       ▼                                 │ │
│  │                           ┌───────────────────────┐                     │ │
│  │                           │ writeback.py          │                     │ │
│  │                           │                       │                     │ │
│  │                           │ Sanitize Mermaid;     │                     │ │
│  │                           │ write kanban.md;      │                     │ │
│  │                           │ batch-confirm; push   │                     │ │
│  │                           └───────────┬───────────┘                     │ │
│  └───────────────────────────────────────┼─────────────────────────────────┘ │
│                                          │ git push (per repo)               │
│  ┌───────────────────────────────────────┼─────────────────────────────────┐ │
│  │  SIBLING REPO CHECKOUTS (symlinked)   │                                 │ │
│  │  ~/Dev/kf-cpto/repos-local/           │                                 │ │
│  │  ├── repo-a -> ../../repo-a/          │                                 │ │
│  │  ├── repo-b -> ../../repo-b/          │                                 │ │
│  │  └── repo-n -> ../../repo-n/          │                                 │ │
│  └───────────────────────────────────────┼─────────────────────────────────┘ │
└──────────────────────────────────────────┼─────────────────────────────────┘
                                           │ repository_dispatch (kanban-updated)
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                   CI / GITHUB ACTIONS (existing, unchanged)                  │
│                                                                              │
│  aggregate.yml: discover → clone → validate → aggregator.py → deploy Pages  │
│                                      │                                       │
│                          aggregator.build_loe_rows()  ◄── Agentic assignee  │
│                          aggregator.write_loe_yaml()      rows live here     │
│                                      │                                       │
│                          docs/_data/loe.yml (canonical intermediate)         │
│                                      │                                       │
│                          sheets_sync.py (reads loe.yml, never kanban.md)    │
│                                      │                                       │
│                    GitHub Pages (canonical) + Google Sheets (downstream)     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### Skill — Smart Input Layer (new code, local only)

| Component | Responsibility | Location (proposed) |
|-----------|----------------|---------------------|
| `repo_enum.py` | Enumerate tracked repos: resolve symlinks in `repos-local/`, verify each has `kanban.md` + `notify-kf-cpto.yml`; return list of `(name, local_path, remote_url)` tuples | `scripts/skill/repo_enum.py` |
| `activity.py` | Per-repo activity mining: read `kanban.md` declared state; read git log, open branches, recent PRs (via `git` CLI, no GitHub API required since local checkout exists); produce a normalized `ActivitySnapshot` per task | `scripts/skill/activity.py` |
| `reconcile.py` | Diff declared vs. observed state; apply status corrections; run agentic-overflow capacity model; emit `ReconcileResult` (list of changes + updated task rows) | `scripts/skill/reconcile.py` |
| `writeback.py` | Sanitize Mermaid-breaking chars in task text; write corrected `kanban.md` to each repo's local checkout; present batch-confirm summary; push each repo (one git push per repo, confirmed as a batch) | `scripts/skill/writeback.py` |
| `skill_main.py` | Entry point / orchestrator for the skill; imports above modules; handles the confirm gate | `scripts/skill/skill_main.py` |

**Skill boundary rule:** The skill stops at the moment `git push` completes on the last tracked repo. Everything that follows — `repository_dispatch`, clone, aggregate, deploy, Sheets sync — is owned by existing CI and must not be touched.

### Existing Pipeline — Deterministic Renderer (unchanged invariants)

| Component | Role in new flow | What changes |
|-----------|-----------------|--------------|
| `aggregator.build_loe_rows()` | Reads the corrected `kanban.md` (now may include `Agentic` assignee rows from skill's writeback) and produces LOE rows as before | **Extend** to pass through `Agentic` as a valid assignee — no other change |
| `aggregator.write_loe_yaml()` | Writes extended rows (including Agentic rows) to `loe.yml` | No code change needed if `assignee` field already flows through as a string |
| `sheets_sync.py` | Reads `loe.yml` exactly as today — Agentic rows appear automatically | No change |
| `auto_blocks.py` / `migration-gantt.md` | §8.2 capacity block needs updating to reference agentic deferral instead of "add 0.5 FTE" | Replace prose content and/or add an `AUTO:capacity` block — the engine itself unchanged |

---

## Decision 1: Where the Agentic-Overflow Capacity Model Lives

**Recommendation: The model runs inside the skill (`reconcile.py`). The aggregator receives its output as ordinary task rows with `assignee: Agentic`.**

Rationale:

The capacity model requires LLM-assisted judgement: it must read the migration-gantt plan, understand which tasks belong to FE vs. BE, compute cumulative hours against the 2-FTE cap, and decide which specific tasks overflow. That reasoning cannot be expressed as a deterministic Python function with the information available at CI time (CI sees only the kanban.md snapshots it just cloned; it has no conversational context).

By having the skill emit rows with `assignee: Agentic` directly into `kanban.md`, the aggregator receives a first-class assignee just like `@frontend` or `@backend`. The LOE model then "renders correctly" in an entirely deterministic way — `build_loe_rows()` sees `Agentic` as a string, writes it to `loe.yml`, `sheets_sync.py` exports it, and the gantt/LOE views show it as their own slice.

If the model lived in `aggregator.py` it would need to re-apply the capacity logic on every CI run. That re-derivation would require the same overflow decisions to be stable across runs, which is only guaranteed if the inputs (task rows) are stable — and those inputs come from the very kanban.md the skill just wrote. It is circular. Putting the model in the aggregator buys nothing and risks non-determinism.

**Exit invariant preserved:** The aggregator gets cleaner input and can stay "dumb." `sheets_sync.py` is never touched.

---

## Decision 2: Where Mermaid Sanitization Lives

**Recommendation: Sanitize in `writeback.py` (skill-side, pre-write). Do NOT add sanitization to the aggregator.**

Rationale:

The aggregator currently renders `unified-kanban.md`, `dependency-graph.md`, and `migration-gantt.md` from kanban.md inputs. If a hand-edited task contains an emoji or a pipe character, the generated Mermaid diagram breaks silently at render time in the Jekyll layout.

Sanitizing at write time in the skill means the kanban.md on disk is always clean. Every subsequent pipeline run — whether triggered by the skill's push or a human's direct edit — produces valid diagrams. The aggregator does not need to know about the sanitization; it simply reads clean data.

If sanitization lived in the aggregator it would: (a) run at every CI invocation including human pushes that don't go through the skill, making it the canonical fence — which is correct but a larger scope change for this milestone; and (b) silently mask bad data in kanban.md rather than cleaning it at source.

For this milestone, skill-side pre-write sanitization is the minimal correct choice. A follow-on hardening can add aggregator-side sanitization as a belt-and-suspenders layer.

**Specific sanitizations to apply in `writeback.py`:**
- Strip or replace Unicode emoji characters in task text and assignee fields
- Escape or remove bare pipe `|` characters inside table cell text (breaks MD table parsing)
- Truncate task text that exceeds a safe Mermaid label length (>80 chars causes diagram overflow)
- Normalize effort strings to `\d+(\.\d+)?d` pattern before writing

---

## Decision 3: Local Repo Access Layout

### Directory Layout

```
kf-cpto/
├── repos/              # CI runtime-only (gitignored, shallow clones)
│   └── discovered.txt  # Written by discover.py
└── repos-local/        # NEW: skill-only (gitignored), symlinks to sibling checkouts
    ├── repo-a          -> ../../repo-a/        (symlink)
    ├── repo-b          -> ../../repo-b/        (symlink)
    └── ...
```

`repos-local/` is a new gitignored directory. Each entry is a symlink to the actual sibling checkout directory on the developer's machine. The path `../../repo-a/` is relative to `repos-local/` and assumes the standard layout `~/Dev/{repo-name}/`.

This keeps `repos/` pristine for CI use (CI creates it fresh on each run) and gives the skill a separate namespace that is unambiguously "local checkout" vs "CI shallow clone."

### Tracking "Tracked" Repos

A repo is "tracked by the skill" when its local checkout contains both:
1. `kanban.md` at the repo root
2. `.github/workflows/notify-kf-cpto.yml` (the dispatch trigger)

`repo_enum.py` enumerates by iterating `repos-local/`, resolving each symlink, and checking for both files. No static list needed — adding a new checkout + symlink is sufficient.

The canonical dynamic list (`repos/discovered.txt`) is the CI source of truth. The skill's `repos-local/` is the local developer's working set. They will overlap but are not required to be identical — a repo may be in `discovered.txt` but not yet symlinked locally, and vice versa. The skill only operates on what is locally present.

### Coexistence with CI's `repos/`

CI creates `repos/` from scratch on each run. The skill never writes to `repos/`. Gitignore covers both:

```
# .gitignore additions
repos-local/
```

(The existing `/repos/` entry in `.gitignore` already covers the CI directory.)

---

## Data Flow: The Write-Back Loop End-to-End

```
[1] SKILL — repo_enum.py
    Reads repos-local/ symlinks → resolves to sibling checkout paths
    Output: list of (repo_name, local_path, remote_url)

[2] SKILL — activity.py
    For each repo:
      - Read kanban.md (declared state)
      - Read git log --oneline HEAD~30..HEAD (recent commits)
      - Read git branch -r (active remote branches)
      - Read git log --all --oneline --grep="Closes #" (PR-linked refs)
    Output: ActivitySnapshot per repo {declared_tasks, git_signals}

[3] SKILL — reconcile.py
    For each repo's ActivitySnapshot:
      - Diff declared status vs. git evidence
        (e.g. branch merged → task Done; commits on branch → In Progress)
      - Run agentic capacity model:
          * Load migration-gantt.md FE/BE task breakdown
          * Accumulate effort per assignee vs. 2-FTE cap (1 FE × 100%, 1 BE × 100%)
          * Tasks that push assignee over 100% → reassign to Agentic in kanban.md
      - Emit ReconcileResult: {changed_tasks: [...], change_log: [...]}

[4] SKILL — writeback.py
    For each repo with changes:
      - Apply Mermaid sanitization to all task text fields
      - Rewrite kanban.md with updated task rows
      - Stage + commit: "chore(skill): reconcile activity [YYYY-MM-DD]"
    Present batch summary of all changes across all repos
    Await single user confirmation (no per-repo prompt — matches no-prompting preference)
    On confirm:
      - git push origin HEAD for each repo

[5] PROJECT REPO — notify-kf-cpto.yml
    Detects push to kanban.md on default branch
    Fires repository_dispatch event type=kanban-updated to katty-fashion/kf-cpto

[6] KFCPTO CI — aggregate.yml
    Triggered by repository_dispatch
    Step: discover.py — re-enumerates org (picks up any new repos)
    Step: clone repos/ — shallow-clones all discovered repos
                         (gets the just-pushed kanban.md with Agentic rows)
    Step: validate_auto_blocks.py — lint AUTO markers
    Step: aggregator.py:
          - load_all_project_data() reads updated kanban.md files
          - build_loe_rows() emits rows including assignee="Agentic"
          - write_loe_yaml() → docs/_data/loe.yml (Agentic rows included)
          - generate_loe_report() renders LOE view with Agentic slice
          - generate_unified_kanban() renders kanban with Agentic tasks
          - auto_blocks.process_page() refreshes migration-gantt.md AUTO blocks
    Step: commit docs/ → push master
    Step: deploy gh-pages → GitHub Pages live

[7] KFCPTO CI — sheets_sync.py
    Reads docs/_data/loe.yml (Agentic rows present as ordinary rows)
    Stages → validates → swaps into LOE Sheet
    Exit 0 always (exit-0 invariant preserved)

[8] Dashboard live:
    - loe-report.md: Agentic appears as its own assignee row/slice
    - unified-kanban.md: Agentic tasks visible in kanban view
    - migration-gantt.md §8.2: capacity model shows agentic deferral
    - Google Sheet LOE tab: Agentic row exported downstream
```

**Where the Agentic model must live to render correctly:** Step [3] — inside `reconcile.py` in the skill. The model's output (tasks with `assignee: Agentic`) is written to `kanban.md` at Step [4]. From Step [6] onward the pipeline is purely deterministic: it reads what is in `kanban.md` and renders it. No special knowledge of the capacity model is needed anywhere in CI.

---

## Recommended File Structure (new code only)

```
kf-cpto/
├── scripts/
│   └── skill/                      # NEW: local Claude skill (never called by CI)
│       ├── __init__.py
│       ├── skill_main.py           # Entry point: orchestrates repo_enum → activity
│       │                           #   → reconcile → writeback
│       ├── repo_enum.py            # Enumerate repos-local/ symlinks; verify kanban.md
│       │                           #   + notify workflow present
│       ├── activity.py             # Mine git signals + kanban declared state per repo
│       ├── reconcile.py            # Diff declared vs. observed; run agentic capacity
│       │                           #   model; emit change list
│       └── writeback.py            # Sanitize, write kanban.md, batch-confirm, push
├── repos-local/                    # NEW: gitignored symlinks to sibling checkouts
│   └── (symlinks — not committed)
└── .planning/
    └── research/                   # this file lives here
```

**Existing files that need targeted edits (not rewrites):**

- `scripts/utils.py`: Add `AGENTIC_ASSIGNEE = "Agentic"` constant so both skill and aggregator share one spelling. Add `MERMAID_SAFE_RE` pattern for sanitization validation.
- `docs/migration-gantt.md`: Replace §8.2 "add 0.5 FTE" recommendation with agentic deferral prose. Consider adding an `AUTO:capacity` block if the capacity numbers should be computed from `loe.yml`.
- `.gitignore`: Add `repos-local/` entry.

---

## Architectural Patterns

### Pattern 1: Write-Back via Existing Dispatch (not a new CI path)

**What:** The skill writes corrected kanban.md to sibling repo checkouts and pushes. The existing `notify-kf-cpto.yml` in each repo fires the dispatch, which triggers the existing `aggregate.yml`. No new CI workflow is needed.

**When to use:** Always. This is the only write path the skill uses.

**Trade-offs:** The skill is not aware of whether CI actually ran — it fires-and-forgets after push. This is correct: the skill's job is to produce accurate inputs; CI's job is to render them. Dashboard latency is ~2–4 minutes (CI run time) after push.

### Pattern 2: Canonical Assignee Injection (not a schema change)

**What:** The Agentic assignee is introduced purely as a new string value of the existing `assignee` field in kanban.md task rows. No new columns, no new frontmatter keys, no schema migration.

**When to use:** For the overflow capacity model. Any task the skill decides exceeds FTE capacity gets its `assignee` field rewritten to `Agentic`.

**Trade-offs:** Simplest possible change. The aggregator, sheets_sync, and all rendering code see it as a first-class row with no special casing. The downside is that the original assignee information is lost in the kanban.md row — if tracking "originally assigned to FE but deferred to Agentic" is needed later, a second field (e.g., `original_assignee`) would need to be added to the 6-column format.

### Pattern 3: Batch-Confirm Gate (single prompt, N repos)

**What:** `writeback.py` accumulates all changes across all repos, presents a summary (repo name, number of tasks changed, change types), and waits for a single user confirmation before pushing any repo. All pushes succeed or the operation is aborted (no partial writes if user declines).

**When to use:** Every skill invocation that results in write-back.

**Trade-offs:** Matches the org-scan no-prompting preference (one confirm, not per-repo). The risk is that a large batch with one bad change requires aborting the whole batch and re-running. Mitigation: the change list is shown per-repo so the user can see exactly what will be pushed.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Agentic Model in aggregator.py

**What people do:** Add capacity computation logic to `aggregator.build_loe_rows()` so Agentic rows are derived at CI render time.

**Why it's wrong:** The aggregator runs in CI without conversational context, LLM access, or the full migration-gantt plan parsed as structured data. Re-deriving the overflow assignment on every CI run requires the same deterministic inputs each time — but the whole point of the capacity model is to make a judgement call that stabilizes into the kanban.md. If the model runs at CI time it either produces the same answer every run (in which case it should have been run once and written back) or it produces different answers on different runs (non-determinism).

**Do this instead:** Run the model once in the skill, write the Agentic assignee into kanban.md, push. Let CI be the dumb renderer.

### Anti-Pattern 2: Symlink `repos-local/` → `repos/`

**What people do:** Reuse the existing `repos/` directory for the skill's local checkouts, either by symlinking into it or by placing local checkouts there.

**Why it's wrong:** `repos/` is created fresh by CI at each run. CI's clone step does not check for existing content — it will overwrite or conflict with any files placed there. The separation between `repos/` (CI shallow clones) and `repos-local/` (developer full checkouts via symlinks) is the correct boundary.

**Do this instead:** Use `repos-local/` for skill-side symlinks. Never write to `repos/` from the skill.

### Anti-Pattern 3: Skill Reads loe.yml as Its Canonical Input

**What people do:** Have the skill read `docs/_data/loe.yml` to understand the current state of tasks, since it is the "canonical intermediate."

**Why it's wrong:** `loe.yml` is an output, not an input. It reflects the last aggregator run, which may be hours or days stale compared to the actual kanban.md files in the repos. The skill must read kanban.md directly from the local checkouts to get the actual current declared state.

**Do this instead:** The skill reads kanban.md from sibling checkouts. `loe.yml` is irrelevant to the skill. The skill's output becomes the new kanban.md, which on the next CI run becomes the new `loe.yml`.

### Anti-Pattern 4: Per-Repo Confirm Prompt

**What people do:** Ask the user "push to repo-a? (y/n)" before each repo push.

**Why it's wrong:** Violates the established no-prompting-during-org-scans preference. With N tracked repos, N prompts stalls the workflow and makes the skill tedious for the common case where all changes are expected.

**Do this instead:** Collect all changes, show a single batch summary, confirm once, push all. For the destructive exception, confirm once if any repo has unusually large diffs (e.g., >50% of tasks changed).

### Anti-Pattern 5: Mermaid Sanitization Only in Aggregator

**What people do:** Add emoji-stripping / pipe-escaping logic to `aggregator.py` so it cleans data at render time, leaving kanban.md files dirty.

**Why it's wrong:** Dirty kanban.md means every human who reads the file (or diffs it) sees the bad content. The aggregator runs at CI time with no way to push a correction back to the source repo. The sanitization is invisible and the source stays corrupt.

**Do this instead:** Sanitize in `writeback.py` before writing kanban.md. The file on disk is always the clean version. Aggregator-side sanitization can be added later as a lint/safety layer, but it should not be the primary fence.

---

## Integration Points

### External: Git (via CLI in skill)

| Operation | Tool | Notes |
|-----------|------|-------|
| Read recent commits | `git log` in sibling checkout | No GitHub API needed; local clone has full history |
| Read branch list | `git branch -r` | Reveals in-flight work not yet in kanban.md |
| Write and commit | `git add / git commit` | Skill commits the corrected kanban.md with a consistent message prefix |
| Push | `git push origin HEAD` | After batch confirm; uses the checkout's existing remote config |

### External: GitHub API (skill does NOT call it)

The skill does not need to call the GitHub API. Discovery of which repos are "tracked" is done by checking for `notify-kf-cpto.yml` in the local checkout. The GitHub API is the CI pipeline's concern (via `discover.py`).

### Internal: Skill → Existing Pipeline Boundary

| Boundary | Communication | Invariant |
|----------|---------------|-----------|
| Skill → project repo | `git push` to the repo's remote | Skill writes `kanban.md` only; no other files |
| Project repo → kf-cpto CI | `repository_dispatch` (via `notify-kf-cpto.yml`) | Fires automatically on push to kanban.md; skill does not trigger it directly |
| CI aggregator → LOE | `loe.yml` (written by aggregator, read by sheets_sync) | Never re-parsed by skill; one-parser invariant preserved |
| CI aggregator → Agentic rendering | `assignee: Agentic` in kanban.md rows | Aggregator treats it as a string; no special casing needed |

---

## Build Order / Phase Implications

The skill's components have a natural dependency order that should drive phase sequencing:

### Phase 1 — Repo Access Foundation
Build `repo_enum.py` + the `repos-local/` symlink convention. Validate that the skill can enumerate tracked repos, read their kanban.md files, and inspect git history. No writes yet. This phase produces the plumbing everything else depends on.

**Inputs to subsequent phases:** confirmed list of (repo, path, git log) tuples; proven gitignore hygiene; no CI interference.

### Phase 2 — Activity Mining + Reconciliation (read-only)
Build `activity.py` + `reconcile.py` through to the point of producing a `ReconcileResult` (change list) that can be reviewed by the user but not yet written back. This is the "show me what would change" mode. The capacity model stub can live here producing placeholder Agentic rows.

**Gate:** User reviews the proposed changes and agrees the signal-to-noise ratio is acceptable before any write-back is built.

### Phase 3 — Write-Back + Sanitization
Build `writeback.py` including Mermaid sanitization, the batch-confirm gate, and the git push. Wire `skill_main.py`. This phase closes the write-back loop. At the end of this phase, a full skill invocation produces a push that triggers CI and deploys corrected dashboards.

**Gate:** End-to-end test: skill runs, pushes, dispatch fires, aggregator runs, Pages deploys with updated data including at least one Agentic row.

### Phase 4 — Agentic Capacity Model (full implementation)
Implement the FE/BE capacity model properly: parse migration-gantt.md task breakdown, accumulate hours, identify and assign overflow tasks to Agentic. Extend `build_loe_rows()` with the `AGENTIC_ASSIGNEE` constant. Update migration-gantt.md §8.2.

**Dependency on Phase 3:** The write-back loop must already work before the model's output can be validated end-to-end.

### Phase 5 — Hardening + Dashboard Polish
- Add aggregator-side sanitization as belt-and-suspenders
- Add `AUTO:capacity` block to migration-gantt.md if capacity numbers should be auto-computed
- Improve the batch-confirm summary format
- Validate diagram robustness across all existing repos

---

## Scaling Considerations

This is a 2-FTE team tool with N = O(10) repos. Scaling is not a concern. The relevant robustness axes are:

| Concern | Approach |
|---------|----------|
| Symlink resolution failures (repo not checked out locally) | `repo_enum.py` skips missing symlinks, logs which repos were skipped; skill continues with what is available |
| Stale local checkout (repo checkout is behind remote) | `activity.py` checks `git fetch` output; warns if local HEAD is behind remote HEAD; reconciliation runs anyway on local state |
| Mermaid sanitization edge cases | Pre-write validation step in `writeback.py` checks the sanitized content against a regex before committing; aborts with a clear error if the result is still unsafe |
| CI dispatch not firing (notify workflow missing or PAT expired) | Out of skill scope — this is an existing CI concern. Skill's job ends at push. |

---

## Sources

- Direct codebase analysis: `.planning/codebase/ARCHITECTURE.md`, `scripts/aggregator.py:489-598`, `scripts/utils.py`, `.github/workflows/aggregate.yml`, `templates/kanban.md`
- Milestone requirements: `.planning/PROJECT.md`
- Invariants confirmed from code inspection (not inferred): exit-0 at `scripts/sheets_sync.py:397`; one-parser contract at `aggregator.build_loe_rows():489`; AUTO-block idempotence at `auto_blocks.py:169`; `repos/` runtime-only confirmed in `.gitignore` and `aggregate.yml:41`

---

*Architecture research for: kf-cpto agentic-capacity skill + pipeline integration*
*Researched: 2026-06-04*
