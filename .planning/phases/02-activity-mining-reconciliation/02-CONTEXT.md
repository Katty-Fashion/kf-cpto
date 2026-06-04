# Phase 2: Activity Mining + Reconciliation - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

The skill produces a **human-readable change list** (old status → new status, triggering signal) for every proposed reconciliation — **dry-run only, no file writes anywhere**. This phase consumes the structured records from Phase 1's `repo_enum.run()`, mines git activity (merged PRs, closed issues, active remote branches) per tracked repo, reconciles that real activity against each declared `kanban.md` status, and prints a reviewable change list. No write-back, no Mermaid sanitization, no capacity modelling — those are Phases 3–4. The deliverable is the reconciliation engine plus its dry-run presentation, proven idempotent before any write code exists.

</domain>

<decisions>
## Implementation Decisions

### Signal → Task Matching
- The kanban table has **no task-ID column** — tasks are free-text names only. Matching links a git signal (PR/branch/issue) to a task by **normalized task-name tokens** found in the PR title/body or branch name.
- **Conservative matching** to avoid false positives: require all significant task-title words to be present (case- and punctuation-normalized) before a signal is considered a match. No fuzzy similarity scoring, no loose substring matching.
- RECON-01 "linked issue-closes": parse the merged PR's `closes/fixes #N` keywords and resolve the linked issue via the GitHub API, then match the **issue title** to a task using the same token rule.
- One signal may match multiple tasks → apply to all matched tasks. On conflicting signals for the same task, keep the **most-advanced** status (Tier-1 / Done wins over Tier-2 / In Progress).

### Signal Tiers & Status Mapping
- **Tier-1** (merged PR carrying a task reference, or closed linked issue) → proposes `Done`.
- **Tier-2** (active remote branch referencing the task) → advances `Todo → In Progress` **only**; never advances past In Progress.
- **Tier-3** (commit-message keywords, file paths touched) → **ignored entirely**; never changes status (RECON-06).
- **Forward-only / monotonic**: never downgrade a declared status. A task already declared `Done` stays Done even if its branch is gone; a `Review` task is not pulled back to In Progress.

### Reverted / Unreachable Merge Detection
- **Hybrid data sources**: GitHub API (via `gh` / `KF_PAT`) to find merged PRs and their `merge_commit_sha`; local git for the reachability gate.
- **Reachability test** (success criterion 3): `git merge-base --is-ancestor <merge_commit_sha> origin/<default-branch>` — the merge commit must be an ancestor of the default-branch tip for the PR to count as Done.
- Reachability is the **canonical revert gate** — it covers force-push drops, rebases, and revert-of-merge uniformly. Do **not** separately parse `Revert "…"` commit messages.
- **Squash/rebase merges** (no classic merge commit): use the API-reported `merge_commit_sha` (the squash/rebase commit) and test *its* reachability — same gate, no special-casing.

### Output Format, Module & Idempotency
- **Change-list format**: text table grouped by repo, each row `task | old → new | [TIER-N] signal`. Uses `[LABEL]` text pills, **no emojis** (user preference).
- **Idempotency rule** (success criterion 5): emit a row **only when proposed status ≠ declared status**. An already-reconciled repo produces an empty change list; running `--dry-run` twice yields the same (empty) output.
- **Mode scope**: dry-run is the **only** behavior in this phase. A `--dry-run` flag is accepted (and is the implicit default); no `--write` path is built here — write-back is Phase 3.
- **Module**: new `reconcile.py` in `.claude/skills/activity-sync/`, importing `repo_enum.run()` for its structured records.

### Claude's Discretion
- `reconcile.py` follows the Phase 1 pattern: **print** the human-readable change list AND **return structured proposals** (Python objects) so Phase 3 write-back can consume them without re-running the engine. (Internal structured return — not a user-facing JSON file this phase.)
- Status values must normalize through the canonical `utils.TASK_STATUSES` enum before appearing in any proposal (RECON-07; note the ROADMAP success-criterion text says `VALID_STATUSES` but the actual constant is `TASK_STATUSES`).
- Exact function decomposition, GitHub API call structure (REST via `requests` + `KF_PAT`, consistent with `discover.py`), token-normalization helper, and log/pill formatting are at Claude's discretion, guided by `scripts/` conventions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.claude/skills/activity-sync/repo_enum.py` — `run()` returns structured records: `{name, local_path, remote_url, branch, fetch_status, kanban_exists, meta, tasks, valid_task_count}`. Phase 2 imports this directly. `_run_git()` arg-list subprocess wrapper, `_get_default_branch()`, and the org-allowlist guard are reusable patterns.
- `scripts/utils.py` — `TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")`, `STATUS_PRIORITY` (for "most-advanced" conflict resolution), `parse_kanban_tasks()`. Reuse the status enum; do NOT add a second parser (REPO-03).
- `scripts/discover.py` — existing GitHub REST API pattern using `requests` + `KF_PAT` (pagination, headers); reference for the PR/issue API calls.

### Established Patterns
- Tasks are matched by free-text name only (no ID); `STATUS_PRIORITY` exists in `utils.py` for ranking statuses → use it for "most-advanced wins."
- `[INFO]` / `[WARN]` / `[ERROR]` log prefixes and `print(f"Warning: ...")` for non-fatal issues; text `[LABEL]` pills, no emojis.
- Read-only guarantee: this phase must still leave the kf-cpto tree clean and write nothing to `repos-local/` checkouts.

### Integration Points
- Upstream: consumes `repo_enum.run()` records (Phase 1).
- Downstream: Phase 3 write-back consumes `reconcile.py`'s structured proposals; Phase 3 also adds Mermaid sanitization.
- GitHub API auth reuses `KF_PAT` env var (same token `discover.py` uses).

</code_context>

<specifics>
## Specific Ideas

- Conservative token matching (all significant title words present) is the chosen guard against false-positive reconciliations — favored over fuzzy matching.
- The reachability gate `git merge-base --is-ancestor <merge_commit_sha> origin/<default>` is the single source of truth for "did this merge actually land" — it transparently handles reverts, force-pushes, and squash/rebase.
- Idempotency is validated in this dry-run phase (run twice → empty list) **before** any write code is built in Phase 3.

</specifics>

<deferred>
## Deferred Ideas

- Write-back of corrected `kanban.md`, batch-confirm, non-fast-forward abort, push to default branch, recovery manifest — Phase 3 (WB-01..05).
- Mermaid-breaking character sanitization — Phase 3 (DIAG-01..03).
- Agentic capacity overflow model — Phase 4 (CAP-01..07).
- Tier-2 ambiguous-signal flagging for human decision (vs. auto-resolve) — v2 (RECON-V2-01).

</deferred>
