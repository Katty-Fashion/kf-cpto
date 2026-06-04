# Codebase Concerns

**Analysis Date:** 2026-06-04

## Tech Debt

**Unpinned CI dependencies:**
- Issue: Both workflows install Python packages with `pip install pyyaml requests google-auth google-api-python-client` — no version constraints, no `requirements.txt` reference, and no pip cache. A breaking upstream release will silently break the entire pipeline on the next run.
- Files: `.github/workflows/aggregate.yml` (line 33), `.github/workflows/sync_to_sheets.yml` (line 25)
- Impact: Silent breakage on any transitive version bump. The venv in `venv/` pins to Python 3.9; CI uses 3.11.
- Fix approach: Add `--requirement requirements.txt` with pinned versions, or generate a `requirements-lock.txt` via `pip-compile` and reference it in both workflows.

**Unpinned GitHub Actions versions:**
- Issue: All actions use floating major-version tags (`actions/checkout@v4`, `actions/setup-python@v5`, `peaceiris/actions-gh-pages@v4`). SHA pinning is the standard for supply-chain security.
- Files: `.github/workflows/aggregate.yml` (lines 24, 28, 70), `.github/workflows/sync_to_sheets.yml` (lines 16, 20)
- Impact: Compromise of an action at that major tag silently affects all runs.
- Fix approach: Pin each action to its full SHA (e.g., `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`) and comment the version for readability.

**`sync_to_sheets.yml` re-runs discover + clone unnecessarily:**
- Issue: The standalone `sync_to_sheets.yml` workflow runs `discover.py` and clones all repos to produce data that `sheets_sync.py` no longer needs — `sheets_sync.py` only reads `docs/_data/loe.yml`, which is already committed by `aggregate.yml`.
- Files: `.github/workflows/sync_to_sheets.yml` (lines 28–42), `scripts/sheets_sync.py` (lines 63–89)
- Impact: Wasted ~2 min of runner time per daily run, plus unnecessary GitHub API calls consuming rate-limit quota. If `loe.yml` is stale or missing the standalone run will silently produce wrong data.
- Fix approach: Remove the discover + clone steps from `sync_to_sheets.yml`; the job only needs checkout + `pip install` + `python scripts/sheets_sync.py`.

**Hard-coded "Status: Active" on every project page:**
- Issue: `generate_project_page()` unconditionally writes `| Status | Active |` regardless of any project-level status field in the kanban frontmatter.
- Files: `scripts/aggregator.py` (line 273)
- Impact: Archived or stalled projects are permanently shown as "Active" on the dashboard.
- Fix approach: Add an optional `status` key to `FRONTMATTER_DEFAULTS` in `utils.py` and render it in the table, defaulting to `"Active"`.

**`venv/` committed to repository:**
- Issue: The `venv/` directory (Python 3.9 virtualenv with ~200 MB of site-packages) is present in the repo. `.gitignore` lists `venv/` but the directory exists locally alongside a `__pycache__` that was checked in (`scripts/__pycache__/utils.cpython-310.pyc`).
- Files: `venv/` (root), `scripts/__pycache__/utils.cpython-310.pyc`
- Impact: Bloats local clone size; `.pyc` file was compiled under Python 3.10, while CI uses 3.11 and the local venv targets 3.9 — inconsistency risk. The `__pycache__` file should never be committed.
- Fix approach: Confirm `venv/` and `__pycache__/` are in `.gitignore` (they are), then `git rm --cached` the committed `.pyc` file. Verify no `venv/` artifacts are tracked.

**`docs/_site/` present locally but not gitignored at correct level:**
- Issue: `.gitignore` includes `_site/` (bare path), which Jekyll resolves relative to the repo root. The actual build output sits at `docs/_site/`. The `_site/` pattern does not match `docs/_site/` in git's pathspec rules unless the project root is also the Jekyll root.
- Files: `.gitignore` (line 28), `docs/_site/`
- Impact: Risk of accidentally committing built HTML to the source branch — could expose stale build artifacts and inflate repo size.
- Fix approach: Add `docs/_site/` explicitly to `.gitignore`.

**`activity/` directory in `.gitignore` but tracked content visible:**
- Issue: `.gitignore` has `activity/` listed, yet `activity/` files appear in the working tree (visible in `git ls-files` output for prior commits). If any were committed before the ignore was added they remain tracked.
- Files: `.gitignore` (line 68), `activity/`
- Impact: Personal activity logs containing contributor names and email handles could leak if the repo ever goes public.
- Fix approach: Run `git rm -r --cached activity/` and commit to stop tracking those files.

---

## Security Considerations

**Mermaid `securityLevel: 'loose'`:**
- Risk: The dashboard layout initializes Mermaid with `securityLevel: 'loose'`, which allows arbitrary HTML inside Mermaid diagram nodes. Task names from kanban.md files are injected verbatim into Mermaid node labels without escaping in `aggregator.py` (e.g., lines 89, 307, 372). A malicious or accidental task name containing `<script>` or an HTML event handler would execute in any visitor's browser.
- Files: `docs/_layouts/default.html` (line 59), `scripts/aggregator.py` (lines 89, 307, 372)
- Current mitigation: The dashboard is only accessible to the org (GitHub Pages on a private org, or login-gated). No sanitization is applied.
- Recommendations: Change `securityLevel` to `'strict'` (default) or `'antiscript'`. If rich HTML in diagram nodes is needed, sanitize task names before injection (strip `<`, `>`, `"` and `'`).

