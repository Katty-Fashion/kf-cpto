---
name: activity-sync
description: "Activity-driven write-back: enumerates tracked sibling repos, mines
  activity signals (merged PRs, closed issues, active branches), and writes reconciled
  task statuses back to each repo's kanban.md with a single batch confirmation. Also
  supports read-only enumeration and dry-run preview. Triggers on: activity sync,
  write back kanban, reconcile task statuses, repo enum, list tracked repos,
  fetch kanban state."
allowed-tools:
  - Bash
  - Read
---

# Activity Sync — Repo Access + Write-Back

Read-only enumeration of tracked sibling repos in `repos-local/`. Fetches remote
state via `git fetch` and parses each `kanban.md` through the canonical
`scripts/utils.py` parsers (one-parser constraint — no local parser in this skill).

---

## Prerequisites

- `repos-local/` must be populated before running `repo_enum.py`.
- Run `bootstrap.py` once on a fresh machine to clone all tracked repos.

---

## Commands

### [BOOTSTRAP] First-run clone and marker seeding

Run once on a fresh machine (or when adding a new tracked repo):

```
python .claude/skills/activity-sync/bootstrap.py
```

What it does:
- Creates `repos-local/` if absent
- Clones each tracked repo via SSH (full clone — no `--depth=1`; Phase 2 needs git history)
- Seeds `kanban.md` and `notify-kf-cpto.yml` from `templates/` into repos that lack them
- `Warning:` on clone failure (non-fatal; continues to next repo)

### [ENUM] Enumerate, fetch, and parse all tracked repos

```
python .claude/skills/activity-sync/repo_enum.py
```

What it does:
- Scans `repos-local/` for valid git repos (no static project list)
- Runs `git fetch origin` per repo before reading (non-fatal on failure)
- Logs `up-to-date` or `new-commits` per repo based on before/after SHA comparison
- Parses `kanban.md` via `utils.parse_kanban_frontmatter()` + `utils.parse_kanban_tasks()`
- Counts valid-status tasks using `utils.TASK_STATUSES` (matches aggregator logic)
- Asserts kf-cpto working tree is clean after run (`git status --porcelain == ""`)
- Returns `list[RepoRecord]` for Phase 2 downstream consumption

### [RECONCILE] Dry-run activity reconciliation

```
python .claude/skills/activity-sync/reconcile.py --dry-run
```

What it does:
- Imports `repo_enum.run()` records (name, local_path, branch, tasks, kanban metadata)
- Mines [TIER-1] signals via GitHub REST API: merged PRs + closed linked issues -> Done
  - Reachability-gates each merge commit via `git merge-base --is-ancestor` (RECON-08)
  - Resolves `closes/fixes #N` body references; fetches closed issue titles for matching
  - Reverted/unreachable merges produce no Done entry
- Mines [TIER-2] signals via local git: active remote branches -> In Progress (Todo only)
  - Pure-local `git for-each-ref refs/remotes/origin/` — no API call for branch detection
- Forward-only: never downgrades a declared status (Done stays Done)
- [TIER-1] Done wins over [TIER-2] In Progress for the same task (conflict resolution)
- Prints a grouped change list to stdout — grouped by repo, task | old -> new | signal
- Writes nothing this phase (dry-run only; Phase 3 implements write-back)
- Requires `KF_PAT` or `GITHUB_TOKEN` env var for GitHub API; warns and continues with
  empty [TIER-1] proposals when no token is set (graceful degradation)

### [GENERATE] Generate distinct per-repo kanbans from the migration plan

```
python scripts/generate_kanban.py                  # dry-run preview (default, safe)
python scripts/generate_kanban.py --reseed         # rebuild plan-of-record from kf-platform, then preview
python scripts/generate_kanban.py --apply          # write + batch-confirm + commit + push
python scripts/generate_kanban.py --apply --no-push   # write + commit locally, no push
```

What it does:
- Reads the migration **plan-of-record** `docs/_data/migration_plan.yml`, seeding it
  once from `kf-platform/kanban.md` (the curated 39-task plan) if absent or `--reseed`.
- **Partitions by discipline** (encoded in the Assignee column) into three distinct repos —
  exactly one repo per task, so the LOE intermediate sums with no double-counting:
  - FE-only (`@<frontend>`) → `kf-fe-platform`
  - BE-only (`@<backend>`) → `kf-be-platform`
  - FE+BE (`@<frontend> + @<backend>`) → `kf-platform` (cross-stack umbrella)
