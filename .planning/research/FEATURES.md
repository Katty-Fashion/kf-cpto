# Feature Research

**Domain:** Activity-driven agentic-capacity migration dashboard skill
**Researched:** 2026-06-04
**Confidence:** HIGH (core patterns), MEDIUM (agentic capacity representation)

---

## Scope Reminder

This file covers the NEW capability being added: the local Claude skill that reconciles
git activity against declared kanban status, writes corrected `kanban.md` back to tracked
repos, and models over-capacity work as a synthetic Agentic assignee. It does NOT cover
existing dashboard features (kanban, gantt, LOE report, calendar, dependency graph,
Sheets export) — those already exist and are validated.

---

## Feature Landscape

### Table Stakes (Skill Is Untrustworthy Without These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Explicit change list on every run | An automated tool that edits source files MUST show every change it made, in plain language, before writing. Without this, it is a black box. | LOW | Per-file: old status → new status, reason. Not a git diff — a human-readable sentence per change. |
| Batch write-back confirmation (once, not per-repo) | The project memory explicitly requires no per-repo prompting. Batch-confirm once or abort. | LOW | Matches org-scan workflow preference. The confirmation gate is the only human checkpoint before pushes fly. |
| Conflict detection before write-back | If a `kanban.md` has been modified since the skill read it, the skill must detect the conflict and abort that repo's write, not silently overwrite. | MEDIUM | Compare file mtime or git HEAD before writing. Failing this destroys concurrent human edits. |
| Signal-to-status mapping transparency | Each status update must state which signal triggered it (e.g., "PR #42 merged 2026-05-30 → Done"). Not just "updated to Done." | LOW | Without the reason, the operator cannot verify or override the inference. |
| No-change idempotency | Running the skill twice on an already-reconciled state must produce zero changes. | LOW | Prevents noise when CI re-runs the skill. Required for the `notify → dispatch` loop to not thrash. |
| Dry-run / preview mode | Run with `--dry-run` to see all proposed changes without writing. | LOW | Critical for first-run trust-building and debugging. Without this, users cannot safely explore what the skill would do. |
| Mermaid sanitization before any write | Any content written to `kanban.md` that will ultimately feed Mermaid diagrams must be stripped of emojis and pathological characters. | LOW | Mermaid v11 does not handle emojis or special characters reliably — they silently break diagram rendering. Sanitize on ingest, not at render time. |

### Differentiators (What Makes This Skill Worth Building)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| [HEADLINE] Agentic-overflow capacity model | Over-capacity work deferred to a synthetic "Agentic" assignee instead of recommending a new hire. Human FTEs are pinned at 100%; only the overflow hours flow to the Agentic row. Replaces the "add 0.5 FTE" recommendation in migration-gantt §8.2. | HIGH | Requires: (1) per-discipline capacity ceiling (FE: 1 FTE, BE: 1 FTE), (2) task-level overflow detection, (3) `assignee: Agentic` as a valid kanban field value, (4) aggregator.build_loe_rows() extended to produce Agentic rows. |
| Agentic shown as its own LOE row/slice | The Agentic assignee appears as a distinct row in the LOE report and a distinct slice in any pie/bar charts — not lumped into BE or FE, not hidden. Makes the agentic share legible without distorting human lines. | MEDIUM | Purely a rendering/data concern: loe.yml must carry `assignee: Agentic` rows; aggregator generates their section; Sheets export renders them in a separate block. |
| Git-signal reconciliation (not keyword matching) | Inference driven by verifiable git events (merged PR, live branch with commits, closed issue linked to branch) rather than free-text scanning of commit messages. Reliable signals only; ambiguous signals produce a flag, not an auto-update. | HIGH | See Signal Tier taxonomy below. Verifiable-only signals auto-update; ambiguous signals flag for human review. This is the line between trustworthy and noisy. |
| Bidirectional status correction (auto-update + flag diffs) | The skill both corrects clear discrepancies automatically AND flags ambiguous ones for human review. Neither silent-fix-all nor flag-only. | MEDIUM | Auto-update: merged PR with no linked task, branch active for task still marked Todo. Flag-only: commit activity for task in Blocked status (might be workaround commits). |
| Replace headcount recommendation in migration-gantt §8.2 | The existing prose recommendation ("add 0.5 FTE BE or descope") is replaced by a computed agentic-deferral statement driven by actual overflow hours. | MEDIUM | This is an AUTO block replacement — the renderer for the §8.2 block computes overflow from loe.yml and emits the deferral narrative. No hand-editing needed after first wiring. |

