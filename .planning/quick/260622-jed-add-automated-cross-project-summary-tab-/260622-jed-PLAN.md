---
phase: quick-260622-jed
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/sheets_sync.py
  - .github/workflows/aggregate.yml
  - .github/workflows/sync_to_sheets.yml
autonomous: true
requirements: [QSUM-01]
must_haves:
  truths:
    - "sheets_sync.py builds a one-row-per-project portfolio summary purely from docs/_data/loe.yml"
    - "The summary is written to a dedicated 'Summary' tab in a SEPARATE spreadsheet (GSHEET_SUMMARY_ID, defaulting to the R3Group sheet id)"
    - "A Summary failure never blocks Pages, the LOE/gantt sync, or changes the exit code (still 0)"
    - "When GSHEET_SUMMARY_ID or creds are absent, the summary step prints a Warning and returns cleanly"
    - "Both workflows pass GSHEET_SUMMARY_ID to sheets_sync.py alongside the existing GSHEET_* vars"
  artifacts:
    - path: scripts/sheets_sync.py
      provides: "build_summary_rows() rollup + sync_summary_to_sheet() exporter, wired into main()"
      contains: "def sync_summary_to_sheet"
    - path: .github/workflows/aggregate.yml
      provides: "GSHEET_SUMMARY_ID env on the sheets sync step"
      contains: "GSHEET_SUMMARY_ID"
    - path: .github/workflows/sync_to_sheets.yml
      provides: "GSHEET_SUMMARY_ID env on the sheets sync step"
      contains: "GSHEET_SUMMARY_ID"
  key_links:
    - from: "scripts/sheets_sync.py:main()"
      to: "sync_summary_to_sheet()"
      via: "guarded try/except after the gantt sync, inside the exit-0 wrapper"
      pattern: "sync_summary_to_sheet"
    - from: "build_summary_rows()"
      to: "docs/_data/loe.yml rows"
      via: "raw yaml read + canonicalize_status bucketing (no second parser)"
      pattern: "canonicalize_status"
---

<objective>
Add an automated cross-project portfolio "Summary" tab to the R3Group Google Sheet, computed every weekly Sheets run.

Purpose: Give stakeholders a one-glance rollup (per-project task counts by status, % done, total LOE, sprint windows) plus a portfolio grand-total, written to a SEPARATE spreadsheet from the per-task LOE sheet.

Output: A build_summary_rows() + sync_summary_to_sheet() pair in scripts/sheets_sync.py, wired into main() as a third additive, guarded, exit-0-safe sync; GSHEET_SUMMARY_ID env wired into both workflows.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

# The exporter you extend. Study sync_gantt_to_sheet (clear+overwrite pattern,
# create-if-absent, skip-on-no-creds), get_sheets_service, _get_sheet_id,
# write_with_retry, and the exit-0 main() try/except.
@scripts/sheets_sync.py

# Constants + helpers you reuse. TASK_STATUSES = ("Todo","In Progress",
# "Review","Done"). canonicalize_status(s) -> canonical value or None.
# now_iso() for timestamps. LOE_DATA_FILE -> docs/_data/loe.yml.
@scripts/utils.py

<interfaces>
<!-- Contracts the executor needs — no codebase exploration required. -->

From scripts/utils.py:
  TASK_STATUSES = ("Todo", "In Progress", "Review", "Done")
  canonicalize_status(status: str) -> Optional[str]   # canonical value, or None if unknown
  now_iso() -> str
  LOE_DATA_FILE   # Path -> docs/_data/loe.yml

From scripts/sheets_sync.py (existing — reuse, do NOT duplicate):
  get_sheets_service()                          # None if creds/libs absent
  _get_sheet_id(service, spreadsheet_id, title) -> int | None
  write_with_retry(service, spreadsheet_id, range_, values) -> None
  GOOGLE_API_AVAILABLE   # bool
  LOE_DATA_FILE          # imported from utils

loe.yml row schema (the ONLY data source — one parser, one canonical intermediate):
  rows: [ {project, sprint, task, assignee, effort_days, start, end, status} ]

