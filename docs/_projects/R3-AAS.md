---
title: R3-AAS
description: "R3GROUP Katty Fashion pilot – digital tools for co-creation, digital twins and technician capacity planning"
project: R3-AAS
type: eu-project
edit_url: "https://github.com/katty-fashion/R3-AAS/edit/main/kanban.md"
generated: 2026-06-05T14:53:18.989734
---

# R3-AAS

> R3GROUP Katty Fashion pilot – digital tools for co-creation, digital twins and technician capacity planning

## Status

| Metric | Value |
| :--- | :--- |
| Status | Active |
| Type | EU Project |
| PO | - |
| Lead | - |
| Current Sprint | S2 |
| Sprint Period | 2026-03-16 to 2026-04-03 |
| Tags | r3group, digital-twin, capacity-planner, manufacturing |
| Dependencies | [ai-rise]({{ '/projects/ai-rise/' | relative_url }}) |

## Current Sprint Kanban &nbsp; [Edit Kanban]({{ '/kanban-builder/' | relative_url }}?project=R3-AAS) <sup>·&nbsp;[raw](https://github.com/katty-fashion/R3-AAS/edit/main/kanban.md)</sup>

<div class="status-legend"><span class="status-pill status-pill--todo">Todo</span>
<span class="status-pill status-pill--in-progress">In Progress</span>
<span class="status-pill status-pill--review">Review</span>
<span class="status-pill status-pill--done">Done</span></div>

```mermaid
kanban
  Todo
    t4["Feature set pentru lansare (MVP)"]
    t5["Ce este „Done” vs „Ready” pentru release"]
    t8["Sesiune demo produse (intern)"]
    t9["Pregătire feature flags (ascundere features incomplete)"]
    t10["Clarificare value proposition (perspectivă tehnică)"]
    t14["Flow sistem (UI → AAS → backend)"]
    t18["Layout simplificat pilot (stații + flux + senzori)"]
    t23["Backend alignment (după modificări Răzvan)"]
    t24["Bug-uri identificate în sistem"]
    t28["Instalare senzor 3 (poziție cutie/flux materiale) — T3.3"]
    t30["Task-uri ↔ Work Packages (WP mapping)"]
    t31["Naming convention pentru task-uri (namespace per proiect)"]
    t32["Evitarea dublării task-urilor între tools"]
    t33["Reprezentare Gantt (timeline / corelare temporală)"]
    t37["Feature flags"]
    t38["Telemetrie (monitorizare)"]
    t39["Code quality / stability înainte de release"]
    t40["Suport tehnic post-launch"]
    t43["Conectivitate sisteme externe"]
    t44["Testare demo produse (clienți + testeri interni)"]
    t45["Interviuri tehnice full-stack"]
    t46["Evaluare competențe React + Node"]
    t47["Evaluare team fit (non-toxic, colaborativ)"]
    t48["Selectare profil echilibrat (nu doar tech heavy)"]
    t49["Sprint plan (tranziție către GTM)"]
    t50["Corelare Sprint tasks ↔ Work Packages"]
    t51["Task-uri cu timeline (start/end)"]
    t52["Rapoarte săptămânale (nu daily)"]
    t53["Gantt / timeline pentru progres"]
    t54["Landing page (claritate produs)"]
    t55["Demo / prezentare produs"]
    t56["Definire tehnică monetizare (SaaS readiness)"]
    t57["Input pentru CRM / pipeline (structură tehnică)"]
    t63["Implement scheduler response parser"]
    t66["Validate suitability constraints and scheduling logic"]
    t67["Run first scheduling tests with real production data"]
    t68["Debug integration issues with LMS team"]
    t69["Integration validation review"]
  In-Progress
    t1["Deploy AAS în Cloud (hosting)"]
    t2["Clarificare acces server R3 (Vangelis)"]
    t3["Clarificare format date platforma R3"]
    t6["Review arhitectură"]
    t7["Identificare gaps / incomplete features"]
    t15["Clarificare acces server R3 (Vangelis)"]
    t16["Integrare între sisteme (Katty / LMS)"]
    t17["Multiple tipuri AAS → standardizare"]
    t19["Integrare LMS (AAS extern)"]
    t22["UI flow (parțial complet)"]
    t26["Deploy AAS în Cloud (hosting)"]
    t27["Clarificare format date pentru platforma R3"]
    t29["Board central Kanban – single source of truth"]
    t42["Acces corect la organizații (login flow issues)"]
    t62["Implement scheduling request endpoint (KF → LMS)"]
    t64["Integrate scheduling results with planner UI"]
    t65["Implement planner visualization improvements (capacity / gaps)"]
  Review
    t21["LMS specs + credentials"]
    t25["Vizualizare date / UI"]
    t34["GitHub Actions pentru sync task-uri"]
    t35["Generare automată status / reports"]
    t36["Pipeline CI/CD (necesar pentru GTM)"]
  Done
    t11["Validare integrare end-to-end (expunere API Nuoform)"]
    t12["Arhitectură multi-tenant (in place)"]
    t13["Separare date per client (in place)"]
    t20["Sketch → JSON → sistem"]
    t41["Acces VPN + onboarding corect"]
    t58["Review LMS API endpoints and AAS structure"]
    t59["Technical architecture alignment for Planner integration"]
    t60["Define integration pipeline (KF UI → LMS Scheduler → KF UI)"]
    t61["Implement automatic AAS JSON export from KF platform"]
```

