---
title: Dependency Graph
generated: 2026-03-16T05:51:04.317548
---

# KF Team — Dependency Graph

> Inter-project dependencies (auto-generated from kanban.md frontmatter)

```mermaid
graph LR
    AIRise-ai-fabric-inspection[Airise Ai Fabric Inspection]:::eu
    Aladin-01[Aladin 01]:::internal
    Edi-test[Edi Test]:::internal
    NuoForm---GTM[Nuoform   Gtm]:::internal
    R3GROUP[R3Group]:::eu
    order-service[Order Service]:::internal
    project-template[Project Template]:::eu
    R3GROUP --> order-service

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