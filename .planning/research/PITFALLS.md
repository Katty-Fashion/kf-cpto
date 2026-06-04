# Pitfalls Research

**Domain:** Activity-driven agentic-capacity migration dashboard skill (kf-cpto)
**Researched:** 2026-06-04
**Confidence:** HIGH — all pitfalls derived directly from the mapped codebase and the specific constraints stated in PROJECT.md

---

## Critical Pitfalls

### Pitfall 1: Write-back Clobbers a Concurrent Human Edit

**What goes wrong:**
The skill reads `kanban.md` from a local symlinked checkout, rewrites it, and force-commits to the tracked repo. If a human edited `kanban.md` (or pushed any commit to the same branch) between the skill's read and its push, the skill's push either fails (fast-forward rejection) or, if forced, silently overwrites the human's changes.

**Why it happens:**
The skill fetches activity, computes reconciled content, then runs a batch push. There is no fetch-immediately-before-write step. The window between "read the kanban" and "push the result" can be minutes if the skill is processing multiple repos sequentially.

**How to avoid:**
Before writing each repo: `git fetch origin && git merge-base --is-ancestor HEAD origin/<branch>`. If not an ancestor, abort that repo and surface it in the change list as `[CONFLICT] — skipped, human edit detected`. Never use `--force`; fail-fast on non-fast-forward. Log the skipped repos as a separate group in the batch confirmation summary so the user can resolve manually.

**Warning signs:**
- Push exit code 1 with `non-fast-forward` in stderr
- `git log origin/<branch>..HEAD` shows commits not in the local history at write time
- Any repo where `git status` shows a detached HEAD or unexpected tracked changes after the skill reads the file

**Phase to address:**
Write-back phase (the phase implementing commit + push to tracked repos)

---

### Pitfall 2: Partial-Batch Failure Leaves Repos Inconsistent

**What goes wrong:**
The skill batch-confirms once and then pushes to N repos sequentially. If repo 3 of 8 fails (network error, auth failure, branch protection rule), repos 1–2 have the updated `kanban.md` and will trigger CI rebuilds. Repos 3–8 still carry the old status. The dashboard aggregates all repos, so it shows a mixed state: some tasks reconciled, some not. Re-running the skill may double-apply changes to repos 1–2.

**Why it happens:**
No transactional semantics across N separate git repos. Batch confirmation happens before any push attempt, so the user has already approved the full set before failures are known.

**How to avoid:**
(a) Dry-run all pushes (verify network, auth, branch writeability) before the confirmation prompt — surface likely failures pre-confirm. (b) Track each repo's push outcome. (c) Write a recovery manifest (`skill-run-YYYYMMDD-HHMMSS.json`) listing which repos succeeded and which failed, with the intended diff, so a partial re-run only retries the failed set and skips already-pushed repos. (d) Make the reconciliation idempotent: running it twice on an already-updated `kanban.md` must produce no diff.

**Warning signs:**
- Any non-zero exit from `git push` for one repo in the batch
- The batch completes but the aggregator shows fewer updated projects than were in the skill's change list
- CI dispatch fires for some repos but not others after the skill run

**Phase to address:**
Write-back phase; also the reconciliation phase must produce idempotent diffs

---

### Pitfall 3: Accidental Push to Wrong Branch

**What goes wrong:**
The skill determines the target branch from the local checkout's current HEAD branch. If a sibling repo has its default branch set to something other than `main`/`master` (e.g., `dev`, `release/v2`), or if the local checkout is on a feature branch the developer was working on, the skill pushes the reconciled `kanban.md` to that branch instead of the canonical default. The `notify-kf-cpto.yml` in that repo may only watch pushes to `main`, so the dispatch never fires and the CI re-render is silently skipped.

**Why it happens:**
The skill reads the repo via symlink to the sibling checkout as-is. It inherits whatever checkout state the developer left the repo in. There is no enforcement that the local checkout must be on the default branch before the skill runs.

**How to avoid:**
At skill startup, for each tracked repo: read the GitHub API `repos/{owner}/{repo}` response to get `default_branch`; verify that the local checkout's `HEAD` branch matches it. Refuse to proceed for any repo where they diverge, and list it as `[WRONG BRANCH] — checkout is on 'feature/x', default is 'main'`. Also verify that `notify-kf-cpto.yml` watches pushes to that default branch, not a hardcoded `main`.