## Task Summary

| Task | Assignee | Effort | Start | End | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Deploy AAS în Cloud (hosting) | Răzvan Boița / Eduard Lazăr |  |  |  | In Progress |
| Clarificare acces server R3 (Vangelis) | Paul Stanciuc |  |  |  | In Progress |
| Clarificare format date platforma R3 | Alexandru Bejenari |  |  |  | In Progress |
| Decizie Made2Flow (demo vs integrare reală) | Eduard Lazăr / Paul Stanciuc |  |  |  | Decizie pending — P1 |
| Feature set pentru lansare (MVP) | Eduard Lazăr / Paul Stanciuc |  |  |  | Todo |
| Ce este „Done" vs „Ready" pentru release | Eduard Lazăr / Paul Stanciuc |  |  |  | Todo |
| Decizie Made2Flow (demo vs integrare reală) | Eduard Lazăr / Paul Stanciuc |  |  |  | Decizie pending |
| Review arhitectură | Răzvan Boița |  |  |  | In Progress |
| Identificare gaps / incomplete features | Alexandru Bejenari |  |  |  | In Progress |
| Sesiune demo produse (intern) | Paul Stanciuc |  |  |  | Todo |
| Pregătire feature flags (ascundere features incomplete) | Răzvan Boița |  |  |  | Todo |
| Clarificare value proposition (perspectivă tehnică) | Paul Stanciuc |  |  |  | Todo |
| Validare integrare end-to-end (expunere API Nuoform) | Răzvan Boița |  |  |  | Done |
| Arhitectură multi-tenant (in place) | Eduard Modreanu |  |  |  | Done |
| Separare date per client (in place) | Eduard Modreanu |  |  |  | Done |
| Flow sistem (UI → AAS → backend) | Răzvan Boița |  |  |  | Todo |
| Clarificare acces server R3 (Vangelis) | Paul Stanciuc |  |  |  | In Progress |
| Integrare între sisteme (Katty / LMS) | Alexandru Bejenari |  |  |  | In Progress |
| Multiple tipuri AAS → standardizare | Răzvan Boița |  |  |  | In Progress |
| Layout simplificat pilot (stații + flux + senzori) | Eduard Lazăr / Paul Stanciuc |  |  |  | Todo |
| Integrare LMS (AAS extern) | Alexandru Bejenari |  |  | ~1 lună | In Progress |
| Sketch → JSON → sistem | Alexandru Bejenari |  |  | — | Done |
| LMS specs + credentials | Alexandru Bejenari |  |  |  | Review |
| UI flow (parțial complet) | Alexandru Bejenari |  |  |  | In Progress |
| Backend alignment (după modificări Răzvan) | Alexandru Bejenari |  |  |  | Todo |
| Bug-uri identificate în sistem | Alexandru Bejenari |  |  |  | Todo |
| Vizualizare date / UI | Alexandru Bejenari |  |  |  | Review |
| Deploy AAS în Cloud (hosting) | Răzvan Boița / Eduard Lazăr |  |  |  | In Progress |
| Clarificare format date pentru platforma R3 | Alexandru Bejenari |  |  |  | In Progress |
| Instalare senzor 3 (poziție cutie/flux materiale) — T3.3 | Eduard Lazăr / Julia |  |  |  | Todo |
| Board central Kanban – single source of truth | Paul Stanciuc |  |  |  | In Progress |
| Task-uri ↔ Work Packages (WP mapping) | Paul Stanciuc |  |  |  | Todo |
| Naming convention pentru task-uri (namespace per proiect) | Paul Stanciuc |  |  |  | Todo |
| Evitarea dublării task-urilor între tools | Paul Stanciuc |  |  |  | Todo |
| Reprezentare Gantt (timeline / corelare temporală) | Paul Stanciuc |  |  |  | Todo |
| GitHub Actions pentru sync task-uri | Paul Stanciuc |  |  |  | Review |
| Generare automată status / reports | Paul Stanciuc |  |  |  | Review |
| Pipeline CI/CD (necesar pentru GTM) | Răzvan Boița |  |  |  | Review |
| Feature flags | Răzvan Boița |  |  |  | Todo |
| Telemetrie (monitorizare) | Răzvan Boița |  |  |  | Todo |
| Code quality / stability înainte de release | Răzvan Boița |  |  |  | Todo |
| Suport tehnic post-launch | Paul Stanciuc |  |  |  | Todo |
| Acces VPN + onboarding corect | Eduard Lazăr |  |  |  | Done |
| Acces corect la organizații (login flow issues) | Eduard Modreanu |  |  |  | In Progress |
| Conectivitate sisteme externe | Alexandru Bejenari |  |  |  | Todo |
| Testare demo produse (clienți + testeri interni) | Paul Stanciuc |  |  |  | Todo |
| Interviuri tehnice full-stack | Eduard Lazăr |  |  |  | Todo |
| Evaluare competențe React + Node | Eduard Lazăr |  |  |  | Todo |
| Evaluare team fit (non-toxic, colaborativ) | Eduard Lazăr |  |  |  | Todo |
| Selectare profil echilibrat (nu doar tech heavy) | Eduard Lazăr |  |  |  | Todo |
| Sprint plan (tranziție către GTM) | Paul Stanciuc |  |  |  | Todo |
| Corelare Sprint tasks ↔ Work Packages | Paul Stanciuc |  |  |  | Todo |
| Task-uri cu timeline (start/end) | Paul Stanciuc |  |  |  | Todo |
| Rapoarte săptămânale (nu daily) | Paul Stanciuc |  |  |  | Todo |
| Gantt / timeline pentru progres | Paul Stanciuc |  |  |  | Todo |
| Landing page (claritate produs) | Alexandru Bejenari |  |  |  | Todo |
| Demo / prezentare produs | Eduard Lazăr / Paul Stanciuc |  |  |  | Todo |
| Definire tehnică monetizare (SaaS readiness) | Răzvan Boița |  |  |  | Todo |
| Input pentru CRM / pipeline (structură tehnică) | Eduard Lazăr / Paul Stanciuc |  |  |  | Todo |
| Review LMS API endpoints and AAS structure | @tech-lead | 1d | 2026-03-16 | 2026-03-16 | Done |
| Technical architecture alignment for Planner integration | @tech-lead | 1d | 2026-03-17 | 2026-03-17 | Done |
| Define integration pipeline (KF UI → LMS Scheduler → KF UI) | @tech-lead | 1d | 2026-03-18 | 2026-03-18 | Done |
| Implement automatic AAS JSON export from KF platform | @backend | 2d | 2026-03-16 | 2026-03-18 | Done |
| Implement scheduling request endpoint (KF → LMS) | @backend | 2d | 2026-03-19 | 2026-03-21 | In Progress |
| Implement scheduler response parser | @backend | 2d | 2026-03-22 | 2026-03-24 | Todo |
| Integrate scheduling results with planner UI | @frontend | 3d | 2026-03-19 | 2026-03-24 | In Progress |
| Implement planner visualization improvements (capacity / gaps) | @frontend | 2d | 2026-03-25 | 2026-03-27 | In Progress |
| Validate suitability constraints and scheduling logic | @backend | 2d | 2026-03-26 | 2026-03-28 | Todo |
| Run first scheduling tests with real production data | @tech-lead | 1d | 2026-03-28 | 2026-03-28 | Todo |
| Debug integration issues with LMS team | @tech-lead | 1d | 2026-03-31 | 2026-03-31 | Todo |
| Integration validation review | @tech-lead | 0.5d | 2026-04-03 | 2026-04-03 | Todo |

