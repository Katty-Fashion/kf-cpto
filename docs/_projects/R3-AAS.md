---
title: R3-AAS
description: "R3GROUP Katty Fashion pilot \u2013 digital tools for co-creation, digital twins and technician capacity planning"
project: R3-AAS
type: eu-project
edit_url: "https://github.com/katty-fashion/R3-AAS/edit/main/kanban.md"
generated: 2026-08-24T04:19:12.861614
---

# R3-AAS

> R3GROUP Katty Fashion pilot – digital tools for co-creation, digital twins and technician capacity planning

## Status

| Metric | Value |
| :--- | :--- |
| Status | Active |
| Type | EU Project |
| PO | @el.tech |
| Lead | @el.tech |
| Current Sprint | S5 |
| Sprint Period | 2026-06-29 to 2026-07-10 |
| Tags | r3group, digital-twin, capacity-planner, manufacturing, aas |
| Dependencies | [ai-rise-options]({{ '/projects/ai-rise-options/' | relative_url }}) |

## Current Sprint Kanban &nbsp; [Edit Kanban]({{ '/kanban-builder/' | relative_url }}?project=R3-AAS) <sup>·&nbsp;[raw](https://github.com/katty-fashion/R3-AAS/edit/main/kanban.md)</sup>

<div class="kanban-board">
  <div class="kanban-col kanban-col--todo">
    <div class="kanban-col__head">Todo <span class="kanban-col__count">3</span></div>
    <div class="kanban-card kanban-card--static">Re-point all connections to Netcompany-hosted R3 (go live)</div>
    <div class="kanban-card kanban-card--static">Pilot KF demo recordings (based on revised Nuoform)</div>
    <div class="kanban-card kanban-card--static">State AI usage in R3 (declaration)</div>
  </div>
  <div class="kanban-col kanban-col--in-progress">
    <div class="kanban-col__head">In Progress <span class="kanban-col__count">4</span></div>
    <div class="kanban-card kanban-card--static">T2.3 — Supply Chain Digital Twin: risk modelling</div>
    <div class="kanban-card kanban-card--static">M2F: finalise &amp; confirm assumed KF-M2F shell structure</div>
    <div class="kanban-card kanban-card--static">Export R3 AAS shells → move to Netcompany-hosted R3 platform</div>
    <div class="kanban-card kanban-card--static">Connect + test M2F V2 API from new Nuoform</div>
  </div>
  <div class="kanban-col kanban-col--review">
    <div class="kanban-col__head">Review <span class="kanban-col__count">12</span></div>
    <div class="kanban-card kanban-card--static">WP1 — AAS platform integration (digital infrastructure)</div>
    <div class="kanban-card kanban-card--static">T2.4 — Capacity Planner: KF Planner UI</div>
    <div class="kanban-card kanban-card--static">T2.4 — Capacity Planner: KF ↔ LMS Integration</div>
    <div class="kanban-card kanban-card--static">T3.3 — IoT Monitoring: sensors deployment</div>
    <div class="kanban-card kanban-card--static">Implement scheduling request endpoint (KF → LMS)</div>
    <div class="kanban-card kanban-card--static">Implement scheduler response parser</div>
    <div class="kanban-card kanban-card--static">Integrate scheduling results with planner UI</div>
    <div class="kanban-card kanban-card--static">Implement planner visualization improvements (capacity / gaps)</div>
    <div class="kanban-card kanban-card--static">Validate suitability constraints and scheduling logic</div>
    <div class="kanban-card kanban-card--static">Run first scheduling tests with real production data</div>
    <div class="kanban-card kanban-card--static">Debug integration issues with LMS team</div>
    <div class="kanban-card kanban-card--static">Integration validation review</div>
  </div>
  <div class="kanban-col kanban-col--done">
    <div class="kanban-col__head">Done <span class="kanban-col__count">1</span></div>
    <div class="kanban-card kanban-card--static">Share KF access for export to NetCompany</div>
  </div>
</div>

## Task Summary

### Status General M36 — Program Deliverables

| Task | Assignee | Effort | Start | End | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| WP1 — AAS platform integration (digital infrastructure) | Mihai A. | — |  |  | Review |
| T2.1 — Co-creation platform (Nuoform) | Alexandru Bejenari | — |  |  | Done |
| T3.2 — Product Digital Twin (AAS model) | Eduard L | — |  |  | Done |
| T3.2 — Process Digital Twin (Tecnomatix simulation) | Eduard L | — |  |  | Done |
| T2.4 — Capacity Planner: LMS Scheduler Backend | LMS | — |  |  | Done |
| T2.4 — Capacity Planner: KF Planner UI | Alexandru Bejenari | 5d |  |  | Review |
| T2.4 — Capacity Planner: KF ↔ LMS Integration | Alexandru Bejenari | 10d |  |  | Review |
| T3.3 — IoT Monitoring: sensors deployment | Eduard Lazar | 5d |  |  | Review |
| T2.3 — Supply Chain Digital Twin: risk modelling | Eduard Lazar | — |  |  | In Progress |
| AAS import/export tooling (aas_export.py, import-demo.sh) | Eduard L | — |  |  | Done |
| Order_3_Aas shell (8 submodels, cost + schedule) | Eduard L | — |  |  | Done |
| Demo UI R3Group (Next 16: Design → Simulation → Shopfloor → Impact; LMS re-optimise) | Alexandru Bejenari | — |  |  | Done |
| OAuth2 auth-server public + per-client provisioning | Răzvan Boița | — |  |  | Done |
| ALADIN WP2 RunSheet service (nginx + Traefik routing) | Răzvan Boița | — |  |  | Done |

