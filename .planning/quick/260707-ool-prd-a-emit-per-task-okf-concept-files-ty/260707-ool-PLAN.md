---
id: 260707-ool
title: PRD A — Emit Per-Task OKF Concept Files
type: quick
phase: quick
plan: 260707-ool
autonomous: true
---

# PRD A — Emit Per-Task OKF Concept Files

## Objective

Emit one OKF `type: Task` concept file per task row so tasks become addressable,
cross-linkable graph nodes in the OKF bundle (prep for PRD B visualizer).

Pure transform of `loe_rows` + `all_project_data` already passed to
`generate_okf_bundle` — no second kanban parser, no new data sources.

## Tasks

### Task 1 — Implement task concept emitter in scripts/okf_export.py

Add the following to `scripts/okf_export.py`:

1. `_task_slug(task_name, seen=None, index=0) -> str` — stable deterministic slug:
   strip outer `[...]`, lower-case, replace non-alphanumeric runs with `-`, trim.
   De-duplicate within a project by appending `-2`, `-3`, ... (deterministic by
   stable input order). Empty/degenerate -> `task-{index}`.

2. `_gen_task_concept(project, row, project_meta) -> str` — `type: Task` concept.
   Frontmatter: `type`, `title`, `status`, `assignee`, `effort` (e.g. `5d`),
   `sprint`, `timestamp` (project `last_updated` — NOT run time), `resource`
   (dashboard project URL). Body: status/effort line + Project up-link +
   LOE metrics link.

3. `_gen_tasks_project_index(project, task_slugs_and_titles) -> str` — per-project
   `tasks/{slug}/index.md` listing all task concepts for that project (no frontmatter
   per spec — it is an index file).

4. `_gen_tasks_root_index(project_task_counts) -> str` — `tasks/index.md` grouping
   all projects with their task counts.

5. Wire into `generate_okf_bundle()`:
   - After project concepts loop, iterate loe_rows grouped by project.
   - Skip projects with 0 rows (ai-rise-options, tech_brainstorming).
   - Write task files to `tasks/{project_slug}/{task_slug}.md`.
   - Write per-project index at `tasks/{project_slug}/index.md`.
   - Write root index at `tasks/index.md`.
   - Update file count.

6. Update `_gen_root_index` to add a Tasks line: `- [Tasks](/tasks/index.md) — N task concepts`.

7. Update `_gen_project_concept` to add a down-link line after the task table:
   `See task concepts: [/tasks/{slug}/index.md](/tasks/{slug}/index.md)`.

## Constraints

- DETERMINISTIC: slugs stable, timestamps from project `last_updated` not run time.
- Reuse `_slug`, `_frontmatter`, `_write`, `_project_loe`; match module style exactly.
- No second kanban parser.
- Verify: aggregator runs clean, validator exits 0, 2nd-run `git diff --stat docs/okf/` empty.

## Verification

1. `python scripts/aggregator.py` — completes without error, shows higher OKF count (~136).
2. `python scripts/validate_okf.py` — exits 0, all files conformant.
3. Run aggregator twice; `git status --porcelain docs/okf/` empty on 2nd run.
4. Spot-check: `docs/okf/tasks/kf-platform/` has 19 task files; one links up to `/projects/kf-platform.md`.
