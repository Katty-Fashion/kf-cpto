# Requirements: kf-cpto — Activity-Driven Migration Dashboard

**Defined:** 2026-06-04
**Core Value:** One command turns actual repo activity into an accurate, deployed dashboard and LOE Sheet — with work beyond a person's capacity flowing to a synthetic Agentic assignee instead of a hire recommendation.

## v1 Requirements

Requirements for this milestone. Each maps to a roadmap phase.

### Repo Access (REPO)

- [x] **REPO-01**: Skill enumerates tracked repos by detecting both `kanban.md` and `notify-kf-cpto.yml` in local sibling checkouts (symlinked under a gitignored `repos-local/`), with no static project list
- [x] **REPO-02**: Skill runs `git fetch` on each tracked repo before reading, so activity reflects remote state (no stale-clone reads)
- [x] **REPO-03**: Skill reuses `scripts/utils.py` parsers and status constants instead of introducing a second `kanban.md` parser

### Activity & Reconciliation (RECON)

- [x] **RECON-01**: Skill detects completed tasks from Tier-1 git signals — merged PRs carrying a task reference and linked issue-closes
- [x] **RECON-02**: Skill advances Todo to In Progress from Tier-2 branch existence
- [x] **RECON-03**: Skill auto-updates declared kanban status to match Tier-1 verified reality
- [x] **RECON-04**: Skill produces a reviewable change list (task, old to new status, triggering signal) for every change it makes
- [x] **RECON-05**: Skill supports a dry-run that previews all proposed changes without writing
- [x] **RECON-06**: Skill ignores Tier-3 noise (commit-message keywords, file paths touched) — these never change status
- [x] **RECON-07**: Skill normalizes every status string through the canonical status enum before any write (no `Unknown status` drops)
- [x] **RECON-08**: Skill ignores reverted/un-reachable merges (a merge no longer reachable from the default-branch tip does not signal Done)

### Write-Back (WB)

- [x] **WB-01**: Skill writes corrected `kanban.md` back to each tracked repo, preserving all non-task content (frontmatter comments, prose)
- [ ] **WB-02**: Skill batch-confirms all writes once before committing (never per-repo prompting)
- [x] **WB-03**: Skill aborts a repo's write on non-fast-forward / divergence rather than clobbering concurrent human edits
- [x] **WB-04**: Skill commits and pushes to each repo's correct default branch, triggering the existing notify to dispatch pipeline
- [ ] **WB-05**: Skill records a recovery manifest of what was written, so a partial-batch failure is recoverable

### Agentic Capacity Model (CAP)

- [ ] **CAP-01**: Aggregator computes per-discipline (FE / BE) demand vs. capacity, denominated in days
- [ ] **CAP-02**: Over-capacity overflow is assigned to a synthetic `Agentic` assignee while the human stays pinned at 100% capacity
- [ ] **CAP-03**: `FE+BE` shared tasks split effort 50/50 across lanes (no double-counting)
- [ ] **CAP-04**: Capacity model respects the existing 20% buffer baked into estimates (no double-buffering)
- [ ] **CAP-05**: Agentic overflow appears as its own row / slice in the LOE outputs (loe.yml, LOE report, Sheet)
- [ ] **CAP-06**: An explicit agentic ceiling exists; breaching it surfaces a `[WARN]` / `[BLOCKER]` instead of silently absorbing unbounded overflow
- [ ] **CAP-07**: The migration-gantt §8.2 "add 0.5 FTE backend" recommendation is replaced by the agentic-deferral view

### Diagram Robustness (DIAG)

- [x] **DIAG-01**: Mermaid-breaking characters (emojis and `: ( ) " # ; { } |`) are sanitized from task content on ingest, before write
- [x] **DIAG-02**: Sanitization is scoped to the task table only — AUTO-block markers and Romanian diacritics (ă/â/î/ș/ț) are preserved
- [x] **DIAG-03**: Dashboard diagrams (gantt, kanban, pie, dependency graph) render without breaking after a skill run

## v2 Requirements

Deferred to a future milestone. Tracked but not in this roadmap.

### Reconciliation

- **RECON-V2-01**: Tier-2 ambiguous-signal flagging — surface discrepancies that can't be auto-resolved for human decision (not just auto-update)

### Capacity

- **CAP-V2-01**: Render capacity as an `AUTO:capacity` block on `migration-gantt.md` (vs. static prose), driven by a `docs/_data/capacity.yml`

### Robustness

- **DIAG-V2-01**: Aggregator-side second-fence sanitization at render time (belt-and-suspenders, in addition to skill-side ingest sanitization)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Net-new dashboard pages | Milestone refines existing views (kanban, gantt, calendar, LOE); no new surface area |
| Replacing the deterministic CI renderer | Skill is the smart input layer; `aggregator.py` + `aggregate.yml` stay the renderer/deployer |
| Two-way / real-time Google Sheets sync | Sheets stays a downstream export; Pages stays canonical |
| Changing the `sheets_sync.py` exit-0 invariant | Pages must never be blocked by a Sheets failure |
| Re-parsing `kanban.md` in `sheets_sync.py` | Preserves "one parser, one canonical intermediate" |
| Inferring FE/BE from branch names or commit metadata | Discipline routing uses the kanban Owner column exclusively (already encoded) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REPO-01 | Phase 1 | Complete |
| REPO-02 | Phase 1 | Complete |
| REPO-03 | Phase 1 | Complete |
| RECON-01 | Phase 2 | Complete |
| RECON-02 | Phase 2 | Complete |
| RECON-03 | Phase 2 | Complete |
| RECON-04 | Phase 2 | Complete |
| RECON-05 | Phase 2 | Complete |
| RECON-06 | Phase 2 | Complete |
| RECON-07 | Phase 2 | Complete |
| RECON-08 | Phase 2 | Complete |
| WB-01 | Phase 3 | Complete |
| WB-02 | Phase 3 | Pending |
| WB-03 | Phase 3 | Complete |
| WB-04 | Phase 3 | Complete |
| WB-05 | Phase 3 | Pending |
| DIAG-01 | Phase 3 | Complete |
| DIAG-02 | Phase 3 | Complete |
| DIAG-03 | Phase 3 | Complete |
| CAP-01 | Phase 4 | Pending |
| CAP-02 | Phase 4 | Pending |
| CAP-03 | Phase 4 | Pending |
| CAP-04 | Phase 4 | Pending |
| CAP-05 | Phase 4 | Pending |
| CAP-06 | Phase 4 | Pending |
| CAP-07 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-06-04*
*Last updated: 2026-06-04 after roadmap creation*
