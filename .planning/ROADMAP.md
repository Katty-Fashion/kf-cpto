# Roadmap: kf-cpto — Activity-Driven Migration Dashboard

## Overview

Five phases build the local Claude skill that turns actual repo activity into an accurate, deployed dashboard. Phases execute in strict dependency order: read-only repo access comes first (no write risk), then activity mining and reconciliation are validated as a dry-run before any write code is written, then write-back closes the loop, then the agentic capacity model flows through the working pipeline, and finally hardening adds belt-and-suspenders validation. The existing `notify → dispatch → aggregate.yml → Pages → Sheets` pipeline is never modified.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Repo Access Foundation** - Read-only repo enumeration, symlink convention, and pre-flight git fetch; no writes, CI unaffected (completed 2026-06-04)
- [x] **Phase 2: Activity Mining + Reconciliation** - Git signal mining, three-tier taxonomy, dry-run change list; validated read-only before any write code exists (completed 2026-06-04)
- [ ] **Phase 3: Write-Back + Diagram Sanitization** - Closes the write-back loop; batch-confirm, push, conflict detection, Mermaid sanitization scoped to task table
- [ ] **Phase 4: Agentic Capacity Model** - FE/BE overflow to synthetic Agentic assignee; ceiling, LOE row, §8.2 replacement
- [ ] **Phase 5: Hardening** - End-to-end validation, aggregator-side second-fence sanitization, integration verification

## Phase Details

### Phase 1: Repo Access Foundation
**Goal**: The skill can enumerate all tracked repos, verify their layout, fetch remote state, and read kanban.md — with no writes and zero CI impact
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: REPO-01, REPO-02, REPO-03
**Success Criteria** (what must be TRUE):
  1. Running `repo_enum.py` on a machine with at least one sibling checkout prints a confirmed list of `(name, local_path, remote_url)` tuples and skips any symlink whose target is missing or lacks `kanban.md` + `notify-kf-cpto.yml`
  2. Each enumerated repo's kanban.md is parsed successfully using `scripts/utils.py` parsers (no second parser introduced); task counts match what `aggregator.py` would produce on the same file
  3. After the skill runs, `git status` in the kf-cpto repo is clean, `repos/` is untouched, and `repos-local/` does not appear in a `git add -A` dry-run (gitignore confirmed)
  4. `git fetch origin` is verifiably executed per tracked repo before any read, and the skill logs whether each repo was already up-to-date or received new commits
**Plans**: 3 plans
- [x] 01-01-PLAN.md — Fix .gitignore (un-blanket .claude/, ignore repos-local/) + scaffold SKILL.md
- [x] 01-02-PLAN.md — bootstrap.py: clone + seed the 6 tracked repos into repos-local/
- [x] 01-03-PLAN.md — repo_enum.py: enumerate → fetch → parse-parity → assert-clean

**Open questions to resolve during planning:**
- Symlink topology: confirm all tracked repos live under the standard `~/Dev/` sibling layout; document any exceptions before implementation

---

### Phase 2: Activity Mining + Reconciliation
**Goal**: The skill produces a human-readable change list (old status → new status, triggering signal) for every proposed reconciliation — dry-run only, no file writes anywhere
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: RECON-01, RECON-02, RECON-03, RECON-04, RECON-05, RECON-06, RECON-07, RECON-08
**Success Criteria** (what must be TRUE):
  1. Running the skill in `--dry-run` on a tracked repo with a merged PR carrying a task reference prints a change list showing the task flipping to Done with the PR as the stated signal, and writes nothing to any file
  2. A task in Todo status with an active remote branch appears in the change list as advancing to In Progress (Tier 2 signal); a task with only commit-message keywords does not appear (Tier 3 correctly ignored)
  3. A merged PR that was subsequently reverted — where the merge commit is no longer reachable from the default-branch tip — does not produce a Done entry in the change list
  4. Every proposed status value in the dry-run output maps to a value in `utils.VALID_STATUSES`; no `Unknown status` warnings appear in the aggregator when the same file is parsed
  5. Running `--dry-run` twice in sequence on an already-reconciled repo produces an empty change list (idempotency confirmed before any write code is built)
**Plans**: 2 plans
- [x] 02-01-PLAN.md — reconcile.py end-to-end dry-run skeleton: Proposal/token-matching/STATUS_RANK + Tier-2 branch detection (RECON-02/04/05/06/07)
- [x] 02-02-PLAN.md — Tier-1 layer: merged-PR + linked-issue mining, reachability gate, conflict resolution; SKILL.md update (RECON-01/03/08)

**Open questions to resolve during planning:**
- pyyaml vs ruamel.yaml: evaluate actual kanban.md templates for hand-authored frontmatter comments before Phase 3 implementation; decision must be locked before writeback is built

---

