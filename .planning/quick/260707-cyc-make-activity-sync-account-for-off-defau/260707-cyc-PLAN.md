---
phase: quick-260707-cyc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .claude/skills/activity-sync/reconcile.py
  - .claude/skills/activity-sync/test_reconcile.py
  - .claude/skills/activity-sync/SKILL.md
  - README.md
autonomous: true
requirements: [QUICK-CYC-A, QUICK-CYC-B, QUICK-CYC-C]

must_haves:
  truths:
    - "A merge reachable only from a non-default integration branch (uat, work, *-migration) is reported Done, not In Progress"
    - "A merge on a plain feature branch (not matching integration globs), not reachable from any integration branch, still surfaces as In Progress via Tier-2"
    - "An integration branch (uat / *-migration) never appears as a Tier-2 In Progress signal — it is excluded from the active-branch scan"
    - "No repo names or branch names are hardcoded in reconcile.py logic — the glob list is the only config"
    - "README How-It-Works diagram lists all 6 tracked repo nodes, each with a push-trigger edge to GHA"
  artifacts:
    - path: ".claude/skills/activity-sync/reconcile.py"
      provides: "INTEGRATION_BRANCH_GLOBS constant + integration-branch set logic in reconcile_repo"
      contains: "INTEGRATION_BRANCH_GLOBS"
    - path: ".claude/skills/activity-sync/test_reconcile.py"
      provides: "Coverage for non-default integration-branch Done + integration-branch Tier-2 exclusion"
    - path: "README.md"
      provides: "6-node How-It-Works mermaid diagram"
  key_links:
    - from: "reconcile_repo Tier-1"
      to: "_is_merge_reachable"
      via: "iterate integration_branches, short-circuit on first True"
      pattern: "_is_merge_reachable"
    - from: "reconcile_repo Tier-2"
      to: "_list_remote_branches"
      via: "exclude every branch in integration_branches from active-branch scan"
      pattern: "_list_remote_branches"
---

<objective>
Make activity-sync's reconciler account for off-default integration branches so finished work merged into `uat` / `*-migration` / `work` (not the repo's default branch) is reported as Done rather than understated as In Progress. Also fix README repo drift: the How-It-Works diagram lists only 4 of the 6 tracked repos.

Purpose: kf-platform's real work lives on `origin/claude-migration`, merged into `origin/uat` via PR #17 — never into `master`. Today Tier-1 only checks reachability from `origin/<default>`, so that merge is invisible to Done, and Tier-2 lists `claude-migration` as an "active branch," demoting finished work to In Progress. The fix generalizes the single default branch into a configurable INTEGRATION-BRANCH SET.

Output: Updated `reconcile.py` (set logic + `INTEGRATION_BRANCH_GLOBS` constant), extended `test_reconcile.py`, a SKILL.md doc note keeping the Tier-1/Tier-2 contract coherent, and a corrected 6-node README diagram.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

@.claude/skills/activity-sync/reconcile.py
@.claude/skills/activity-sync/test_reconcile.py
@.claude/skills/activity-sync/SKILL.md
@README.md

<constraints_recap>
- CLAUDE.md anti-pattern: NO hardcoded project/branch names — the glob list is the config (no "kf-platform", no "claude-migration", no "uat" literal outside INTEGRATION_BRANCH_GLOBS).
- One-parser constraint: this skill never adds a second kanban parser; unchanged here.
- Skill is local-only; CI must stay self-contained (no new CI dependency).
- Security posture (T-02-*): branch/sha values flow ONLY into arg-list `_run_git` calls; never `shell=True`, never f-string into a shell command. Preserve the `_run_git` arg-list pattern.
- Tier-2 stays pure-local git (no API).
- Conservative revert gate: a merge counts as Done only when `_is_merge_reachable` returns True (never False, never None).
- Text-pills convention: `[LABEL]` pills, no emojis (already followed in reconcile.py output).
</constraints_recap>

<interfaces>
Key existing signatures in reconcile.py the executor builds against (do NOT re-explore the codebase):

