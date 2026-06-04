---
phase: 02-activity-mining-reconciliation
plan: "02"
subsystem: activity-sync-skill
tags: [reconciliation, tier-1, merged-pr, github-api, reachability-gate, tdd, python]
dependency_graph:
  requires:
    - phase: "02"
      plan: "01"
      provides: "reconcile.py skeleton: Proposal, STATUS_RANK, task_matches_signal, reconcile_repo (Tier-2), run(), main()"
  provides:
    - reconcile.py extended with Tier-1 acquisition: _build_headers, _list_merged_prs, _extract_issue_refs, _get_issue, _is_merge_reachable
    - reconcile_repo(record, headers) -> list[Proposal] with Tier-1 + Tier-2 conflict resolution
    - SKILL.md [RECONCILE] command section with [TIER-1]/[TIER-2] pill output documentation
  affects:
    - phase: "03"
      reason: "Phase 3 write-back consumes run() -> list[Proposal]; reconcile_repo signature is the integration point"
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN cycle (task 1 RED c95ff55, GREEN b267b41; task 2 RED 11a6f09, GREEN 075aa25)"
    - "Tier-1 acquisition: paginated GET /pulls?state=closed filtered by merged_at; _CLOSING_KEYWORDS_RE for same-repo #N only"
    - "Reachability gate: git merge-base --is-ancestor via arg-list _run_git (T-02-07/08)"
    - "Graceful degradation: _build_headers warns on missing token; _list_merged_prs returns [] on non-200; run() continues with empty Tier-1"
    - "Conflict resolution: Tier-1 Done (rank 3) beats Tier-2 In Progress (rank 1) via most_advanced in same proposals dict"
key_files:
  created: []
  modified:
    - .claude/skills/activity-sync/reconcile.py
    - .claude/skills/activity-sync/test_reconcile.py
    - .claude/skills/activity-sync/SKILL.md
decisions:
  - "reconcile_repo signature extended from (record) to (record, headers); run() builds _build_headers() once and passes through all calls"
  - "Tier-1 block inserted BEFORE Tier-2 in reconcile_repo so both feed same per-task proposals dict; most_advanced resolves Done > In Progress"
  - "reachable is not True guard (covers both False and None) — conservative per RECON-08; no revert-message parsing"
  - "Tier-2 tests stub _list_merged_prs to return [] to isolate Tier-2 behavior from Tier-1"
metrics:
  duration: "8m22s"
  completed_date: "2026-06-04"
  tasks_completed: 2
  files_changed: 3
---

# Phase 02 Plan 02: Tier-1 Signal Acquisition + reconcile_repo Integration Summary

Extended `reconcile.py` with Tier-1 merged-PR acquisition via GitHub REST API, closing-keyword linked-issue resolution, `git merge-base --is-ancestor` reachability gate, and integrated Tier-1 Done candidates into the existing conflict-resolution step so Tier-1 wins over Tier-2. Updated `SKILL.md` with the `[RECONCILE]` command section.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing tests for Tier-1 acquisition helpers | c95ff55 | test_reconcile.py |
| 1 (GREEN) | Implement _build_headers, _list_merged_prs, _extract_issue_refs, _get_issue, _is_merge_reachable | b267b41 | reconcile.py |
| 2 (RED) | Add failing integration tests for Tier-1 reconcile_repo + headers | 11a6f09 | test_reconcile.py |
| 2 (GREEN) | Integrate Tier-1 into reconcile_repo; update run() and SKILL.md | 075aa25 | reconcile.py, test_reconcile.py, SKILL.md |

## What Was Built

`reconcile.py` (590 lines) now delivers the full Tier-1 + Tier-2 vertical slice:

**New Tier-1 helpers:**
- `_build_headers()`: `KF_PAT` > `GITHUB_TOKEN` dual env-var lookup; warns on missing token; Authorization header present iff token set; token value never printed (T-02-05)
- `_list_merged_prs(org, repo, headers)`: paginated `GET /repos/{org}/{repo}/pulls?state=closed`; filters `merged_at is not None`; `[WARN]` when `X-RateLimit-Remaining < 100`; breaks on non-200
- `_extract_issue_refs(body)`: `_CLOSING_KEYWORDS_RE` (9 GitHub keywords, `re.IGNORECASE`); same-repo `#N` only; cross-repo `OWNER/REPO#N` silently excluded; `None` body returns `[]` (Pitfall 4)
- `_get_issue(org, repo, issue_number, headers)`: `GET /repos/{org}/{repo}/issues/{N}`; `200` returns json, `404` returns `None`, other status warns + `None`
- `_is_merge_reachable(repo_path, merge_commit_sha, default_branch)`: arg-list `_run_git(["merge-base", "--is-ancestor", sha, "origin/<branch>"])`; exit-0 `True`, exit-1 `False`, other `None` (conservative)