- Preserves each target repo's curated frontmatter verbatim; regenerates the task table
  (full names, person-day effort, dates) + the milestone reference trailer.
- **Status merge:** a target repo's own valid status for a task wins over the plan status,
  so re-running never reverts statuses set by [RECONCILE]/[WRITE-BACK]. Generation owns the
  skeleton; activity-sync owns status truth.
- Idempotent (byte-compare gate); single batch confirmation; reuses `writeback.py`'s
  conflict gate, KF_PAT push, and recovery manifest. `--apply` needs `KF_PAT` (unless `--no-push`).
- Run the aggregator afterward to refresh `docs/_data/loe.yml` and the dashboard.

Prerequisites: `repos-local/` populated ([BOOTSTRAP]); for `--apply` push, `KF_PAT` set.

---

## Script Locations (Phase 1 and 2)

| Script | Path | Role |
|--------|------|------|
| Bootstrap | `.claude/skills/activity-sync/bootstrap.py` | One-shot clone + seed |
| Enumeration | `.claude/skills/activity-sync/repo_enum.py` | Fetch + parse all tracked repos |
| Reconcile | `.claude/skills/activity-sync/reconcile.py` | Activity mining + dry-run reconciliation |
| Generate | `scripts/generate_kanban.py` | Partition the migration plan-of-record into per-repo kanbans |

See the Phase 3: Write-Back section below for `writeback.py`.

---

## Output Format

`repo_enum.py` prints one status line per repo:

```
[INFO] <repo-name>: <fetch-status> (branch: <branch>)
[INFO] <repo-name>: <N> valid-status tasks
Warning: <repo-name>: kanban.md missing — run bootstrap.py first
```

Where `<fetch-status>` is one of: `up-to-date`, `new-commits`, `fetch-failed`.

`reconcile.py` prints a change list grouped by repo:

```
Activity Sync — Reconcile — Starting...
Warning: No KF_PAT or GITHUB_TOKEN set. API rate limits will be very low.

Repo: kf-some-project
Task                                          Old          New  Signal
------------------------------------------------------------------------------------------
Setup authentication                         Todo ->        Done  [TIER-1] PR #42: Setup authentication flow (merged)
Add product catalog                          Todo ->        Done  [TIER-1] issue #7 closed (via PR #12)
Migrate legacy API                           Todo ->  In Progress  [TIER-2] branch origin/migrate-legacy-api exists

Activity Sync — Reconcile — Done!
```

When no changes are proposed (all declared statuses match activity):

```
[INFO] No changes proposed — all declared statuses match activity.
```

Pill legend:
- `[TIER-1]` — merged PR or closed linked issue (verified via git reachability gate)
- `[TIER-2]` — active remote branch (local git, no API)

---

## [NOTE] Parser Constraint

This skill [NEVER] calls `utils.load_project_kanban()` — it is hardwired to `repos/`
(the CI clone dir). The skill calls `utils.parse_kanban_frontmatter()` and
`utils.parse_kanban_tasks()` directly with paths from `repos-local/`.

---

## [NOTE] repos-local/ Is Gitignored

`repos-local/` is listed in `.gitignore` (runtime-only; populated by `bootstrap.py`).
Never commit files under `repos-local/`.

---

## Phase 3: Write-Back

### [WRITE-BACK] Apply reconciled statuses and push to all tracked repos

```
python .claude/skills/activity-sync/writeback.py [--dry-run]
```

What it does:

- Calls `reconcile.run()` to get the full list of proposed status changes
- Groups proposals by repo and prints ONE [INFO] batch-confirm summary table
- Reads a SINGLE `y/N` prompt before performing any write or push (zero per-repo prompts — matches the org-scan preference: confirm destructive ops once as a batch)
- For each repo with proposals:
  - Runs `_is_behind_origin()` (git fetch + rev-list) before writing — aborts that repo with `[CONFLICT]` if local is behind origin; continues with remaining repos
  - Applies `apply_status_change()` THEN `sanitize_body()` on the kanban.md body
  - Byte-compares proposed content to current file — skips write+commit+push if identical (idempotency gate SC-4)
  - Commits with `chore(kanban): reconcile task statuses from repo activity` and pushes using HTTPS+KF_PAT (SSH URL restored in `finally`)
