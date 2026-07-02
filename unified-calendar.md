---
title: Unified Calendar
generated: 2026-07-02T13:59:39.194382
---

# KF Team — Unified Calendar

> Effort by Project (person-days)

```mermaid
pie title Effort by Project (person-days)
    "kf-platform" : 167.0
    "kf-be-platform" : 77.0
    "kf-fe-platform" : 62.0
    "R3-AAS" : 18.5
```

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

## Full Timeline — All Projects

> Every dated task across all tracked repos, coloured by status

```mermaid
gantt
    title Aggregated Timeline — all projects (dated tasks)
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    excludes weekends

    section R3-AAS
    Review LMS API endpoints and AAS structure :done, 2026-03-16, 2026-03-16
    Implement automatic AAS JSON export from KF platform :done, 2026-03-16, 2026-03-18
    Technical architecture alignment for Planner integration :done, 2026-03-17, 2026-03-17
    Define integration pipeline (KF UI → LMS Scheduler → KF UI) :done, 2026-03-18, 2026-03-18
    Implement scheduling request endpoint (KF → LMS) :crit, 2026-03-19, 2026-03-21
    Integrate scheduling results with planner UI :crit, 2026-03-19, 2026-03-24
    Implement scheduler response parser :crit, 2026-03-22, 2026-03-24
    Implement planner visualization improvements (capacity / gaps) :crit, 2026-03-25, 2026-03-27
    Validate suitability constraints and scheduling logic :crit, 2026-03-26, 2026-03-28
    Run first scheduling tests with real production data :crit, 2026-03-28, 2026-03-28
    Debug integration issues with LMS team :crit, 2026-03-31, 2026-03-31
    Integration validation review :crit, 2026-04-03, 2026-04-03
    section kf-be-platform
    (F1.S2.DB Schema v2 + RLS) :done, 2026-05-25, 2026-06-21
    (F1.S2.CI/CD Pipeline) :crit, 2026-05-25, 2026-06-07
    (F2.S3.IDP + SMTP) :done, 2026-06-08, 2026-06-28
    (F2.S3.RBAC System) :done, 2026-06-08, 2026-07-05
    (F2.S5.Tenant Management) :done, 2026-06-29, 2026-07-19
    (F5.S13.EPCIS Export) :2026-10-19, 2026-11-08
    (F5.S13.LLM Ecodesign (WP4)) :2026-10-26, 2026-11-15
    (F5.S14.IoT Adapter (T2.5)) :2026-11-02, 2026-11-22
    (F5.S15.Notifications) :active, 2026-11-23, 2026-12-06
    (F6.S17.Data Migration Scripts) :2026-12-14, 2026-12-27
    section kf-fe-platform
    (F1.S2.Design System) :done, 2026-05-25, 2026-06-21
    (F1.S4.Login Flow) :done, 2026-06-22, 2026-07-05
    (F2.S5.Admin Console) :done, 2026-07-06, 2026-07-26
    (F2.S6.Overview Refactor) :active, 2026-07-13, 2026-08-02
    (F3.S7.Models Page) :done, 2026-08-03, 2026-08-23
    (F3.S8.Tech Pack Layout) :done, 2026-08-10, 2026-08-30
    (F3.S9.Model Sheet Fixes) :done, 2026-08-24, 2026-09-06
    (F3.S10.3D Performance) :active, 2026-09-07, 2026-09-27
    (F5.S14.Garment Configurator (T2.3)) :2026-11-09, 2026-11-29
    (F5.S15.i18n / l10n) :active, 2026-11-16, 2026-11-29
    section kf-platform
    (F1.S2.Project Setup) :done, 2026-05-25, 2026-06-07
    (F3.S6.Collections Refactor) :done, 2026-07-20, 2026-08-16
    (F3.S8.BOM Editor) :done, 2026-08-17, 2026-09-13
    (F4.S9.Orders Refactor) :active, 2026-08-24, 2026-09-20
    (F3.S9.Sizing & QA Flow) :done, 2026-08-31, 2026-09-20
    (F4.S10.Planner) :active, 2026-09-07, 2026-10-11
    (F3.S10.Cost Breakdown) :active, 2026-09-14, 2026-10-04
    (F3.S11.Tech Process Refactor) :active, 2026-09-21, 2026-10-11
    (F4.S11.Batches & Assignment) :active, 2026-09-21, 2026-10-18
    (F5.S11.DPP Module (T2.4)) :2026-09-21, 2026-10-25
    (F4.S11.Inventory & Reception) :done, 2026-09-28, 2026-10-18
    (F4.S11.Operator View) :2026-09-28, 2026-10-25
    (F4.S12.QC Module) :active, 2026-10-05, 2026-10-25
    (F4.S12.Reports & Cutting) :active, 2026-10-12, 2026-10-25
    (F5.S12.Public DPP / GS1) :2026-10-12, 2026-11-01
    (F5.S15.Auditor View) :2026-11-16, 2026-11-29
    (F5.S16.Made2Flow Schema) :2026-11-30, 2026-12-13
    (F6.S16.Migration Testing) :2026-12-07, 2026-12-20
    (F6.S17.Final QA & Cutover) :2026-12-21, 2027-01-03
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

    section kf-be-platform
    (F2.S5.Tenant Management) :done, 2026-06-29, 2026-07-19
    section kf-fe-platform
    (F2.S5.Admin Console) :done, 2026-07-06, 2026-07-26
    (F2.S6.Overview Refactor) :active, 2026-07-13, 2026-08-02
    section kf-platform
    (F3.S6.Collections Refactor) :done, 2026-07-20, 2026-08-16
```

<p class="gantt-legend"><span class="pill pill--planned">Planned</span><span class="pill pill--active">In work</span><span class="pill pill--late">Late / At risk</span><span class="pill pill--done">Done</span></p>