### Tasks — Sprint S2 (16 March → 03 April 2026)

| Task | Assignee | Effort | Start | End | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Implement scheduling request endpoint (KF → LMS) | @backend | 2d | 2026-06-29 | 2026-07-10 | Review |
| Implement scheduler response parser | @backend | 2d | 2026-06-29 | 2026-07-10 | Review |
| Integrate scheduling results with planner UI | @frontend | 3d | 2026-06-29 | 2026-07-10 | Review |
| Implement planner visualization improvements (capacity / gaps) | @frontend | 2d | 2026-06-29 | 2026-07-10 | Review |
| Validate suitability constraints and scheduling logic | @backend | 2d | 2026-06-29 | 2026-07-10 | Review |
| Run first scheduling tests with real production data | @tech-lead | 1d | 2026-06-29 | 2026-07-10 | Review |
| Debug integration issues with LMS team | @tech-lead | 1d | 2026-06-29 | 2026-07-10 | Review |
| Integration validation review | @tech-lead | 0.5d | 2026-06-29 | 2026-07-10 | Review |

### 10. Outstanding — R3 Handover, M2F &amp; Pilot

| Task | Assignee | Effort | Start | End | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| M2F: finalise &amp; confirm assumed KF-M2F shell structure | Eduard Lazăr / M2F | 2d | 2026-06-29 | 2026-07-10 | In Progress |
| Export R3 AAS shells → move to Netcompany-hosted R3 platform | Eduard Lazăr / Netcompany | 3d | 2026-07-13 | 2026-07-17 | In Progress |
| Share KF access for export to NetCompany | Eduard Lazăr | 1d | 2026-07-07 | 2026-07-07 | Done |
| Share KF-M2F shell with M2F (so they build their own) | Eduard Lazăr | 1d | 2026-07-13 | 2026-07-14 | Done |
| Connect + test M2F V2 API from new Nuoform | Alexandru Bejenari | 5d | 2026-07-20 | 2026-07-24 | In Progress |
| Re-point all connections to Netcompany-hosted R3 (go live) | Mihai A. | 3d | 2026-07-27 | 2026-07-31 | Todo |
| Pilot KF demo recordings (based on revised Nuoform) | Eduard Lazăr | 3d | 2026-08-03 | 2026-08-05 | Todo |
| State AI usage in R3 (declaration) | Eduard Lazăr | 1d | 2026-07-16 | 2026-07-17 | Todo |


## LOE Summary

| Metric | Value |
| :--- | :--- |
| Total Effort | 52.5d |
| In Progress | 10.0d |
| Completed | 2.0d |
| Remaining | 50.5d |

## Effort — Planned vs Done

```mermaid
pie showData title Effort — Planned vs Done (person-days)
    "Done" : 2.0
    "Planned" : 50.5
```

## Sprint Timeline

```mermaid
gantt
    title S5 — R3-AAS (dated tasks)
    dateFormat YYYY-MM-DD
    excludes weekends

    M2F finalise & confirm assumed KF-M2F shell structure :crit, 2026-06-29, 2026-07-10
    Implement scheduling request endpoint (KF → LMS) :crit, 2026-06-29, 2026-07-10
    Implement scheduler response parser :crit, 2026-06-29, 2026-07-10
    Integrate scheduling results with planner UI :crit, 2026-06-29, 2026-07-10
    Implement planner visualization improvements (capacity / gaps) :crit, 2026-06-29, 2026-07-10
    Validate suitability constraints and scheduling logic :crit, 2026-06-29, 2026-07-10
    Run first scheduling tests with real production data :crit, 2026-06-29, 2026-07-10
    Debug integration issues with LMS team :crit, 2026-06-29, 2026-07-10
    Integration validation review :crit, 2026-06-29, 2026-07-10
    Share KF access for export to NetCompany :done, 2026-07-07, 2026-07-07
    Share KF-M2F shell with M2F (so they build their own) :done, 2026-07-13, 2026-07-14
    Export R3 AAS shells → move to Netcompany-hosted R3 platform :crit, 2026-07-13, 2026-07-17
    State AI usage in R3 (declaration) :crit, 2026-07-16, 2026-07-17
    Connect + test M2F V2 API from new Nuoform :crit, 2026-07-20, 2026-07-24
    Re-point all connections to Netcompany-hosted R3 (go live) :crit, 2026-07-27, 2026-07-31
    Pilot KF demo recordings (based on revised Nuoform) :crit, 2026-08-03, 2026-08-05
```

<p class="gantt-legend"><span class="pill pill--planned">Planned</span><span class="pill pill--active">In work</span><span class="pill pill--late">Late / At risk</span><span class="pill pill--done">Done</span></p>

> 5 open task(s) have no start/end dates and are not charted — add dates in kanban.md to plot them.

## Links

- [Edit Kanban]({{ '/kanban-builder/' | relative_url }}?project=R3-AAS) ·&nbsp;[raw](https://github.com/katty-fashion/R3-AAS/edit/main/kanban.md)
- [Repository](https://github.com/katty-fashion/R3-AAS)
- [Kanban Board](https://github.com/katty-fashion/R3-AAS/blob/main/kanban.md)

---

*Auto-generated by KF Aggregator*