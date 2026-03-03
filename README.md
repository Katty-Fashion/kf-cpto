# KF-CPTO — Git-Native Project Management Dashboard

> **Single Pane of Glass** for KF Team projects — aggregating Kanban boards, calendars, and LOE tracking across multiple repositories.

## Overview

KF-CPTO is a centralized dashboard that automatically aggregates project management data from multiple KF Team repositories into a unified view. It provides:

- **Unified Kanban Board** — All project tasks in one view
- **Sprint Calendar** — Visual timeline with Gantt charts
- **LOE (Level of Effort) Reports** — Effort tracking by project and assignee
- **Google Sheets Integration** — Automatic sync for reporting
- **GitHub Pages Deployment** — Live dashboard at `https://kf-team.github.io/kf-cpto/`

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    KF-CPTO Repository                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│   │ ai-rise  │  │ airegio  │  │ nuoform  │  │waist-mgmt│       │
│   │ repo     │  │ repo     │  │ repo     │  │ repo     │       │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│        │             │             │             │              │
│        └─────────────┴──────┬──────┴─────────────┘              │
│                             │                                   │
│                             ▼                                   │
│                    ┌────────────────┐                           │
│                    │  aggregator.py │                           │
│                    └────────┬───────┘                           │
│                             │                                   │
│              ┌──────────────┼──────────────┐                    │
│              ▼              ▼              ▼                    │
│     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│     │unified-     │ │unified-     │ │loe-report   │            │
│     │kanban.md    │ │calendar.md  │ │.md          │            │
│     └─────────────┘ └─────────────┘ └──────┬──────┘            │
│                                            │                    │
│                                            ▼                    │
│                                   ┌────────────────┐            │
│                                   │ sheets_sync.py │            │
│                                   └────────┬───────┘            │
│                                            │                    │
│                                            ▼                    │
│                                   ┌────────────────┐            │
│                                   │ Google Sheets  │            │
│                                   └────────────────┘            │
│                                                                 │
│                    GitHub Pages (docs/)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Project Repositories

