---
phase: quick-260622-jed
plan: "01"
subsystem: sheets-export
tags: [sheets, rollup, portfolio, loe, summary]

dependency_graph:
  requires:
    - docs/_data/loe.yml (canonical intermediate written by aggregator.py)
  provides:
    - scripts/sheets_sync.py:build_summary_rows() — pure rollup function
    - scripts/sheets_sync.py:sync_summary_to_sheet() — portfolio Summary tab writer
  affects:
    - .github/workflows/aggregate.yml (GSHEET_SUMMARY_ID env added)
    - .github/workflows/sync_to_sheets.yml (GSHEET_SUMMARY_ID env added)

tech_stack:
  added: []
  patterns:
    - "Pure rollup function (build_summary_rows): no network, no env reads — offline-testable"
    - "Additive guarded try/except in main() after gantt sync — preserves exit-0 invariant"
    - "Create-if-absent + clear + overwrite pattern (mirrors sync_gantt_to_sheet)"
    - "canonicalize_status() bucketing: unknown values flow to Other, never silently dropped"
    - "_ISO_DATE_RE compiled module-level regex for ISO-only window computation"

key_files:
  modified:
    - scripts/sheets_sync.py
    - .github/workflows/aggregate.yml
    - .github/workflows/sync_to_sheets.yml
    - README.md
  created: []

decisions:
  - "Read raw loe.yml dicts in main() directly (not load_loe_from_yaml which returns shaped Sheets rows) so build_summary_rows gets the original dict fields"
  - "GSHEET_SUMMARY_ID defaults to DEFAULT_SUMMARY_SHEET_ID in sync_summary_to_sheet, not just in main() — so the function itself is testable without env setup"
  - "PORTFOLIO TOTAL row leaves per-status counts empty (not per-bucket sums) to keep the row shape unambiguous — only Total / Done / LOE aggregated at portfolio level"

metrics:
  duration: "~15 min"
  completed: "2026-06-22"
  tasks_completed: 3
  files_changed: 4
---

# Quick Task 260622-jed: Add Automated Cross-Project Summary Tab

**One-liner:** Portfolio summary rollup (per-project task counts by status, % done, total LOE) written to a dedicated Summary tab in the R3Group Google Sheet, computed purely from `docs/_data/loe.yml` every weekly Sheets run.

## What Was Built

### Task 1 — Summary constants + `build_summary_rows()` rollup (commit `b426f4d`)

Added to `scripts/sheets_sync.py`:

- Extended existing `from utils import (...)` block to include `TASK_STATUSES` and `canonicalize_status` (no second import statement).
- Module-level constants: `SUMMARY_TAB = "Summary"`, `DEFAULT_SUMMARY_SHEET_ID` (R3Group sheet id), `SUMMARY_HEADER` (15 columns).
- `_ISO_DATE_RE` compiled regex and `_is_iso_date(s)` helper for window computation.
- `build_summary_rows(loe_rows: list[dict]) -> list[list]`: pure function (no network, no env, no Sheets API). Groups rows by project, buckets status via `canonicalize_status()` with unknown values flowing to "Other", accumulates `effort_days`, computes modal sprint, ISO-only min/max windows, outputs header + alpha-sorted project rows + PORTFOLIO TOTAL row.
- All self-check assertions passed; script deleted before commit (not committed).

### Task 2 — `sync_summary_to_sheet()` + `main()` wiring (commit `13a179b`)

- Added `sync_summary_to_sheet(rows: list[list]) -> dict`: mirrors `sync_gantt_to_sheet` pattern; targets `GSHEET_SUMMARY_ID` (separate spreadsheet); create-if-absent + clear + overwrite; two skip guards (missing sheet_id/GOOGLE_API_AVAILABLE, then no service) that each print a Warning naming SUMMARY_TAB and the R3Group context.
- Wired into `main()` AFTER the gantt try/except, inside its own `try/except Exception as se:  # noqa: BLE001` block; reads raw `loe.yml` dicts directly (not `load_loe_from_yaml`); a failure prints `Warning: Summary sync failed (non-fatal): {se}` to stderr and never changes exit code or blocks LOE/gantt/sync_status.
- Offline verification: `python scripts/sheets_sync.py` with no GSHEET_/credential env vars exits 0 and logs "KF Summary Sync — skipped (N rows)".

### Task 3 — GSHEET_SUMMARY_ID wired into both workflows + README doc (commit `5284368`)

- `aggregate.yml`: added `GSHEET_SUMMARY_ID: ${{ secrets.GSHEET_SUMMARY_ID }}` directly after `GSHEET_ID` on the Sheets sync step env block (exact indentation preserved).
- `sync_to_sheets.yml`: same addition on the "Sync to Google Sheets" step env block.
- `README.md`: added `GSHEET_SUMMARY_ID` row to the Secrets table noting it targets the SEPARATE R3Group spreadsheet and the sheet must be shared (Editor) with `GSHEET_CLIENT_EMAIL`.
- Both workflow YAML files parse cleanly (`YAML_OK`); grep count >= 1 in each file.

## Verification Results

```
AST_OK                          # sheets_sync.py parses cleanly
EXIT=0                          # no-creds run exits 0
SUMMARY_STEP_RAN                # Summary step present in output
1                               # GSHEET_SUMMARY_ID count in aggregate.yml
1                               # GSHEET_SUMMARY_ID count in sync_to_sheets.yml
YAML_OK                         # both workflow YAML files parse
No kanban references (clean)    # no second kanban parser introduced
```

## Deviations from Plan

None. Plan executed exactly as written.

## Known Stubs

None. `build_summary_rows()` is fully wired to real `loe.yml` data. The Summary tab is skipped cleanly when credentials are absent (not stubbed with placeholder data).

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries were introduced. `sync_summary_to_sheet` uses the same credential path (`get_sheets_service()`) as all existing Sheets write functions.

## Self-Check

- [x] `scripts/sheets_sync.py` modified and committed (`b426f4d`, `13a179b`)
- [x] `.github/workflows/aggregate.yml` modified and committed (`5284368`)
- [x] `.github/workflows/sync_to_sheets.yml` modified and committed (`5284368`)
- [x] `README.md` modified and committed (`5284368`)
- [x] Self-check script ran, all assertions passed, script deleted (not committed)
- [x] Offline no-creds run: EXIT=0, SUMMARY_STEP_RAN

## Self-Check: PASSED
