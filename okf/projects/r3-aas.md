---
type: Project
title: R3-AAS
description: R3GROUP Katty Fashion pilot – digital tools for co-creation, digital twins and technician capacity planning
resource:
  - "https://github.com/katty-fashion/R3-AAS"
  - "https://katty-fashion.github.io/kf-cpto/projects/r3-aas/"
tags:
  - r3group
  - digital-twin
  - capacity-planner
  - manufacturing
  - aas
timestamp: 2026-07-02
po: "@el.tech"
lead: "@el.tech"
sprint: S5
---

# R3-AAS

> R3GROUP Katty Fashion pilot – digital tools for co-creation, digital twins and technician capacity planning

## LOE Rollup

| Metric | Value |
| :--- | :--- |
| Total effort | 52d |
| Done | 2d |
| Remaining | 50d |

> Effort is person-days (`Nd`) as declared in `kanban.md`.
> See [/metrics/loe.md](/metrics/loe.md) for semantics.

## Tasks

| Task | Assignee | Effort | Status |
| :--- | :--- | :--- | :--- |
| WP1 — AAS platform integration (digital infrastructure) | Mihai A. | — | Review |
| T2.1 — Co-creation platform (Nuoform) | Alexandru Bejenari | — | Done |
| T3.2 — Product Digital Twin (AAS model) | Eduard L | — | Done |
| T3.2 — Process Digital Twin (Tecnomatix simulation) | Eduard L | — | Done |
| T2.4 — Capacity Planner: LMS Scheduler Backend | LMS | — | Done |
| T2.4 — Capacity Planner: KF Planner UI | Alexandru Bejenari | 5d | Review |
| T2.4 — Capacity Planner: KF ↔ LMS Integration | Alexandru Bejenari | 10d | Review |
| T3.3 — IoT Monitoring: sensors deployment | Eduard Lazar | 5d | Review |
| T2.3 — Supply Chain Digital Twin: risk modelling | Eduard Lazar | — | In Progress |
| AAS import/export tooling (aas_export.py, import-demo.sh) | Eduard L | — | Done |
| Order_3_Aas shell (8 submodels, cost + schedule) | Eduard L | — | Done |
| Demo UI R3Group (Next 16: Design → Simulation → Shopfloor → Impact; LMS re-optimise) | Alexandru Bejenari | — | Done |
| OAuth2 auth-server public + per-client provisioning | Răzvan Boița | — | Done |
| ALADIN WP2 RunSheet service (nginx + Traefik routing) | Răzvan Boița | — | Done |
| Implement scheduling request endpoint (KF → LMS) | @backend | 2d | Review |
| Implement scheduler response parser | @backend | 2d | Review |
| Integrate scheduling results with planner UI | @frontend | 3d | Review |
| Implement planner visualization improvements (capacity / gaps) | @frontend | 2d | Review |
| Validate suitability constraints and scheduling logic | @backend | 2d | Review |
| Run first scheduling tests with real production data | @tech-lead | 1d | Review |
| Debug integration issues with LMS team | @tech-lead | 1d | Review |
| Integration validation review | @tech-lead | 0.5d | Review |
| M2F: finalise & confirm assumed KF-M2F shell structure | Eduard Lazăr / M2F | 2d | In Progress |
| Export R3 AAS shells → move to Netcompany-hosted R3 platform | Eduard Lazăr / Netcompany | 3d | In Progress |
| Share KF access for export to NetCompany | Eduard Lazăr | 1d | Done |
| Share KF-M2F shell with M2F (so they build their own) | Eduard Lazăr | 1d | Done |
| Connect + test M2F V2 API from new Nuoform | Alexandru Bejenari | 5d | In Progress |
| Re-point all connections to Netcompany-hosted R3 (go live) | Mihai A. | 3d | Todo |
| Pilot KF demo recordings (based on revised Nuoform) | Eduard Lazăr | 3d | Todo |
| State AI usage in R3 (declaration) | Eduard Lazăr | 1d | Todo |

See task concepts: [/tasks/r3-aas/index.md](/tasks/r3-aas/index.md)

## Dependencies

- [ai-rise-options](/projects/ai-rise-options.md)