**Warning signs:**
- `git branch --show-current` returns something other than `main` or `master` for a project repo
- CI dispatch does not fire after a push that the skill recorded as successful
- Dashboard does not update within the expected CI window after skill run

**Phase to address:**
Pre-flight validation phase (before any write-back)

---

### Pitfall 4: Inferred "Done" from a Reverted PR

**What goes wrong:**
The skill sees a merged PR and marks the corresponding task as `Done`. The PR was subsequently reverted (a second merge of a revert PR). The revert PR has a different title/branch naming convention, so the skill does not connect it to the original task. The dashboard now shows a task as `Done` that is actually back in progress or cancelled.

**Why it happens:**
Activity mining typically looks at merge events. Revert PRs are named `Revert "..."` by GitHub's default, but branch names vary (`revert-123-feature-name`, `hotfix/revert-auth`, etc.). Without checking whether the merged commit is still reachable from the default branch tip, the merge event is an unreliable "done" signal.

**How to avoid:**
Do not infer `Done` from the PR merge event alone. Use `git merge-base --is-ancestor <merge-commit-sha> origin/<default-branch>` to verify the merged commit is still in the live history. If the commit is not reachable (it was reverted), do not promote the task. Additionally, if two PRs exist for the same task slug — one a merge and one a revert — treat the task as `needs-review` and flag it in the change list instead of auto-setting status.

**Warning signs:**
- A task moves to `Done` but engineers immediately re-open or comment on related work
- The default branch tip's `git log --oneline` contains a `Revert "..."` commit referencing the same feature
- PR list for the repo shows a merged revert PR within days of the original merge

**Phase to address:**
Activity-mining phase

---

### Pitfall 5: Branch-Naming Assumptions Break FE/BE Attribution

**What goes wrong:**
The skill routes capacity by parsing task owner fields (`FE`, `BE`, `FE+BE`) from `kanban.md`. But when inferring which commits belong to which task for activity signals, it may fall back to branch names (e.g., `feature/auth-FE`, `fix/api-timeout`). If repo authors do not follow a branch-naming convention, the heuristic fails silently: BE commits are attributed to FE capacity or vice versa, making the overflow model wrong without any error surfacing.

**Why it happens:**
Branch naming is entirely unconstrained. The skill developer assumes a pattern that works on their own repos but is inconsistently followed across the org.

**How to avoid:**
Ground FE/BE attribution exclusively in the `kanban.md` task table's Owner column, not in branch names or commit metadata. Treat git activity (commits, PRs, branches) only as signals for *whether* a task moved, not *who* it belongs to. The owner/discipline assignment must always come from the structured `kanban.md` data, not inferred from unstructured git metadata.

**Warning signs:**
- Capacity model shows FE at 40% and BE at 160% but task table shows roughly equal distribution — attribution logic is wrong
- Commits from a known BE engineer are appearing in FE capacity calculations
- Skill output changes radically when a repo switches from `feature/FE-xxx` to `feat/xxx` branch naming

**Phase to address:**
Activity-mining phase; also capacity-model phase must document that owner comes from kanban, not git

---

### Pitfall 6: Stale Local Clone Produces Wrong Activity Signals

**What goes wrong:**
The skill reads git activity from the sibling checkout symlinks. If those checkouts are days or weeks behind `origin`, the skill will not see recent commits or PRs. It will report tasks as `In Progress` or `Not Started` when they are actually merged and deployed. The reconciliation will "revert" a Done status back to In Progress and push that incorrect regression to the repo.

**Why it happens:**
The skill uses local symlinks to sibling repos for convenience. Those repos are only as fresh as when the developer last ran `git pull`. There is no skill-side fetch step that updates them before reading.

**How to avoid:**
At skill startup, `git fetch origin` each tracked repo before reading any git history or branch state. Do not rely on the working tree or local log for activity; always compare against `origin/<default-branch>` after fetching. Log the fetch result (new commits found vs. already up to date) in the pre-run summary.

**Warning signs:**
- Skill reports no recent activity for repos the team knows have been active
- `git log HEAD..origin/main` returns commits after the skill runs a fetch
- The skill's inferred status contradicts what the developer can see on GitHub

