---
name: kanban-groom
description: Interactive, numbered grooming of a tracked repo's kanban.md — list every task as a stable-numbered table with hygiene flags, then update or delete rows by number from user feedback. Use when the user says "groom the kanban", "list R3-AAS tasks", "clean up the board", "update task 12", "delete tasks 3 and 7", "mark 5 done", or wants an interactive review of a repo's task list. Adapted from kf-platform's uat-list/uat-check pattern for the kf-cpto hub.
---

# Kanban Groom

UAT-checklist-style workflow over any tracked repo's `kanban.md` in `repos-local/`:
one numbered table (the *base foundation* for tracking and flagging tasks), then
by-number edits driven by user feedback. Backed by `groom.py`, which reuses the
canonical `scripts/utils.py` table grammar (one-parser constraint — no second parser).

## Commands

```bash
python .claude/skills/kanban-groom/groom.py list <repo>
python .claude/skills/kanban-groom/groom.py set <repo> <n> field=value [field=value ...]
python .claude/skills/kanban-groom/groom.py delete <repo> <n> [<n> ...]
```

## [LIST] The numbered table

`list` prints a one-line status summary, then one row per parseable task:

```
| # | Section | Task | Status | Flags |
```

Hygiene flags:
- `[BAD-STATUS]` — status not in Todo / In Progress / Review / Done
- `[DUP]` — same task name appears in more than one table (e.g. blockers + section)
- `[NO-EFFORT]` — no `Nd` effort → the task never counts in LOE person-days
- `[NO-DATES]` — no start date → the task never lands on a Gantt

Present the table to the user and invite feedback ("delete 12", "mark 5 done",
"set effort 3d on 7", "rename 9 to ..."). Lead with the summary counts.

## [SET] / [DELETE] Applying feedback

- Map the user's words to commands: "mark 5 done" → `set <repo> 5 status=Done`;
  "give 7 three days effort" → `set <repo> 7 effort=3d`; "drop 3 and 12" →
  `delete <repo> 3 12`.
- `set` accepts canonical fields (task, assignee/owner, effort, start, end,
  status) **plus any literal header label** of that row's own table (note,
  prioritate, blocker, ...). Status values are validated and canonicalized.
- **Numbers shift after a delete** — always re-run `list` and show the fresh
  table before applying further edits.
- Batch the user's whole instruction list first, apply, then re-`list` once.

## Guard rails

- `kf-platform`, `kf-fe-platform`, `kf-be-platform` boards are **generator-owned**
  (`scripts/generate_kanban.py` from `docs/_data/migration_plan.yml`); `set`/`delete`
  refuse them — groom the plan-of-record instead (`$EDITOR docs/_data/migration_plan.yml`
  then regenerate). `list` still works for read-only review.
- Edits are working-tree only. Committing + pushing the repo's `kanban.md` is a
  separate, batch-confirmed step (same convention as activity-sync write-back):
  show the diff summary, confirm once, `git commit` + `push` in `repos-local/<repo>`,
  and the repo's `notify-kf-cpto.yml` dispatch rebuilds the dashboard.
- Frontmatter is out of scope here — derive it per the R3-AAS pattern
  (backup + canonical keys) when a repo's frontmatter is stale.

## Relation to per-repo skills

Additive to repos that already have their own skills (e.g. kf-platform's
`uat-list` / `uat-check` / `sync-kanban`): those remain the source-of-truth flows
inside that repo; kanban-groom is the hub-side interactive cleanup for any
tracked board that is hand-maintained (R3-AAS, ai-rise-options, tech_brainstorming).
