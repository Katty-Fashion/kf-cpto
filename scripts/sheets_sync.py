#!/usr/bin/env python3
"""
Google Sheets Sync Script for KF Team

Syncs LOE (Level of Effort) data to Google Sheets using Service Account authentication.
"""

import os
from datetime import datetime

from utils import (
    REPOS_DIR,
    load_projects,
    parse_kanban_frontmatter,
    parse_kanban_tasks,
    parse_effort_days,
)

# Google API imports (optional - graceful fallback if not available)
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("Warning: Google API libraries not installed. Running in dry-run mode.")

PROJECTS = load_projects()


def get_sheets_service():
    """Initialize Google Sheets API service"""
    if not GOOGLE_API_AVAILABLE:
        return None

    client_email = os.environ.get("GSHEET_CLIENT_EMAIL")
    private_key = os.environ.get("GSHEET_PRIVATE_KEY")

    if not client_email or not private_key:
        print("Warning: Google Sheets credentials not configured")
        return None

    # Handle escaped newlines in private key
    private_key = private_key.replace("\\n", "\n")

    credentials_info = {
        "type": "service_account",
        "client_email": client_email,
        "private_key": private_key,
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    return build("sheets", "v4", credentials=credentials)


def load_loe_data() -> list[list]:
    """Load LOE data from all project repos and format for Google Sheets"""
    rows = [
        ["Project", "Sprint", "Task", "Assignee", "Effort (days)", "Status", "Updated"]
    ]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    for project in PROJECTS:
        kanban_path = REPOS_DIR / project / "kanban.md"
        if not kanban_path.exists():
            continue

        content = kanban_path.read_text()
        meta = parse_kanban_frontmatter(content)
        tasks = parse_kanban_tasks(content)

        sprint = meta.get("sprint", "-")

        for task in tasks:
            effort_days = parse_effort_days(task["effort"])
            rows.append([
                project,
                sprint,
                task["task"],
                task["assignee"],
                effort_days,
                task["status"],
                timestamp
            ])

    return rows


def sync_to_sheets(rows: list[list]):
    """Sync LOE data to Google Sheets"""
    sheet_id = os.environ.get("GSHEET_ID")

    if not sheet_id:
        print("Warning: GSHEET_ID not configured. Printing data instead:")
        for row in rows:
            print("\t".join(str(cell) for cell in row))
        return

    service = get_sheets_service()
    if not service:
        print("Dry run - would sync the following data:")
        for row in rows:
            print("\t".join(str(cell) for cell in row))
        return

    # Clear existing data and write new
    range_name = "LOE!A1:G1000"

    # Clear the sheet
    service.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=range_name
    ).execute()

    # Write new data
    body = {"values": rows}
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="LOE!A1",
        valueInputOption="RAW",
        body=body
    ).execute()

    print(f"Synced {len(rows)} rows to Google Sheets")


def main():
    """Main sync workflow"""
    print("KF Sheets Sync — Starting...")

    rows = load_loe_data()
    print(f"Loaded {len(rows) - 1} tasks from {len(PROJECTS)} projects")

    sync_to_sheets(rows)

    print("KF Sheets Sync — Done!")


if __name__ == "__main__":
    main()