NOTE: status values in loe.yml are RAW, not canonical (e.g. "Decizie pending — P1",
"Decizie pending", "Done", "In Progress"). Bucket via utils.canonicalize_status();
when it returns None, count the task in the project's Total and an "Other" bucket but
NOT in any of the four canonical status columns. effort_days is a float (often 0.0).
start/end are ISO date strings OR junk ('', '—', '~1 lună') — a value counts only if it
matches YYYY-MM-DD; ignore everything else when computing min/max windows.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add config constants + build_summary_rows() rollup (pure, from loe.yml)</name>
  <files>scripts/sheets_sync.py</files>
  <behavior>
    build_summary_rows(loe_rows) takes the RAW loe.yml row dicts and returns a
    list[list] = header + one row per project (alphabetical) + a final grand-total row.
    - Header (15 cols): ["Project","Todo","In Progress","Review","Done","Other","Total","% Done","Total LOE (days)","Current Sprint","Window Start","Window End","Earliest Start","Latest End","Updated"]
    - Test A (canonical bucketing): statuses ["Done","Done","Todo","In Progress","Review"] for one project -> Done=2, Todo=1, In Progress=1, Review=1, Other=0, Total=5, "% Done"=40.0 (Done/Total*100, 1dp).
    - Test B (non-canonical -> Other): status "Decizie pending - P1" -> canonicalize_status returns None -> Other=1, Total=1, four canonical cols = 0, "% Done"=0.0.
    - Test C (LOE sum): effort_days [2.0,3.0,0.0] -> "Total LOE (days)"=5.0.
    - Test D (sprint + windows): ISO starts ["2026-05-25","2026-06-08"], ends ["2026-06-21","2026-07-05"], sprint "S3" -> Current Sprint = modal sprint ("S3"), Window Start = min ISO start, Window End = max ISO end, Earliest Start = min start, Latest End = max end. Non-ISO start/end ('', '—', '~1 lună') ignored; a project with zero ISO dates leaves those four window cells = "".
    - Test E (dynamic projects): project set derived from rows, never hardcoded; rows for {R3-AAS, kf-platform} only -> exactly those two project rows + header + grand total, project rows sorted alphabetically.
    - Test F (grand total): final row label "PORTFOLIO TOTAL", Total = sum of project totals, "% Done" = overall Done/overall Total*100 (1dp), "Total LOE (days)" = sum across projects; sprint/window cols left "".
    - Div-by-zero: any project or the portfolio with Total=0 yields "% Done"=0.0, never raises.
  </behavior>
  <action>
    In scripts/sheets_sync.py add module constants directly after GANTT_HEADER/GANTT_TAB:
      SUMMARY_TAB = "Summary"
      DEFAULT_SUMMARY_SHEET_ID = "11hdbqxDl-9MVEEUovS_jpGJSe52TSy19"   # R3Group sheet — a DIFFERENT spreadsheet from GSHEET_ID
      SUMMARY_HEADER = [...]   the 15-column list from <behavior>
    Add a comment block above DEFAULT_SUMMARY_SHEET_ID stating: the R3Group sheet MUST be SHARED (Editor) with the GSHEET_CLIENT_EMAIL service account for CI writes to land.
    Extend the EXISTING `from utils import ( ... )` block to also import canonicalize_status and TASK_STATUSES — do NOT add a second import statement.
    Add private helper `_is_iso_date(s: str) -> bool` returning True iff s matches r"^\d{4}-\d{2}-\d{2}$" (use a module-level compiled regex, e.g. _ISO_DATE_RE).
    Add `build_summary_rows(loe_rows: list[dict]) -> list[list]`:
      - Computed PURELY from the loe.yml row dicts. Do NOT re-parse kanban.md and do NOT add a second parser — hard project constraint ("one parser, one canonical intermediate"; "never re-parse kanban in sheets_sync").
      - Group by project. Per project accumulate: a count per TASK_STATUSES value plus an "Other" count when canonicalize_status(status) is None; total task count; summed effort_days as float(r.get("effort_days") or 0.0); the modal sprint string; min/max of ISO-valid start and end strings via _is_iso_date.
      - Emit project rows sorted alphabetically by project name, then a "PORTFOLIO TOTAL" row aggregating Total / Done / LOE across all projects (sprint + window cells left "").
      - Shape every row to SUMMARY_HEADER order; put now_iso() in the trailing Updated column.
      - Round percentages to 1 decimal; guard all divisions against zero.
      - This function is PURE: no network, no env reads, no Sheets API — so it is unit-testable offline. Implement after the assertions in <verify> pass.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && python scripts/_summary_selfcheck_task1.py</automated>
    <note>Create a throwaway self-check script scripts/_summary_selfcheck_task1.py with the assertions below, run it, then delete it (it must NOT be committed). Sample input mixes a canonical Done + a non-canonical "Decizie pending - P1" (-> Other) for R3-AAS, and an In Progress + Todo for kf-platform.</note>
    Assertions the self-check MUST make:
      - rows[0] == SUMMARY_HEADER
      - project rows are exactly {R3-AAS, kf-platform} + PORTFOLIO TOTAL
      - R3-AAS: Done==1, Other==1, Total==2, "% Done"==50.0, "Total LOE (days)"==5.0, Window Start=="2026-03-16", Window End=="2026-03-18"
      - kf-platform: "In Progress"==1, Todo==1, "% Done"==0.0, Window Start=="2026-05-25", Window End=="2026-06-21"
      - PORTFOLIO TOTAL: Total==4, "Total LOE (days)"==15.0, "% Done"==25.0
      - project rows sorted alphabetically; final row label == "PORTFOLIO TOTAL"
      - DEFAULT_SUMMARY_SHEET_ID == "11hdbqxDl-9MVEEUovS_jpGJSe52TSy19" and SUMMARY_TAB == "Summary"
  </verify>
  <done>build_summary_rows() returns header + alphabetically-sorted per-project rows + PORTFOLIO TOTAL with correct canonical+Other buckets, % done, summed LOE, modal sprint, ISO-only min/max windows; SUMMARY_TAB / SUMMARY_HEADER / DEFAULT_SUMMARY_SHEET_ID constants present; the self-check script passes and is then removed.</done>
