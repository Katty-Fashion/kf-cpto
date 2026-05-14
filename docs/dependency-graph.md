---
title: Dependency Graph
generated: 2026-05-14T07:19:28.782237
---

# KF Team — Dependency Graph

> Inter-project dependencies (auto-generated from kanban.md frontmatter)

```mermaid
graph LR
    AIRise-ai-fabric-inspection[Airise Ai Fabric Inspection]:::eu
    Aladin-01[Aladin 01]:::internal
    Edi-test[Edi Test]:::internal
    NuoForm---GTM[Nuoform   Gtm]:::internal
    R3-AAS[R3 Aas]:::eu
    kf-be-platform[Kf Be Platform]:::eu
    kf-fe-platform[Kf Fe Platform]:::eu
    order-service[Order Service]:::internal
    project-template[Project Template]:::eu

    classDef saas fill:#4CAF50,color:#fff
    classDef eu fill:#2196F3,color:#fff
    classDef internal fill:#FF9800,color:#fff
```

*No inter-project dependencies declared yet. Add `depends_on` to your kanban.md frontmatter.*

## Legend

| Color | Type |
| :--- | :--- |
| Green | SaaS Product |
| Blue | EU Project |
| Orange | Internal |