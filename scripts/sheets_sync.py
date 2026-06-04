#!/usr/bin/env python3
"""
Google Sheets Sync — Downstream LOE Export

Reads canonical LOE data from docs/_data/loe.yml (written by aggregator.py)
and exports it to a Google Sheet for upstream stakeholders.

Design properties:
  - Pages-first: this script runs AFTER GH Pages publishes. A failure here
    never blanks the team's primary dashboard.
  - Shadow-tab swap: new data is staged in `LOE_staging`, validated, then
    atomically swapped with `LOE` (renamed `LOE` -> `LOE_prev_<ts>`).
    If anything fails, the live `LOE` tab is untouched.
  - User-notes preservation: any columns J+ in the existing `LOE` tab are
    preserved per (Project, Task) composite key.
  - Never crashes the workflow: all failures are caught, surfaced via a
    `sync-failure` GitHub issue, and recorded in docs/_data/sync_status.yml.
    Exit code is 0 even on failure — the workflow proceeds.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

import yaml

from utils import (
    GANTT_DATA_FILE,
    LOE_DATA_FILE,
    now_compact,
    now_iso,
    update_sync_status,
)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("Warning: Google API libraries not installed. Running in dry-run mode.")

LOE_HEADER = [
    "Project", "Sprint", "Task", "Assignee", "Effort (days)",
    "Start", "End", "Status", "Updated",
]
EXPECTED_COL_COUNT = len(LOE_HEADER)
LIVE_TAB = "LOE"
STAGING_TAB = "LOE_staging"
GANTT_TAB = "Gantt_example"
GANTT_HEADER = [
    "Phase", "Task", "Discipline", "Start", "End", "Effort (days)", "Type", "Updated",
]
BACKUP_PREFIX = "LOE_prev_"
BACKUPS_TO_KEEP = 3
MAX_WRITE_RETRIES = 3


# --------------------------------------------------------------------------- #
# Data loading                                                                 #
# --------------------------------------------------------------------------- #

def load_loe_from_yaml() -> list[list]:
    """Read canonical LOE data from docs/_data/loe.yml and shape into Sheets rows.

    Returns the full payload including the header row. Raises if the file
    is missing — that means the aggregator never ran, which is a real failure
    worth surfacing.
    """
    if not LOE_DATA_FILE.exists():
        raise FileNotFoundError(
            f"{LOE_DATA_FILE} missing — run aggregator.py first."
        )
    payload = yaml.safe_load(LOE_DATA_FILE.read_text()) or {}
    rows = [LOE_HEADER]
    updated = payload.get("generated_at", now_iso())
    for r in payload.get("rows", []):
        rows.append([
            r.get("project", ""),
            r.get("sprint", "-"),
            r.get("task", ""),
            r.get("assignee", ""),
            r.get("effort_days", 0),
            r.get("start", ""),
            r.get("end", ""),
            r.get("status", ""),
            updated,
        ])
    return rows


def load_gantt_from_yaml() -> list[list]:
    """Read canonical migration-gantt data from docs/_data/gantt.yml into Sheets rows.

    Returns header + data rows for the Gantt_example tab. Returns just the header
    if the file is absent (gantt is an additive, non-critical export — its absence
    must never fail the LOE sync).
    """
    rows = [GANTT_HEADER]
    if not GANTT_DATA_FILE.exists():
        print(f"Warning: {GANTT_DATA_FILE} missing — Gantt_example tab will not be updated.")
        return rows
    payload = yaml.safe_load(GANTT_DATA_FILE.read_text()) or {}
    updated = payload.get("generated_at", now_iso())
    for r in payload.get("rows", []):
        rows.append([
            r.get("phase", ""),
            r.get("task", ""),
            r.get("discipline", ""),
            r.get("start", ""),
            r.get("end", ""),
            r.get("effort_days", 0),
            r.get("type", "task"),
            updated,
        ])
    return rows


# --------------------------------------------------------------------------- #
# Sheets API helpers                                                           #
# --------------------------------------------------------------------------- #

def get_sheets_service():
    if not GOOGLE_API_AVAILABLE:
        return None
    client_email = os.environ.get("GSHEET_CLIENT_EMAIL")
    private_key = os.environ.get("GSHEET_PRIVATE_KEY")
    if not client_email or not private_key:
        print("Warning: Google Sheets credentials not configured")
        return None
    private_key = private_key.replace("\\n", "\n")
    credentials_info = {
        "type": "service_account",
        "client_email": client_email,
        "private_key": private_key,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=credentials)


def _get_sheet_id(service, spreadsheet_id: str, title: str) -> int | None:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == title:
            return s["properties"]["sheetId"]
    return None


def _list_backup_tabs(service, spreadsheet_id: str) -> list[tuple[str, int]]:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    out = []
    for s in meta.get("sheets", []):
        title = s["properties"]["title"]
        if title.startswith(BACKUP_PREFIX):
            out.append((title, s["properties"]["sheetId"]))
    out.sort(key=lambda x: x[0])  # ts suffix is lexically sortable
    return out


def ensure_staging_tab(service, spreadsheet_id: str) -> int:
    """Make sure LOE_staging exists and is empty. Returns its sheetId."""
    staging_id = _get_sheet_id(service, spreadsheet_id, STAGING_TAB)
    if staging_id is None:
        body = {"requests": [{"addSheet": {"properties": {"title": STAGING_TAB}}}]}
        resp = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()
        staging_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
    else:
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=f"{STAGING_TAB}!A1:Z10000"
        ).execute()
    return staging_id


def read_existing_notes(service, spreadsheet_id: str) -> dict[tuple, list]:
    """Read columns J+ from the live LOE tab, keyed by (project, task).

    Returns empty dict if LOE doesn't exist yet (first run).
    """
    if _get_sheet_id(service, spreadsheet_id, LIVE_TAB) is None:
        return {}
    existing = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"{LIVE_TAB}!A1:Z10000"
    ).execute().get("values", [])
    notes = {}
    for erow in existing[1:]:  # skip header
        if len(erow) < 3:
            continue
        key = (erow[0], erow[2])
        extras = erow[9:] if len(erow) > 9 else []
        if any((cell or "").strip() for cell in extras):
            notes[key] = extras
    return notes


def write_with_retry(service, spreadsheet_id: str, range_: str, values: list[list]) -> None:
    delay = 1.0
    last_err = None
    for attempt in range(1, MAX_WRITE_RETRIES + 1):
        try:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_,
                valueInputOption="RAW",
                body={"values": values},
            ).execute()
            return
        except Exception as e:  # noqa: BLE001 — Google API can raise many concrete types
            last_err = e
            print(f"  write attempt {attempt}/{MAX_WRITE_RETRIES} failed: {e}")
            if attempt < MAX_WRITE_RETRIES:
                time.sleep(delay)
                delay *= 2
    raise RuntimeError(f"write failed after {MAX_WRITE_RETRIES} attempts: {last_err}")


def validate_staged(service, spreadsheet_id: str, expected_row_count: int) -> None:
    """Read back the staging tab and confirm shape. Raises on mismatch."""
    resp = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"{STAGING_TAB}!A1:Z1"
    ).execute()
    header = (resp.get("values") or [[]])[0]
    if header[:EXPECTED_COL_COUNT] != LOE_HEADER:
        raise RuntimeError(
            f"staging header mismatch — got {header[:EXPECTED_COL_COUNT]}, "
            f"expected {LOE_HEADER}"
        )
    resp2 = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"{STAGING_TAB}!A1:A10000"
    ).execute()
    actual = len(resp2.get("values", []))
    if actual != expected_row_count:
        raise RuntimeError(
            f"staging row count mismatch — got {actual}, expected {expected_row_count}"
        )


def swap_staging_into_live(service, spreadsheet_id: str) -> str:
    """Atomically rename: LOE -> LOE_prev_<ts>, LOE_staging -> LOE.

    Returns the new backup tab name. If LOE doesn't exist yet (first run),
    just promotes staging to LOE.
    """
    staging_id = _get_sheet_id(service, spreadsheet_id, STAGING_TAB)
    if staging_id is None:
        raise RuntimeError(f"{STAGING_TAB} missing — cannot swap")
    live_id = _get_sheet_id(service, spreadsheet_id, LIVE_TAB)
    backup_name = f"{BACKUP_PREFIX}{now_compact()}"
    requests = []
    if live_id is not None:
        requests.append({"updateSheetProperties": {
            "properties": {"sheetId": live_id, "title": backup_name},
            "fields": "title",
        }})
    requests.append({"updateSheetProperties": {
        "properties": {"sheetId": staging_id, "title": LIVE_TAB},
        "fields": "title",
    }})
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()
    return backup_name


def cleanup_old_backups(service, spreadsheet_id: str, keep: int = BACKUPS_TO_KEEP) -> int:
    """Delete LOE_prev_* tabs beyond the newest `keep`. Returns count deleted."""
    backups = _list_backup_tabs(service, spreadsheet_id)
    if len(backups) <= keep:
        return 0
    to_delete = backups[:-keep]
    requests = [{"deleteSheet": {"sheetId": sid}} for _, sid in to_delete]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()
    return len(to_delete)


# --------------------------------------------------------------------------- #
# Failure surfacing                                                            #
# --------------------------------------------------------------------------- #

def file_sync_failure_issue(error_msg: str) -> str | None:
    """File a sync-failure issue in this repo. Best-effort: silent on failure
    so a missing gh CLI / token never blocks the workflow.

    Returns the issue URL if successful, None otherwise.
    """
    if not os.environ.get("GH_TOKEN") and not os.environ.get("GITHUB_TOKEN"):
        print("  (no GH_TOKEN/GITHUB_TOKEN — skipping issue creation)")
        return None
    run_url = ""
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if repo and run_id:
        run_url = f"{server}/{repo}/actions/runs/{run_id}"
    body = (
        f"Sheets export failed at {now_iso()}.\n\n"
        f"**Error:**\n```\n{error_msg}\n```\n\n"
        f"**Workflow run:** {run_url or '(local run)'}\n\n"
        f"The live `LOE` tab was **not** modified — staged data did not pass "
        f"validation or the swap step failed. The team's primary dashboard "
        f"(GH Pages) is unaffected.\n\n"
        f"_Filed automatically by `scripts/sheets_sync.py`._"
    )
    title = f"Sheets sync failed at {now_iso()}"
    try:
        result = subprocess.run(
            ["gh", "issue", "create",
             "--label", "sync-failure",
             "--title", title,
             "--body", body],
            check=False, capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            url = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
            print(f"  filed issue: {url}")
            return url
        print(f"  gh issue create failed: {result.stderr.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"  could not invoke gh CLI: {e}")
    return None


def notify_chat(text: str) -> None:
    """Optional Google Chat webhook ping. Reuses GOOGLE_CHAT_WEBHOOK already
    configured in the workflow for build summaries. Silent if unset."""
    webhook = os.environ.get("GOOGLE_CHAT_WEBHOOK")
    if not webhook:
        return
    try:
        import requests
        requests.post(webhook, json={"text": text}, timeout=10)
    except Exception as e:  # noqa: BLE001
        print(f"  chat notify failed: {e}")


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #

def sync_to_sheets(rows: list[list]) -> dict:
    """Stage, validate, swap. Returns a status dict for sync_status.yml."""
    started_at = time.monotonic()
    sheet_id = os.environ.get("GSHEET_ID")
    if not sheet_id:
        print("Warning: GSHEET_ID not configured. Printing data instead:")
        for row in rows:
            print("\t".join(str(cell) for cell in row))
        return {
            "last_run_at": now_iso(),
            "last_run_status": "skipped",
            "row_count": len(rows) - 1,
            "duration_seconds": round(time.monotonic() - started_at, 2),
            "last_error": None,
        }

    service = get_sheets_service()
    if not service:
        print("Dry run — would sync the following data:")
        for row in rows:
            print("\t".join(str(cell) for cell in row))
        return {
            "last_run_at": now_iso(),
            "last_run_status": "skipped",
            "row_count": len(rows) - 1,
            "duration_seconds": round(time.monotonic() - started_at, 2),
            "last_error": None,
        }

    # 1. Preserve user notes (cols J+) from the live LOE tab.
    notes_map = read_existing_notes(service, sheet_id)
    print(f"Preserving user notes for {len(notes_map)} tasks")

    # 2. Merge notes onto fresh rows.
    merged = [rows[0]]
    for row in rows[1:]:
        key = (row[0], row[2])
        extras = notes_map.get(key, [])
        merged.append(row + extras)

    # 3. Stage to LOE_staging.
    ensure_staging_tab(service, sheet_id)
    write_with_retry(service, sheet_id, f"{STAGING_TAB}!A1", merged)

    # 4. Validate the staged tab matches expectations.
    validate_staged(service, sheet_id, expected_row_count=len(merged))

    # 5. Atomic swap.
    backup_name = swap_staging_into_live(service, sheet_id)
    print(f"Swapped {STAGING_TAB} -> {LIVE_TAB} (previous LOE preserved as {backup_name})")

    # 6. Cleanup old rolling backups.
    deleted = cleanup_old_backups(service, sheet_id)
    if deleted:
        print(f"Cleaned up {deleted} old {BACKUP_PREFIX}* backup tab(s)")

    duration = round(time.monotonic() - started_at, 2)
    print(f"Synced {len(merged) - 1} data rows in {duration}s")
    return {
        "last_run_at": now_iso(),
        "last_run_status": "ok",
        "row_count": len(merged) - 1,
        "duration_seconds": duration,
        "last_error": None,
    }


def sync_gantt_to_sheet(rows: list[list]) -> dict:
    """Write the migration gantt to the Gantt_example tab (clear + overwrite).

    Simpler than the LOE shadow-swap: Gantt_example is a derived/reference tab
    (no user notes to preserve), so a clear-then-write is sufficient. Creates the
    tab if absent. Skips cleanly (no creds / no GSHEET_ID) and is called inside
    its own guard in main(), so it never affects the LOE sync or the exit code.
    """
    started_at = time.monotonic()
    data_rows = len(rows) - 1
    sheet_id = os.environ.get("GSHEET_ID")
    if not sheet_id or not GOOGLE_API_AVAILABLE:
        print(f"Gantt sync skipped (no GSHEET_ID/creds) — {data_rows} rows would go to {GANTT_TAB}")
        return {"status": "skipped", "row_count": data_rows}
    service = get_sheets_service()
    if not service:
        print(f"Gantt sync skipped (no service) — {data_rows} rows would go to {GANTT_TAB}")
        return {"status": "skipped", "row_count": data_rows}

    # Ensure the tab exists, then clear and overwrite.
    if _get_sheet_id(service, sheet_id, GANTT_TAB) is None:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": GANTT_TAB}}}]},
        ).execute()
        print(f"Created tab {GANTT_TAB}")
    service.spreadsheets().values().clear(
        spreadsheetId=sheet_id, range=f"{GANTT_TAB}!A1:Z10000"
    ).execute()
    write_with_retry(service, sheet_id, f"{GANTT_TAB}!A1", rows)
    duration = round(time.monotonic() - started_at, 2)
    print(f"Synced {data_rows} gantt rows -> {GANTT_TAB} in {duration}s")
    return {"status": "ok", "row_count": data_rows}


def main() -> int:
    """Main entry point. Returns 0 even on failure — the workflow proceeds."""
    print("KF Sheets Sync — Starting...")
    try:
        rows = load_loe_from_yaml()
        print(f"Loaded {len(rows) - 1} rows from {LOE_DATA_FILE}")
        result = sync_to_sheets(rows)
        update_sync_status("sheets_export", **result)
        print(f"KF Sheets Sync — Done ({result['last_run_status']})")

        # Additive: push the migration gantt to the Gantt_example tab.
        # Guarded separately so a gantt failure never affects the LOE result/exit.
        try:
            gantt_rows = load_gantt_from_yaml()
            gantt_result = sync_gantt_to_sheet(gantt_rows)
            print(f"KF Gantt Sync — {gantt_result['status']} ({gantt_result['row_count']} rows)")
        except Exception as ge:  # noqa: BLE001
            print(f"Warning: Gantt_example sync failed (non-fatal): {ge}", file=sys.stderr)
        return 0
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        print("KF Sheets Sync — FAILED")
        print(tb, file=sys.stderr)

        issue_url = file_sync_failure_issue(f"{e}\n\n{tb}")
        notify_chat(
            f"[KF Dashboard] Sheets export failed at {now_iso()}. "
            f"Live LOE tab unchanged. Issue: {issue_url or 'n/a'}"
        )

        existing = update_existing_failures(str(e), issue_url)
        update_sync_status(
            "sheets_export",
            last_run_at=now_iso(),
            last_run_status="failed",
            last_error=str(e),
            last_error_issue=issue_url,
            recent_failures=existing,
        )
        # Exit 0 — Pages is already live, downstream failure is recorded.
        return 0


def update_existing_failures(error_msg: str, issue_url: str | None) -> list[dict]:
    """Append the new failure to the rolling recent_failures list (keep last 5)."""
    from utils import load_sync_status
    status = load_sync_status()
    failures = list(status.get("sheets_export", {}).get("recent_failures", []))
    failures.append({
        "at": now_iso(),
        "error": error_msg[:500],
        "issue": issue_url,
    })
    return failures[-5:]


if __name__ == "__main__":
    sys.exit(main())
