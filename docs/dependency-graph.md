---
title: Dependency Graph
generated: 2026-10-26T17:57:27.247033
---

# KF Team — Dependency Graph

> Inter-project dependencies (auto-generated from kanban.md frontmatter)

```mermaid
graph LR
    R3_AAS["R3 Aas"]:::eu
    ai_rise_options["Ai Rise Options"]:::eu
    kf_be_platform["Kf Be Platform"]:::saas
    kf_fe_platform["Kf Fe Platform"]:::saas
    kf_platform["Kf Platform"]:::saas
    tech_brainstorming["Tech_Brainstorming"]:::internal
    kf_infra_base["Kf Infra Base"]:::internal
    kf_idp_stack["Kf Idp Stack"]:::internal
    kf_vault["Kf Vault"]:::internal
    kf_wiki["Kf Wiki"]:::internal
    kf_platform_modules["Kf Platform Modules"]:::saas
    kf_modular_demo["Kf Modular Demo"]:::saas
    kf_clo3d_plugin["Kf Clo3D Plugin"]:::saas
    n_3D_ODIN_ELAIS["3D Odin Elais"]:::eu
    AIRise_ai_fabric_inspection["Airise Ai Fabric Inspection"]:::eu
    ai_rise_options --> R3_AAS
    R3_AAS --> kf_be_platform
    kf_be_platform --> kf_fe_platform
    kf_fe_platform --> kf_platform
    kf_be_platform --> kf_platform
    kf_infra_base --> kf_idp_stack
    kf_infra_base --> kf_vault
    kf_infra_base --> kf_wiki
    kf_platform --> kf_platform_modules
    kf_platform_modules --> kf_modular_demo
    kf_platform --> kf_clo3d_plugin

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