</task>

<task type="auto">
  <name>Task 2: Add sync_summary_to_sheet() and wire it into main() (exit-0 safe)</name>
  <files>scripts/sheets_sync.py</files>
  <action>
    Add `sync_summary_to_sheet(rows: list[list]) -> dict`, modelled EXACTLY on sync_gantt_to_sheet, with two differences: a SEPARATE spreadsheet and the SUMMARY_TAB:
      - sheet_id = os.environ.get("GSHEET_SUMMARY_ID", DEFAULT_SUMMARY_SHEET_ID) — defaults to the R3Group sheet when the env var is unset.
      - Two skip guards mirroring sync_gantt_to_sheet: return {"status":"skipped","row_count": len(rows)-1} when (not sheet_id or not GOOGLE_API_AVAILABLE), and again when get_sheets_service() returns None. The skip Warning must name SUMMARY_TAB and note the target is the separate R3Group sheet.
      - Create-if-absent: if _get_sheet_id(service, sheet_id, SUMMARY_TAB) is None -> batchUpdate addSheet {"title": SUMMARY_TAB}; then values().clear(range=f"{SUMMARY_TAB}!A1:Z10000"); then write_with_retry(service, sheet_id, f"{SUMMARY_TAB}!A1", rows).
      - Return {"status":"ok","row_count": len(rows)-1} with a timing print like the gantt function.
      - Docstring must note: (1) computed purely from loe.yml, (2) targets GSHEET_SUMMARY_ID (a SEPARATE spreadsheet from GSHEET_ID, default = R3Group id), (3) the R3Group sheet MUST be shared (Editor) with the GSHEET_CLIENT_EMAIL service account for writes to land, (4) guarded in main() so a failure never affects LOE/gantt or the exit code.
    In main(), AFTER the existing gantt try/except block and BEFORE `return 0`, add a SEPARATE guarded block mirroring the gantt one:
      try: read raw rows -> payload = yaml.safe_load(LOE_DATA_FILE.read_text()) or {}; loe_rows = payload.get("rows", []); summary_rows = build_summary_rows(loe_rows); summary_result = sync_summary_to_sheet(summary_rows); print a one-line "KF Summary Sync — {status} ({row_count} rows)".
      except Exception as se:  # noqa: BLE001  -> print "Warning: Summary sync failed (non-fatal): {se}" to stderr.
    Read the RAW row dicts directly (do NOT call load_loe_from_yaml — that returns shaped LOE Sheets rows, not the dicts build_summary_rows needs).
    Do NOT touch sync_to_sheets(), sync_gantt_to_sheet(), the outer try/except, or the return-0 behavior.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && python -c "import ast; ast.parse(open('scripts/sheets_sync.py').read()); print('PARSE_OK')" && env -u GSHEET_ID -u GSHEET_SUMMARY_ID -u GSHEET_CLIENT_EMAIL -u GSHEET_PRIVATE_KEY python scripts/sheets_sync.py > /tmp/ss.out 2>&1; echo "EXIT=$?"; grep -qi summary /tmp/ss.out && echo SUMMARY_STEP_RAN || echo MISSING_SUMMARY_LOG</automated>
  </verify>
  <done>sheets_sync.py parses; running it with NO GSHEET_/cred env vars exits 0 (EXIT=0), emits a Summary-related log/Warning line (SUMMARY_STEP_RAN), and never raises — confirming the summary step is wired into main() inside the exit-0 wrapper and skips cleanly without creds.</done>
</task>

