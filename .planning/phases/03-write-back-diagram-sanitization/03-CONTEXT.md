# Phase 3: Write-Back + Diagram Sanitization - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

The skill writes corrected `kanban.md` back to each tracked repo, sanitizes Mermaid-breaking characters in task-table rows, and pushes — triggering the existing `notify-kf-cpto.yml` → `kanban-updated` dispatch → `aggregate.yml` loop that re-renders and deploys the dashboard. This phase consumes Phase 2's `reconcile.run()` `Proposal` list and turns it into real, idempotent, conflict-aware writes guarded by a single batch confirmation and a recovery manifest. It does NOT add capacity modelling (Phase 4) or aggregator-side second-fence sanitization (deferred to v2 / Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Content Preservation Strategy (resolves the locked pyyaml-vs-ruamel question)
- **USE ruamel.yaml** (user override of the in-place-only recommendation). Add `ruamel.yaml>=0.17` as a skill-local dependency in `requirements.txt`. CI self-containment is preserved because CI never imports the skill — `aggregate.yml` installs only its own four packages and does not run write-back; ruamel is for the local skill venv only.
- Write-back reconstructs `kanban.md` by **round-tripping the YAML frontmatter through ruamel.yaml** (round-trip mode preserves hand-authored `#` inline comments, key order, and quoting — `WB-01`), then rewriting the markdown body.
- The **task-table Status changes live in the markdown body, not the frontmatter** (reconcile.py only changes task `status`). Body edits are **targeted string replacement of the Status cell** for each `Proposal`'s matched row — matched by task name. The table header, `| :--- |` separator, column count (4-col vs 6-col, auto-detected), HTML comments, and prose are left byte-for-byte intact.
- **AUTO-block markers do not appear in kanban.md** (they live only in `docs/` Jekyll pages) — so kanban write-back cannot disturb them. The `validate_auto_blocks.py` exit-0 check in SC-5 is a *post-write sanity assertion* that the docs pipeline is still consistent, not a kanban concern.
- Phase 3 **re-reads `repos-local/{repo}/kanban.md` fresh at write time** and applies changes there (the `Proposal` dataclass carries no raw content; `repo` field routes to the local checkout).

### Mermaid Sanitization Rules (DIAG-01/02/03)
- Sanitize **emojis + the character set `: ( ) " # ; { } |`** (per PROJECT.md) — applied to **task-table cell text only**, never frontmatter, prose, or HTML comments (DIAG-02 scope).
- **Readable substitution** (not blunt stripping): `:` → ` -`, `"` → `'`, `|` → `/`, `;` → `,`, `( )` and `{ }` → dropped, `#` → dropped; emoji codepoints stripped. Goal: legible task titles that no longer break Mermaid or the markdown pipe-table.
- **Romanian diacritics ă/â/î/ș/ț are preserved verbatim** via an explicit allowlist — only the break-set + emoji ranges are touched (DIAG-02).
- Sanitization runs **skill-side on the write path only** this phase (DIAG-01). Aggregator-side second-fence sanitization (DIAG-V2-01) is deferred to v2 / Phase 5 hardening.

### Push, Auth & CI-Dispatch
- **Git auth: reconfigure each repo's `origin` to HTTPS + `KF_PAT` at push time**, mirroring the `aggregate.yml` pattern (`https://<KF_PAT>@github.com/<org>/<repo>.git`). Portable; does not assume bootstrap's SSH key is present.
- **Dispatch strategy (resolves locked question): natural per-repo dispatch.** Each repo's push to its default branch fires `notify-kf-cpto.yml` → `repository_dispatch{event_type: kanban-updated}` → `aggregate.yml`. Do **NOT** add `[skip ci]` to kanban commits — the dispatch is the whole point. N pushes may produce N aggregate runs; that is acceptable because aggregate re-clones all repos, so any run reflects the full corrected set.
- **NO live push during this autonomous build.** Build and unit-test the write path against a **local fixture / throwaway/bare git remote**; the read-only invariant for kf-cpto still holds. **SC-1 (live push → CI → Pages deploy) is a human-validated UAT item** — autonomous mode must not fire live pushes to real `katty-fashion` org repos unprompted. The verifier should classify SC-1 as `human_needed`.
- Commit message: `chore(kanban): reconcile task statuses from repo activity` (no `[skip ci]`). Push to each repo's **detected default branch** (main/master per repo — never hardcoded; carried from Phase 1).

