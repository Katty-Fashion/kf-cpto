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

<!-- Valid statuses: Todo, In Progress, Review, Done (exact spelling required) -->
<!-- Effort format: Nd (e.g. 1d, 0.5d, 3d) — Start/End are optional (YYYY-MM-DD) -->
<!-- 4-column format (without dates) also supported for backward compatibility -->

| Task | Assignee | Effort | Start | End | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Project setup | @lead | 1d | 2026-03-03 | 2026-03-03 | Done |
| Initial architecture | @tech-lead | 2d | 2026-03-04 | 2026-03-05 | In Progress |
| Documentation | @developer | 1d | | | Todo |
