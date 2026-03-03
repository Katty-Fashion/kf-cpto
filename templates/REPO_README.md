# {PROJECT_NAME}

> {PROJECT_DESCRIPTION}

## Quick Links

- [KF Dashboard](https://kf-team.github.io/kf-cpto/) — Unified project view
- [Project Page](https://kf-team.github.io/kf-cpto/projects/{project-name}.html) — Auto-generated from kanban
- [Unified Kanban](https://kf-team.github.io/kf-cpto/unified-kanban.html) — All tasks across KF Team

---

## Kanban Management

This repository uses a `kanban.md` file for task tracking that integrates with the [KF-CPTO Dashboard](https://github.com/kf-team/kf-cpto).

### Updating Tasks

Edit `kanban.md` in the repository root:

```markdown
---
project: {project-name}
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

### Task Status Values

| Status | Description |
| :--- | :--- |
| `Todo` | Not started |
| `In Progress` | Currently being worked on |
| `Review` | Awaiting code review or approval |
| `Done` | Completed |

### Effort Format

Use `Nd` format where N is the number of days:
- `1d` — 1 day
- `0.5d` — Half day
- `3d` — 3 days

### Sprint Updates

Update the frontmatter at the start of each sprint:

```yaml
---
project: {project-name}
sprint: S4              # Increment sprint number
sprint_start: 2026-03-16  # New sprint start
sprint_end: 2026-03-27    # New sprint end
---
```

---

## Development

### Prerequisites

```bash
# Required tools
- Python 3.9+
- Node.js 18+ (if applicable)
- Docker (if applicable)
```

### Setup

```bash
# Clone the repository
git clone https://github.com/kf-team/{project-name}.git
cd {project-name}

# Install dependencies
# Add project-specific setup commands here
```

### Running Locally

```bash
# Add project-specific run commands here
```

### Testing

```bash
# Add project-specific test commands here
```

---

## Project Structure

```
{project-name}/
├── kanban.md              # Task tracking (synced to KF-CPTO)
├── README.md              # This file
├── .github/
│   └── workflows/
│       └── notify-kf-cpto.yml  # Auto-sync to dashboard
└── src/                   # Project source code
```

---

## KF-CPTO Integration

### Automatic Sync

When you push changes to `kanban.md`, the KF-CPTO dashboard automatically updates via GitHub Actions.

### Manual Trigger

To manually trigger a dashboard sync:

```bash
# Via GitHub CLI
gh workflow run notify-kf-cpto.yml
```

### Workflow Configuration

The `.github/workflows/notify-kf-cpto.yml` file handles automatic sync:

```yaml
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

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Update `kanban.md` with your task
3. Make your changes
4. Update task status in `kanban.md`
5. Commit and push
6. Create a Pull Request

---

## Team

| Role | Contact |
| :--- | :--- |
| Project Lead | @{lead} |
| Tech Lead | @{tech-lead} |
| Team | @kf-team/{project-name} |

---


File	Purpose
REPO_README.md	Full project README with kanban docs, dev setup, team section
kanban.md	Starter kanban with frontmatter and example tasks
.github/workflows/notify-kf-cpto.yml	Auto-sync workflow to trigger dashboard updates
Quick setup for new repos:


# From project repo root
curl -sL https://raw.githubusercontent.com/kf-team/kf-cpto/master/templates/kanban.md -o kanban.md
curl -sL https://raw.githubusercontent.com/kf-team/kf-cpto/master/templates/REPO_README.md -o README.md
mkdir -p .github/workflows
curl -sL https://raw.githubusercontent.com/kf-team/kf-cpto/master/templates/.github/workflows/notify-kf-cpto.yml -o .github/workflows/notify-kf-cpto.yml
Then replace {project-name}, {PROJECT_DESCRIPTION}, etc.

*Part of [KF Team](https://github.com/kf-team) · Managed via [KF-CPTO](https://github.com/kf-team/kf-cpto)*
