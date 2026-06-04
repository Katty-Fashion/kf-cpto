---
phase: 03-write-back-diagram-sanitization
reviewed: 2026-06-04T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - .claude/skills/activity-sync/writeback.py
  - .claude/skills/activity-sync/sanitize.py
  - .claude/skills/activity-sync/test_writeback.py
  - .claude/skills/activity-sync/SKILL.md
findings:
  critical: 3
  warning: 6
  info: 4
  total: 13
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-06-04
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the activity-sync write-back engine (`writeback.py`), the Mermaid/table
sanitizer (`sanitize.py`), the test suite (`test_writeback.py`), and the skill
manual (`SKILL.md`).

The security posture for the KF_PAT push path is largely sound: `_run_git` is
arg-list only (no `shell=True`), the token URL is never printed, the origin URL
is restored in a `finally` block, and the manifest path is genuinely gitignored
(verified `git check-ignore` returns 0). KF_PAT is read lazily at push time and
fail-fast when unset. Those properties hold.

However, the table-handling logic has **three correctness defects that corrupt
tracked-repo data** — all caused by the same flawed assumption that every
pipe-table row is fully delimited with a trailing `|` and that every separator
row uses left-aligned `:---` markers. GitHub-flavored Markdown permits
trailing-pipe-less rows and `---` / `:--:` / `---:` separators, and the code
mishandles all of them. These violate the core idempotency/no-op invariant
(SC-4) and write the new status into the wrong cell. The test suite passes only
because every fixture uses the one canonical shape the code assumes — the bugs
are invisible to the tests. There is also a frontmatter round-trip defect for
empty/edge-case YAML that breaks byte-identity, and a latent token-in-error-string
exposure path.

## Critical Issues

### CR-01: Separator rows that are not `:---` are corrupted by `sanitize_body`

**File:** `.claude/skills/activity-sync/sanitize.py:154`
**Issue:** Separator-row detection only matches `:---` (left-align). GitHub-flavored
Markdown table separators are also valid as `---` (no colon), `:--:` (center),
and `---:` (right). For those rows, `sanitize_body` falls through to the data-row
branch and runs `sanitize_cell` over the separator cells. The `:` → ` -`
substitution then mangles them:

```
input : | --- | :--: | ---: |
output: | --- | --- - | --- - |   # table separator destroyed
```

This corrupts the table on the **first** run (so it is not even idempotent on
first contact), turning a valid kanban.md into one that no longer parses as a
table — directly breaking the "edits only the Status cell" and SC-4 invariants.
The template happens to use `:---`, which is why the suite never catches it.

**Fix:** Detect separator rows structurally rather than by the `:---` literal.
Treat any row whose non-empty cells all match `^:?-{3,}:?$` as a separator and
pass it through verbatim:

```python
import re
_SEP_CELL_RE = re.compile(r"^:?-{3,}:?$")

def _is_separator_row(stripped: str) -> bool:
    cells = [c.strip() for c in stripped.split("|")[1:-1]]
    return bool(cells) and all(_SEP_CELL_RE.match(c) for c in cells)
...
if _is_separator_row(stripped):
    result.append(line)
    continue
```

### CR-02: Status written to wrong cell when a row has no trailing pipe

**File:** `.claude/skills/activity-sync/writeback.py:796` and `:803`
**Issue:** `apply_status_change` assumes the Status column is always `parts[-2]`,
which is only true when the row ends with a trailing `|`. GitHub-flavored
Markdown allows rows without the closing pipe. For such a row the split yields no
trailing empty part, so `parts[-2]` is the **Effort** cell, not Status:

```
input : | Documentation | @dev | 1d | Todo        (no trailing pipe)
output: | Documentation | @dev | Done | Todo       (effort overwritten, status untouched)
```

This silently corrupts the row and leaves the real status unchanged — a data-loss
defect pushed to the tracked repo. The same trailing-pipe assumption exists in
`sanitize_body` (`sanitize.py:158`, which preserves `parts[-1]` as the trailing
cell), so a trailing-pipe-less data row also gets its last cell skipped from
sanitization.

**Fix:** Normalize/validate row shape before indexing. Either require a trailing
pipe and skip rows that lack one (with a `[WARN]`), or compute the Status cell
index from the header column count rather than `parts[-2]`. Minimal guard:

```python
# A well-formed row must start AND end with '|'
if not (stripped.startswith("|") and stripped.endswith("|")):
    print(f"[WARN] Skipping malformed (no trailing pipe) row: {stripped!r}")
    new_lines.append(line)
    continue
```

Apply the identical guard in `sanitize_body`.

### CR-03: Empty / edge-case frontmatter breaks byte-identity round-trip

**File:** `.claude/skills/activity-sync/writeback.py:699-705`
**Issue:** `roundtrip_frontmatter` claims byte-identity for unmodified files
(docstring at `:712` and the test at `test_writeback.py:340`). For an empty or
whitespace-only frontmatter block, `yaml.load("")` returns `None` and ruamel
dumps it as a YAML scalar plus a document-end marker:

```
input : ---\n\n---\nbody\n
output: ---\nnull\n...\n---\nbody\n      # injects 'null' and '...'
```

This rewrites the file (failing the SC-4 idempotency / no-op gate), commits a
spurious `null\n...\n` frontmatter, and pushes it to the tracked repo. Any repo
with an empty frontmatter block — or one whose ruamel representation differs from
the source byte layout (flow-style lists re-emitted in block style, scalar
re-quoting) — will produce a perpetual non-idempotent diff. The single test
fixture (`_KANBAN_ORIG`) was hand-picked to round-trip cleanly, so the suite
gives false confidence; the test comment at `:289-292` even acknowledges that
`{placeholder}` template values would break it.

**Fix:** Guard the empty/None case and avoid re-dumping when load yields no
mapping; preserve the raw text instead:

```python
def roundtrip_frontmatter(fm_str: str) -> str:
    if not fm_str.strip():
        return fm_str if fm_str.endswith("\n") else fm_str + "\n"
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(fm_str)
    if data is None:
        return fm_str.rstrip("\n") + "\n"
    ...
```

Additionally, add a round-trip test fixture with flow-style values
(`depends_on: [a, b]`, quoted vs unquoted scalars) to prove byte-identity holds
for the real-world shapes before this ships.

## Warnings

### WR-01: `new_status` is never validated against `TASK_STATUSES`

**File:** `.claude/skills/activity-sync/writeback.py:289`, `:734-808`
**Issue:** `apply_status_change` writes `new_status` verbatim into the Status cell
with no membership check against `utils.TASK_STATUSES`. The docstring at `:753`
asserts the caller validates it ("validated TASK_STATUSES member by caller"), but
neither `_write_repo` nor `run()` performs that check — they trust the Proposal
object blindly. A malformed proposal (typo, downstream regression in
`reconcile.run()`) would push an invalid status that the aggregator's parser then
warns on or drops. `TASK_STATUSES` is even imported but unused (see IN-01).

**Fix:** Validate before applying, and skip with a `[WARN]` on a non-member:

```python
from utils import TASK_STATUSES
...
if proposal.new_status not in TASK_STATUSES:
    print(f"[WARN] {repo_name}: invalid status {proposal.new_status!r} — skipping")
    continue
```

### WR-02: `set-url` failure error string can leak the token URL into the manifest/stdout

**File:** `.claude/skills/activity-sync/writeback.py:199-200`
**Issue:** When `remote set-url origin <https_url>` fails, the function returns
`f"remote set-url failed: {set_r.stderr.strip()}"`. Git can echo the offending
URL (including the embedded `kf_pat`) in certain failure modes (malformed URL).
That error string is then (a) printed via `_write_repo` and (b) persisted into
the recovery manifest JSON (`writeback.py:322`/`:333` → `error` field), defeating
the "token never logged or stored in manifest" invariant the SKILL.md table
promises (line 227). The current bare-init test happened not to echo the URL, but
that is git-version/condition dependent, not guaranteed.

**Fix:** Never surface raw git stderr from the token-bearing command. Redact:

```python
if set_r.returncode != 0:
    return False, "remote set-url failed (origin URL not changed)"
```

Also scrub any returned error string before it reaches the manifest.

### WR-03: TOCTOU window between conflict check and push (no `--force-with-lease`, no re-check)

**File:** `.claude/skills/activity-sync/writeback.py:266-326`
**Issue:** `_is_behind_origin` runs at step 1, then the code reads/edits/commits,
then pushes at step 9. A competing human push landing in that window produces a
non-fast-forward that the plain `git push` rejects — handled (returns `failed`) —
but the conflict was the exact scenario the gate exists to prevent, and the gap
is unbounded by design. The push uses a bare `push` (good — no `--force`), so no
data is overwritten, but the conflict-vs-failed classification becomes racy and
the manifest mislabels a real conflict as a generic `failed`.

**Fix:** Acceptable to keep the simple gate, but classify a non-fast-forward push
rejection as `conflict` (parse `stderr` for `non-fast-forward`/`rejected`) so the
manifest stays accurate, and document the residual window.

### WR-04: `_FM_RE` allows a non-frontmatter file to be misparsed as having frontmatter

**File:** `.claude/skills/activity-sync/writeback.py:65`, `:680`
**Issue:** `_FM_RE = r'^---\n(.*?)\n---\n?'` is non-greedy and matches the first
`\n---\n` it finds. A document that opens with `---` as a Markdown horizontal
rule (not YAML frontmatter) followed later by another `---` would be silently
split, treating arbitrary prose as YAML and feeding it to ruamel. While kanban.md
is expected to start with real frontmatter, the parser provides no guard that the
captured block is actually valid YAML mapping before round-tripping it.