**PAT used as git HTTPS credential in workflow logs:**
- Risk: The clone step in both workflows inlines `secrets.KF_PAT` into the git URL: `https://${{ secrets.KF_PAT }}@github.com/...`. GitHub masks the token value in logs, but the URL form exposes it to any process that reads `git remote -v` or inspects the git config on the runner.
- Files: `.github/workflows/aggregate.yml` (line 50), `.github/workflows/sync_to_sheets.yml` (line 39)
- Current mitigation: GitHub Actions secrets masking.
- Recommendations: Use the `actions/checkout` credential helper pattern or `gh auth` instead of inline URL credentials. Alternatively, configure `git config --global url."https://x-access-token:${KF_PAT}@github.com/".insteadOf "https://github.com/"` before cloning so the token never appears in remote URLs.

**Google service account private key passed as plain env var:**
- Risk: `GSHEET_PRIVATE_KEY` is passed as a raw env var containing the RSA private key PEM. If the runner emits error tracebacks that include the environment, the key could leak.
- Files: `.github/workflows/aggregate.yml` (lines 83–86), `scripts/sheets_sync.py` (line 104)
- Current mitigation: GitHub Actions secrets masking, `private_key.replace("\\n", "\n")` in script.
- Recommendations: Store the full service account JSON as a single secret (base64-encoded), decode it in the script, and pass it to `from_service_account_info()` to avoid the `\n` → newline fragility.

---

## Performance Bottlenecks

**Sequential kanban discovery (N+1 HTTP calls):**
- Problem: `discover.py` fetches all repos in a loop and then makes one HTTP `GET` per repo to check for `kanban.md`. With 10 active repos this is 10 sequential requests; the org already has enough repos that discovery saturates its log output.
- Files: `scripts/discover.py` (lines 59–70)
- Cause: GitHub Contents API is called one repo at a time with no parallelism.
- Improvement path: Use `concurrent.futures.ThreadPoolExecutor` to check 5–10 repos in parallel; or use the Search API (`GET /search/code?q=filename:kanban.md+org:katty-fashion`) to find all repos with a single call.

**No pip cache in CI:**
- Problem: Both workflows install all Python packages from scratch on every run (`pip install pyyaml requests google-auth google-api-python-client`) with no `cache:` step.
- Files: `.github/workflows/aggregate.yml` (line 33), `.github/workflows/sync_to_sheets.yml` (line 25)
- Cause: Missing `actions/setup-python` cache key.
- Improvement path: Add `cache: 'pip'` to the `actions/setup-python` step and reference a pinned `requirements.txt`. This saves ~15–30 seconds per run.

---

## Fragile Areas

**`parse_kanban_tasks` regex: greedy match on separator rows:**
- Files: `scripts/utils.py` (lines 161–197)
- Why fragile: The separator row filter (`if first in ("Task", ":---") or first.startswith(":")`) only checks the first column. A separator row that starts with a non-colon value (e.g., if someone puts a label column first) would be mistakenly treated as a task row. The same regex matches any 4- or 6-column table in the file, including prose tables that aren't the task table.
- Safe modification: Add a sentinel header match (look for the specific header text "Task | Assignee | Effort") before entering the loop.
- Test coverage: Zero automated tests exist for this parsing logic.

**`parse_kanban_tasks` 6-column detection by pipe count:**
- Files: `scripts/utils.py` (lines 157–163)
- Why fragile: Format detection counts the number of `|` characters in the first table header row. If a task name or column header happens to contain `|` (e.g., a pipe character in a URL), the column count will misfire and assign fields to the wrong columns.
- Safe modification: Match headers by name (`"Start" in header_row` and `"End" in header_row`) rather than pipe count.
- Test coverage: None.

**Auto-block marker pairing assumes document order:**
- Files: `scripts/auto_blocks.py` (lines 136–163)
- Why fragile: `find_marker_pairs()` pairs opens and closes by zip-in-order. If a page has two different auto-block types, the pairing assumes opens and closes appear in matched order. A misplaced close marker would silently pair with the wrong open marker, corrupting the page.
- Safe modification: Pair by explicit name lookup — find the close marker whose name matches each open marker.
- Test coverage: None.

**`write_loe_yaml` overwrites file non-atomically:**
- Files: `scripts/aggregator.py` (lines 514–522)
- Why fragile: `LOE_DATA_FILE.write_text(...)` writes in place. If the aggregator crashes mid-write, `loe.yml` will be truncated, causing `sheets_sync.py` to raise `FileNotFoundError` or parse corrupt YAML on the next run.
- Safe modification: Write to a `.tmp` file first, then `os.replace()` it into place (atomic rename on the same filesystem).