### Anti-Features (Deliberately NOT Built)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Silent rewrites (no change list) | Seems faster | Destroys trust. Operator has no way to verify correctness or catch model errors. One wrong status flip silently propagates through CI. | Always emit an explicit change list. Make it impossible to write back without the list being shown first. |
| Commit-message keyword inference for Done status | Seems clever ("feat: implement X" → task X is Done) | Commit messages are noisy, inconsistently formatted, and only weakly correlated with declared task scope. False-positive rate is high enough to corrupt the board. | Only use verifiable signals: merged PR, closed branch, issue-close event. |
| File-path-touched inference for task scope | Seems data-rich (if `src/checkout/` changed, checkout task is Done) | File paths don't map cleanly to kanban task names. The same files are touched across many tasks. Produces systematic false positives. | Require explicit task-ID references in branch names or PR titles for scope binding. |
| Per-repo interactive confirmation during org scan | Feels safer | Creates interactive stalls across N repos. Violates the explicit project constraint and org-scan preference. | Batch-confirm once. List all proposed writes upfront. |
| Agentic capacity as a percentage of a hypothetical FTE | Easier to present | Fabricated. There is no principled basis for "Agentic = 0.5 FTE." It is a guess dressed as a number. | Express agentic share in the same units as human effort — days (Nd). Overflow hours are calculable; just label them Agentic. |
| Real-time or continuous reconciliation | Seems powerful | Introduces polling, statefulness, and race conditions against concurrent human edits. The pipeline is event-driven (push → dispatch), not continuous. | Run on demand (one command) or on push. Let the existing notify → dispatch loop handle re-renders. |
| Auto-close tasks with no recent git activity | Seems like cleanup | "No activity" is not a reliable signal — tasks can legitimately be blocked, deferred, or waiting for dependencies. Silently closing them corrupts the plan. | Flag zero-activity tasks in the diff report. Let a human decide. |
| New dashboard pages | Feels like natural extension | Explicitly out of scope for this milestone. Scope creep into new views delays the core reconciliation and capacity features. | Refine existing views (kanban, gantt, LOE). |

---

## Signal Tier Taxonomy

This taxonomy drives what the reconciliation engine auto-updates vs. flags vs. ignores.

### Tier 1 — Verifiable (auto-update allowed)

These events are deterministic, timestamped, and cannot be misattributed:

| Signal | Status Inference | Notes |
|--------|-----------------|-------|
| PR merged to main/master, branch name contains task ID | Done | Highest confidence. Merge is irreversible and explicitly scoped. |
| GitHub issue closed, issue title matches task | Done | Issue close is deliberate human action. Use title match as secondary confirmation. |
| Branch `feature/<task-id>-*` exists with commits, task status is Todo | In Progress | Branch creation is an explicit human action. Safe to advance. |
| PR open (not draft), task status is Todo or In Progress | In Review | PR opening is deliberate. Use only when PR title references task or branch carries task ID. |

### Tier 2 — Ambiguous (flag, do not auto-update)

These signals suggest something may be wrong but are not conclusive:

| Signal | Flag Message | Reason for Caution |
|--------|-------------|-------------------|
| Commit activity on a branch for a task marked Blocked | "Task X is Blocked but branch Y has N commits since blockage date" | Could be workaround commits, unrelated fixups, or the block is resolved but status not updated. |
| Task marked Done but no merged PR and no closed branch found | "Task X is Done but no merged PR or closed branch found" | Could be non-code work (docs, design) legitimately completed without a PR. Do not revert to Todo automatically. |
| Stale In Progress — branch exists but last commit is >14 days ago, task not Done | "Task X has been In Progress for >14 days with no recent commits" | Might be blocked, abandoned, or waiting for review. Flag for human review. |
| Multiple open PRs touching same files as task | "Possible overlap: PRs Y and Z both touch files associated with task X" | Ambiguous scope. Do not auto-reassign. |

