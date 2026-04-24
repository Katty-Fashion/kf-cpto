---
project: r3group-kf
description: "R3GROUP Katty Fashion pilot – digital tools for co-creation, digital twins and technician capacity planning"
type: eu-project

team:
  CPTO: el.tech@katty-fashion.ro
  Tech Lead: eduard.modreanu@katty-fashion.ro
  Front-End: alexandru.bejenari@katty-fashion.ro
  Back-End: razvan.boita@katty-fashion.ro
  Product Owner: ps.tech@katty-fashion.ro

sprint: S2
sprint_start: 2026-03-16
sprint_end: 2026-04-03

depends_on: [ai-rise]
tags: [r3group, digital-twin, capacity-planner, manufacturing]
---

# Project Kanban — R3GROUP Katty Fashion (M36+)

## Project Context (Updated M36)

Katty Fashion implements the **R3GROUP Horizon Europe pilot** to enable **digital integration between product development and manufacturing processes**.

The pilot introduces a **digital manufacturing ecosystem** composed of the following core systems:

1. **Co-Creation Platform (T2.1)**
   - Nuoform B2B collaboration platform
   - Fully implemented and tested with 2 pilot clients
   - Handles: technical packs, orders, receptions, inventory
   - Integrated with **Made2Flow sustainability API**

2. **Product Digital Twin (T3.2)**
   - AAS-compliant structure finalized
   - Integrates product lifecycle data: technical packs, order metadata, manufacturing processes

3. **Process Digital Twin (T3.2)**
   - Implemented using **Siemens Tecnomatix simulation**
   - Validated using historical production data
   - Enables workflow balancing and production simulations

4. **Technician Capacity Planner (T2.4)**
   - Planner UI implemented in **Katty Fashion platform**
   - Mathematical scheduling model developed by **LMS**
   - Integration between UI and LMS scheduler currently underway

5. **IoT Monitoring (T3.3)**
   - Operator presence sensors (60GHz radar)
   - Energy consumption monitoring
   - Sensors deployed and validated in production environment

> **Final objective:** Create a **digital thread between product design, planning and manufacturing operations**, enabling a **reconfigurable production system**.

---

## Status General M36

| Pillar | Component | Status |
|---|---|---|
| WP1 — Digital Infrastructure | AAS platform integration | 90% |
| T2.1 — Co-creation platform | Nuoform platform | ✅ Completed |
| T3.2 — Product Digital Twin | AAS model | ✅ Completed |
| T3.2 — Process Digital Twin | Tecnomatix simulation | ✅ Implemented & validated |
| T2.4 — Capacity Planner | LMS Scheduler Backend | ✅ Completed |
| T2.4 — Capacity Planner | KF Planner UI | 🔄 Near completion |
| T2.4 — Capacity Planner | KF ↔ LMS Integration | 🔄 In progress |
| T3.3 — IoT Monitoring | Sensors deployment | 🧪 Testing |
| T2.3 — Supply Chain Digital Twin | Risk modelling | 🔄 Running |

---

## KPI Targets

| KPI | Target |
|---|---|
| Scrap reduction | −20% |
| Reconfiguration time reduction | −35% |
| Production lead time reduction | −50% |
| Pre-production waste reduction | −95% |

---

## Current Technical Integration Focus

**Technician Capacity Planner integration**

```
KF Planner UI
  ↓ Generate AAS JSON
  ↓ Send to LMS Scheduling API
  ↓ LMS Optimization Algorithm
  ↓ Return schedule assignments
  ↓ Display schedule in KF UI
```

> Integration milestone: **M42 (June 2026)**

---

## Tasks — Sprint S2 (16 March → 03 April 2026)

<!-- Valid statuses: Todo, In Progress, Review, Done -->

| Task | Assignee | Effort | Start | End | Status |
|---|---|---|---|---|---|
| Review LMS API endpoints and AAS structure | @tech-lead | 1d | 2026-03-16 | 2026-03-16 | Todo |
| Technical architecture alignment for Planner integration | @tech-lead | 1d | 2026-03-17 | 2026-03-17 | Todo |
| Define integration pipeline (KF UI → LMS Scheduler → KF UI) | @tech-lead | 1d | 2026-03-18 | 2026-03-18 | Todo |
| Implement automatic AAS JSON export from KF platform | @backend | 2d | 2026-03-16 | 2026-03-18 | Todo |
| Implement scheduling request endpoint (KF → LMS) | @backend | 2d | 2026-03-19 | 2026-03-21 | Todo |
| Implement scheduler response parser | @backend | 2d | 2026-03-22 | 2026-03-24 | Todo |
| Integrate scheduling results with planner UI | @frontend | 3d | 2026-03-19 | 2026-03-24 | Todo |
| Implement planner visualization improvements (capacity / gaps) | @frontend | 2d | 2026-03-25 | 2026-03-27 | Todo |
| Validate suitability constraints and scheduling logic | @backend | 2d | 2026-03-26 | 2026-03-28 | Todo |
| Run first scheduling tests with real production data | @tech-lead | 1d | 2026-03-28 | 2026-03-28 | Todo |
| Debug integration issues with LMS team | @tech-lead | 1d | 2026-03-31 | 2026-03-31 | Todo |
| Integration validation review | @tech-lead | 0.5d | 2026-04-03 | 2026-04-03 | Todo |

---

## Responsibilities Overview (Next 3 Weeks)

### Eduard Modreanu — Tech Lead (@tech-lead)

**Responsibilities:** architecture alignment · technical coordination with LMS · integration supervision · algorithm validation

**Main tasks:**
- Finalize integration design
- Coordinate API integration
- Validate scheduling logic
- Prepare technical documentation for R3GROUP

### Răzvan Boita — Backend (@backend)

**Responsibilities:** backend integration · AAS data pipeline · LMS scheduler communication

**Main tasks:**
- Generate AAS data structures
- Implement API calls to LMS
- Handle scheduling responses
- Ensure compatibility with KF data model

### Alexandru Bejenari — Frontend (@frontend)

**Responsibilities:** planner interface · scheduling visualization · integration with backend APIs

**Main tasks:**
- Connect planner UI with scheduling results
- Improve technician workload visualization
- Support planner interaction (calendar, capacity)

---

## Next Steps (Project Level)

| Priority | Action | Responsible |
|---|---|---|
| 🔴 High | Complete KF ↔ LMS scheduling integration | Backend + Frontend |
| 🔴 High | Validate scheduling algorithm with real production data | Tech Lead |
| 🟡 Medium | Integrate sensor data with digital twins | Backend |
| 🟡 Medium | Extend Process Digital Twin data exchange | Tech Lead |
| 🟢 Low | Prepare TRL7 pilot demonstration | Tech Lead |

---

## Milestones

| Milestone | Date |
|---|---|
| Integration testing start | March 2026 |
| Capacity planner integration | June 2026 (M42) |
| Pilot validation | Autumn 2026 |
| Project completion | End 2026 |

---

## Summary

The Katty Fashion pilot has successfully implemented most of the **digital infrastructure required for R3GROUP**.

Current focus is on **integrating the Technician Capacity Planner with the LMS optimization model**, which represents the final technical step toward a fully operational **digital manufacturing planning workflow**.
