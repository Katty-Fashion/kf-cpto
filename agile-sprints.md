---
title: Agile Sprints
generated: 2026-07-07T16:00:20.574459
---

# KF Team — Agile Sprints

## Sprint Timeline

> Previous · current · next sprint per project (from each repo's declared sprint)

```mermaid
gantt
    title Sprint Cadence — previous / current / next
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    excludes weekends

    section R3-AAS
    S4 :done, 2026-06-15, 2026-06-26
    S5 :active, 2026-06-29, 2026-07-10
    S6 :2026-07-13, 2026-07-24
    section ai-rise-options
    S4 :done, 2026-06-15, 2026-06-26
    S5 :active, 2026-06-29, 2026-07-10
    S6 :2026-07-13, 2026-07-24
    section kf-be-platform
    S4 :done, 2026-06-15, 2026-06-26
    S5 :active, 2026-06-29, 2026-07-10
    S6 :2026-07-13, 2026-07-24
    section kf-fe-platform
    S4 :done, 2026-06-15, 2026-06-26
    S5 :active, 2026-06-29, 2026-07-10
    S6 :2026-07-13, 2026-07-24
    section kf-platform
    S4 :done, 2026-06-15, 2026-06-26
    S5 :active, 2026-06-29, 2026-07-10
    S6 :2026-07-13, 2026-07-24
    section tech_brainstorming
    S4 :done, 2026-06-15, 2026-06-26
    S5 :active, 2026-06-29, 2026-07-10
    S6 :2026-07-13, 2026-07-24
```

<p class="gantt-legend"><span class="pill pill--planned">Planned</span><span class="pill pill--active">In work</span><span class="pill pill--late">Late / At risk</span><span class="pill pill--done">Done</span></p>

## Sprint Views — previous / current / next

### Sprint S4 (previous) — 2026-06-15 → 2026-06-26

```mermaid
gantt
    title S4 (previous) — 2026-06-15 → 2026-06-26
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    excludes weekends

    section kf-be-platform
    (F1.S2.DB Schema v2 + RLS) :done, 2026-05-25, 2026-06-21
    (F2.S3.IDP + SMTP) :done, 2026-06-08, 2026-06-28
    (F2.S3.RBAC System) :done, 2026-06-08, 2026-07-05
    section kf-fe-platform
    (F1.S2.Design System) :done, 2026-05-25, 2026-06-21
    (F1.S4.Login Flow) :done, 2026-06-22, 2026-07-05
```

<p class="gantt-legend"><span class="pill pill--planned">Planned</span><span class="pill pill--active">In work</span><span class="pill pill--late">Late / At risk</span><span class="pill pill--done">Done</span></p>

### Sprint S5 (current) — 2026-06-29 → 2026-07-10

```mermaid
gantt
    title S5 (current) — 2026-06-29 → 2026-07-10
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    excludes weekends

    section R3-AAS
    Implement scheduling request endpoint (KF → LMS) :active, 2026-06-29, 2026-07-10
    Implement scheduler response parser :active, 2026-06-29, 2026-07-10
    Integrate scheduling results with planner UI :active, 2026-06-29, 2026-07-10
    Implement planner visualization improvements (capacity / gaps) :active, 2026-06-29, 2026-07-10
    Validate suitability constraints and scheduling logic :active, 2026-06-29, 2026-07-10
    Run first scheduling tests with real production data :active, 2026-06-29, 2026-07-10
    Debug integration issues with LMS team :active, 2026-06-29, 2026-07-10
    Integration validation review :active, 2026-06-29, 2026-07-10
    M2F finalise & confirm assumed KF-M2F shell structure :active, 2026-06-29, 2026-07-10
    Share KF access for export to NetCompany :done, 2026-07-07, 2026-07-07
    section kf-be-platform
    (F2.S3.RBAC System) :done, 2026-06-08, 2026-07-05
    (F2.S5.Tenant Management) :done, 2026-06-29, 2026-07-19
    section kf-fe-platform
    (F1.S4.Login Flow) :done, 2026-06-22, 2026-07-05
    (F2.S5.Admin Console) :done, 2026-07-06, 2026-07-26
```

<p class="gantt-legend"><span class="pill pill--planned">Planned</span><span class="pill pill--active">In work</span><span class="pill pill--late">Late / At risk</span><span class="pill pill--done">Done</span></p>

### Sprint S6 (next) — 2026-07-13 → 2026-07-24

```mermaid
gantt
    title S6 (next) — 2026-07-13 → 2026-07-24
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    excludes weekends

    section R3-AAS
    Export R3 AAS shells → move to Netcompany-hosted R3 platform :active, 2026-07-13, 2026-07-17
    Share KF-M2F shell with M2F (so they build their own) :done, 2026-07-13, 2026-07-14
    Connect + test M2F V2 API from new Nuoform :active, 2026-07-20, 2026-07-24
    State AI usage in R3 (declaration) :2026-07-16, 2026-07-17
    section kf-be-platform
    (F2.S5.Tenant Management) :done, 2026-06-29, 2026-07-19
    section kf-fe-platform
    (F2.S5.Admin Console) :done, 2026-07-06, 2026-07-26
    (F2.S6.Overview Refactor) :done, 2026-07-13, 2026-08-02
    section kf-platform
    (F3.S6.Collections Refactor) :done, 2026-07-20, 2026-08-16
```

<p class="gantt-legend"><span class="pill pill--planned">Planned</span><span class="pill pill--active">In work</span><span class="pill pill--late">Late / At risk</span><span class="pill pill--done">Done</span></p>

## Sprint Summary

| Project | Sprint | Window | Total Effort | % Done |
| :--- | :--- | :--- | :---: | :---: |
| R3-AAS | S5 | 2026-06-29 → 2026-07-10 | 52.5d | 3.8% |
| ai-rise-options | S5 | 2026-06-29 → 2026-07-10 | 0d | 0% |
| kf-be-platform | S5 | 2026-06-29 → 2026-07-10 | 77.0d | 54.5% |
| kf-fe-platform | S5 | 2026-06-29 → 2026-07-10 | 62.0d | 83.9% |
| kf-platform | S5 | 2026-06-29 → 2026-07-10 | 167.0d | 58.1% |
| tech_brainstorming | S5 | 2026-06-29 → 2026-07-10 | 0d | 0% |
| **TOTAL** | | | **358.5d** | **53.8%** |