### Tier 3 — Noise (ignore)

| Signal | Why Ignored |
|--------|-------------|
| Commit message text (feat: ..., fix: ...) without task ID | Too noisy and inconsistently maintained. |
| File paths touched | No reliable mapping from file path to kanban task scope. |
| Commit count or frequency | Activity level says nothing about completion. A complex task has many commits; a simple one has one. |
| Draft PR | Author has explicitly signaled the work is not ready. Treat as no signal. |

---

## Capacity Model Specification

### Units: Effort Days (Nd)

Effort days (already the existing unit in `kanban.md` — e.g., `2d`, `L=5d`) are the correct unit for the agentic model. Do NOT introduce:
- Story points (not used in this codebase, adds translation complexity)
- Percentages (misleading — "Agentic = 20%" of what, exactly?)
- Hours (false precision for tasks sized at S/M/L/XL)

Stick with days. The overflow calculation is simple: `sum(task_effort_days where assignee = BE) - BE_capacity_days = agentic_overflow_days`.

### Capacity Ceiling Definition

```
FE capacity  = 1.0 FTE × sprint_working_days
BE capacity  = 1.0 FTE × sprint_working_days
Agentic      = sum(overflow hours beyond each discipline's ceiling)
```

Human FTEs are NEVER raised above 1.0 to absorb overflow. The overflow is reassigned to Agentic, not redistributed to the human.

### Overflow Presentation

Credible resource planners use color-coded threshold bars (green <80%, amber 80-100%, red >100%). For this dashboard's LOE outputs:

- Human rows show utilization against their ceiling (days assigned / sprint capacity × 100%)
- Agentic row shows total overflow days — no percentage, just raw days (a percentage would require a fictional "Agentic capacity" denominator)
- The §8.2 AUTO block replaces "add 0.5 FTE" with: "BE overflow: Xd assigned to Agentic. FE overflow: Yd assigned to Agentic."

### What Makes the Numbers Honest

1. Overflow days are derived directly from existing `effort_days` values in `loe.yml` — no estimation or rounding.
2. The Agentic row is labeled `[SYNTHETIC]` in the change list so reviewers know it is model-generated, not a real assignee.
3. No claim is made about AI speed multipliers, token budgets, or agentic "velocity." Those are unknowable and would be fabricated.
4. If overflow is zero, the Agentic row is absent from loe.yml — not shown as "0d" — because an empty synthetic row is noise.

---

## Feature Dependencies

```
[Dry-run mode]
    └──requires──> [Signal-to-status inference engine]

[Explicit change list]
    └──requires──> [Signal-to-status inference engine]
    └──required by──> [Batch write-back confirmation gate]

[Batch write-back confirmation gate]
    └──required by──> [Conflict detection]
    └──required by──> [Write-back to repos]

[Write-back to repos]
    └──triggers (existing)──> [notify → dispatch → CI render]

[Agentic-overflow capacity model]
    └──requires──> [Extend aggregator.build_loe_rows() + write_loe_yaml()]
    └──requires──> [Agentic as valid assignee in kanban.md schema]
    └──feeds──> [Agentic LOE row/slice in dashboard]
    └──feeds──> [§8.2 AUTO block replacement in migration-gantt]

[§8.2 AUTO block replacement]
    └──requires──> [Agentic-overflow capacity model]
    └──requires (existing)──> [auto_blocks.AUTO_BLOCK_RENDERERS registry]

[Mermaid sanitization]
    └──required by──> [Write-back to repos]  (sanitize before any write)
    └──required by──> [aggregator.py generated content]  (sanitize on ingest path)
```

### Dependency Notes

- **Write-back requires the change list to be shown first:** The batch confirmation gate cannot be bypassed — without it the skill would be an autonomous rewriter with no human checkpoint.
- **Agentic model requires aggregator extension, not a new parser:** The "one parser, one canonical intermediate" constraint means overflow computation happens inside `aggregator.build_loe_rows()`, reading the same parsed data that everything else reads. A second parser for agentic calculation would be an architectural violation.
- **§8.2 AUTO block depends on loe.yml being written first:** The AUTO block renderer reads the canonical intermediate; it cannot run before aggregation completes.
- **Mermaid sanitization must be upstream of any write:** Sanitize during ingest (when reading `kanban.md` from the tracked repos) not at render time. Dirty content stored in loe.yml would corrupt every downstream consumer.