## LOE Summary

| Metric | Value |
| :--- | :--- |
| Total Effort | 18.5d |
| In Progress | 7.0d |
| Completed | 5.0d |
| Remaining | 13.5d |

## Sprint Timeline

```mermaid
gantt
    title S2 — R3-AAS
    dateFormat YYYY-MM-DD
    excludes weekends

    Validare integrare end-to-end (expunere API Nuoform) :done, 2026-03-16, 1d
    Arhitectură multi-tenant (in place) :done, 2026-03-17, 1d
    Separare date per client (in place) :done, 2026-03-18, 1d
    Sketch → JSON → sistem :done, 2026-03-19, 1d
    Acces VPN + onboarding corect :done, 2026-03-20, 1d
    Review LMS API endpoints and AAS structure :done, 2026-03-16, 2026-03-16
    Technical architecture alignment for Planner integration :done, 2026-03-17, 2026-03-17
    Define integration pipeline (KF UI → LMS Scheduler → KF UI) :done, 2026-03-18, 2026-03-18
    Implement automatic AAS JSON export from KF platform :done, 2026-03-16, 2026-03-18
    Deploy AAS în Cloud (hosting) :active, 2026-03-18, 1d
    Clarificare acces server R3 (Vangelis) :active, 2026-03-19, 1d
    Clarificare format date platforma R3 :active, 2026-03-20, 1d
    Review arhitectură :active, 2026-03-21, 1d
    Identificare gaps / incomplete features :active, 2026-03-22, 1d
    Clarificare acces server R3 (Vangelis) :active, 2026-03-23, 1d
    Integrare între sisteme (Katty / LMS) :active, 2026-03-24, 1d
    Multiple tipuri AAS → standardizare :active, 2026-03-25, 1d
    Integrare LMS (AAS extern) :active, 2026-03-26, 1d
    UI flow (parțial complet) :active, 2026-03-27, 1d
    Deploy AAS în Cloud (hosting) :active, 2026-03-28, 1d
    Clarificare format date pentru platforma R3 :active, 2026-03-29, 1d
    Board central Kanban – single source of truth :active, 2026-03-30, 1d
    Acces corect la organizații (login flow issues) :active, 2026-03-31, 1d
    Implement scheduling request endpoint (KF → LMS) :active, 2026-03-19, 2026-03-21
    Integrate scheduling results with planner UI :active, 2026-03-19, 2026-03-24
    Implement planner visualization improvements (capacity / gaps) :active, 2026-03-25, 2026-03-27
    LMS specs + credentials :2026-03-27, 1d
    Vizualizare date / UI :2026-03-28, 1d
    GitHub Actions pentru sync task-uri :2026-03-29, 1d
    Generare automată status / reports :2026-03-30, 1d
    Pipeline CI/CD (necesar pentru GTM) :2026-03-31, 1d
    Feature set pentru lansare (MVP) :2026-04-01, 1d
    Ce este „Done” vs „Ready” pentru release :2026-04-02, 1d
    Sesiune demo produse (intern) :2026-04-03, 1d
    Pregătire feature flags (ascundere features incomplete) :2026-04-04, 1d
    Clarificare value proposition (perspectivă tehnică) :2026-04-05, 1d
    Flow sistem (UI → AAS → backend) :2026-04-06, 1d
    Layout simplificat pilot (stații + flux + senzori) :2026-04-07, 1d
    Backend alignment (după modificări Răzvan) :2026-04-08, 1d
    Bug-uri identificate în sistem :2026-04-09, 1d
    Instalare senzor 3 (poziție cutie/flux materiale) — T3.3 :2026-04-10, 1d
    Task-uri ↔ Work Packages (WP mapping) :2026-04-11, 1d
    Naming convention pentru task-uri (namespace per proiect) :2026-04-12, 1d
    Evitarea dublării task-urilor între tools :2026-04-13, 1d
    Reprezentare Gantt (timeline / corelare temporală) :2026-04-14, 1d
    Feature flags :2026-04-15, 1d
    Telemetrie (monitorizare) :2026-04-16, 1d
    Code quality / stability înainte de release :2026-04-17, 1d
    Suport tehnic post-launch :2026-04-18, 1d
    Conectivitate sisteme externe :2026-04-19, 1d
    Testare demo produse (clienți + testeri interni) :2026-04-20, 1d
    Interviuri tehnice full-stack :2026-04-21, 1d
    Evaluare competențe React + Node :2026-04-22, 1d
    Evaluare team fit (non-toxic, colaborativ) :2026-04-23, 1d
    Selectare profil echilibrat (nu doar tech heavy) :2026-04-24, 1d
    Sprint plan (tranziție către GTM) :2026-04-25, 1d
    Corelare Sprint tasks ↔ Work Packages :2026-04-26, 1d
    Task-uri cu timeline (start/end) :2026-04-27, 1d
    Rapoarte săptămânale (nu daily) :2026-04-28, 1d
    Gantt / timeline pentru progres :2026-04-29, 1d
    Landing page (claritate produs) :2026-04-30, 1d
    Demo / prezentare produs :2026-05-01, 1d
    Definire tehnică monetizare (SaaS readiness) :2026-05-02, 1d
    Input pentru CRM / pipeline (structură tehnică) :2026-05-03, 1d
    Implement scheduler response parser :2026-03-22, 2026-03-24
    Validate suitability constraints and scheduling logic :2026-03-26, 2026-03-28
    Run first scheduling tests with real production data :2026-03-28, 2026-03-28
    Debug integration issues with LMS team :2026-03-31, 2026-03-31
    Integration validation review :2026-04-03, 2026-04-03
    Decizie Made2Flow (demo vs integrare reală) :2026-04-03, 1d
    Decizie Made2Flow (demo vs integrare reală) :2026-04-04, 1d
```

## Effort Distribution

```mermaid
pie title Effort by Status
    "Todo" : 6.5
    "In Progress" : 7.0
    "Done" : 5.0
```

## Links

- [Edit Kanban]({{ '/kanban-builder/' | relative_url }}?project=R3-AAS) ·&nbsp;[raw](https://github.com/katty-fashion/R3-AAS/edit/main/kanban.md)
- [Repository](https://github.com/katty-fashion/R3-AAS)
- [Kanban Board](https://github.com/katty-fashion/R3-AAS/blob/main/kanban.md)

---

*Auto-generated by KF Aggregator*