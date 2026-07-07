---
title: Dependency Graph
generated: 2026-07-07T16:31:18.459119
---

# KF Team — Dependency Graph

> Inter-project dependencies (auto-generated from kanban.md frontmatter)

```mermaid
graph LR
    R3_AAS["R3 Aas"]:::eu
    ai_rise_options["Ai Rise Options"]:::eu
    kf_be_platform["Kf Be Platform"]:::eu
    kf_fe_platform["Kf Fe Platform"]:::eu
    kf_platform["Kf Platform"]:::eu
    tech_brainstorming["Tech_Brainstorming"]:::internal
    kf_fe_platform --> kf_be_platform
    R3_AAS --> kf_be_platform

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