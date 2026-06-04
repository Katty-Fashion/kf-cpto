# Project Research Summary

**Project:** kf-cpto — Activity-Driven Agentic-Capacity Migration Dashboard Skill
**Domain:** Local Claude skill + Python/Jekyll CI pipeline integration
**Researched:** 2026-06-04
**Confidence:** HIGH

## Executive Summary

This milestone adds a local Claude Code skill on top of an existing deterministic Python + Jekyll CI pipeline. The skill is the *smart input layer*: it reads real git activity from tracked sibling repo checkouts, reconciles declared kanban status against verifiable git signals (merged PRs, active branches, closed issues), writes corrected `kanban.md` files back to those repos, and models over-capacity work as a synthetic Agentic assignee — replacing the current "add 0.5 FTE" recommendation in migration-gantt §8.2. The existing `notify → dispatch → aggregate.yml → Pages → Sheets` pipeline is the deterministic renderer and stays entirely unchanged. The skill boundary ends at `git push`; everything downstream is CI's concern.

Four research threads reached consensus on the implementation approach. The stack is zero new dependencies: Python stdlib (`subprocess`, `re`, `unicodedata`, `pathlib`, `json`, `datetime`, `difflib`) plus the already-installed `pyyaml` and existing `gh` CLI. The skill imports `scripts/utils.py` parse functions to honour the one-parser constraint. The agentic capacity model runs inside the skill's `reconcile.py` and writes `assignee: Agentic` rows directly into `kanban.md`, which the aggregator then passes through as a first-class string value with no special-casing. Reconciliation uses a strict three-tier signal taxonomy: only Tier 1 signals (merged PR with task ref, issue-close) trigger auto-updates; Tier 2 (active branch) advances Todo to In Progress; Tier 3 (commit messages, file paths) is ignored.

The principal risks are all write-back integrity issues: clobbering a concurrent human edit, partial-batch failure leaving repos in a mixed state, and the Mermaid sanitizer either over-stripping Romanian diacritics (ă/â/î/ș/ț) or corrupting AUTO-block markers. All three are addressed by a pre-write `git fetch` + non-fast-forward abort, per-repo recovery manifests, and scoping the sanitizer strictly to the task table section of each file. A mandatory dry-run mode and a single batch-confirm gate are table-stakes safety features — the skill must never write without showing a human-readable change list first.

---

## Key Findings

### Recommended Stack

The stack decision is unambiguous: zero new dependencies. The existing toolchain — Python stdlib, `pyyaml`, and the `gh` CLI — covers every requirement. `subprocess` + `git --format` handles all local activity mining (log, branches, merge detection, dirty-state checks). `gh` CLI handles remote API queries (merged PRs, open branches, repo metadata). `pyyaml` with `allow_unicode=True` roundtrips frontmatter without corrupting Romanian project names. `unicodedata.category()` + `re.sub` provides precise emoji-stripping that leaves Romanian diacritics intact. The Claude Code skill is packaged at `.claude/skills/reconcile-activity/SKILL.md` with `disable-model-invocation: true` and `context: fork` — both flags are required together to prevent auto-triggering on ambient conversation.

**Core technologies:**
- `subprocess` + `git` CLI: local activity mining (commits, branches, merge detection, dirty checks) — no new dep; structured `--format` strings are sufficient; GitPython ruled out due to resource-leak risk
- `gh` CLI (existing, v2.87.3): GitHub API queries for merged PRs and remote branch state — already in PATH, already used by `sheets_sync.py`, handles auth and pagination automatically
- `pyyaml` (existing, `>=6.0`): frontmatter roundtrip with `allow_unicode=True` — already installed; required flag preserves non-ASCII content
- `unicodedata` + `re` (stdlib): Mermaid-safe sanitization — strips emoji by Unicode category (`So`, `Mn`, `Cs`, `Cf`, `Co`) and Mermaid-breaking punctuation without touching Romanian diacritics
- Claude Code skill at `.claude/skills/reconcile-activity/`: `disable-model-invocation: true` + `context: fork`; supporting Python scripts in `scripts/skill/`

**Open question — pyyaml comment preservation:** `pyyaml.dump` drops inline comments from frontmatter. If `kanban.md` frontmatter has hand-authored comments that must survive write-back, `ruamel.yaml` is the alternative. Evaluate before implementing the write-back phase.

### Expected Features