**Phase to address:**
Activity-mining phase (pre-flight fetch must be the first step)

---

### Pitfall 7: Monorepo Commit Attribution Ambiguity

**What goes wrong:**
If a tracked repo contains both FE and BE code in subdirectories (a monorepo), a single commit may touch FE files, BE files, or both. The skill has no way to determine from commit metadata alone whether the commit represents FE work, BE work, or mixed. Attributing it to one discipline over-counts one capacity lane and under-counts the other.

**Why it happens:**
The activity mining looks at commits to the whole repo. Monorepos are common in the katty-fashion org, and the `kanban.md` task table uses `FE+BE` as a combined owner tag that means "both disciplines, not one or the other."

**How to avoid:**
For monorepo repos, do not attempt to infer FE/BE split from commit file paths. Trust the task-level Owner field entirely. A task tagged `FE+BE` counts toward both discipline budgets at its declared effort. A task tagged `FE` counts only toward FE even if the commit touched a BE file. Document this explicitly in the skill's reconciliation logic comment.

**Warning signs:**
- A repo with `src/frontend/` and `src/backend/` directories shows unexpected capacity imbalances
- BE capacity is undercounted for sprints where all work was in a monorepo
- `FE+BE` tasks are appearing only once in the total hours count instead of contributing to both lanes

**Phase to address:**
Capacity-model phase; note in design doc that file-path-based attribution is explicitly out of scope

---

### Pitfall 8: Agentic Number Becomes Meaningless

**What goes wrong:**
The agentic assignee row in the LOE output shows 80+ hours, which the team reads as "80h of AI magic will handle it." In reality the model just deferred everything that didn't fit into human capacity without any feasibility check. The agentic total grows unboundedly as more sprints overflow, masking genuine over-scope risk. Stakeholders stop treating the timeline as actionable because "agentic handles it."

**Why it happens:**
The capacity model is pure arithmetic: `agentic_hours = max(0, total_task_hours - human_capacity)`. It never asks whether the deferred work is actually amenable to agentic execution, and it never surfaces a ceiling. The replacement of the 0.5 FTE recommendation in migration-gantt §8.2 only makes sense if the agentic designation is bounded and interpretable.

**How to avoid:**
Introduce an explicit agentic capacity ceiling (e.g., 20% of combined FTE capacity per sprint, or a fixed absolute limit like 16h/week). When overflow exceeds the ceiling, surface it as `[WARN: agentic capacity exceeded — Xh unresolved]` in the change list, not silently packed into the agentic row. The agentic row must show: declared hours, ceiling, and whether the ceiling was breached. Add a note in the LOE output or migration-gantt §8.2 replacement section explaining what "agentic" means in context.

**Warning signs:**
- Agentic row in LOE grows by 20+ hours sprint over sprint without any corresponding descope decision
- No sprint has ever shown the agentic limit as breached
- Team members cannot explain what the agentic row means when asked

**Phase to address:**
Capacity-model phase

---

### Pitfall 9: Double-Counting FE+BE Tasks

**What goes wrong:**
A task tagged `Owner: FE+BE` with `Effort: 3d` is intended to mean "3 days total, split across both disciplines." If the capacity model counts it as 3d against FE capacity AND 3d against BE capacity, it inflates total demand by 100% for all joint tasks. The overflow sent to agentic will be too large, and the "BE at 106%" figure from migration-gantt §8.2 will be over-reported.

**Why it happens:**
The effort string is a single number with no per-discipline split. Naive iteration over task rows counts each row's effort once per matching discipline if the filter is `if owner in ('FE', 'FE+BE')`.

**How to avoid:**
Define a canonical split rule before implementing: `FE+BE` tasks split effort 50/50 by default (1.5d FE + 1.5d BE for a 3d task), unless the task carries an explicit split override. Document this rule in the skill's code and in the migration-gantt §8.2 replacement comment so the math is auditable. Never count the full effort against both lanes.

**Warning signs:**
- Total demand hours across FE + BE is more than the sum of all task effort-days in the kanban
- FE and BE overflow appear to be nearly identical (a sign that joint tasks are counted twice in both lanes)
- Removing all `FE+BE` tasks makes the totals match expected values

**Phase to address:**
Capacity-model phase (must be specified before any implementation)

---

