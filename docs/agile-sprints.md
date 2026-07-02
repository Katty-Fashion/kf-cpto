---
title: Agile Sprints
generated: 2026-07-02T21:28:48.564984
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
    Implement scheduling request endpoint (KF → LMS) :2026-06-29, 2026-07-10
    Implement scheduler response parser :2026-06-29, 2026-07-10
    Integrate scheduling results with planner UI :2026-06-29, 2026-07-10
    Implement planner visualization improvements (capacity / gaps) :2026-06-29, 2026-07-10
    Validate suitability constraints and scheduling logic :2026-06-29, 2026-07-10
    Run first scheduling tests with real production data :2026-06-29, 2026-07-10
    Debug integration issues with LMS team :2026-06-29, 2026-07-10
    Integration validation review :2026-06-29, 2026-07-10
    M2F finalise & confirm assumed KF-M2F shell structure :active, 2026-06-29, 2026-07-10
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
    Export R3 AAS shells → move to Netcompany-hosted R3 platform :2026-07-13, 2026-07-17
    Share KF access for export to NetCompany :2026-07-13, 2026-07-14
    Share KF-M2F shell with M2F (so they build their own) :2026-07-13, 2026-07-14
    Connect + test M2F V2 API from new Nuoform :2026-07-20, 2026-07-24
    State AI usage in R3 (declaration) :2026-07-16, 2026-07-17
    section kf-be-platform
    (F2.S5.Tenant Management) :done, 2026-06-29, 2026-07-19
    section kf-fe-platform
    (F2.S5.Admin Console) :done, 2026-07-06, 2026-07-26
    (F2.S6.Overview Refactor) :active, 2026-07-13, 2026-08-02
    section kf-platform
    (F3.S6.Collections Refactor) :done, 2026-07-20, 2026-08-16
```

<p class="gantt-legend"><span class="pill pill--planned">Planned</span><span class="pill pill--active">In work</span><span class="pill pill--late">Late / At risk</span><span class="pill pill--done">Done</span></p>

## Sprint Summary

| Project | Sprint | Window | Total Effort | % Done |
| :--- | :--- | :--- | :---: | :---: |
| R3-AAS | S5 | 2026-06-29 → 2026-07-10 | 52.5d | 0.0% |
| kf-be-platform | S5 | 2026-06-29 → 2026-07-10 | 77.0d | 45.5% |
| kf-fe-platform | S5 | 2026-06-29 → 2026-07-10 | 62.0d | 59.7% |
| kf-platform | S5 | 2026-06-29 → 2026-07-10 | 167.0d | 19.2% |
| **TOTAL** | | | **358.5d** | **29.0%** |