### Phase 3: Write-Back + Diagram Sanitization
**Goal**: The skill writes corrected kanban.md to each tracked repo, sanitizes Mermaid-breaking characters in task table rows, and pushes — triggering CI to re-render and deploy the corrected dashboard
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: WB-01, WB-02, WB-03, WB-04, WB-05, DIAG-01, DIAG-02, DIAG-03
**Success Criteria** (what must be TRUE):
  1. A full skill invocation (not dry-run) on at least one tracked repo with pending changes commits a corrected kanban.md, pushes to the correct default branch, and the existing `notify-kf-cpto.yml` fires a `repository_dispatch` that triggers `aggregate.yml` — resulting in an updated dashboard on GitHub Pages within the normal CI window
  2. The skill presents a single batch-confirm summary covering all repos before any push; no per-repo confirmation prompt appears at any point during the run
  3. When a tracked repo's local checkout is behind `origin/<default-branch>` (simulated by making a competing push), the skill aborts that repo's write, logs it as `[CONFLICT]`, and continues with the remaining repos — the already-pushed repos' dispatch fires normally
  4. A recovery manifest file is written for each run recording which repos succeeded and which failed, and re-running the skill on a repo that already has the correct kanban.md produces zero git diff (idempotency)
  5. Task table rows containing emojis or Mermaid-breaking punctuation are sanitized before write; Romanian diacritics (ă/â/î/ș/ț) are preserved verbatim; AUTO-block marker lines are unchanged in the git diff; running `validate_auto_blocks.py` locally after the write produces exit 0
**Plans**: 3 plans
- [x] 03-01-PLAN.md — sanitize.py + frontmatter round-trip + status-cell builder + idempotency (pure, git-free); requirements.txt/.gitignore groundwork (WB-01, DIAG-01/02/03)
- [x] 03-02-PLAN.md — writeback.py git layer: conflict detection + token-masked push + _write_repo against a throwaway bare remote (WB-03, WB-04)
- [ ] 03-03-PLAN.md — batch-confirm + recovery manifest + run()/main() orchestration over reconcile.run() + SKILL.md (WB-02, WB-05)

**Note (SC-1):** The live push → CI → Pages deploy is a human-validated UAT item. The autonomous build tests the full write path against a local throwaway bare git remote; it never pushes to live katty-fashion org repos.

---

### Phase 4: Agentic Capacity Model
**Goal**: The skill computes FE/BE capacity overflow and assigns excess tasks to a synthetic Agentic assignee, which flows through the existing pipeline as a first-class LOE row — replacing the §8.2 "add 0.5 FTE" recommendation
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: CAP-01, CAP-02, CAP-03, CAP-04, CAP-05, CAP-06, CAP-07
**Success Criteria** (what must be TRUE):
  1. After a skill run, the LOE report on GitHub Pages contains a distinct Agentic assignee row showing overflow effort in days; when there is no overflow the row is absent; the Google Sheet LOE tab reflects the same Agentic row as a downstream export
  2. A `FE+BE` task with 3d effort contributes 1.5d to FE capacity and 1.5d to BE capacity (50/50 split); the sum of per-discipline totals equals the sum of all task effort-days (no double-counting); this is verifiable by inspecting the skill's logged capacity breakdown
  3. The capacity model uses raw 40h/week per FTE with no additional buffer; a `ESTIMATES_INCLUDE_20PCT_BUFFER = True` constant and `AGENTIC_ASSIGNEE = "Agentic"` constant exist in `scripts/utils.py`
  4. When overflow exceeds the explicit agentic ceiling constant, the skill's output contains a visible `[WARN: agentic capacity exceeded — Xd unresolved]` entry; the ceiling value is a named constant (not a magic number)
  5. The migration-gantt §8.2 section no longer recommends "add 0.5 FTE backend" — it shows the agentic-deferral view with computed overflow hours
**Plans**: TBD

**Open questions to resolve during planning:**
- Agentic ceiling value: requires a CPTO decision; must be established as a named constant before implementation begins
- capacity.yml intermediate vs. parse migration-gantt.md directly: decide which approach is used for the capacity model's input; resolve during phase planning

---

### Phase 5: Hardening
**Goal**: The full skill pipeline is validated end-to-end across all tracked repos, with aggregator-side sanitization as a second fence for human-direct-push paths that bypass the skill
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: (end-to-end integration validation — all v1 requirements covered in Phases 1-4)
**Success Criteria** (what must be TRUE):
  1. Running the full skill pipeline against all currently-tracked repos produces a clean run: no `[CONFLICT]` repos (or all conflicts are expected and documented), no `[WARN: agentic capacity exceeded]` without a corresponding CPTO decision, and `aggregate.yml` completes successfully with all diagrams rendering in the deployed Pages site
  2. The aggregator-side Mermaid sanitization (second fence) is in place: any kanban.md pushed directly by a human containing an emoji in a task row does not break the gantt or kanban diagram on the next CI run
  3. The end-to-end integration invariants all hold: `sheets_sync.py` exits 0, `validate_auto_blocks.py` passes in CI, the one-parser contract is verified (grep for kanban parsing outside `scripts/utils.py` returns zero results in the skill's code), and `repos-local/` does not appear in any committed file
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Repo Access Foundation | 4/4 | Complete   | 2026-06-04 |
| 2. Activity Mining + Reconciliation | 2/2 | Complete   | 2026-06-04 |
| 3. Write-Back + Diagram Sanitization | 2/3 | In Progress|  |
| 4. Agentic Capacity Model | 0/TBD | Not started | - |
| 5. Hardening | 0/TBD | Not started | - |