**Fix:** After `yaml.load`, assert the result is a mapping (`dict`-like); raise
`ValueError` otherwise so the repo is reported as `failed` rather than corrupted:

```python
if not hasattr(data, "items"):
    raise ValueError("Frontmatter did not parse to a YAML mapping")
```

### WR-05: Redundant `git config user.name/email` and silent config failures

**File:** `.claude/skills/activity-sync/writeback.py:203-204`, `:312-313`
**Issue:** `git config user.name/email` is set twice (once in `_write_repo` step 8,
again in `_push_with_auth`), and in both places the `_run_git` return code is
ignored. If `git config` fails, the subsequent commit can fail with an opaque
"empty ident" error surfaced only as a generic commit failure. The duplication
also means the identity-setting responsibility is split across two functions.

**Fix:** Set identity once (in `_write_repo` before commit) and check the return
code, or use per-invocation `-c user.name=... -c user.email=...` on the commit
call so it cannot be missed.

### WR-06: `git fetch origin` is unbounded and not pinned to the target branch

**File:** `.claude/skills/activity-sync/writeback.py:152`
**Issue:** `_is_behind_origin` runs `git fetch origin` (all refs) rather than
`git fetch origin <branch>`. For repos with many refs this fetches more than
needed, and more importantly the subsequent `rev-list HEAD..origin/<branch>`
depends on `origin/<branch>` existing as a remote-tracking ref. If the local
clone was made with a different default branch or a restricted refspec,
`origin/<branch>` may be stale/absent and `rev-list` errors → conservative
`(True, -1)` conflict, silently skipping a repo that is actually fine.

**Fix:** Fetch the specific branch and update the tracking ref explicitly:
`_run_git(["-C", repo_path, "fetch", "origin", branch])`, then
`rev-list --count HEAD..FETCH_HEAD` (or ensure the refspec maps to
`origin/<branch>`).

## Info

### IN-01: Unused imports — `ORG`, `TASK_STATUSES`, `Any`, `unicodedata`

**File:** `.claude/skills/activity-sync/writeback.py:44`, `:56`; `.claude/skills/activity-sync/sanitize.py:18`
**Issue:** `from utils import ORG, TASK_STATUSES` — neither is used (`ORG` is
duplicated by the hardcoded `_KF_ORG`; `TASK_STATUSES` is referenced only in a
docstring). `from typing import Any` is imported but never used. In `sanitize.py`,
`import unicodedata` carries a `# noqa: F401 — used implicitly via ord/chr`
comment, but `ord`/`chr` are builtins — `unicodedata` is genuinely unused and the
comment is misleading.
**Fix:** Remove the unused imports. Either use `TASK_STATUSES` for WR-01
validation, or drop it. Delete `Any` and `unicodedata`.

### IN-02: `_KF_ORG` hardcodes the org instead of reusing `utils.ORG`

**File:** `.claude/skills/activity-sync/writeback.py:74`
**Issue:** `_KF_ORG = "katty-fashion"` duplicates `utils.ORG` (already imported on
line 56). CLAUDE.md's "no second source of truth" spirit and the inline comment
"matches utils.ORG" both argue for reuse. Drift risk if the org is ever renamed.
**Fix:** `_KF_ORG = ORG` (and then `ORG` is no longer an unused import).

### IN-03: `import traceback`, `import argparse`, `import reconcile` are function-local

**File:** `.claude/skills/activity-sync/writeback.py:354`, `:618-619`, `:475`
**Issue:** `traceback` is imported inside the exception handler, and `argparse` /
`reconcile` / `repo_enum` are imported inside functions. The deferred
`repo_enum`/`reconcile` imports are justified (circular-import avoidance, noted in
comments), but `traceback` and `argparse` are stdlib with no cycle risk and would
read more clearly at module top. Minor style inconsistency with the rest of the
codebase (per CLAUDE.md import-organization convention).
**Fix:** Hoist `traceback` and `argparse` to the module-level import block.

### IN-04: Test suite uses no isolation harness and pollutes the real `MANIFESTS_DIR`

**File:** `.claude/skills/activity-sync/test_writeback.py:1273-1282`, `:1523`
**Issue:** The gitignore test and the continue-after-conflict test write real
files into the canonical `MANIFESTS_DIR` (`.claude/skills/activity-sync/manifests/`)
and the latter does not clean them up (`glob("*.json")` will accumulate across
runs and a stale manifest could make `total_repos=2`/summary assertions flaky if
a prior run left files). The token-leak tests (`_push_to_local`, `_capturing_push`)
re-implement `_push_with_auth` as shims rather than exercising the real function,
so they assert the contract of the *shim*, not the production code path — the real
`_push_with_auth` token-output behavior is never directly tested.
**Fix:** Point manifest tests at a `tempfile.mkdtemp()` dir and clean it up;
assert token-absence against the real `_push_with_auth` by monkeypatching only the
remote URL construction, not the whole function body.

---

_Reviewed: 2026-06-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
