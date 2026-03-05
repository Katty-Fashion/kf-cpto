---
project: {project-name}
description: "Short project description"
type: saas                # saas | eu-project | internal
po: "@product-owner"
lead: "@tech-lead"
sprint: S1
sprint_start: 2026-03-02
sprint_end: 2026-03-13
depends_on: []            # e.g. [nuoform, ai-rise]
tags: []                  # e.g. [frontend, ml, mvp]
---

# Project Kanban

<!-- Columns are fixed: Task | Assignee | Effort | Status — do not add or rename columns -->
<!-- Valid statuses: Todo, In Progress, Review, Done (exact spelling required) -->
<!-- Effort format: Nd (e.g. 1d, 0.5d, 3d) -->

| Task | Assignee | Effort | Status |
| :--- | :--- | :--- | :--- |
| Project setup | @lead | 1d | Done |
| Initial architecture | @tech-lead | 2d | In Progress |
| Documentation | @developer | 1d | Todo |