### Batch-Confirm, Conflict Handling & Recovery Manifest
- **Single batch confirmation** before any push: print one summary table (all repos × proposed changes), confirm once, then push all. **Zero per-repo prompts** (matches the user's org-scan preference — confirm destructive ops once as a batch).
- **Conflict detection (WB-03):** before writing a repo, `git fetch` and detect whether the local checkout is behind/diverged from `origin/<default-branch>` (non-fast-forward). If so, **abort that repo's write, log `[CONFLICT]`, and continue** with the remaining repos. Already-pushed repos' dispatches fire normally.
- **Recovery manifest (WB-05):** write a per-run JSON manifest recording each repo's outcome (`succeeded` / `failed` / `conflict` / `skipped`), the pushed sha, and any error. Store in a **gitignored skill-local directory** (e.g. `.claude/skills/activity-sync/manifests/` — add to `.gitignore`); never committed into kf-cpto.
- **Idempotency (SC-4):** a re-run with no new `Proposal`s performs no writes → zero git diff. The write path **no-ops when the reconciled + sanitized content already equals the current file**.

### Claude's Discretion
- Module layout: a new `writeback.py` (and a `sanitize.py` helper, or a sanitization function within) in `.claude/skills/activity-sync/`, consuming `reconcile.run()` proposals. Exact decomposition, manifest schema, and confirm-prompt wording at Claude's discretion, following Phase 1/2 skill patterns (`_run_git` arg-list subprocess, `run()`/`main()` split, `[LABEL]` text pills, no emojis).
- The throwaway-remote test harness shape (bare repo under a temp dir, or a fixture in the test file) is at Claude's discretion as long as no live org push occurs.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.claude/skills/activity-sync/reconcile.py` — `run() -> list[Proposal]`; `Proposal{repo, task, old_status, new_status, tier, signal, signal_url}`. Phase 3 consumes this. `_run_git()` arg-list subprocess wrapper is reusable for fetch/commit/push.
- `.claude/skills/activity-sync/repo_enum.py` — records carry per-repo `branch` (default branch), `local_path`, `remote_url`, and the kanban `raw` content (in the kanban sub-dict). `_get_default_branch()` and the fetch/SHA-compare logic are reusable for conflict detection.
- `scripts/utils.py` — `parse_kanban_tasks()` (4-vs-6-col detection via header pipe count), `TASK_STATUSES`. Reuse for locating/validating rows; do not add a second parser (REPO-03).
- `aggregate.yml` — reference for HTTPS+KF_PAT remote URL and git commit/push identity pattern. `templates/notify-kf-cpto.yml` — fires `kanban-updated` on push of `kanban.md` to main/master.

### Established Patterns
- pyyaml does NOT preserve `#` frontmatter comments on round-trip (confirmed) — hence ruamel.yaml for the frontmatter.
- No existing Mermaid-character sanitization anywhere; aggregator embeds task titles into Mermaid labels largely unescaped (`aggregator.py` kanban/gantt generators) — this phase is the first sanitization fence.
- `[skip ci]` is used in aggregate.yml's own docs commits to avoid recursion; kanban write-back deliberately does NOT use it (we want the dispatch).

### Integration Points
- Upstream: `reconcile.run()` proposals (Phase 2).
- Downstream: pushes trigger `notify-kf-cpto.yml` → `kanban-updated` → `aggregate.yml` (existing CI; no changes to CI this phase).
- Auth: `KF_PAT` (same token discover.py / CI uses) injected into the HTTPS origin URL at push time.

</code_context>

<specifics>
## Specific Ideas

- ruamel.yaml round-trip for frontmatter is the chosen comment-preservation mechanism (user-selected over in-place-only editing).
- The reachability/conflict check reuses the Phase-1 fetch + SHA-compare approach to detect "local behind origin" before writing.
- The live end-to-end push (SC-1) is explicitly deferred to human UAT — the autonomous run builds and tests against a local throwaway remote, never a live org push.

</specifics>

<deferred>
## Deferred Ideas

- Agentic capacity overflow model (CAP-01..07) — Phase 4.
- Aggregator-side second-fence sanitization at render time (DIAG-V2-01) — v2 / Phase 5 hardening.
- Tier-2 ambiguous-signal human-decision flagging (RECON-V2-01) — v2.
- Two-way / real-time Sheets sync — out of scope (Pages canonical, Sheets downstream).

</deferred>