### Pitfall 10: Migration-Gantt 20% Buffer Already in Estimates

**What goes wrong:**
The capacity model treats each FTE as having a raw `40h/week` budget and computes overflow as anything above that. But migration-gantt task estimates may already include a 20% buffer baked in by the author. Applying another 20% buffer in the capacity model (e.g., "use 80% of 40h = 32h effective capacity") double-buffers. Conversely, if no buffer is applied in the model, estimates that already include padding will produce less overflow than reality, hiding risk.

**Why it happens:**
The planning doc (migration-gantt §8.2) and the capacity model are written by different agents at different times. The buffer convention is not recorded in the kanban frontmatter or any machine-readable field — it exists only as a prose note in the migration-gantt.

**How to avoid:**
Read migration-gantt §8.2 before implementing the capacity model. Document explicitly in the skill's design: "task effort estimates include a 20% buffer; do NOT apply additional buffer in the model; use raw 40h/week per FTE." Add a machine-readable assertion (e.g., a comment constant `ESTIMATES_INCLUDE_20PCT_BUFFER = True`) in the capacity model code so future editors do not accidentally add another layer.

**Warning signs:**
- Capacity model shows both FE and BE under 80% utilization in a sprint that engineering described as slammed
- Agentic overflow is zero for every sprint (buffer-on-buffer is masking real overflow)
- Removing the buffer multiplier from the model doubles the overflow figure

**Phase to address:**
Capacity-model phase (design decision, not implementation detail)

---

### Pitfall 11: Mermaid Sanitizer Over-Strips Legitimate Content

**What goes wrong:**
The sanitizer removes anything that looks like a problematic character. It strips Romanian diacritics (ă, â, î, ș, ț) from task names because they fall outside ASCII, or because a naive regex targets non-ASCII generally. Project names and assignee names in the katty-fashion org may use these characters legitimately. Stripping them changes the content of kanban entries, causing mismatches between the dashboard display and the source `kanban.md`.

**Why it happens:**
The sanitizer's threat model is "Mermaid breaks on certain characters." The developer writes a regex like `[^\x00-\x7F]` (strip non-ASCII) when the actual Mermaid constraint is narrower: quotes inside node labels, semicolons in gantt date fields, and the specific characters that break Mermaid's tokenizer.

**How to avoid:**
Define the sanitizer's whitelist precisely: Mermaid breaks on unescaped `"` inside quoted labels, `;` and `:` in certain Mermaid dialects, and `<>` with `securityLevel: 'loose'` (already flagged in CONCERNS.md). Romanian diacritics do not break Mermaid and must pass through untouched. Emojis do break Mermaid gantt rendering and should be stripped. The sanitizer must have an allowlist of specific problematic patterns, not a blocklist of "non-ASCII." Write unit tests with Romanian strings before shipping the sanitizer.

**Warning signs:**
- A task named `Ediție finală` appears as `Editie final` in the dashboard
- Team members report that project names look wrong after a skill run
- The sanitizer's output differs from the input for strings containing ă/â/î/ș/ț but no emojis

**Phase to address:**
Mermaid sanitization phase

---

### Pitfall 12: Sanitizer Breaks AUTO-Block Idempotency

**What goes wrong:**
The skill sanitizes `kanban.md` content before writing it back. The sanitizer also runs over the full file, including the AUTO-block markers (`<!-- AUTO:calendar -->` etc.) or the content inside AUTO-block sections. After the push, `aggregate.yml` runs `validate_auto_blocks.py`, which checks marker/renderer/frontmatter consistency. If the sanitizer has altered a marker comment (e.g., stripped a character from inside a Liquid tag or reformatted a comment), `validate_auto_blocks.py` exits non-zero and blocks the CI run.

**Why it happens:**
The sanitizer is applied to the full file content, not just the human-edited task table rows. AUTO-block markers are HTML comments that could hypothetically match a "strip HTML-like patterns" rule.

**How to avoid:**
Scope the sanitizer strictly to the Markdown task table rows only (the lines between the table header and the end of the table section). Never run the sanitizer over frontmatter, AUTO-block markers, or AUTO-block interior content. Parse the file into sections first, sanitize only the task table section, then reassemble. Add an assertion: the sanitizer's output must pass `validate_auto_blocks.py` locally before the file is written to disk.