**Gantt cursor auto-scheduling ignores non-business days:**
- Files: `scripts/aggregator.py` (lines 386–391)
- Why fragile: When advancing the cursor for auto-scheduled tasks, the code adds calendar days (`timedelta(days=int(effort_d))`), not business days. A 1d task starting on a Friday will schedule the next task to start on a Saturday, producing an invalid Mermaid date.
- Safe modification: Advance by business days (skip weekends) or use the existing `excludes weekends` Mermaid directive and accept the visual offset.

---

## Known Bugs

**`test_r3group` file in `docs/_projects/`:**
- Symptoms: A file named `test_r3group` (no `.md` extension) exists in `docs/_projects/`. Jekyll will attempt to process it as a collection document. Without a proper extension or frontmatter, it may cause a Jekyll build warning or appear as a broken project entry.
- Files: `docs/_projects/test_r3group`
- Trigger: Present on every aggregator run that doesn't clean the directory.
- Workaround: The file appears to be a raw kanban.md copy — delete it or rename with `.md` extension and proper frontmatter.

**Dashboard "Current Sprint Overview" Gantt is static:**
- Symptoms: `docs/index.md` contains a hard-coded Mermaid Gantt block for "Sprint 3" with dates in March 2026. As of June 2026 this is three sprints behind.
- Files: `docs/index.md` (lines 58–68)
- Trigger: No aggregator logic writes to `index.md`; the block is manually maintained prose.
- Workaround: The per-project pages and unified calendar are accurate. The index Gantt is only misleading, not breaking.

**Dependency links in generated project pages use raw Liquid syntax:**
- Symptoms: Lines like `[ai-rise]({{ '/projects/ai-rise/' | relative_url }})` appear in `docs/_projects/*.md` files. These render correctly when processed by Jekyll, but the raw `.md` files viewed on GitHub or in editors will show the unexpanded Liquid tag as literal text.
- Files: `docs/_projects/Edi-test.md` (line 25), `docs/_projects/R3GROUP.md` (line 25), and several others
- Trigger: `generate_project_page()` in `scripts/aggregator.py` (lines 248–251) injects Liquid syntax into generated markdown.
- Workaround: No production impact for the Pages site. For raw-file readability, use the absolute URL form or a relative path instead of a Liquid filter.

---

## Test Coverage Gaps

**Zero automated tests for all scripts:**
- What's not tested: All parsing logic in `scripts/utils.py` (`parse_kanban_tasks`, `parse_kanban_frontmatter`, `parse_effort_days`, `normalize_frontmatter`), all rendering logic in `scripts/aggregator.py` and `scripts/auto_blocks.py`, and the sheets sync staging/swap/validation pipeline in `scripts/sheets_sync.py`.
- Files: `scripts/` (all five `.py` files)
- Risk: Regressions in kanban parsing silently corrupt the entire dashboard output. The auto-block injection logic (`inject_auto_blocks`, `find_marker_pairs`) has several edge cases (nested markers, mismatched names, missing context keys) that only surface during a full aggregator run.
- Priority: High — `parse_kanban_tasks` and `parse_effort_days` are the most critical paths; add unit tests with fixture `.md` files (4-col, 6-col, edge cases) first.

**No integration or end-to-end test for the aggregation pipeline:**
- What's not tested: The full `aggregator.py` → `loe.yml` → `sheets_sync.py` pipeline is never exercised in CI except during actual production runs.
- Files: `scripts/aggregator.py`, `scripts/sheets_sync.py`
- Risk: A breaking change in one script may not surface until the Monday 04:00 UTC scheduled run.
- Priority: Medium — a simple smoke test that runs `aggregator.py` against fixture repos and asserts the output files are valid YAML/Markdown would catch most regressions.

---

## Missing Critical Features

**No staleness check on `loe.yml`:**
- Problem: `sheets_sync.py` trusts `docs/_data/loe.yml` unconditionally. If the aggregator has not run for an extended period, the Sheets export will push stale data without warning.
- Blocks: Accurate Sheets export when the pipeline runs out of order (e.g., manual `sync_to_sheets.yml` trigger before `aggregate.yml` has run).
- Files: `scripts/sheets_sync.py` (lines 63–89)

**No alerting when discover.py returns zero repos:**
- Problem: `discover.py` prints a warning but does not exit non-zero when no repos are found. The aggregator will then produce empty dashboard pages without surfacing a failure.
- Files: `scripts/discover.py` (lines 87–91), `scripts/aggregator.py` (line 541)

**No lock / concurrency guard on workflow runs:**
- Problem: Both `aggregate.yml` and `sync_to_sheets.yml` can run simultaneously (e.g., a `push` event triggers `aggregate.yml` while the daily cron fires `sync_to_sheets.yml`). There is no concurrency group preventing overlapping runs from producing interleaved commits or Sheets writes.
- Files: `.github/workflows/aggregate.yml`, `.github/workflows/sync_to_sheets.yml`
- Fix approach: Add a `concurrency:` key to both workflows with `cancel-in-progress: false` to queue rather than cancel runs.

---

*Concerns audit: 2026-06-04*
