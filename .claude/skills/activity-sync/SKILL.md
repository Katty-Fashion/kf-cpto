---
name: activity-sync
description: "Read-only enumeration and parsing of tracked sibling repos. Fetches
  remote state and parses each kanban.md through the canonical scripts/utils.py
  parsers. Use to inspect kanban state across all tracked repos. Triggers on:
  activity sync, repo enum, list tracked repos, fetch kanban state."
allowed-tools:
  - Bash
  - Read
---

# Activity Sync — Repo Access

Read-only enumeration of tracked sibling repos in `repos-local/`. Fetches remote
state via `git fetch` and parses each `kanban.md` through the canonical
`scripts/utils.py` parsers (one-parser constraint — no local parser in this skill).

---

## Prerequisites

- `repos-local/` must be populated before running `repo_enum.py`.
- Run `bootstrap.py` once on a fresh machine to clone all tracked repos.

---

## Commands

### [BOOTSTRAP] First-run clone and marker seeding

Run once on a fresh machine (or when adding a new tracked repo):

```
python .claude/skills/activity-sync/bootstrap.py
```

What it does:
- Creates `repos-local/` if absent
- Clones each tracked repo via SSH (full clone — no `--depth=1`; Phase 2 needs git history)
- Seeds `kanban.md` and `notify-kf-cpto.yml` from `templates/` into repos that lack them
- [WARN] on clone failure (non-fatal; continues to next repo)

### [ENUM] Enumerate, fetch, and parse all tracked repos

```
python .claude/skills/activity-sync/repo_enum.py
```

What it does:
- Scans `repos-local/` for valid git repos (no static project list)
- Runs `git fetch origin` per repo before reading (non-fatal on failure)
- Logs `up-to-date` or `new-commits` per repo based on before/after SHA comparison
- Parses `kanban.md` via `utils.parse_kanban_frontmatter()` + `utils.parse_kanban_tasks()`
- Counts valid-status tasks using `utils.TASK_STATUSES` (matches aggregator logic)
- Asserts kf-cpto working tree is clean after run (`git status --porcelain == ""`)
- Returns `list[RepoRecord]` for Phase 2 downstream consumption

---

## Script Locations

| Script | Path | Role |
|--------|------|------|
| Bootstrap | `.claude/skills/activity-sync/bootstrap.py` | One-shot clone + seed |
| Enumeration | `.claude/skills/activity-sync/repo_enum.py` | Fetch + parse all tracked repos |

---

## Output Format

`repo_enum.py` prints one status line per repo:

```
[INFO] <repo-name>: <fetch-status> (branch: <branch>)
[INFO] <repo-name>: <N> valid-status tasks
[WARN] <repo-name>: kanban.md absent — run bootstrap.py first
```

Where `<fetch-status>` is one of: `up-to-date`, `new-commits`, `fetch-failed`.

---

## [NOTE] Parser Constraint

This skill [NEVER] calls `utils.load_project_kanban()` — it is hardwired to `repos/`
(the CI clone dir). The skill calls `utils.parse_kanban_frontmatter()` and
`utils.parse_kanban_tasks()` directly with paths from `repos-local/`.

---

## [NOTE] repos-local/ Is Gitignored

`repos-local/` is listed in `.gitignore` (runtime-only; populated by `bootstrap.py`).
Never commit files under `repos-local/`.
