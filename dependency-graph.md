---
title: Dependency Graph
generated: 2026-03-05T00:44:24.366359
---

# KF Team — Dependency Graph

> Inter-project dependencies (auto-generated from kanban.md frontmatter)

```mermaid
graph LR
    Aladin-01[Aladin 01]:::internal
    project-template[Project Template]:::internal
    project-template --> Aladin-01

    classDef saas fill:#4CAF50,color:#fff
    classDef eu fill:#2196F3,color:#fff
    classDef internal fill:#FF9800,color:#fff
```

## Legend

| Color | Type |
| :--- | :--- |
| Green | SaaS Product |
| Blue | EU Project |
| Orange | Internal |