The feature set is fully specified. Every P1 feature is required for the milestone; no P1 items are deferred.

**Must have (table stakes — skill is untrustworthy without these):**
- Explicit human-readable change list before any write (old status → new status, reason per task — not a git diff)
- Dry-run / preview mode (`--dry-run` flag; required for trust-building and safe exploration)
- Batch write-back confirmation — once for all repos, never per-repo; matches the [NO prompting during org scans] project constraint
- Conflict detection — `git fetch` + non-fast-forward check before each repo write; skip and report rather than clobber
- Signal-to-status transparency — every inferred change states which signal triggered it
- No-change idempotency — two runs on an already-reconciled board produce zero diff
- Mermaid sanitization on ingest — scoped to task table rows only, never full file

**Should have (differentiators that define the milestone's value):**
- Agentic-overflow capacity model: overflow days beyond each discipline's 1-FTE ceiling → `assignee: Agentic` rows; denominated in effort-days (Nd), never percentage; 50/50 split for `FE+BE` tasks; explicit agentic ceiling with breach warning; existing 20% buffer in estimates is not double-buffered
- §8.2 AUTO block replacement: "add 0.5 FTE" replaced by computed agentic deferral narrative
- Tier 1 signal reconciliation: merged PR with task ref → Done; active branch for Todo task → In Progress; PR open with task ref → In Review
- Agentic shown as a distinct LOE row/slice (not lumped into FE or BE, absent when overflow is zero)

**Defer (v1.x after validation):**
- Tier 2 ambiguous-signal flagging (branch active for Blocked task, Done with no merged PR)
- Stale In Progress detection (>14d no commits)

**Defer (v2+):**
- Historical drift trending
- Per-sprint agentic capacity report beyond the existing LOE row

**Anti-features — explicitly not built:**
- Silent rewrites with no change list
- Commit-message keyword inference for Done status (Tier 3 noise)
- File-path-touched inference for task scope (Tier 3 noise)
- Agentic capacity as percentage of a hypothetical FTE
- Real-time or continuous reconciliation
- Auto-close tasks with no recent git activity

### Architecture Approach

The skill is a four-module pipeline that runs entirely on the developer's machine and terminates at `git push`. It reads from `repos-local/` (a new gitignored directory of symlinks to sibling checkouts) and writes corrected `kanban.md` back to those checkouts. The agentic capacity model runs inside `reconcile.py` and emits `assignee: Agentic` task rows — the aggregator receives these as ordinary string values and passes them through to `loe.yml` with no special-casing required. Mermaid sanitization happens in `writeback.py` before any file write, scoped strictly to the task table section (never frontmatter, never AUTO-block markers). The `repos/` directory (CI shallow clones) is never touched by the skill.

**Major components:**
1. `repo_enum.py` — resolves `repos-local/` symlinks, verifies each has `kanban.md` + `notify-kf-cpto.yml`, returns `(name, local_path, remote_url)` tuples
2. `activity.py` — per-repo activity mining via `git log`, `git branch -r`, `gh pr list --json`; produces `ActivitySnapshot` per task
3. `reconcile.py` — diffs declared vs. observed state using Tier 1 signals only; runs agentic-overflow capacity model; emits `ReconcileResult` with change list
4. `writeback.py` — sanitizes task table rows, writes `kanban.md`, presents batch summary, awaits single confirm, pushes all repos
5. `skill_main.py` — orchestrator; wires the four modules; hosts the dry-run / confirm gate

**Existing pipeline targeted edits (not rewrites):**
- `scripts/utils.py`: add `AGENTIC_ASSIGNEE = "Agentic"` constant and `MERMAID_SAFE_RE` pattern
- `aggregator.build_loe_rows()`: confirm `assignee` field passes through as string; add `Agentic` to any allowlist if one exists
- `docs/migration-gantt.md` §8.2: replace "add 0.5 FTE" prose with agentic deferral narrative
- `.gitignore`: add `repos-local/`

### Critical Pitfalls

1. **Write-back clobbers a concurrent human edit** — before writing each repo, run `git fetch origin` then verify local HEAD is an ancestor of `origin/<branch>`; abort and log as `[CONFLICT]` if not; never use `--force`

2. **Mermaid sanitizer strips Romanian diacritics (ă/â/î/ș/ț)** — strip by Unicode category (`So`, `Mn`, etc.) and specific Mermaid-breaking punctuation, never by non-ASCII range; Romanian diacritics are category `Ll`/`Lu` (letters) and must pass through untouched; validate with a fixture test before shipping

3. **Sanitizer scope bleeds into AUTO-block markers** — apply sanitization only to the task table rows; never run over frontmatter or AUTO-block interior; run `validate_auto_blocks.py` locally before any file write

4. **FE+BE tasks double-counted in capacity model** — `FE+BE` tasks must split effort 50/50 by default (1.5d FE + 1.5d BE for a 3d task); verify by asserting sum of per-discipline hours equals sum of all task effort-days

5. **Existing 20% buffer in estimates double-buffered** — migration-gantt estimates already include a 20% buffer; do not apply another buffer in the model; use raw 40h/week per FTE; document with `ESTIMATES_INCLUDE_20PCT_BUFFER = True` constant

6. **Agentic ceiling absent, overflow grows unboundedly** — introduce an explicit agentic ceiling constant; when exceeded, emit `[WARN: agentic capacity exceeded — Xd unresolved]`; ceiling value is an open question to resolve during planning

7. **Skill re-parses kanban.md with a local parser** — always import `scripts.utils.parse_kanban_tasks` and `parse_kanban_frontmatter`; set `sys.path` to include the project root; a second parser diverges on edge cases and violates the one-parser constraint

---

## Implications for Roadmap

The five-phase build order is the consensus recommendation from both the architecture and features researchers. Each phase has a clear gate; no phase should begin until its predecessor's gate is passed.

### Phase 1: Repo Access Foundation

**Rationale:** Everything else depends on reliable repo enumeration, symlink resolution, and pre-flight git fetches. No writes yet — pure read infrastructure. Proving gitignore hygiene and CI non-interference before any write risk is introduced.

**Delivers:** Confirmed `(repo, local_path, remote_url)` list; `repos-local/` symlink convention; `repo_enum.py` that skips missing symlinks gracefully; verified `git fetch` + log read per tracked repo.

**Addresses:** One-parser constraint (import `utils.py` from day one); stale-clone risk (pre-flight `git fetch`); wrong-branch risk (verify HEAD matches default branch at startup).

**Avoids pitfalls:** Stale local clone produces wrong signals (P6); accidental push to wrong branch (P3); skill re-parses kanban.md locally (P14).

**Research flag:** Standard patterns — no additional research needed.

---

### Phase 2: Activity Mining + Reconciliation (read-only)

**Rationale:** Build the inference engine before the write-back loop so signal-to-noise ratio can be validated by a human reviewer without any write risk. The `--dry-run` mode is the deliverable of this phase. Human gate: operator reviews the change list and agrees signal quality is acceptable before any write code is built.

**Delivers:** `activity.py` (git signals per repo — commits, branches, PRs via Tier 1 taxonomy), `reconcile.py` (signal inference → change list), dry-run output showing proposed status changes with reasons per task.

**Addresses:** Tier 1 signal taxonomy; explicit change list (old status → new status, signal); idempotency; Done inferred from reverted PR (use merge-base reachability check, not merge event alone); FE/BE owner from kanban task table only, never from branch names.

**Avoids pitfalls:** Commit-message keyword inference for Done (anti-feature); non-deterministic LLM output leaking into status (P13 — normalize to `utils.VALID_STATUSES` before any write).

**Research flag:** Standard patterns — signal tier taxonomy fully specified; no additional research needed.

---

### Phase 3: Write-Back + Sanitization

**Rationale:** Closes the write-back loop after the dry-run gate proves signal quality. Adds actual file write, Mermaid sanitization scoped to task table only, batch-confirm gate, and `git push`. End gate: full skill invocation produces a push that triggers CI and deploys corrected dashboards with at least one updated task.

**Delivers:** `writeback.py` (sanitize → write kanban.md → batch confirm → push); `skill_main.py` orchestrator; conflict detection (pre-push fetch + non-fast-forward abort); recovery manifest per run; `[skip ci]` on repo commits + single `gh workflow run aggregate.yml`.

**Addresses:** Conflict detection; batch-confirm once; Mermaid sanitization scoped to task table; Romanian diacritics preservation; AUTO-block marker protection; partial-batch failure recovery.

**Avoids pitfalls:** Write-back clobbers human edit (P1); partial-batch failure (P2); sanitizer strips Romanian diacritics (P11); sanitizer breaks AUTO-block idempotency (P12); Sheets exit-0 invariant broken by skill code (P15).

**Open question — skip-ci dispatch strategy:** `[skip ci]` on per-repo commits + explicit `gh workflow run aggregate.yml` vs. natural per-repo dispatch. Resolve before implementation.

**Research flag:** Standard patterns for git write-back; skip-ci dispatch strategy needs explicit decision.

---

### Phase 4: Agentic Capacity Model (full implementation)

**Rationale:** Write-back loop must already work (Phase 3) before capacity model output can be validated end-to-end through CI. Highest-complexity component; hardest to debug without a working pipeline.

**Delivers:** Full FE/BE capacity model in `reconcile.py` — parses migration-gantt.md FE/BE task breakdown, accumulates effort per discipline against 1-FTE ceiling (40h/week raw, no additional buffer), assigns overflow tasks to `assignee: Agentic`; `AGENTIC_ASSIGNEE` constant in `utils.py`; `ESTIMATES_INCLUDE_20PCT_BUFFER = True` constant; explicit agentic ceiling with `[WARN]` on breach; §8.2 replacement (agentic deferral narrative); Agentic as distinct LOE row/slice.

**Addresses:** FE+BE task 50/50 split rule; no double-buffering; agentic ceiling + breach warning; Agentic LOE row absent when overflow is zero; §8.2 AUTO:capacity block (open question: dynamic AUTO block vs. static replacement prose).

**Avoids pitfalls:** Agentic number grows unboundedly (P8); double-counting FE+BE tasks (P9); 20% buffer double-applied (P10); agentic capacity model placed in aggregator.py (Architecture Anti-Pattern 1).

**Open questions:**
- Agentic ceiling value: requires a CPTO decision; must be a named constant
- `capacity.yml` intermediate vs. parse `migration-gantt.md` directly

**Research flag:** Needs one phase-planning session — ceiling value and `FE+BE` split rule documentation.

---

### Phase 5: Hardening + Dashboard Polish

**Rationale:** Belt-and-suspenders hardening after the full skill is validated end-to-end. Adds aggregator-side sanitization as a second fence for human-direct-push paths that bypass the skill.

**Delivers:** Aggregator-side Mermaid sanitization (secondary fence); Tier 2 ambiguous-signal flagging (flag report alongside change list, no auto-update); improved batch-confirm summary format; diagram robustness validation across all tracked repos; optional `AUTO:capacity` block if capacity numbers should be dynamically computed from `loe.yml`.

**Avoids pitfalls:** Mermaid sanitization only in aggregator (Architecture Anti-Pattern 5 — skill-side is primary; aggregator-side is belt-and-suspenders only).

**Research flag:** Standard patterns — no additional research needed.

---

### Phase Ordering Rationale

- Phase 1 before Phase 2: activity mining requires reliable repo enumeration and pre-flight fetches; signal quality cannot be validated without knowing which repos are being read
- Phase 2 before Phase 3: human validation of the dry-run change list must happen before any write code is built — prevents building an automated rewriter on a broken signal base
- Phase 3 before Phase 4: the capacity model's output only has meaning when it flows through a working write-back loop and CI render; debugging the model in isolation from the pipeline is misleading
- Phase 4 before Phase 5: hardening is only meaningful once the full skill is validated; premature hardening wastes effort

### Research Flags

**Needs a design decision before implementation:**
- Phase 3: skip-ci dispatch strategy (per-repo `[skip ci]` + explicit `gh workflow run` vs. natural per-repo dispatch)
- Phase 4: agentic ceiling value (named constant, resolve with CPTO)
- Phase 4: `capacity.yml` intermediate vs. parse `migration-gantt.md` directly

**Needs one phase-planning session:**
- Phase 4: capacity model design review (ceiling, `FE+BE` split rule, §8.2 AUTO block vs. static prose)

**Standard patterns (skip research-phase):**
- Phase 1: symlink resolution, gitignore hygiene, git CLI operations
- Phase 2: git signal mining, status normalization — fully specified in signal tier taxonomy
- Phase 3: write-back loop, Mermaid sanitization — fully specified in ARCHITECTURE.md and PITFALLS.md
- Phase 5: aggregator-side sanitization, Tier 2 flagging — incremental additions to established patterns

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All decisions verified against live codebase: pyyaml roundtrip confirmed, gh CLI JSON output confirmed, unicodedata.category() emoji detection confirmed, subprocess git operations confirmed. Zero new dependencies — no install risk. |
| Features | HIGH (core), MEDIUM (agentic model) | Signal tier taxonomy and table-stakes features are unambiguous. Agentic capacity model is MEDIUM because ceiling value and FE+BE split rule are design decisions not yet confirmed with the CPTO. |
| Architecture | HIGH | Based on direct codebase analysis, not speculation. All integration points (aggregator.build_loe_rows, auto_blocks, validate_auto_blocks, sheets_sync exit-0) verified from source. |
| Pitfalls | HIGH | All 15 pitfalls derived from the mapped codebase and specific constraints in PROJECT.md. Recovery strategies specified. "Looks Done But Isn't" checklist ready. |

**Overall confidence:** HIGH

### Gaps to Address

These open questions must be resolved as explicit decisions before the affected phase begins — they do not block research, but they do block implementation.

- **pyyaml comment preservation vs. ruamel.yaml:** If frontmatter has hand-authored comments that must survive write-back, ruamel.yaml is the correct tool. Evaluate actual kanban.md templates before Phase 3 implementation.
- **Agentic ceiling value:** Requires a CPTO decision, not a research decision. Must be a named constant in the code.
- **capacity.yml vs. parse migration-gantt directly:** Introducing `capacity.yml` adds a parseable intermediate at the cost of a new maintenance surface. Parsing migration-gantt.md directly keeps one source of truth but requires a more complex parser. Resolve during Phase 4 planning.
- **Symlink topology:** Architecture assumes `repos-local/<name> -> ../../<name>/` relative to `kf-cpto/` (standard `~/Dev/` layout). Confirm whether any tracked repos live outside this standard sibling layout before Phase 1 implementation.
- **skip-ci dispatch strategy:** `[skip ci]` on per-repo commits + explicit `gh workflow run aggregate.yml` (one pipeline run for N repos) vs. natural per-repo dispatch (N pipeline runs). Confirm preference before Phase 3 implementation.

---

## Sources

### Primary (HIGH confidence)

- `.planning/codebase/ARCHITECTURE.md` — existing pipeline architecture; integration points; anti-patterns documented from source
- `.planning/codebase/CONCERNS.md` — tech debt, fragile areas, Mermaid securityLevel concern, PAT credential handling
- `.planning/PROJECT.md` — scope, constraints, key decisions, team size, migration-gantt §8.2 context
- `scripts/aggregator.py:489-598` — `build_loe_rows()` and `write_loe_yaml()` confirmed from source; one-parser contract
- `scripts/utils.py` — `VALID_STATUSES`, `parse_kanban_tasks`, `parse_kanban_frontmatter` — canonical parser confirmed
- `.github/workflows/aggregate.yml` — pipeline order (Pages before Sheets), dispatch trigger, `repos/` runtime-only confirmed
- `scripts/auto_blocks.py:169` — AUTO-block idempotence confirmed from source
- `scripts/sheets_sync.py:397` — exit-0 invariant confirmed from source
- https://code.claude.com/docs/en/skills — Claude Code skills spec: `disable-model-invocation`, `context: fork`, `allowed-tools`, dynamic context injection. Fetched 2026-06-04.

### Secondary (MEDIUM confidence)

- https://github.com/mermaid-js/mermaid/issues/1981 — `#` and `;` break Mermaid gantt parser confirmed; exact v11 behavior against live instance unverified
- https://linear.app/integrations/github — industry-standard PR-to-status automation model
- https://mstone.ai/blog/engineering-capacity-planning-explained/ — units (effort days), utilization targets, over-capacity presentation patterns
- https://www.scrum.org/resources/blog/how-do-sprint-planning-when-half-your-team-are-ai-agents — human review bottleneck as real agentic capacity constraint
- https://www.digitalapplied.com/blog/agentic-ai-anti-patterns-10-ways-teams-botch-deployment-2026 — silent failure, no audit trail anti-patterns

### Tertiary (LOW confidence)

- https://gitpython.readthedocs.io/en/stable/tutorial.html — resource-leak risk documented; used to rule GitPython out; not validated against skill's specific use case at scale

---

*Research completed: 2026-06-04*
*Ready for roadmap: yes*