**Warning signs:**
- CI fails on `validate_auto_blocks.py` immediately after a skill run
- The diff of a sanitized `kanban.md` shows changes outside the task table rows
- AUTO-block marker lines appear in the git diff for a file the skill touched

**Phase to address:**
Mermaid sanitization phase; also write-back phase must run local validation before pushing

---

### Pitfall 13: Non-Deterministic LLM Output Leaks into the Deterministic Renderer

**What goes wrong:**
The skill uses Claude to infer task status from commit messages or PR titles. The LLM output (e.g., `In Progress`, `Done`, `Blocked`) is written directly into `kanban.md` task rows. Across two runs on identical inputs, the LLM returns slightly different phrasing (`In Progress` vs `in progress` vs `In-Progress`). The aggregator's `parse_kanban_tasks()` recognizes only the exact status values defined in `utils.VALID_STATUSES`. An unrecognized status emits a `Warning:` and may default to empty, silently dropping the task from LOE output.

**Why it happens:**
The skill's reconciliation logic does not normalize LLM output to the canonical status vocabulary before writing. LLMs do not reliably reproduce exact strings without structured output constraints.

**How to avoid:**
Use a structured output schema (e.g., `response_format: {type: 'json_schema'}` or explicit enum constraint) when asking the LLM to classify task status. Map the LLM's response through a normalization function before writing: `{"done": "Done", "in progress": "In Progress", "in-progress": "In Progress", ...}`. Run the output through `utils.parse_kanban_tasks()` locally and assert all statuses are valid before committing the file.

**Warning signs:**
- `Warning: Unknown status 'in-progress'` in aggregator output after a skill run
- LOE report row count drops after a skill run compared to before
- Status values in the pushed `kanban.md` use varied capitalization or hyphenation

**Phase to address:**
Reconciliation phase (normalization must be a hard constraint before any file write)

---

### Pitfall 14: Re-Parsing kanban.md Inside the Skill Bypasses the Canonical Parser

**What goes wrong:**
The skill reads `kanban.md` to build its own in-memory representation for reconciliation. If it writes a custom parser (even a lightweight one) rather than calling `utils.parse_kanban_tasks()` and `utils.parse_kanban_frontmatter()`, two parsers exist for the same format. When the existing parsers have known fragilities (pipe-count column detection, greedy separator matching — both documented in CONCERNS.md), the skill's parser will have different fragilities. The two parsers will disagree on edge cases, producing different status readings, effort values, or missing tasks.

**Why it happens:**
The skill is a local tool, not a CI script; developers reach for quick string parsing rather than importing the existing `utils.py`. The parsers are in `scripts/utils.py`, which requires some path setup to import from a skill context.

**How to avoid:**
Import `scripts/utils.py` directly in the skill. Set `sys.path` to include the project root so `from scripts.utils import parse_kanban_tasks, parse_kanban_frontmatter` works. This is the "one parser" contract stated in PROJECT.md constraints. Any new fields the skill needs to write must be added to `utils.py` and `aggregator.build_loe_rows()` — not handled in skill-local code.

**Warning signs:**
- The skill reports a different task count for a repo than `aggregator.py` does on the same file
- Effort values parsed by the skill differ from what appears in the LOE report
- The skill's status reading for a 6-column table is wrong but the aggregator reads it correctly (or vice versa)

**Phase to address:**
Reconciliation phase and activity-mining phase (import `utils.py` from day one)

---

### Pitfall 15: Sheets exit-0 Invariant Silently Broken by New Skill Code

**What goes wrong:**
The skill adds a new step that writes to `docs/_data/loe.yml` (e.g., injecting agentic row data) or modifies `sync_status.yml` outside the normal `aggregator.py` path. If this step raises an exception and the skill does not wrap it in a try/except with exit 0, the CI step that runs the skill fails, blocking the Pages deploy step that follows.

**Why it happens:**
The invariant is enforced in `sheets_sync.py` but not described as a general pipeline rule. A new developer adds skill-adjacent code to the pipeline without realizing the exit-0 contract applies to every step that follows the Pages deploy.

