---
title: Unified Kanban
generated: 2026-03-09T07:46:05.788243
---

# KF Team — Unified Kanban

> Auto-generated from all project kanbans

<div class="status-legend"><span class="status-pill status-pill--todo">Todo</span>
<span class="status-pill status-pill--in-progress">In Progress</span>
<span class="status-pill status-pill--review">Review</span>
<span class="status-pill status-pill--done">Done</span></div>

```mermaid
kanban
  Todo
    task5["AIRise-ai-fabric-inspection: Design data ingestion pipeline: Apache NiFi + MinIO on-premise"]
    task6["AIRise-ai-fabric-inspection: Design data preprocessing pipeline: Apache Spark + augmentation strategy"]
    task7["AIRise-ai-fabric-inspection: Define CNN/YOLO model architecture for fabric defect detection"]
    task8["AIRise-ai-fabric-inspection: Define defect taxonomy and annotation schema (Damage, Hole, Knot, Line, Oil Stain, Stain, Wrinkle)"]
    task9["AIRise-ai-fabric-inspection: Backend: FastAPI playback API (Plan B) — endpoints for defect results + annotations"]
    task10["AIRise-ai-fabric-inspection: Backend: PostgreSQL/Supabase schema for defect events and annotations"]
    task11["AIRise-ai-fabric-inspection: Frontend: PlaybackAnnotator UI — defect review and validation interface"]
    task12["AIRise-ai-fabric-inspection: Frontend: TextileViewer component — live WebRTC defect stream view"]
    task13["AIRise-ai-fabric-inspection: Jetson setup: YOLO multiprocess detector (4x parallel, 100+ FPS target)"]
    task14["AIRise-ai-fabric-inspection: Define S3 storage strategy: MinIO on-premise (active) + Cloudflare R2 (archive)"]
    task15["AIRise-ai-fabric-inspection: Define ELK stack monitoring: model prediction logs + feedback loop"]
    task16["AIRise-ai-fabric-inspection: Create architecture diagrams and technical documentation"]
    task17["AIRise-ai-fabric-inspection: Prepare KPI tracking dashboard (F1-score, inference speed, waste reduction)"]
    task18["AIRise-ai-fabric-inspection: Define model retraining pipeline (target: retraining within 48h of new data)"]
    task19["AIRise-ai-fabric-inspection: Prepare dissemination content: LinkedIn technical deep-dive post (mid-implementation)"]
    task22["Aladin-01: Architecture documentation & DevOps playbook (Kubernetes, CI/CD, OAuth 2.0)"]
    task23["Aladin-01: B2B layer — core database schema & NuoForm instance setup (T2.2)"]
    task24["Aladin-01: B2B layer — Tech Pack & BOM backend services (T2.2)"]
    task25["Aladin-01: B2C frontend — OAuth 2.0 multi-tenant login & registration (T2.3)"]
    task26["Aladin-01: B2C frontend — Client Garment Configurator MVP (T2.3)"]
    task27["Aladin-01: | Todo"]
    task30["Edi-test: Documentation"]
    task35["NuoForm---GTM: Define MVP scope + success metrics"]
    task36["NuoForm---GTM: Market segmentation + ICP definition"]
    task37["NuoForm---GTM: Sustainability + compliance claims validation"]
    task38["NuoForm---GTM: Product requirements baseline (PRD-lite)"]
    task39["NuoForm---GTM: Define optimisation KPIs (efficiency %, waste %, cost)"]
    task40["NuoForm---GTM: Data model for materials, BOM, suppliers"]
    task41["NuoForm---GTM: UX architecture + MVP screen flows"]
    task42["NuoForm---GTM: Define layplan optimisation algorithm approach"]
    task43["NuoForm---GTM: BOM ingestion + validation workflow"]
    task44["NuoForm---GTM: Pattern file ingestion (DXF or equivalent)"]
    task45["NuoForm---GTM: Pattern geometry extraction"]
    task46["NuoForm---GTM: Layplan nesting engine (baseline optimisation)"]
    task47["NuoForm---GTM: Waste calculation engine (area, length, efficiency)"]
    task48["NuoForm---GTM: Waste cost model (direct + indirect costs)"]
    task49["NuoForm---GTM: Waste analytics API"]
    task50["NuoForm---GTM: Waste dashboard UI"]
    task51["NuoForm---GTM: Exportable waste report (PDF/HTML)"]
    task52["NuoForm---GTM: Circular initiatives catalogue (recycle, return, donation)"]
    task53["NuoForm---GTM: Waste reduction simulation scenarios"]
    task54["NuoForm---GTM: Traceability document generator"]
    task55["NuoForm---GTM: Role-based access (designer/factory/customer/admin)"]
    task56["NuoForm---GTM: Activity audit log"]
    task57["NuoForm---GTM: Internal QA testing"]
    task58["NuoForm---GTM: Performance tuning"]
    task59["NuoForm---GTM: Pilot partner shortlist"]
    task60["NuoForm---GTM: Pilot onboarding kit"]
    task61["NuoForm---GTM: Pilot garment baseline waste analysis"]
    task62["NuoForm---GTM: Pilot optimisation run + results"]
    task63["NuoForm---GTM: Case study generation"]
    task64["NuoForm---GTM: Pricing model definition"]
    task65["NuoForm---GTM: Landing page + positioning narrative"]
    task66["NuoForm---GTM: Sales demo script"]
    task67["NuoForm---GTM: CRM pipeline setup"]
    task68["NuoForm---GTM: Launch readiness review"]
    task69["NuoForm---GTM: MVP launch"]
    task72["R3GROUP: 2d"]
    task74["order-service: AAS integration with new Tech Process Structure"]
    task75["order-service: Implement telemetry and observability"]
    task76["order-service: Write documentation for backend API"]
    task77["order-service: Generate more photos for AiRise dataset"]
    task80["project-template: Define integration between ALADIN and NuoForm platform"]
    task81["project-template: Define Digital Product Passport (DPP) data model for garments"]
    task82["project-template: Design micro-factory orchestration workflow"]
    task83["project-template: Define circular production lifecycle (R-strategies: reuse, repair, recycle)"]
    task84["project-template: Frontend architecture for product configuration and customization UI"]
    task85["project-template: Backend services for product lifecycle and traceability"]
    task86["project-template: Define demonstrator products (T-shirt, Kidswear Parka, Blazer Dress)"]
    task87["project-template: Define API layer for design, production orchestration and DPP"]
    task88["project-template: Define integration with external services (manufacturing, supply chain, sustainability metrics)"]
    task89["project-template: Create architecture diagrams and technical documentation"]
    task90["project-template: Prepare roadmap and Level-of-Effort estimation for ALADIN implementation"]
    task91["project-template: Prepare dashboard integration for KF-CPTO monitoring"]
  In-Progress
    task2["AIRise-ai-fabric-inspection: Define system architecture: edge (Jetson) + cloud (MinIO/NiFi/Spark)"]
    task4["AIRise-ai-fabric-inspection: Define streaming architecture: Plan A (WebRTC) vs Plan B (Async) vs Plan C (RTSP)"]
    task21["Aladin-01: Initial platform architecture (WP2 / T2.1) — user personas & journey mapping"]
    task29["Edi-test: Initial architecture"]
    task33["NuoForm---GTM: Initial architecture (services, storage, auth, telemetry)"]
    task70["R3GROUP: 2d"]
    task71["R3GROUP: 3d"]
    task73["order-service: Tech Process Blocker - Template for Techpack, Copy Version for Order Entry"]
    task79["project-template: Define ALADIN system architecture (platform + microfactory orchestration)"]
  Review
  Done
    task1["AIRise-ai-fabric-inspection: Project scope definition & AIRISE initialisation report review"]
    task3["AIRise-ai-fabric-inspection: Setup repository structure and KF-CPTO kanban integration"]
    task20["Aladin-01: Project setup & repo bootstrap"]
    task28["Edi-test: Project setup"]
    task31["NuoForm---GTM: Project kickoff + team alignment"]
    task32["NuoForm---GTM: Project setup (repo, CI/CD, environments)"]
    task34["NuoForm---GTM: Vision statement + problem definition"]
    task78["project-template: Project scope definition and requirements analysis"]
```

## Summary by Project

| Project | Todo | In Progress | Review | Done | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| AIRise-ai-fabric-inspection | 15 | 2 | 0 | 2 | 19 |
| Aladin-01 | 6 | 1 | 0 | 1 | 8 |
| Edi-test | 1 | 1 | 0 | 1 | 3 |
| NuoForm---GTM | 35 | 1 | 0 | 3 | 39 |
| R3GROUP | 1 | 2 | 0 | 0 | 3 |
| order-service | 4 | 1 | 0 | 0 | 5 |
| project-template | 12 | 1 | 0 | 1 | 14 |