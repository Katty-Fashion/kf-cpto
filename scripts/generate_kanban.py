#!/usr/bin/env python3
"""
Generate distinct per-repo kanban.md files from the migration plan-of-record.

The migration plan is the full 39-task migration with person-day effort, real
dates, statuses, and discipline encoded in the Assignee column. It lives in a
canonical intermediate, docs/_data/migration_plan.yml, SEEDED ONCE from the
curated kf-platform/kanban.md. The generator then PARTITIONS that plan by
discipline into three distinct, well-formed kanban.md files:

    FE-only tasks  (@<frontend>)              -> kf-fe-platform
    BE-only tasks  (@<backend>)               -> kf-be-platform
    FE+BE tasks    (@<frontend> + @<backend>) -> kf-platform   (cross-stack umbrella)

Every task lands in exactly ONE repo, so the downstream LOE intermediate
(docs/_data/loe.yml) sums cleanly with NO double-counting.

Why a separate plan-of-record file? Clean partition means kf-platform keeps only
its FE+BE tasks — it is both the original source AND a partition target. Reading
the plan from a stable intermediate (not from the partitioned kf-platform) keeps
generation idempotent: re-running never loses the FE-only / BE-only tasks. Edit
the plan-of-record (migration_plan.yml) going forward, or --reseed from a
full-plan kf-platform kanban.

Design:
- One canonical parser only — imports scripts/utils.py (never re-parses by hand).
- Frontmatter preserved verbatim per target repo (never clobbers curated YAML).
- Statuses MERGE: a target repo's own valid status for a task wins over the plan
  status, so re-running never reverts statuses set by the activity-sync skill.
- Idempotent: a no-op regeneration writes nothing (byte-compare gate).
- Reuses the activity-sync write-back primitives (conflict gate, KF_PAT push,
  recovery manifest) rather than forking that hardened git logic.

Usage:
    python scripts/generate_kanban.py                # dry-run preview (default, safe)
    python scripts/generate_kanban.py --reseed       # rebuild plan-of-record from kf-platform, then preview
    python scripts/generate_kanban.py --apply        # write + batch-confirm + commit + push
    python scripts/generate_kanban.py --apply --no-push   # write + commit locally, no push
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# scripts/ is this file's directory; activity-sync skill holds the write primitives.
_SCRIPTS_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPTS_DIR.parent
_SKILL_DIR = _REPO_ROOT / ".claude" / "skills" / "activity-sync"
for _p in (str(_SCRIPTS_DIR), str(_SKILL_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import utils  # noqa: E402
from utils import (  # noqa: E402
    DATA_DIR,
    TASK_STATUSES,
    now_iso,
    parse_kanban_frontmatter,
    parse_kanban_tasks,
    parse_effort_days,
)

# Reuse the hardened git/push/manifest primitives from the activity-sync skill.
import writeback  # noqa: E402

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

# Full clones live here (repos/ is a symlink tree into repos-local/).
REPOS_LOCAL_DIR = _REPO_ROOT / "repos-local"

# Canonical plan-of-record intermediate (seeded from kf-platform; never partitioned).
PLAN_FILE = DATA_DIR / "migration_plan.yml"

# The curated kanban the plan is seeded from.
SEED_REPO = "kf-platform"

# Discipline -> owning repo. FE+BE (cross-stack) stays in the kf-platform umbrella.
DISCIPLINE_TO_REPO = {
    "FE": "kf-fe-platform",
    "BE": "kf-be-platform",
    "FE+BE": "kf-platform",
}
TARGET_REPOS = ("kf-fe-platform", "kf-be-platform", "kf-platform")

COMMIT_MSG = "chore(kanban): generate from migration plan (discipline split)"

_FM_BLOCK_RE = re.compile(r"^(---\n.*?\n---\n)", re.DOTALL)
_MILESTONE_BLOCK_RE = re.compile(r"(<!--[^>]*?Milestones.*?-->)", re.DOTALL)

# Plan-task fields persisted to migration_plan.yml.
_PLAN_FIELDS = ("task", "assignee", "effort", "start", "end", "status", "repo")


# ---------------------------------------------------------------------------
# Discipline classification
# ---------------------------------------------------------------------------

def _email_to_handle(email: str) -> str:
    """'alexandru.bejenari@katty-fashion.ro' -> '@alexandru.bejenari'."""
    local = (email or "").split("@", 1)[0].strip()
    return f"@{local}" if local else ""


def derive_handles(meta: dict) -> tuple[str, str]:
    """Return (fe_handle, be_handle) from a repo's team frontmatter.

    Raises ValueError if the team block lacks frontend/backend — without it we
    cannot classify tasks by discipline.
    """
    team = meta.get("team") or {}
    fe = _email_to_handle(team.get("frontend", ""))
    be = _email_to_handle(team.get("backend", ""))
    if not fe or not be:
        raise ValueError(
            f"{SEED_REPO}/kanban.md frontmatter must define team.frontend and "
            f"team.backend (got frontend={fe!r}, backend={be!r})"
        )
    return fe, be


def classify_repo(assignee: str, fe_handle: str, be_handle: str) -> str | None:
    """Map an assignee string to its owning repo, or None if unrecognized."""
    has_fe = fe_handle in assignee
    has_be = be_handle in assignee
    if has_fe and has_be:
        return DISCIPLINE_TO_REPO["FE+BE"]
    if has_fe:
        return DISCIPLINE_TO_REPO["FE"]
    if has_be:
        return DISCIPLINE_TO_REPO["BE"]
    return None


# ---------------------------------------------------------------------------
# Plan-of-record I/O
# ---------------------------------------------------------------------------

def _extract_frontmatter_block(content: str) -> str:
    """Return the raw '---\\n...\\n---\\n' frontmatter block, or '' if absent."""
    m = _FM_BLOCK_RE.match(content or "")
    return m.group(1) if m else ""


def _extract_milestone_block(content: str) -> str:
    """Return the milestone reference HTML comment block, or ''."""
    m = _MILESTONE_BLOCK_RE.search(content or "")
    return m.group(1) if m else ""


def seed_plan() -> dict:
    """Build the plan-of-record from the SEED_REPO's current kanban and persist it.

    Resolves each task's owning repo (discipline) up front so partitioning is
    stable and never depends on the (later partitioned) kf-platform kanban.
    """
    src_path = REPOS_LOCAL_DIR / SEED_REPO / "kanban.md"
    if not src_path.exists():
        raise FileNotFoundError(
            f"{src_path} not found — run the activity-sync bootstrap first."
        )
    content = src_path.read_text(encoding="utf-8")
    meta = parse_kanban_frontmatter(content)
    tasks = parse_kanban_tasks(content, project=SEED_REPO)
    if not tasks:
        raise ValueError(f"{src_path} has no parseable tasks — cannot seed plan.")

    fe_handle, be_handle = derive_handles(meta)
    plan_tasks = []
    for t in tasks:
        repo = classify_repo(t["assignee"], fe_handle, be_handle)
        if repo is None:
            print(
                f"Warning: task {t['task']!r} assignee {t['assignee']!r} matches "
                f"neither {fe_handle} nor {be_handle} — assigning to {SEED_REPO}"
            )
            repo = SEED_REPO
        plan_tasks.append({
            "task": t["task"],
            "assignee": t["assignee"],
            "effort": t["effort"],
            "start": t["start"],
            "end": t["end"],
            "status": t["status"],
            "repo": repo,
        })

    plan = {
        "generated_at": now_iso(),
        "source": SEED_REPO,
        "milestone_block": _extract_milestone_block(content),
        "row_count": len(plan_tasks),
        "tasks": plan_tasks,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_FILE.write_text(
        yaml.safe_dump(plan, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    print(f"[INFO] Seeded plan-of-record {PLAN_FILE} from {SEED_REPO} "
          f"({len(plan_tasks)} tasks).")
    return plan


def load_plan(reseed: bool = False) -> dict:
    """Load the plan-of-record, seeding it from kf-platform if missing or --reseed."""
    if reseed or not PLAN_FILE.exists():
        return seed_plan()
    plan = yaml.safe_load(PLAN_FILE.read_text(encoding="utf-8")) or {}
    if not plan.get("tasks"):
        print(f"[WARN] {PLAN_FILE} has no tasks — reseeding from {SEED_REPO}.")
        return seed_plan()
    return plan


# ---------------------------------------------------------------------------
# Content generation
# ---------------------------------------------------------------------------

def existing_status_map(content: str, project: str = "") -> dict[str, str]:
    """Map task name -> canonical status for a repo's CURRENT kanban (valid only).

    Drives status preservation: a target repo's own status for a task wins over
    the plan status, so re-running never reverts activity-sync.
    """
    out: dict[str, str] = {}
    for task in parse_kanban_tasks(content, project=project):
        if task["status"] in TASK_STATUSES:
            out[task["task"]] = task["status"]
    return out


def build_body(tasks: list[dict], milestone_block: str) -> str:
    """Render the kanban body: heading, hint comments, 6-col table, milestone trailer."""
    lines = [
        "# Project Kanban",
        "",
        "<!-- Valid statuses: Todo, In Progress, Review, Done -->",
        "<!-- Effort format: Nd (e.g. 1d, 0.5d, 3d) -->",
        "<!-- Generated by scripts/generate_kanban.py from docs/_data/migration_plan.yml "
        "(discipline split). Re-run the generator rather than hand-editing rows. -->",
        "",
        "| Task | Assignee | Effort | Start | End | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for t in tasks:
        lines.append(
            f"| {t['task']} | {t['assignee']} | {t['effort']} | "
            f"{t['start']} | {t['end']} | {t['status']} |"
        )
    body = "\n".join(lines) + "\n"
    if milestone_block:
        body += "\n" + milestone_block + "\n"
    return body


def build_repo_content(repo: str, tasks: list[dict], milestone_block: str) -> str:
    """Compose a full kanban.md for one target repo (frontmatter preserved + new body)."""
    kanban_path = REPOS_LOCAL_DIR / repo / "kanban.md"
    existing = kanban_path.read_text(encoding="utf-8") if kanban_path.exists() else ""

    fm_block = _extract_frontmatter_block(existing)
    if not fm_block:
        raise ValueError(
            f"{repo}/kanban.md has no frontmatter to preserve — refusing to "
            f"generate without curated frontmatter (project/team/sprint)."
        )

    # Status merge: this repo's own valid status for a task wins over the plan.
    own_status = existing_status_map(existing, project=repo)
    merged = [{**t, "status": own_status.get(t["task"], t["status"])} for t in tasks]

    return fm_block + "\n" + build_body(merged, milestone_block)


def partition(plan_tasks: list[dict]) -> dict[str, list[dict]]:
    """Group plan tasks into {repo: [tasks]} by their resolved repo field."""
    buckets: dict[str, list[dict]] = {r: [] for r in TARGET_REPOS}
    for t in plan_tasks:
        repo = t.get("repo")
        if repo not in buckets:
            print(f"Warning: plan task {t.get('task')!r} has repo {repo!r} not in "
                  f"{TARGET_REPOS} — assigning to {SEED_REPO}")
            repo = SEED_REPO
        buckets[repo].append(t)
    return buckets


def generate(reseed: bool = False) -> tuple[dict[str, str], dict[str, list[dict]], list[dict]]:
    """Build new kanban.md content for every target repo.

    Returns (outputs, buckets, plan_tasks):
      outputs:    {repo: full kanban.md content}
      buckets:    {repo: [partitioned plan task dicts]}
      plan_tasks: the full plan task list (for invariant checks)
    """
    plan = load_plan(reseed=reseed)
    plan_tasks = plan["tasks"]
    milestone_block = plan.get("milestone_block", "")
    buckets = partition(plan_tasks)
    outputs = {r: build_repo_content(r, buckets[r], milestone_block) for r in TARGET_REPOS}
    return outputs, buckets, plan_tasks


# ---------------------------------------------------------------------------
# Preview (dry-run)
# ---------------------------------------------------------------------------

def _effort_sum(tasks: list[dict]) -> float:
    return sum(parse_effort_days(t["effort"]) for t in tasks)


def preview(outputs: dict, buckets: dict, plan_tasks: list[dict]) -> None:
    """Print per-repo diff, partition counts, and the no-double-count LOE invariant."""
    print("\n[INFO] Dry-run preview — no files written.\n")

    for repo in TARGET_REPOS:
        path = REPOS_LOCAL_DIR / repo / "kanban.md"
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        new = outputs[repo]
        if current == new:
            print(f"  [SKIP] {repo}: no change (already current)")
            continue
        sys.stdout.writelines(difflib.unified_diff(
            current.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{repo}/kanban.md",
            tofile=f"b/{repo}/kanban.md",
        ))
        print()

    print("\n[INFO] Partition (no task in two repos):")
    print(f"  {'Repo':<18} {'Tasks':>6} {'Effort(d)':>10}")
    print(f"  {'-'*18} {'-'*6} {'-'*10}")
    total_tasks = total_effort = 0
    for repo in TARGET_REPOS:
        t = buckets[repo]
        eff = _effort_sum(t)
        total_tasks += len(t)
        total_effort += eff
        print(f"  {repo:<18} {len(t):>6} {eff:>10.1f}")
    print(f"  {'-'*18} {'-'*6} {'-'*10}")
    print(f"  {'TOTAL':<18} {total_tasks:>6} {total_effort:>10.1f}")

    plan_effort = _effort_sum(plan_tasks)
    ok = (total_tasks == len(plan_tasks)) and abs(total_effort - plan_effort) < 1e-6
    print(
        f"\n[INVARIANT] split totals == plan-of-record: "
        f"tasks {total_tasks}=={len(plan_tasks)}, "
        f"effort {total_effort:.1f}=={plan_effort:.1f} -> "
        f"[{'OK' if ok else 'MISMATCH'}]"
    )
    print("\n[INFO] Re-run with --apply to write and push.")


# ---------------------------------------------------------------------------
# Origin sync — keep our write a single kanban.md-only commit on top of origin
# ---------------------------------------------------------------------------

def _changed_files(repo_path: str, rev_range: str) -> set:
    """Return the set of file paths changed across a commit range (git diff --name-only)."""
    r = writeback._run_git(["-C", repo_path, "diff", "--name-only", rev_range])
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def _sync_to_origin(repo_path: str, branch: str) -> tuple[str, str]:
    """Bring a tracked clone in line with origin/<branch> WITHOUT touching others' work.

    Mindfulness contract — we only ever add a single kanban.md-only commit on top
    of the current origin tip, and never force-push or discard commits we didn't
    author:
      - dirty working tree              -> ('blocked', ...)   (don't touch)
      - already current / ahead only    -> ('current', ...)
      - behind only                     -> fast-forward       ('fast-forwarded')
      - diverged, BUT our local-ahead   -> reset to origin    ('resynced')
        commits touch only kanban.md       (discards only OUR regenerable commits;
        AND origin didn't touch kanban.md   others' commits are preserved)
      - any other divergence            -> ('conflict', ...)  (skip; never clobber)

    Returns (status, detail). Statuses 'current'/'fast-forwarded'/'resynced' mean
    the repo is safe to (re)generate onto; 'blocked'/'conflict' mean skip it.
    """
    st = writeback._run_git(["-C", repo_path, "status", "--porcelain"])
    if st.stdout.strip():
        return "blocked", "working tree not clean — resolve manually"

    fetch = writeback._run_git(["-C", repo_path, "fetch", "origin", branch])
    if fetch.returncode != 0:
        return "conflict", f"fetch failed: {fetch.stderr.strip()}"

    behind = int(writeback._run_git(
        ["-C", repo_path, "rev-list", "--count", "HEAD..FETCH_HEAD"]).stdout or "0")
    ahead = int(writeback._run_git(
        ["-C", repo_path, "rev-list", "--count", "FETCH_HEAD..HEAD"]).stdout or "0")

    if behind == 0:
        return "current", (f"up-to-date (+{ahead} local)" if ahead else "up-to-date")

    if ahead == 0:
        ff = writeback._run_git(["-C", repo_path, "merge", "--ff-only", "FETCH_HEAD"])
        if ff.returncode != 0:
            return "conflict", f"fast-forward failed: {ff.stderr.strip()}"
        return "fast-forwarded", f"+{behind} from origin/{branch}"

    # Diverged: we have local commits AND origin has new ones.
    ahead_files = _changed_files(repo_path, "FETCH_HEAD..HEAD")
    origin_touched_kanban = "kanban.md" in _changed_files(repo_path, "HEAD..FETCH_HEAD")
    if ahead_files and ahead_files <= {"kanban.md"} and not origin_touched_kanban:
        # Our only local commits are regenerable kanban.md commits, and origin's
        # new commits don't touch kanban.md → safe to rebase onto origin by reset.
        r = writeback._run_git(["-C", repo_path, "reset", "--hard", "FETCH_HEAD"])
        if r.returncode != 0:
            return "conflict", f"reset failed: {r.stderr.strip()}"
        return "resynced", f"rebased {ahead} local kanban-only commit(s) onto origin/{branch}"

    return "conflict", (
        f"diverged (+{ahead}/-{behind}); local-ahead touches {sorted(ahead_files) or '∅'}, "
        f"origin-changed-kanban={origin_touched_kanban} — resolve manually"
    )


_SYNC_OK = ("current", "fast-forwarded", "resynced")


# ---------------------------------------------------------------------------
# Apply (sync -> generate -> confirm -> write + commit + push)
# ---------------------------------------------------------------------------

def _will_change(repo: str, outputs: dict) -> bool:
    path = REPOS_LOCAL_DIR / repo / "kanban.md"
    if not path.exists():
        return True
    return path.read_text(encoding="utf-8") != outputs[repo]


def _confirm_batch(outputs: dict, push: bool, eligible: list[str]) -> bool:
    """Single y/N gate over the eligible+changed repos (batch-confirm once)."""
    changed = [r for r in eligible if _will_change(r, outputs)]
    action = "commit + push" if push else "commit (no push)"
    print(f"\n[INFO] Generate summary — {len(changed)} repo(s) to {action}:")
    for r in changed:
        print(f"  {r}")
    if not changed:
        print("  (none — all eligible repos already current)")
        return False
    answer = input(f"\nProceed to {action} {len(changed)} repo(s)? [y/N]: ")
    return answer.strip().lower() in ("y", "yes")


def apply(push: bool, reseed: bool = False, sync: bool = True) -> list[dict]:
    """Sync each clone to origin, generate, batch-confirm, then write/commit/push.

    Returns manifest entries. Repos that can't be safely synced are recorded as
    'conflict' and skipped — their commits/edits by others are never overwritten.
    """
    utils.load_projects()  # populates utils.PROJECT_BRANCHES from discovered.txt
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # 1. Sync each target to origin tip (mindful: our kanban-only commits only).
    eligible: list[str] = []
    sync_results: dict[str, tuple[str, str]] = {}
    for repo in TARGET_REPOS:
        branch = utils.PROJECT_BRANCHES.get(repo, "main")
        if sync:
            status, detail = _sync_to_origin(str(REPOS_LOCAL_DIR / repo), branch)
        else:
            status, detail = "current", "sync skipped (--no-sync)"
        sync_results[repo] = (status, detail)
        tag = "[SYNC]" if status in _SYNC_OK else "[CONFLICT]"
        print(f"{tag} {repo}: {status} — {detail}")
        if status in _SYNC_OK:
            eligible.append(repo)

    if not eligible:
        print("[INFO] No repos eligible after sync — nothing to do.")
        return []

    # 2. Generate from the plan-of-record (reads the freshly-synced repo content).
    try:
        outputs, _buckets, _plan = generate(reseed=reseed)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return []

    # 3. Single batch confirmation over eligible+changed repos.
    if not _confirm_batch(outputs, push, eligible):
        print("[INFO] Cancelled — nothing written.")
        return []

    # 4. Read KF_PAT only at push time (SSH clones don't need it for manual push).
    kf_pat = ""
    if push:
        kf_pat = os.environ.get("KF_PAT", "")
        if not kf_pat:
            print("[ERROR] KF_PAT unset — set it or re-run with --no-push.")
            raise RuntimeError("KF_PAT unset — cannot push")

    results: list[dict] = []
    for repo in TARGET_REPOS:
        repo_path = str(REPOS_LOCAL_DIR / repo)
        kanban_path = REPOS_LOCAL_DIR / repo / "kanban.md"
        branch = utils.PROJECT_BRANCHES.get(repo, "main")
        entry = {"repo": repo, "outcome": "failed", "pushed_sha": None,
                 "changes": [], "error": None}

        if repo not in eligible:
            status, detail = sync_results[repo]
            entry.update(outcome="conflict", error=f"{status}: {detail}")
            results.append(entry)
            continue

        new_content = outputs[repo]
        try:
            # After sync the clone sits on origin tip, so this is fast-forward-only.
            if not writeback._content_changed(str(kanban_path), new_content):
                print(f"[SKIP] {repo}: content unchanged")
                entry.update(outcome="skipped")
                results.append(entry)
                continue

            kanban_path.write_text(new_content, encoding="utf-8")
            # Stage ONLY kanban.md — our commit never carries unrelated files.
            writeback._run_git(["-C", repo_path, "add", "kanban.md"])
            commit_r = writeback._run_git([
                "-C", repo_path,
                "-c", f"user.name={writeback._BOT_NAME}",
                "-c", f"user.email={writeback._BOT_EMAIL}",
                "commit", "-m", COMMIT_MSG,
            ])
            if commit_r.returncode != 0:
                entry.update(error=f"commit failed: {commit_r.stderr.strip()}")
                results.append(entry)
                continue

            if not push:
                sha_r = writeback._run_git(["-C", repo_path, "rev-parse", "HEAD"])
                sha = sha_r.stdout.strip() if sha_r.returncode == 0 else "unknown"
                print(f"[DONE] {repo}: committed {sha[:8]} (no push)")
                entry.update(outcome="succeeded", pushed_sha=sha)
                results.append(entry)
                continue

            ok, sha_or_err = writeback._push_with_auth(repo_path, repo, branch, kf_pat)
            if not ok:
                outcome = ("conflict" if writeback._is_non_fast_forward(sha_or_err)
                           else "failed")
                print(f"[{outcome.upper()}] {repo}: {sha_or_err}")
                entry.update(outcome=outcome, error=sha_or_err)
                results.append(entry)
                continue

            print(f"[DONE] {repo}: pushed {sha_or_err[:8]} (branch: {branch})")
            entry.update(outcome="succeeded", pushed_sha=sha_or_err)
            results.append(entry)
        except Exception as exc:  # noqa: BLE001 — per-repo boundary; batch continues
            print(f"[FAIL] {repo}: {exc}", file=sys.stderr)
            entry.update(error=str(exc))
            results.append(entry)

    writeback._write_manifest(writeback.MANIFESTS_DIR, run_id, results)
    tally = {"succeeded": 0, "failed": 0, "conflict": 0, "skipped": 0}
    for e in results:
        tally[e["outcome"]] = tally.get(e["outcome"], 0) + 1
    print(
        f"\n[TALLY] {tally['succeeded']} [DONE] / {tally['conflict']} [CONFLICT] / "
        f"{tally['skipped']} [SKIP] / {tally['failed']} [FAIL]"
    )
    if push and tally["succeeded"]:
        print("[INFO] Pushed kanban.md updates trigger each repo's notify-kf-cpto.yml "
              "dispatch → kf-cpto aggregate.yml rebuilds the dashboard + Sheet.")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate distinct per-repo kanban.md files by partitioning the "
            "migration plan-of-record by discipline."
        )
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Sync + generate + batch-confirm + commit + push (default is dry-run preview).",
    )
    parser.add_argument(
        "--no-push", action="store_true",
        help="With --apply: write and commit locally but do not push (no KF_PAT needed).",
    )
    parser.add_argument(
        "--no-sync", action="store_true",
        help="With --apply: skip the fetch/fast-forward-to-origin step (not recommended).",
    )
    parser.add_argument(
        "--reseed", action="store_true",
        help=f"Rebuild docs/_data/migration_plan.yml from {SEED_REPO}'s current kanban "
             f"before generating (use only when {SEED_REPO} holds the full plan).",
    )
    args = parser.parse_args()

    print("KF Kanban Generator — Starting...")
    if args.apply:
        apply(push=not args.no_push, reseed=args.reseed, sync=not args.no_sync)
    else:
        try:
            outputs, buckets, plan_tasks = generate(reseed=args.reseed)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        preview(outputs, buckets, plan_tasks)

    print("KF Kanban Generator — Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