**How to avoid:**
The skill does not run in CI — it runs locally (PROJECT.md constraint: "CI stays self-contained"). The skill must never be called from `aggregate.yml` or any workflow. If the skill ever produces output that feeds into `loe.yml`, it must do so by writing a valid `kanban.md` and letting the existing CI pipeline regenerate `loe.yml` from scratch. Do not shortcut by directly writing `loe.yml` from the skill.

**Warning signs:**
- Any `import sheets_sync` or `import aggregator` in the skill's main script
- A PR adds the skill as a CI step in `aggregate.yml`
- The skill writes directly to `docs/_data/` instead of to the project repos' `kanban.md`

**Phase to address:**
Architecture / integration phase (must be clear in design before implementation)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Write a local kanban.md parser in the skill | Avoids import path setup | Two parsers diverge; edge cases handled differently | Never — import `utils.py` |
| Use branch names for FE/BE attribution | Easy to implement | Attribution breaks when naming conventions vary | Never — use Owner column |
| Skip pre-push `git fetch` | Faster skill execution | Stale clone overwrites newer human edits | Never |
| Apply sanitizer to full file | Simpler code | Corrupts AUTO-block markers, breaks CI validate step | Never |
| No agentic ceiling | Simpler model | Agentic row grows unboundedly, hides real over-scope | Never |
| Infer Done from merge event alone | Simple signal | Reverted PRs leave tasks incorrectly marked Done | Never |
| Write directly to `loe.yml` from skill | Bypasses CI roundtrip | Breaks "one parser, one canonical intermediate" | Never |
| Batch-confirm after partial push has started | Cleaner UX | Partial batch leaves repos in mixed state | Never |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| git push to N repos | Assume all succeed or all fail atomically | Track per-repo outcome; write recovery manifest; make reconciliation idempotent |
| GitHub API `default_branch` | Assume it is always `main` | Read `repos/{owner}/{repo}` API response; verify local checkout matches |
| `notify-kf-cpto.yml` dispatch trigger | Assume push to any branch triggers CI | Verify the notify workflow's `on.push.branches` filter matches the actual default branch |
| `utils.py` import | Create a new parser to avoid import path complexity | Add repo root to `sys.path` and import `scripts.utils` directly |
| AUTO-block markers | Run sanitizer over full file | Scope sanitizer to task table section only; verify with `validate_auto_blocks.py` locally |
| LLM status classification | Accept raw LLM text as kanban status | Use structured output or post-process through a normalization map |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential git fetch across N repos | Skill startup is slow (10–30s per repo) | `ThreadPoolExecutor` for fetches; they are independent | At 5+ tracked repos |
| Read full git log for activity mining | Slow on repos with long history | Use `git log --since=<sprint-start>` or `--max-count=100`; history beyond the current sprint is noise | Repos with 1000+ commits |
| Shallow clone depth 1 in CI vs. full clone locally | Skill sees full history locally but CI only sees depth-1 | Ensure activity mining uses the same depth assumption; do not rely on merge-base operations that require full history | Any repo used in both contexts |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Inlining `KF_PAT` in git remote URLs | Token visible in `git remote -v` and process listings | Use `git config --global credential.helper` or credential store pattern (already flagged in CONCERNS.md) |
| Writing unvalidated LLM output to `kanban.md` | Injected content could break Mermaid rendering or introduce XSS via `securityLevel: 'loose'` (already flagged in CONCERNS.md) | Normalize status to enum; sanitize task names before write; validate output parses cleanly before commit |
| Skill reads PAT from env and logs it in error traces | Key leakage in local terminal history | Catch auth errors specifically; never print the token value in error messages |

## "Looks Done But Isn't" Checklist