```python
# Conservative revert gate — returns True | False | None. Uses arg-list _run_git.
def _is_merge_reachable(repo_path: str, merge_commit_sha: str, default_branch: str) -> Optional[bool]

# Pure-local git for-each-ref; excludes HEAD and default_branch; returns sorted short names.
def _list_remote_branches(repo_path: str, default_branch: str) -> list[str]

# reconcile_repo reads: record["name"], record["local_path"], record["branch"] (default_branch)
def reconcile_repo(record: dict, headers: dict) -> list[Proposal]
```

Existing module constants block is at ~line 43 (REPOS_LOCAL_DIR, GIT_TIMEOUT_SECONDS, ...). `_STOPWORDS` is a frozenset there — mirror that style.

Test idiom (test_reconcile.py) uses context-manager monkeypatch classes that swap a module attr in `__enter__` and restore in `__exit__`:
`_FakeBranches(branches)`, `_FakeNoMergedPRs`, `_FakeMergedPRs(prs)`, `_FakeIsReachable(result)`, `_FakeGetIssue(data)`, `_FakeRunGit(returncode, stdout, stderr)`.
Note `_FakeIsReachable` currently stubs with `lambda path, sha, branch: result` (3 positional args) — a per-branch reachability test needs a stub that can vary by branch (see Task 2).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Introduce integration-branch set in reconcile.py</name>
  <files>.claude/skills/activity-sync/reconcile.py</files>
  <behavior>
    - A helper `_integration_branches(repo_path, default_branch)` returns `[default_branch]` plus every locally-known remote branch whose short name matches any glob in `INTEGRATION_BRANCH_GLOBS` (via `fnmatch.fnmatch`), de-duplicated, default first.
    - Tier-1: a merge is Done if `_is_merge_reachable(repo_path, sha, b)` is True for ANY b in the integration set; iterate and short-circuit on first True. Non-True (False or None) for all branches → not Done.
    - Tier-2: `_list_remote_branches` output is filtered so no branch in the integration set is scanned for active-branch In Progress signals (today only default_branch is excluded).
    - No repo/branch string literals in logic outside INTEGRATION_BRANCH_GLOBS.
  </behavior>
  <action>
    Add `import fnmatch` with the other stdlib imports (top of file, alongside `import re`).

    Add a module constant near the existing constants block (~line 43, after HTTP_TIMEOUT_SECONDS / GITHUB_API), in SCREAMING_SNAKE_CASE, with a comment explaining it: `INTEGRATION_BRANCH_GLOBS = ["uat", "work", "*-migration"]`. Comment must state these are short-name glob patterns (fnmatch), that the set they build is the source of config (NO hardcoded repo names per CLAUDE.md), and that the default branch is always a member regardless of glob match.

    Add a private helper `_integration_branches(repo_path: str, default_branch: str) -> list[str]`: build the set as `{default_branch}` unioned with every short name from `_list_remote_branches(repo_path, default_branch)` — wait: `_list_remote_branches` already EXCLUDES default_branch, so call it, then keep only names where `any(fnmatch.fnmatch(name, g) for g in INTEGRATION_BRANCH_GLOBS)`. Return `default_branch` first, then the sorted glob-matched integration branches, de-duplicated. Reuse `_list_remote_branches` so there is one source of remote-branch truth; do not add a second for-each-ref call.

    In `reconcile_repo` (~line 356): after `default_branch = record["branch"]`, compute `integration_branches = _integration_branches(repo_path, default_branch)` once.

    Tier-1 change (~line 377): replace the single `reachable = _is_merge_reachable(repo_path, sha, default_branch)` with an iteration over `integration_branches` that short-circuits on the first `is True`. Keep the conservative gate: only a True counts; if no branch yields True, skip conservatively (matches today's `reachable is not True` behavior). Preserve the T-02-07 comment noting sha flows via arg-list `_run_git`, never shell-interpolated.

    Tier-2 change (~line 412): currently `remote_branches = _list_remote_branches(repo_path, default_branch)`; then it iterates all of them. Filter out every branch in `integration_branches` before the task-match loop so integration branches never emit a Tier-2 In Progress signal. (default_branch is already excluded by `_list_remote_branches`; this additionally excludes uat/work/*-migration.) Keep it pure-local (no API).

    Do NOT change `_is_merge_reachable`'s or `_list_remote_branches`'s signatures — reuse them as-is. Do NOT introduce a per-repo override map; the glob set is the only config.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && python -c "import sys; sys.path.insert(0,'.claude/skills/activity-sync'); import reconcile; print(reconcile.INTEGRATION_BRANCH_GLOBS); print(reconcile._integration_branches.__name__)"</automated>
  </verify>
  <done>
    reconcile.py imports fnmatch, defines INTEGRATION_BRANCH_GLOBS = ["uat", "work", "*-migration"] with an explanatory comment, defines `_integration_branches`, and reconcile_repo uses the set for both Tier-1 (any-branch reachability, short-circuit) and Tier-2 (exclude integration branches). No hardcoded repo/branch literals in logic. `python .claude/skills/activity-sync/test_reconcile.py` still exits 0 for pre-existing tests.
  </done>
</task>

<task type="auto">
  <name>Task 2: Extend test_reconcile.py coverage</name>
  <files>.claude/skills/activity-sync/test_reconcile.py</files>
  <action>
    Add tests in the existing hermetic idiom (context-manager monkeypatch classes; `check(name, condition)` assertions; no pytest). Append new blocks after the existing `reconcile_repo Tier-1 integration` section, before the Summary block.

    Because the new Tier-1 logic calls `_is_merge_reachable(repo_path, sha, branch)` once per integration branch, the current `_FakeIsReachable` (which returns a fixed result regardless of branch) is insufficient to prove per-branch behavior. Add a new context-manager class (e.g. `_FakeReachableByBranch`) that stubs `reconcile._is_merge_reachable` with `lambda path, sha, branch: mapping.get(branch)` where `mapping` maps a branch short name → True/False/None. Follow the exact `__enter__`/`__exit__` save-restore pattern of the existing fakes.

    Also stub `_list_remote_branches` via the existing `_FakeBranches` so the integration set is deterministic without a real git repo. Remember `_integration_branches` calls `_list_remote_branches` internally, so `_FakeBranches(["claude-migration", "some-feature"])` controls what the integration-set builder sees.

    Test A — merge reachable ONLY via a non-default integration branch → Done:
    - Record with a Todo task whose tokens match the PR title (e.g. task "Migrate platform", PR title "Migrate platform to new stack").
    - `_FakeBranches(["claude-migration"])` so `*-migration` matches → integration set = {default, claude-migration}.
    - `_FakeReachableByBranch({"master": False, "claude-migration": True})` (use the record's default branch name as the default key).
    - `_FakeMergedPRs([pr_matching_with_sha])`, `_FakeGetIssue(None)`.
    - Assert exactly 1 proposal, new_status == "Done", tier == 1. This proves any-branch reachability promotes to Done even when the default branch is not reachable.

    Test B — integration branch does NOT produce a Tier-2 In Progress demotion:
    - Same `_FakeBranches(["claude-migration"])` (a `*-migration` integration branch whose tokens match the task), but NO merged PR (`_FakeNoMergedPRs` or `_FakeMergedPRs([])`).
    - Assert result == [] (the integration branch is excluded from the Tier-2 scan, so a token-matching integration branch produces no In Progress proposal).

    Test C — plain feature branch still surfaces as In Progress via Tier-2:
    - `_FakeBranches(["migrate-platform"])` — a plain feature branch NOT matching the integration globs (no uat/work suffix, not `*-migration`), token-matching the task.
    - No merged PR.
    - Assert exactly 1 proposal, new_status == "In Progress", tier == 2. This proves the fix does not suppress legitimate Tier-2 signals for non-integration branches.

    Keep every test hermetic (mocked helpers / no network, no real git). Use `check(...)` for each assertion and guard indexed access with `if proposals:` as the existing tests do.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && python .claude/skills/activity-sync/test_reconcile.py</automated>
  </verify>
  <done>
    test_reconcile.py includes the three new tests (non-default integration-branch Done; integration branch no Tier-2 demotion; plain feature branch stays In Progress) plus a per-branch reachability fake. `python .claude/skills/activity-sync/test_reconcile.py` prints all PASS and exits 0.
  </done>
</task>

<task type="auto">
  <name>Task 3: Fix README repo drift + SKILL.md doc note</name>
  <files>README.md, .claude/skills/activity-sync/SKILL.md</files>
  <action>
    README.md — How-It-Works mermaid diagram (~lines 160-170). The `repos` subgraph currently declares 4 nodes (A kf-platform, B kf-fe-platform, C kf-be-platform, D R3-AAS) with 4 `-->|push trigger| GHA` edges. Add two nodes and two edges for the remaining tracked repos:
    - `E["ai-rise-options/kanban.md<br/>MermaidJS Kanban"]`
    - `F["tech_brainstorming/kanban.md<br/>MermaidJS Kanban"]`
    - `E -->|push trigger| GHA`
    - `F -->|push trigger| GHA`
    Match the existing node/edge formatting exactly (same `<br/>MermaidJS Kanban` label pattern, same edge label `|push trigger|`). Plain diagram nodes — no pills needed.

    Adjust any nearby framing prose that implies "the 3 KF repos + R3-AAS" is the complete tracked set, so it reflects 6 dynamically-scanned repos (activity-sync scans repos-local/, not a static 4). Do NOT touch the separate correct statement that the kanban GENERATOR (`generate_kanban.py`) splits only the 3 platform repos by discipline — that is about generator discipline-split, a different concern; leave it intact.

    SKILL.md — add a short doc note (in the RECONCILE section's [TIER-1]/[TIER-2] description, ~lines 68-73) stating that Tier-1 Done reachability and Tier-2 In Progress exclusion are evaluated against an INTEGRATION-BRANCH SET (default branch plus branches matching `INTEGRATION_BRANCH_GLOBS`: uat, work, *-migration), not the default branch alone — so work merged into an off-default integration branch is reported Done and integration branches never demote finished work to In Progress. Keep the [LABEL] text-pills convention; no emojis. Do not restate implementation details beyond the contract.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && grep -c 'push trigger| GHA' README.md | grep -qx 6 && grep -q 'ai-rise-options' README.md && grep -q 'tech_brainstorming' README.md && grep -q 'INTEGRATION_BRANCH_GLOBS' .claude/skills/activity-sync/SKILL.md && echo OK</automated>
  </verify>
  <done>
    README How-It-Works diagram has 6 repo nodes (A-F) each with a `|push trigger| GHA` edge (grep counts exactly 6); ai-rise-options and tech_brainstorming present; nearby framing reflects 6 tracked repos while the generator discipline-split statement is untouched. SKILL.md documents the integration-branch-set semantics for Tier-1/Tier-2. Verify command prints OK.
  </done>
</task>

</tasks>

<verification>
- `python .claude/skills/activity-sync/test_reconcile.py` exits 0 with all PASS (pre-existing + 3 new tests).
- `grep -c 'push trigger| GHA' README.md` returns 6.
- No hardcoded repo/branch name literals introduced into reconcile.py logic (grep for "kf-platform" / "claude-migration" / bare "uat" outside INTEGRATION_BRANCH_GLOBS returns nothing in the logic paths).
- Security posture preserved: sha/branch values only enter `_run_git` arg lists (no `shell=True`, no f-string-into-shell added).
</verification>

<success_criteria>
- Tier-1 Done is granted when a merge is reachable from ANY branch in the integration set (default ∪ glob-matched), short-circuiting on first True, conservative gate preserved (True only).
- Tier-2 excludes every integration-set branch from the active-branch scan, so integration branches never demote finished work to In Progress.
- Config lives solely in `INTEGRATION_BRANCH_GLOBS`; no per-repo override map, no hardcoded repo/branch literals in logic.
- Tests cover: non-default integration-branch Done, integration-branch Tier-2 exclusion, plain-feature-branch In Progress retention — all hermetic.
- README How-It-Works diagram shows all 6 tracked repos; SKILL.md documents the integration-branch-set contract; generator discipline-split statement untouched.
</success_criteria>

<output>
Create `.planning/quick/260707-cyc-make-activity-sync-account-for-off-defau/260707-cyc-SUMMARY.md` when done.
</output>
