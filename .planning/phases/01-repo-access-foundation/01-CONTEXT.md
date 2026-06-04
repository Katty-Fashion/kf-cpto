# Phase 1: Repo Access Foundation - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

The skill can enumerate all tracked repos, verify their layout, fetch remote state, and read `kanban.md` — with **no writes and zero CI impact**. This phase delivers the read-only access foundation: a `repo_enum.py` that resolves the curated tracked-repo set from local checkouts, runs `git fetch` per repo, parses each `kanban.md` through the existing `scripts/utils.py` parsers, and proves the kf-cpto working tree stays clean. No reconciliation, no write-back, no capacity modelling — those are later phases.

</domain>

<decisions>
## Implementation Decisions

### Skill Structure & Topology
- Skill lives at `.claude/skills/activity-sync/` with a `SKILL.md` index plus Python modules (project skill dir per CLAUDE.md conventions).
- `repo_enum.py` lives inside the skill dir and imports `scripts/utils.py` from the repo root via `sys.path` injection — honoring the one-parser constraint (REPO-03); no second kanban parser.
- Tracked sibling checkouts live under a gitignored `repos-local/` directory at the repo root (distinct from CI's runtime `repos/`).
- **Bootstrap helper clones missing tracked repos into `repos-local/`** (user-selected over symlink-only). The skill is self-sufficient on a fresh machine — it clones any tracked repo not yet present, then operates on the local checkout.
- For tracked repos missing markers, bootstrap **seeds** `kanban.md` and/or `notify-kf-cpto.yml` from `templates/` so they join the standard notify → dispatch pipeline.

### Tracked Repo Set (Curated Allowlist)
- The tracked set is an **explicit, user-curated allowlist**, NOT pure marker auto-discovery across the whole org.
- The allowlist is realized by **`repos-local/` membership** — which repos are cloned/symlinked there IS the list. This keeps "no static project list in skill code" (REPO-01 intent): enumeration scans `repos-local/` at runtime rather than reading a hardcoded array.
- The set **may include repos absent from the migration-gantt plan** — the skill must support adding new repos over time, not just the original gantt repos.
- **Initial tracked set (6 repos) to seed into `repos-local/`:**
  | Repo | default branch | markers today | in gantt? |
  |------|----------------|---------------|-----------|
  | kf-be-platform | main | kanban + notify | yes |
  | kf-fe-platform | main | kanban + notify | yes |
  | kf-platform | master | kanban + notify | yes |
  | R3-AAS | main | kanban only (seed notify) | yes |
  | ai-rise-options | master | none (seed both) | **no — new-repo example** |
  | tech_brainstorming | main | none (seed both) | **no — new-repo example** |
- `ai-rise-options` and `tech_brainstorming` are deliberately included as the worked example of "track a repo that is NOT in the initial migration gantt."
- Org context: 33 repos total in `katty-fashion`; 11 carry markers today. Excluded by curation: `Aladin-01`, `order-service`, `NuoForm---GTM`, `AIRise-ai-fabric-inspection` (core gantt repos with markers, but not in this tracked set), plus non-projects `project-template` (seed template), `Edi-test` (test repo), `R3GROUP` (archived). `donot_order-service` (a local duplicate checkout of `order-service`) is excluded — duplicate remote.

### Enumeration Behavior & Output
- A directory qualifies for enumeration by being present in `repos-local/`; marker presence (`kanban.md` + `notify-kf-cpto.yml`) is verified and seeded if absent (rather than used as the sole gate).
- Output: human-readable list of `(name, local_path, remote_url)` tuples to stdout (success criterion 1) **plus** a structured return value (Python objects) for downstream Phase 2 consumption.
- Default branch is resolved per repo (some are `main`, some `master`) — never hardcode a single branch.
- `git fetch origin` runs per tracked repo **before any read** (REPO-02), and the skill logs whether each repo was already up-to-date or received N new commits (success criterion 4).
- kanban parsing reuses `scripts/utils.py` parsers; assert task counts match what `aggregator.py` would produce on the same file (success criterion 2).

### Error Handling & Read-Only Guarantee
- Missing clone target / unreadable checkout → skip with `[WARN]`, continue (success criterion 1).
- Repo missing a marker file → seed it from `templates/`; if seeding isn't possible, skip with `[WARN]` (not a hard error).
- `git fetch` failure (offline / no remote) → `[WARN]`, fall back to local state, **non-fatal** — the skill is read-only this phase and must not abort the whole run.
- Read-only verification is explicit: after the skill runs, assert `git status` in kf-cpto is clean, `repos/` is untouched, and `repos-local/` does NOT appear in a `git add -A` dry-run (gitignore confirmed — success criterion 3).

### Claude's Discretion
- Exact module/function decomposition within the skill dir, log line formatting, and the structured-return shape are at Claude's discretion, guided by codebase conventions in `scripts/`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/utils.py` — `parse_kanban_frontmatter()`, `parse_kanban_tasks()`, `normalize_frontmatter()`, `load_project_kanban()`, `load_all_project_data()`, plus `ORG = "katty-fashion"` and status constants. MUST be reused (REPO-03).
- `scripts/discover.py` — existing org-scan / kanban-detection pattern (`discover_kanban_repos()`); reference for clone/branch handling, but the skill targets a curated local set, not a full org scan.
- `templates/` — seed `kanban.md` template and `notify-kf-cpto.yml` workflow for repos lacking markers.

### Established Patterns
- Python 3.9+ scripts in `scripts/`, `snake_case.py`, `print(f"Warning: ...")` for non-fatal issues, `[LABEL]` text pills (no emojis) per user preference.
- `utils.PROJECT_BRANCHES` is populated as a side effect of `load_projects()` — per-repo default branch is tracked there.
- `repos/` is gitignored and CI-runtime-only; `repos-local/` must be added to `.gitignore` similarly.

### Integration Points
- The skill produces inputs only; CI (`aggregate.yml`) remains the deterministic renderer/deployer. Phase 1 adds NO CI dependency.
- Downstream: Phase 2 (Activity Mining + Reconciliation) consumes `repo_enum.py`'s structured output.

</code_context>

<specifics>
## Specific Ideas

- Use `ai-rise-options` and `tech_brainstorming` as the concrete demonstration of tracking a repo outside the migration gantt.
- `repos-local/` membership = the tracked allowlist (omission is exclusion); no hardcoded project array in skill code.
- Per-repo default branch must be honored (mix of `main` and `master` in the org).

</specifics>

<deferred>
## Deferred Ideas

- Activity mining / git-signal reconciliation — Phase 2.
- Write-back, push, and Mermaid sanitization — Phase 3.
- Agentic capacity model — Phase 4.
- A richer exclude mechanism beyond `repos-local/` membership (e.g., an `exclude:` config) — not needed; membership covers it.

</deferred>
