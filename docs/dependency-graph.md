---
title: Dependency Graph
generated: 2026-06-26T09:47:02.814756
---

# KF Team — Dependency Graph

> Inter-project dependencies (auto-generated from kanban.md frontmatter)

```mermaid
graph LR
    R3_AAS["R3 Aas"]:::eu
    kf_be_platform["Kf Be Platform"]:::eu
    kf_fe_platform["Kf Fe Platform"]:::eu
    kf_platform["Kf Platform"]:::eu
    kf_platform --> kf_be_platform
    R3_AAS --> kf_be_platform
    kf_platform --> kf_fe_platform

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