- Writes a per-run JSON recovery manifest to `.claude/skills/activity-sync/manifests/{run_id}.json` recording each repo's outcome (`succeeded` / `failed` / `conflict` / `skipped`), pushed sha, and error
- Prints a `[TALLY]` line: `N [DONE] / N [CONFLICT] / N [SKIP] / N [FAIL]`

```
python .claude/skills/activity-sync/writeback.py --dry-run
```

Dry-run path:

- Previews the batch-confirm summary table
- Writes nothing, pushes nothing
- Does NOT read `KF_PAT` from env (token not required for dry-run)

### Output pills

- `[INFO]`    — batch summary, dry-run indicator, no-op status
- `[CONFLICT]` — repo's local checkout is behind origin; write skipped; batch continues
- `[SKIP]`   — content unchanged (idempotent no-op); no git operations
- `[DONE]`   — write succeeded; pushed sha logged
- `[FAIL]`   — unexpected per-repo error; batch continues; error recorded in manifest
- `[WARN]`   — non-fatal warning (e.g., manifest write failure, repo not in enum records)
- `[ERROR]`  — fatal error printed to stderr (e.g., KF_PAT unset when push required)
- `[TALLY]`  — final run summary line

### Recovery manifest

Each run writes `.claude/skills/activity-sync/manifests/{run_id}.json` (gitignored; never committed):

```json
{
  "run_id": "20260604T114000Z",
  "timestamp": "2026-06-04T11:40:00+00:00",
  "total_repos": 3,
  "summary": {"succeeded": 2, "failed": 0, "conflict": 1, "skipped": 0},
  "repos": [
    {
      "repo": "kf-some-project",
      "outcome": "succeeded",
      "pushed_sha": "abc123def456...",
      "changes": [{"task": "Setup authentication", "old_status": "Todo", "new_status": "Done"}],
      "error": null
    },
    ...
  ]
}
```

Use the manifest to identify which repos were not written in a partial-failure run and re-run selectively.

### [CONFLICT] handling

A `[CONFLICT]` on one repo does NOT stop the batch. The loop continues to the next repo. Already-pushed repos' `notify-kf-cpto.yml` dispatches fire normally (natural per-repo dispatch, no `[skip ci]`).

To resolve a conflict: `git pull` in the affected `repos-local/<repo>` dir, then re-run `writeback.py`.

### Environment variables

| Variable | Required | When read | Notes |
|----------|----------|-----------|-------|
| `KF_PAT` | Yes (live push) | Inside `run()` at push time, NOT at import time | GitHub PAT with `repo` scope; never logged or stored in manifest |
| `KF_PAT` | No (dry-run) | Never read in `--dry-run` mode | |

### [IMPORTANT] SC-1 — Live push is human-validated UAT

[WARN] SC-1 (live push to katty-fashion org repos → CI dispatch → aggregate.yml → GitHub Pages deploy) is a **human-validated UAT step**. The autonomous skill build never fires live pushes to real org repos unprompted.

Before running `writeback.py` against live org repos:
1. Confirm `repos-local/` contains up-to-date clones (run `bootstrap.py` or `git pull` as needed)
2. Run `writeback.py --dry-run` first to preview the proposed changes
3. Review the batch-confirm summary carefully — it authorises pushes to N repos at once
4. Confirm the single `y/N` prompt to proceed
5. After pushing, verify the `notify-kf-cpto.yml` dispatch fired and `aggregate.yml` completed (GitHub Actions tab)
6. Confirm the dashboard at `https://katty-fashion.github.io/kf-cpto/` reflects the updated task statuses

SC-1 is explicitly not automated. This is a write-once confirmation loop, not a CI step.

---

## Script Locations (updated)

| Script | Path | Role |
|--------|------|------|
| Bootstrap | `.claude/skills/activity-sync/bootstrap.py` | One-shot clone + seed |
| Enumeration | `.claude/skills/activity-sync/repo_enum.py` | Fetch + parse all tracked repos |
| Reconcile | `.claude/skills/activity-sync/reconcile.py` | Activity mining + dry-run reconciliation |
| Write-back | `.claude/skills/activity-sync/writeback.py` | Batch write + push to tracked repos |

Manifests (gitignored, runtime output only):
- `.claude/skills/activity-sync/manifests/` — per-run JSON recovery manifests