- [ ] **Reconciliation:** Status values written to `kanban.md` must be verified against `utils.VALID_STATUSES` before commit — do not trust LLM output directly
- [ ] **Write-back:** Pre-push fetch must happen for every repo in the batch, not just the first one
- [ ] **Capacity model:** `FE+BE` tasks must use split effort, not full effort against both lanes — verify by summing all task hours and comparing to the total from `loe.yml`
- [ ] **Sanitizer:** Must be verified against strings containing ă/â/î/ș/ț to confirm they are not stripped — add a fixture test
- [ ] **Sanitizer:** Must be verified that AUTO-block marker lines are unchanged after sanitization — diff must show zero changes outside the task table
- [ ] **Agentic ceiling:** The agentic row must show a warning when overflow exceeds the ceiling — verify by constructing a scenario where it overflows
- [ ] **Idempotency:** Running the skill twice in sequence on an already-updated repo must produce zero git diff — verify before shipping the reconciliation phase
- [ ] **Branch safety:** Skill must refuse to write to a repo where the local checkout is not on the default branch — verify with a test repo checked out to a feature branch

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Clobbered human edit | HIGH | `git reflog` in the affected repo to find the clobbered commit; cherry-pick human changes on top of the skill's commit; push; re-trigger CI dispatch |
| Partial batch failure | MEDIUM | Read recovery manifest; re-run skill with `--retry-failed` flag targeting only failed repos; verify idempotency before retry |
| Wrong branch push | MEDIUM | `git checkout <default-branch>` in affected repo; cherry-pick the skill's commit; delete the wrong-branch commit; push to correct branch |
| LLM status leak causing Warning | LOW | Manually correct the status value in `kanban.md`; push; CI will re-render cleanly |
| Sanitizer stripped Romanian chars | MEDIUM | Revert the skill's commit in the affected repo; fix the sanitizer's allowlist; re-run |
| AUTO-block marker corruption | HIGH | Revert the skill's commit; fix the sanitizer scope; re-run; CI will validate markers on the next push |
| Double-counted FE+BE capacity | HIGH | Recalculate capacity model with correct split rule; re-run skill; audit all historical LOE exports if Sheets was already updated |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Write-back clobbers human edit | Write-back phase | Pre-push fetch is in the code; non-fast-forward causes repo to be skipped, not overwritten |
| Partial-batch failure | Write-back phase | Recovery manifest is written; re-run on failed set works without double-applying |
| Accidental push to wrong branch | Pre-flight validation phase | Skill refuses to proceed for repos with wrong local branch; verified with a test repo on a feature branch |
| Done inferred from reverted PR | Activity-mining phase | Test with a repo that has a merge + revert pair; task must not be marked Done |
| Branch-naming FE/BE attribution | Activity-mining phase | Owner values come exclusively from task table; grep for branch-based attribution in skill code returns zero results |
| Stale local clone | Activity-mining phase | Skill logs `git fetch` output for each repo; activity reads from `origin/<branch>` not local HEAD |
| Monorepo commit attribution | Capacity-model phase | No file-path logic exists in attribution code; `FE+BE` tasks use split effort |
| Agentic number meaningless | Capacity-model phase | Agentic ceiling constant exists; breach emits visible warning in change list |
| Double-counting FE+BE | Capacity-model phase | Sum of per-discipline hours equals sum of task effort-days (not double); validated by unit test |
| 20% buffer already baked in | Capacity-model phase | `ESTIMATES_INCLUDE_20PCT_BUFFER = True` constant; raw 40h capacity used; documented in §8.2 replacement |
| Sanitizer over-strips Romanian | Mermaid sanitization phase | Unit test with ă/â/î/ș/ț fixture; output must equal input for those characters |
| Sanitizer breaks AUTO-blocks | Mermaid sanitization phase | Local `validate_auto_blocks.py` run is a required step before any file write |
| LLM output leaks non-canonical status | Reconciliation phase | Status normalization map exists; output validated against `utils.VALID_STATUSES` before write |
| Skill re-parses kanban.md locally | Reconciliation + activity-mining phases | Single `import scripts.utils` in skill; no other kanban parsing code exists |
| Sheets exit-0 invariant broken | Architecture / integration phase | Skill has no presence in `aggregate.yml`; writes only to project repos' `kanban.md` |

## Sources

- Codebase mapping: `.planning/codebase/ARCHITECTURE.md` (anti-patterns, error handling, fragile areas)
- Codebase concerns: `.planning/codebase/CONCERNS.md` (tech debt, fragile areas, known bugs)
- Project scope and constraints: `.planning/PROJECT.md` (out of scope, constraints, key decisions)
- Mermaid rendering: Mermaid securityLevel concern flagged in CONCERNS.md security section
- Pipeline topology: Pages-first, Sheets downstream (PROJECT.md context, ARCHITECTURE.md data flow)

---
*Pitfalls research for: activity-driven agentic-capacity migration dashboard skill (kf-cpto)*
*Researched: 2026-06-04*
