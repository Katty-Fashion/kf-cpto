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
| Done | 0d |
| Remaining | 52d |

> Effort is person-days (`Nd`) as declared in `kanban.md`.
> See [/metrics/loe.md](/metrics/loe.md) for semantics.

## Tasks

| Task | Assignee | Effort | Status |
| :--- | :--- | :--- | :--- |
| WP1 — AAS platform integration (digital infrastructure) | Mihai A. | — | Review |
| T2.1 — Co-creation platform (Nuoform) | Alexandru Bejenari | — | Done |
| T3.2 — Product Digital Twin (AAS model) | Răzvan Boița | — | Done |
| T3.2 — Process Digital Twin (Tecnomatix simulation) | Eduard Modreanu | — | Done |
| T2.4 — Capacity Planner: LMS Scheduler Backend | LMS | — | Done |
| T2.4 — Capacity Planner: KF Planner UI | Alexandru Bejenari | 5d | Review |
| T2.4 — Capacity Planner: KF ↔ LMS Integration | Alexandru Bejenari | 10d | Review |
| T3.3 — IoT Monitoring: sensors deployment | Eduard Modreanu | 5d | Review |
| T2.3 — Supply Chain Digital Twin: risk modelling | Eduard Lazăr | — | In Progress |
| AAS import/export tooling (aas_export.py, import-demo.sh) | Răzvan Boița | — | Done |
| Order_3_Aas shell (8 submodels, cost + schedule) | Răzvan Boița | — | Done |
| Demo UI R3Group (Next 16: Design → Simulation → Shopfloor → Impact; LMS re-optimise) | Alexandru Bejenari | — | Done |
| OAuth2 auth-server public + per-client provisioning | Răzvan Boița | — | Done |
| ALADIN WP2 RunSheet service (nginx + Traefik routing) | Răzvan Boița | — | Done |
| Clarificare acces server R3 (Vangelis) | Paul Stanciuc |  | Done |
| Clarificare format date platforma R3 | Alexandru Bejenari |  | Done |
| Feature set pentru lansare (MVP) | Eduard Lazăr |  | Todo |
| Ce este „Done" vs „Ready" pentru release | Eduard Lazăr |  | Todo |
| Decizie Made2Flow (demo vs integrare reală) | Eduard Lazăr |  | Todo |
| Review arhitectură | Răzvan Boița |  | Done |
| Identificare gaps / incomplete features | Alexandru Bejenari |  | Done |
| Sesiune demo produse (intern) | Eduard Lazăr |  | In Progress |
| Pregătire feature flags (ascundere features incomplete) | Mihai A. |  | Todo |
| Clarificare value proposition (perspectivă tehnică) | Eduard Lazăr |  | Todo |
| Validare integrare end-to-end (expunere API Nuoform) | Răzvan Boița |  | Done |
| Arhitectură multi-tenant (in place) | Eduard Modreanu |  | Done |
| Separare date per client (in place) | Eduard Modreanu |  | Done |
| Flow sistem (UI → AAS → backend) | Răzvan Boița |  | Done |
| Integrare între sisteme (Katty / LMS) | Alexandru Bejenari |  | Review |
| Multiple tipuri AAS → standardizare | Răzvan Boița |  | Done |
| Layout simplificat pilot (stații + flux + senzori) | Eduard Lazăr / Paul Stanciuc |  | Done |
| Integrare LMS (AAS extern) | Alexandru Bejenari |  | Review |
| Sketch → JSON → sistem | Alexandru Bejenari |  | Done |
| LMS specs + credentials | Alexandru Bejenari |  | Done |
| UI flow (parțial complet) | Alexandru Bejenari |  | Review |
| Backend alignment (după modificări Răzvan) | Alexandru Bejenari |  | Todo |
| Bug-uri identificate în sistem | Alexandru Bejenari |  | Todo |
| Vizualizare date / UI | Alexandru Bejenari |  | Done |
| Deploy AAS în Cloud (hosting) | Răzvan Boița / Eduard Lazăr |  | Done |
| Clarificare format date pentru platforma R3 | Alexandru Bejenari |  | Done |
| Instalare senzor 3 (poziție cutie/flux materiale) — T3.3 | Eduard Lazăr / Julia |  | Todo |
| Board central Kanban – single source of truth | Paul Stanciuc |  | Done |
| Task-uri ↔ Work Packages (WP mapping) | Paul Stanciuc |  | Done |
| Naming convention pentru task-uri (namespace per proiect) | Eduard Lazăr |  | Todo |
| Evitarea dublării task-urilor între tools | Eduard Lazăr |  | Todo |
| Reprezentare Gantt (timeline / corelare temporală) | Paul Stanciuc |  | Done |
| GitHub Actions pentru sync task-uri | Paul Stanciuc |  | Done |
| Generare automată status / reports | Paul Stanciuc |  | Done |
| Pipeline CI/CD (necesar pentru GTM) | Răzvan Boița |  | Done |
| Feature flags | Mihai A. |  | Todo |
| Telemetrie (monitorizare) | Mihai A. |  | Todo |
| Code quality / stability înainte de release | Mihai A. |  | Todo |
| Suport tehnic post-launch | Eduard Lazăr |  | Todo |
| Acces VPN + onboarding corect | Eduard Lazăr |  | Done |
| Acces corect la organizații (login flow issues) | Eduard Modreanu |  | In Progress |
| Conectivitate sisteme externe | Alexandru Bejenari |  | Todo |
| Testare demo produse (clienți + testeri interni) | Eduard Lazăr |  | In Progress |
| Sprint plan (tranziție către GTM) | Eduard Lazăr |  | Todo |
| Corelare Sprint tasks ↔ Work Packages | Paul Stanciuc |  | Done |
| Task-uri cu timeline (start/end) | Paul Stanciuc |  | Done |
| Rapoarte săptămânale (nu daily) | Eduard Lazăr |  | Todo |
| Gantt / timeline pentru progres | Paul Stanciuc |  | Done |
| Landing page (claritate produs) | Alexandru Bejenari |  | Todo |
| Demo / prezentare produs | Eduard Lazăr |  | In Progress |
| Definire tehnică monetizare (SaaS readiness) | Mihai A. |  | Todo |
| Input pentru CRM / pipeline (structură tehnică) | Eduard Lazăr |  | Todo |
| Implement scheduling request endpoint (KF → LMS) | @backend | 2d | Review |
| Implement scheduler response parser | @backend | 2d | Review |
| Integrate scheduling results with planner UI | @frontend | 3d | Review |
| Implement planner visualization improvements (capacity / gaps) | @frontend | 2d | Review |
| Validate suitability constraints and scheduling logic | @backend | 2d | Review |
| Run first scheduling tests with real production data | @tech-lead | 1d | Review |
| Debug integration issues with LMS team | @tech-lead | 1d | Review |
| Integration validation review | @tech-lead | 0.5d | Review |
| M2F: finalise & confirm assumed KF-M2F shell structure | Eduard Lazăr / M2F | 2d | In Progress |
| Export R3 AAS shells → move to Netcompany-hosted R3 platform | Mihai A. | 3d | Todo |
| Share KF access for export to NetCompany | Eduard Lazăr | 1d | Todo |
| Share KF-M2F shell with M2F (so they build their own) | Mihai A. | 1d | Todo |
| Connect + test M2F V2 API from new Nuoform | Alexandru Bejenari | 5d | Todo |
| Re-point all connections to Netcompany-hosted R3 (go live) | Mihai A. | 3d | Todo |
| Pilot KF demo recordings (based on revised Nuoform) | Eduard Lazăr | 3d | Todo |
| State AI usage in R3 (declaration) | Eduard Lazăr | 1d | Todo |

## Dependencies

- ai-rise _(not in tracked repo set)_