---

## MVP Definition

### Launch With (v1 — the milestone as scoped)

- [x] Activity gathering — git signals (branches, PRs, merges) per tracked repo
- [x] Signal-to-status inference using Tier 1 verifiable signals only
- [x] Explicit change list (per-file: old → new, reason) before any write
- [x] Dry-run mode (`--dry-run`)
- [x] Conflict detection before write-back
- [x] Batch write-back confirmation (once) → push → notify → dispatch
- [x] Agentic-overflow capacity model: overflow days → `assignee: Agentic` rows in loe.yml
- [x] §8.2 AUTO block replacement using computed overflow
- [x] Mermaid sanitization on ingest

### Add After Validation (v1.x)

- [ ] Tier 2 ambiguous-signal flagging — generates a flag report alongside the change list, but does NOT auto-update. Add once the Tier 1 auto-update path has been validated as trustworthy.
- [ ] Stale In Progress detection (>14d no commits) — useful but generates noise until the Tier 1 path is calibrated.

### Future Consideration (v2+)

- [ ] Historical drift trending (how often does declared status lag git reality, per project) — useful for process improvement but requires run history.
- [ ] Per-sprint agentic capacity report showing which specific tasks flowed to Agentic — adds detail but the LOE row already carries this information.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Explicit change list | HIGH | LOW | P1 |
| Dry-run mode | HIGH | LOW | P1 |
| Tier 1 signal inference (merged PR, closed branch → Done/In Progress) | HIGH | MEDIUM | P1 |
| Batch write-back with conflict detection | HIGH | MEDIUM | P1 |
| Agentic-overflow capacity model (overflow → Agentic rows) | HIGH | HIGH | P1 |
| §8.2 AUTO block replacement | MEDIUM | MEDIUM | P1 |
| Mermaid sanitization | MEDIUM | LOW | P1 |
| Tier 2 ambiguous-signal flagging | MEDIUM | MEDIUM | P2 |
| Stale In Progress detection | LOW | LOW | P2 |
| Historical drift trending | LOW | HIGH | P3 |

**Priority key:**
- P1: Required for this milestone
- P2: Add after v1 validation
- P3: Defer to a later milestone

---

## Sources

- [Your Kanban board is lying to you (and Git knows it) — DEV Community](https://dev.to/mdenda/your-kanban-board-is-lying-to-you-and-git-knows-it-1hof) — Signal reliability taxonomy, "verifiable state" test
- [GitHub Integration — Linear](https://linear.app/integrations/github) — Industry-standard PR-to-status automation model (branch create → In Progress, PR open → In Review, merge → Done)
- [Agentic AI Anti-Patterns — DigitalApplied](https://www.digitalapplied.com/blog/agentic-ai-anti-patterns-10-ways-teams-botch-deployment-2026) — Silent failure, no observability/audit trail patterns
- [Engineering Capacity Planning Explained — Milestone](https://mstone.ai/blog/engineering-capacity-planning-explained/) — Units, utilization targets (70-80%), over-capacity presentation patterns
- [How to Do Sprint Planning When Half Your Team Are AI Agents — Scrum.org](https://www.scrum.org/resources/blog/how-do-sprint-planning-when-half-your-team-are-ai-agents) — Human review bottleneck as the real agentic capacity constraint
- [Special characters break parsing — mermaid-js/mermaid #54](https://github.com/mermaid-js/mermaid/issues/54) — Mermaid special character fragility, confirmed upstream issue
- [Resource Overallocation — Project Plan 365](https://www.projectplan365.com/articles/resource-overallocation/) — Color-coded over-capacity visualization (blue = ok, red = overallocated) as industry standard
- [Team Capacity Planning Calculator — FullScale](https://fullscale.io/blog/team-capacity-planning/) — Effort days as unit, 70-80% utilization as honest target

---

*Feature research for: activity-driven agentic-capacity migration dashboard skill*
*Researched: 2026-06-04*