| Project | Type | Description | Repository |
| :--- | :--- | :--- | :--- |
| **ai-rise** | EU Project | European Union AI research and innovation project | [kf-team/ai-rise](https://github.com/kf-team/ai-rise) |
| **airegio** | EU Project | EU Regional AI initiative | [kf-team/airegio](https://github.com/kf-team/airegio) |
| **nuoform** | SaaS Product | SaaS platform | [kf-team/nuoform](https://github.com/kf-team/nuoform) |
| **waist-mgmt** | SaaS Product | Health SaaS application | [kf-team/waist-mgmt](https://github.com/kf-team/waist-mgmt) |

Each project repository contains a `kanban.md` file with task tracking in a standardized format.

### Adding/Removing Projects

Projects are configured in `_config.yml` under `kf_projects`:

```yaml
kf_projects:
  - ai-rise
  - airegio
  - nuoform
  - waist-mgmt
```

To add a new project, append it to the list. The aggregator scripts and GitHub Actions workflow read from this single source of truth.

## Repository Setup Guide

Follow these steps to integrate a new project repository with the KF-CPTO dashboard.

### Step 1: Create `kanban.md` in Your Repository

Create a `kanban.md` file in the **root** of your project repository with this structure:

```markdown
---
project: your-project-name
sprint: S3
sprint_start: 2026-03-02
sprint_end: 2026-03-13
---

# Project Kanban

| Task | Assignee | Effort | Status |
| :--- | :--- | :--- | :--- |
| Implement feature X | @developer | 3d | In Progress |
| Code review for Y | @reviewer | 1d | Review |
| Deploy to staging | @devops | 2d | Todo |
```

**Frontmatter fields:**

| Field | Required | Description |
| :--- | :---: | :--- |
| `project` | Yes | Project identifier (should match repo name) |
| `sprint` | Yes | Current sprint name (e.g., S3, Sprint-5) |
| `sprint_start` | Yes | Sprint start date (YYYY-MM-DD) |
| `sprint_end` | Yes | Sprint end date (YYYY-MM-DD) |

**Task table columns:**

| Column | Format | Valid Values |
| :--- | :--- | :--- |
| Task | Free text | Task description |
| Assignee | `@username` | GitHub username with @ prefix |
| Effort | `Nd` | Number + 'd' for days (e.g., `3d`, `0.5d`) |
| Status | Exact match | `Todo`, `In Progress`, `Review`, `Done` |

### Step 2: Register in KF-CPTO

1. **Fork/clone** the kf-cpto repository
2. **Edit** `docs/_config.yml` and add your project to `kf_projects`:

```yaml
kf_projects:
- ai-rise
- airegio
- nuoform
- waist-mgmt
- your-new-project  # Add here
```

3. **Commit and push** — the GitHub Action will clone your repo and aggregate

### Step 3: (Optional) Auto-Trigger on Kanban Updates

Add a GitHub Action to your project repo to notify kf-cpto when `kanban.md` changes:

```yaml
# .github/workflows/notify-kf-cpto.yml
name: Notify KF-CPTO

on:
  push:
    paths:
      - 'kanban.md'

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger KF-CPTO Aggregation
        run: |
          curl -X POST \
            -H "Accept: application/vnd.github+json" \
            -H "Authorization: Bearer ${{ secrets.KF_PAT }}" \
            https://api.github.com/repos/kf-team/kf-cpto/dispatches \
            -d '{"event_type":"kanban-update","client_payload":{"project":"${{ github.repository }}"}}'
```

**Required secret:** `KF_PAT` — Personal Access Token with `repo` scope for kf-cpto.

### Step 4: Verify Integration

After the aggregator runs:

1. Check the [Unified Kanban](https://kf-team.github.io/kf-cpto/unified-kanban.html) — your tasks should appear
2. Check your [Project Page](https://kf-team.github.io/kf-cpto/projects/your-project.html) — auto-generated
3. Check the [LOE Report](https://kf-team.github.io/kf-cpto/loe-report.html) — effort totals included

### Troubleshooting

| Issue | Solution |
| :--- | :--- |
| Tasks not appearing | Verify `kanban.md` is in repo root, not a subdirectory |
| Status not recognized | Use exact values: `Todo`, `In Progress`, `Review`, `Done` |
| Effort not calculated | Format must be `Nd` (e.g., `3d`, `1.5d`) |
| Project page missing | Ensure project name in `_config.yml` matches repo name exactly |
| Aggregator warnings | Check GitHub Actions logs for specific parsing errors |

## Automation Workflows

### Primary Workflow: Unified Sync

The main workflow (`.github/workflows/aggregate.yml`) runs automatically:

- **On push to main/master** — Immediate sync
- **On repository dispatch** — When any project updates its kanban
- **Weekly schedule** — Every Monday at 04:00 UTC
- **Manual trigger** — Via workflow_dispatch

**Steps:**
1. Clone all project repositories
2. Run `aggregator.py` to generate:
   - `unified-kanban.md` — All tasks across projects
   - `unified-calendar.md` — Sprint timeline
   - `loe-report.md` — Level of Effort summary
   - `projects/{project}.md` — Individual project pages (auto-generated)
3. Sync LOE data to Google Sheets via `sheets_sync.py`
4. Commit and push updated docs
5. Deploy to GitHub Pages
6. Notify Google Chat webhook

### Secondary Workflow: Sheets Sync

A lightweight workflow (`.github/workflows/sync_to_sheets.yml`) for frequent LOE updates:

- **Weekday schedule** — Monday-Friday at 09:00 UTC
- **Manual trigger** — Via workflow_dispatch

**Steps:**
1. Clone all project repositories
2. Sync LOE data to Google Sheets via `sheets_sync.py`

## Kanban Format

Each project's `kanban.md` should follow this format:

```markdown
---
project: project-name
sprint: S3
sprint_start: 2026-03-02
sprint_end: 2026-03-13
---

# Project Kanban

| Task | Assignee | Effort | Status |
| :--- | :--- | :--- | :--- |
| Implement feature X | @developer | 3d | In Progress |
| Code review for Y | @reviewer | 1d | Review |
| Deploy to staging | @devops | 2d | Todo |
```

## MermaidJS Visualization Examples

The dashboard uses MermaidJS for visual representations. Here are valid syntax examples:

### Pie Chart — Time Allocation

```mermaid
pie title Monthly 50h CPTO Allocation
    "Sync & Team Rhythm" : 10
    "Technical Health" : 12
    "Pre-Sales" : 8
    "EU Projects" : 10
    "SaaS Products" : 8
    "Team Events" : 2
```

### Gantt Chart — Sprint Calendar

```mermaid
gantt
    title Sprint Calendar
    dateFormat YYYY-MM-DD
    excludes weekends

    section nuoform
    Sprint 3 Planning        :crit, 2026-03-02, 1d
    Sprint 3 Active          :active, 2026-03-03, 9d
    Sprint 3 Demo + Retro    :crit, 2026-03-13, 1d

    section ai-rise
    Research Phase           :2026-03-03, 5d
    Documentation            :2026-03-10, 3d
```

### Kanban Diagram

MermaidJS supports native Kanban diagrams (since v11.4):

```mermaid
kanban
  Todo
    id1[OAS3 Billing API]
    id2[ArgoCD Pipeline Config]
  In-Progress
    id3[OpenTelemetry Integration]
  Review
    id4[HLD Architecture v2]
  Done
    id5[HLD Diagram v1]
```

### Timeline — Project Milestones

```mermaid
timeline
    title KF Team Q1 2026 Milestones
    section January
        ai-rise Kickoff : Project launch
        nuoform v1.0 : Initial release
    section February
        airegio Phase 1 : Complete
        waist-mgmt Beta : Beta launch
    section March
        Sprint 3 : All projects aligned
        Q1 Review : Quarterly assessment
```

### Quadrant Chart — Project Priority Matrix

```mermaid
quadrantChart
    title Project Priority Matrix
    x-axis Low Effort --> High Effort
    y-axis Low Impact --> High Impact
    quadrant-1 Quick Wins
    quadrant-2 Major Projects
    quadrant-3 Fill-ins
    quadrant-4 Time Sinks
    nuoform: [0.7, 0.8]
    ai-rise: [0.8, 0.9]
    airegio: [0.6, 0.7]
    waist-mgmt: [0.4, 0.6]
```

## Configuration

### Required GitHub Secrets

| Secret | Description |
| :--- | :--- |
| `KF_PAT` | Personal Access Token with repo access to clone project repos |
| `GSHEET_ID` | Google Sheets document ID for LOE sync |
| `GSHEET_CLIENT_EMAIL` | Google Service Account email |
| `GSHEET_PRIVATE_KEY` | Google Service Account private key |
| `GOOGLE_CHAT_WEBHOOK` | Google Chat webhook URL for notifications |

### Jekyll Configuration

The `docs/_config.yml` configures GitHub Pages and serves as the single source of truth for:

- `kf_projects` — List of project repositories to aggregate
- Custom layout with Pico CSS
- MermaidJS client-side rendering (v11)
- Project collections for individual project pages

## Local Development

```bash
# Clone the repository
git clone https://github.com/kf-team/kf-cpto.git
cd kf-cpto

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Clone project repos locally (reads from docs/_config.yml)
mkdir -p repos
PROJECTS=$(python -c "import yaml; print(' '.join(yaml.safe_load(open('docs/_config.yml'))['kf_projects']))")
for repo in $PROJECTS; do
    git clone https://github.com/kf-team/${repo}.git repos/${repo}
done

# Run the aggregator
python scripts/aggregator.py

# Run sheets sync (dry-run without credentials)
python scripts/sheets_sync.py

# Serve docs locally with Jekyll
cd docs && bundle exec jekyll serve
```

## File Structure

```
kf-cpto/
├── .github/
│   └── workflows/
│       ├── aggregate.yml      # Primary workflow - full sync pipeline
│       └── sync_to_sheets.yml # Secondary workflow - LOE sync only
├── docs/
│   ├── _config.yml            # Jekyll configuration
│   ├── _layouts/
│   │   └── default.html       # Custom layout with MermaidJS
│   ├── index.md               # Dashboard homepage
│   ├── unified-kanban.md      # Aggregated kanban (auto-generated)
│   ├── unified-calendar.md    # Sprint calendar (auto-generated)
│   ├── loe-report.md          # LOE report (auto-generated)
│   └── projects/              # Individual project pages (auto-generated)
│       ├── ai-rise.md
│       ├── airegio.md
│       ├── nuoform.md
│       └── waist-mgmt.md
├── scripts/
│   ├── aggregator.py          # Main aggregation script
│   ├── sheets_sync.py         # Google Sheets sync
│   └── utils.py               # Shared utilities module
├── requirements.txt           # Python dependencies
└── README.md
```

## License

KF Team Internal Project

---

*KF Team — Git-Native Project Management*