<task type="auto">
  <name>Task 3: Wire GSHEET_SUMMARY_ID into both workflows + doc note</name>
  <files>.github/workflows/aggregate.yml, .github/workflows/sync_to_sheets.yml</files>
  <action>
    In .github/workflows/aggregate.yml, on the "Sync LOE to Google Sheets (downstream export)" step's env: block (currently ~lines 98-100: GSHEET_ID / GSHEET_CLIENT_EMAIL / GSHEET_PRIVATE_KEY), add directly after the GSHEET_ID line, at the same indentation:
      GSHEET_SUMMARY_ID: ${{ secrets.GSHEET_SUMMARY_ID }}
    In .github/workflows/sync_to_sheets.yml, on the "Sync to Google Sheets" step's env: block (currently ~lines 55-57), add the same line directly after GSHEET_ID, same indentation.
    Match the existing indentation exactly (env keys sit under env: at step level). Do NOT alter any other env keys, steps, triggers, or the ordering of the Sheets sync after the Pages publish step in aggregate.yml. GSHEET_SUMMARY_ID is optional at runtime (the script defaults to the R3Group id); wiring the secret lets the target sheet be overridden without a code change.
    Doc note: grep README.md and docs/ for an existing GSHEET_ / secrets / Configuration section. If one exists, add a bullet for GSHEET_SUMMARY_ID stating it is the SEPARATE R3Group spreadsheet for the cross-project Summary tab and the sheet must be shared (Editor) with GSHEET_CLIENT_EMAIL. If no such section exists, the docstring added in Task 2 satisfies the documentation requirement — do NOT create a new doc file.
  </action>
  <verify>
    <automated>cd /Users/machina/Dev/kf-cpto && grep -c GSHEET_SUMMARY_ID .github/workflows/aggregate.yml && grep -c GSHEET_SUMMARY_ID .github/workflows/sync_to_sheets.yml && python -c "import yaml; yaml.safe_load(open('.github/workflows/aggregate.yml')); yaml.safe_load(open('.github/workflows/sync_to_sheets.yml')); print('YAML_OK')"</automated>
  </verify>
  <done>Both workflows contain GSHEET_SUMMARY_ID wired onto the Sheets sync step alongside the existing GSHEET_* vars (grep count >= 1 each); both workflow YAML files still parse (YAML_OK). The summary export now runs on every weekly Sheets run via both entry points.</done>
</task>

</tasks>

<verification>
Run from repo root:
1. python scripts/_summary_selfcheck_task1.py prints OK (rollup math correct), then the script is deleted (not committed).
2. python -c "import ast; ast.parse(open('scripts/sheets_sync.py').read())" succeeds.
3. env -u GSHEET_ID -u GSHEET_SUMMARY_ID -u GSHEET_CLIENT_EMAIL -u GSHEET_PRIVATE_KEY python scripts/sheets_sync.py exits 0 and logs a Summary skip line (no creds -> clean skip).
4. grep -c GSHEET_SUMMARY_ID on both workflow files returns >= 1; both YAML files parse.
5. Manual: confirm sheets_sync.py contains no second kanban parser and reads only loe.yml for the summary (grep -n "kanban" scripts/sheets_sync.py returns nothing new).
</verification>

<success_criteria>
- A cross-project Summary (one row per project + PORTFOLIO TOTAL) is computed purely from docs/_data/loe.yml — no second parser, kanban.md never re-read.
- The Summary writes to a dedicated "Summary" tab in the SEPARATE R3Group spreadsheet (GSHEET_SUMMARY_ID, default 11hdbqxDl-9MVEEUovS_jpGJSe52TSy19), create-if-absent then overwrite, mirroring sync_gantt_to_sheet.
- Per-project columns: Todo/In Progress/Review/Done/Other counts, Total, % Done, Total LOE (days), Current Sprint, window start/end, earliest start, latest end. Final PORTFOLIO TOTAL row: total tasks, overall % done, total LOE.
- Projects derived dynamically from loe.yml rows (not hardcoded).
- The summary sync is guarded in main() AFTER the gantt sync, inside the exit-0 wrapper: a Summary failure never blocks Pages or changes the exit code; missing GSHEET_SUMMARY_ID/creds -> clean Warning + return.
- GSHEET_SUMMARY_ID wired into both aggregate.yml and sync_to_sheets.yml; sharing requirement documented in the docstring (and config docs if present).
- Naming conventions honored: SCREAMING_SNAKE_CASE constants, snake_case functions, type hints on new signatures.
</success_criteria>

<output>
Create .planning/quick/260622-jed-add-automated-cross-project-summary-tab-/260622-jed-SUMMARY.md when done.
</output>