**reconcile_repo extension (signature change):**
- `reconcile_repo(record: dict, headers: dict) -> list[Proposal]`
- Tier-1 block runs before Tier-2: iterates merged PRs, skips falsy `merge_commit_sha` (Pitfall 1), skips when `_is_merge_reachable is not True` (RECON-08), token-matches PR title and linked closed-issue titles to tasks, appends `("Done", 1, signal, url)` to the shared proposals dict
- Tier-2 block unchanged: appends `("In Progress", 2, ...)` to same dict
- `most_advanced` conflict resolution: `STATUS_RANK["Done"] == 3` beats `STATUS_RANK["In Progress"] == 1` — Tier-1 wins (RECON-03)

**run() update:** `headers = _build_headers()` built once before record loop; passed to each `reconcile_repo(record, headers)` call.

**test_reconcile.py** (698 lines, 83 tests): Tier-2 tests updated to stub `_list_merged_prs` to `[]`; new integration tests cover all `<behavior>` cases (reachable Tier-1, None sha skip, unreachable skip, linked-issue Done, Tier-1-beats-Tier-2 conflict, kanban_exists=False with headers).

**SKILL.md**: `[RECONCILE]` command section added (mirrors `[ENUM]` style); `reconcile.py` in Script Locations table; sample dry-run output with `[TIER-1]`/`[TIER-2]` pills; `[INFO] No changes proposed` empty-case line; no emojis.

## Verification Results

- `python .claude/skills/activity-sync/test_reconcile.py` — 83/83 PASS
- `python .claude/skills/activity-sync/reconcile.py --dry-run` — exits 0
- `git status --porcelain` after run — no files written by reconcile.py (read-only invariant, RECON-05)
- Idempotency: two consecutive `--dry-run` runs produce byte-identical stdout
- `grep -E 'merge-base.*is-ancestor' reconcile.py` — 3 matches (gate present, RECON-08)
- `grep -E 'Revert|rev-list|git log' reconcile.py` — only comment (no revert-message parsing)
- No `print(` referencing `token` variable (T-02-05)
- `python -c "import ast; ast.parse(open('reconcile.py').read())"` — parse OK on Python 3.9

## Deviations from Plan

None — plan executed exactly as written.

The `reconcile_repo` signature change from `(record)` to `(record, headers)` and the corresponding `run()` call-site update were explicitly specified in the plan. The Tier-2 test isolation stub (`_FakeNoMergedPRs`) was added to prevent existing Tier-2 tests from hitting the new Tier-1 code path — this is a test hygiene fix within scope of Task 2.

## TDD Gate Compliance

- RED gate: `test(02-02)` commit c95ff55 (Task 1) — imports `_build_headers`, `_extract_issue_refs`, `_is_merge_reachable` which don't exist yet; ImportError at import time confirms RED
- GREEN gate: `feat(02-02)` commit b267b41 (Task 1) — all 66 tests pass
- RED gate: `test(02-02)` commit 11a6f09 (Task 2) — calls `reconcile_repo(record, headers)` which fails with `TypeError: takes 1 positional argument but 2 were given`; confirms RED
- GREEN gate: `feat(02-02)` commit 075aa25 (Task 2) — all 83 tests pass

## Known Stubs

None. All Tier-1 helpers are fully implemented. The dry-run produces real proposals based on actual GitHub API data (or empty proposals when no token set). No hardcoded values, placeholder text, or mock data in production paths.

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`:
- T-02-05 (KF_PAT token): `_build_headers()` places token in `Authorization` header only; never in any `print()` call — mitigated
- T-02-06 (crafted PR title/body): matched via `task_matches_signal` token normalization (plaintext, no eval) — mitigated
- T-02-07 (merge_commit_sha in git subprocess): passed via arg-list `_run_git`; falsy sha skipped before git call — mitigated
- T-02-08 (reverted/unreachable merge): `_is_merge_reachable` is the sole gate; no `Revert "..."` message parsing — mitigated
- T-02-09 (rate limit): `[WARN]` emitted when `X-RateLimit-Remaining < 100`; unauthenticated runs degrade to empty proposals — accepted

## Self-Check: PASSED

Files modified:
- /Users/machina/Dev/kf-cpto/.claude/skills/activity-sync/reconcile.py: FOUND
- /Users/machina/Dev/kf-cpto/.claude/skills/activity-sync/test_reconcile.py: FOUND
- /Users/machina/Dev/kf-cpto/.claude/skills/activity-sync/SKILL.md: FOUND

Commits:
- c95ff55 (test RED task 1): FOUND
- b267b41 (feat GREEN task 1): FOUND
- 11a6f09 (test RED task 2): FOUND
- 075aa25 (feat GREEN task 2): FOUND
