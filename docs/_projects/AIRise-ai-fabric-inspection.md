---
title: AIRise-ai-fabric-inspection
description: "AIFR-AI \u2013 AI-powered fabric defect detection system for Katty Fashion. CNN/YOLO-based real-time quality inspection on Jetson edge devices, integrated with MinIO/NiFi/Spark infrastructure. EU Horizon Europe \u2013 AIRISE Open Call 1."
project: AIRise-ai-fabric-inspection
type: eu-project
edit_url: "https://github.com/katty-fashion/AIRise-ai-fabric-inspection/edit/main/kanban.md"
generated: 2026-10-26T17:57:27.280639
---

# AIRise-ai-fabric-inspection

> AIFR-AI – AI-powered fabric defect detection system for Katty Fashion. CNN/YOLO-based real-time quality inspection on Jetson edge devices, integrated with MinIO/NiFi/Spark infrastructure. EU Horizon Europe – AIRISE Open Call 1.

## Status

| Metric | Value |
| :--- | :--- |
| Status | Active |
| Type | EU Project |
| PO | @ps.tech |
| Lead | @el.tech |
| Current Sprint | S1 |
| Sprint Period | 2026-03-09 to 2026-03-20 |
| Tags | eu-project, ai, computer-vision, yolo, cnn, textile, defect-detection, jetson, edge-ai, minio, fastapi, nextjs, synthetic-data, grad-cam, shap |
| Dependencies | None |

## Current Sprint Kanban &nbsp; [Edit Kanban]({{ '/kanban-builder/' | relative_url }}?project=AIRise-ai-fabric-inspection) <sup>·&nbsp;[raw](https://github.com/katty-fashion/AIRise-ai-fabric-inspection/edit/main/kanban.md)</sup>

<div class="kanban-board">
  <div class="kanban-col kanban-col--todo">
    <div class="kanban-col__head">Todo <span class="kanban-col__count">17</span></div>
    <div class="kanban-card kanban-card--static">[BLOCKER] Strategie generare date sintetice — prioritizare GAN/augmentare pentru suplimentare dataset</div>
    <div class="kanban-card kanban-card--static">Design data ingestion pipeline: Apache NiFi + MinIO on-premise</div>
    <div class="kanban-card kanban-card--static">Design data preprocessing pipeline: Apache Spark + augmentation strategy</div>
    <div class="kanban-card kanban-card--static">Define defect taxonomy and annotation schema (Damage, Hole, Knot, Line, Oil Stain, Stain, Wrinkle)</div>
    <div class="kanban-card kanban-card--static">Define CNN/YOLO model architecture for fabric defect detection</div>
    <div class="kanban-card kanban-card--static">Integrate model explainability: Grad-CAM + SHAP pentru vizualizare decizii AI</div>
    <div class="kanban-card kanban-card--static">Backend: FastAPI playback API (Plan B) — endpoints for defect results + annotations</div>
    <div class="kanban-card kanban-card--static">Backend: PostgreSQL/Supabase schema for defect events and annotations</div>
    <div class="kanban-card kanban-card--static">Frontend: PlaybackAnnotator UI — defect review and validation interface</div>
    <div class="kanban-card kanban-card--static">Frontend: TextileViewer component — live WebRTC defect stream view</div>
    <div class="kanban-card kanban-card--static">Jetson setup: YOLO multiprocess detector (4x parallel, 100+ FPS target)</div>
    <div class="kanban-card kanban-card--static">Define S3 storage strategy: MinIO on-premise (active) + Cloudflare R2 (archive)</div>
    <div class="kanban-card kanban-card--static">Define ELK stack monitoring: model prediction logs + feedback loop</div>
    <div class="kanban-card kanban-card--static">Create architecture diagrams and technical documentation</div>
    <div class="kanban-card kanban-card--static">Prepare KPI tracking dashboard (F1 ≥70-80%, inferență ≤1000ms, deșeuri -20%)</div>
    <div class="kanban-card kanban-card--static">Define model retraining pipeline (target: retraining within 48h of new data)</div>
    <div class="kanban-card kanban-card--static">Prepare dissemination content: LinkedIn technical deep-dive post (mid-implementation)</div>
  </div>
  <div class="kanban-col kanban-col--in-progress">
    <div class="kanban-col__head">In Progress <span class="kanban-col__count">3</span></div>
    <div class="kanban-card kanban-card--static">Define system architecture: edge (Jetson) + cloud (MinIO/NiFi/Spark)</div>
    <div class="kanban-card kanban-card--static">Define streaming architecture — Plan B (Async Playback) selectat ca variantă recomandată</div>
    <div class="kanban-card kanban-card--static">[BLOCKER] Audit dataset existent — evaluare volum și calitate imagini defecte reale disponibile</div>
  </div>
  <div class="kanban-col kanban-col--review">
    <div class="kanban-col__head">Review <span class="kanban-col__count">0</span></div>
  </div>
  <div class="kanban-col kanban-col--done">
    <div class="kanban-col__head">Done <span class="kanban-col__count">2</span></div>
    <div class="kanban-card kanban-card--static">Project scope definition &amp; AIRISE initialisation report review</div>
    <div class="kanban-card kanban-card--static">Setup repository structure and KF-CPTO kanban integration</div>
  </div>
</div>

## Task Summary

| Task | Assignee | Effort | Start | End | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Project scope definition &amp; AIRISE initialisation report review | @ps.tech | 1d | 2026-03-09 | 2026-03-09 | Done |
| Setup repository structure and KF-CPTO kanban integration | @alexandru.bejenari | 1d | 2026-03-09 | 2026-03-09 | Done |
| Define system architecture: edge (Jetson) + cloud (MinIO/NiFi/Spark) | @el.tech | 3d | 2026-03-09 | 2026-03-11 | In Progress |
| Define streaming architecture — Plan B (Async Playback) selectat ca variantă recomandată | @el.tech | 1d | 2026-03-10 | 2026-03-10 | In Progress |
| [BLOCKER] Audit dataset existent — evaluare volum și calitate imagini defecte reale disponibile | @ps.tech | 1d | 2026-03-11 | 2026-03-11 | In Progress |
| [BLOCKER] Strategie generare date sintetice — prioritizare GAN/augmentare pentru suplimentare dataset | @el.tech | 2d | 2026-03-12 | 2026-03-13 | Todo |
| Design data ingestion pipeline: Apache NiFi + MinIO on-premise | @razvan.boita | 2d | 2026-03-11 | 2026-03-12 | Todo |
| Design data preprocessing pipeline: Apache Spark + augmentation strategy | @razvan.boita | 2d | 2026-03-13 | 2026-03-14 | Todo |
| Define defect taxonomy and annotation schema (Damage, Hole, Knot, Line, Oil Stain, Stain, Wrinkle) | @ps.tech | 1d | 2026-03-13 | 2026-03-13 | Todo |
| Define CNN/YOLO model architecture for fabric defect detection | @el.tech | 3d | 2026-03-13 | 2026-03-17 | Todo |
| Integrate model explainability: Grad-CAM + SHAP pentru vizualizare decizii AI | @el.tech | 2d | 2026-03-17 | 2026-03-18 | Todo |
| Backend: FastAPI playback API (Plan B) — endpoints for defect results + annotations | @razvan.boita | 3d | 2026-03-16 | 2026-03-18 | Todo |
| Backend: PostgreSQL/Supabase schema for defect events and annotations | @razvan.boita | 2d | 2026-03-19 | 2026-03-20 | Todo |
| Frontend: PlaybackAnnotator UI — defect review and validation interface | @alexandru.bejenari | 3d | 2026-03-16 | 2026-03-18 | Todo |
| Frontend: TextileViewer component — live WebRTC defect stream view | @alexandru.bejenari | 2d | 2026-03-19 | 2026-03-20 | Todo |
| Jetson setup: YOLO multiprocess detector (4x parallel, 100+ FPS target) | @el.tech | 2d | 2026-03-19 | 2026-03-20 | Todo |
| Define S3 storage strategy: MinIO on-premise (active) + Cloudflare R2 (archive) | @razvan.boita | 1d | 2026-03-20 | 2026-03-20 | Todo |
| Define ELK stack monitoring: model prediction logs + feedback loop | @el.tech | 1d | 2026-03-20 | 2026-03-20 | Todo |
| Create architecture diagrams and technical documentation | @alexandru.bejenari | 1d | 2026-03-20 | 2026-03-20 | Todo |
| Prepare KPI tracking dashboard (F1 ≥70-80%, inferență ≤1000ms, deșeuri -20%) | @ps.tech | 1d | 2026-03-21 | 2026-03-21 | Todo |
| Define model retraining pipeline (target: retraining within 48h of new data) | @el.tech | 2d | 2026-03-23 | 2026-03-24 | Todo |
| Prepare dissemination content: LinkedIn technical deep-dive post (mid-implementation) | @ps.tech | 1d | 2026-03-25 | 2026-03-25 | Todo |

## LOE Summary

| Metric | Value |
| :--- | :--- |
| Total Effort | 38.0d |
| In Progress | 5.0d |
| Completed | 2.0d |
| Remaining | 36.0d |

## Effort — Planned vs Done

```mermaid
pie showData title Effort — Planned vs Done (person-days)
    "Done" : 2.0
    "Planned" : 36.0
```

## Sprint Timeline

```mermaid
gantt
    title S1 — AIRise-ai-fabric-inspection (dated tasks)
    dateFormat YYYY-MM-DD
    excludes weekends

    Project scope definition & AIRISE initialisation report review :done, 2026-03-09, 2026-03-09
    Setup repository structure and KF-CPTO kanban integration :done, 2026-03-09, 2026-03-09
    Define system architecture edge (Jetson) + cloud (MinIO/NiFi/Spark) :crit, 2026-03-09, 2026-03-11
    Define streaming architecture — Plan B (Async Playback) selectat ca variantă recomandată :crit, 2026-03-10, 2026-03-10
    (BLOCKER) Audit dataset existent — evaluare volum și calitate imagini defecte reale disponibile :crit, 2026-03-11, 2026-03-11
    Design data ingestion pipeline Apache NiFi + MinIO on-premise :crit, 2026-03-11, 2026-03-12
    (BLOCKER) Strategie generare date sintetice — prioritizare GAN/augmentare pentru suplimentare dataset :crit, 2026-03-12, 2026-03-13
    Design data preprocessing pipeline Apache Spark + augmentation strategy :crit, 2026-03-13, 2026-03-14
    Define defect taxonomy and annotation schema (Damage, Hole, Knot, Line, Oil Stain, Stain, Wrinkle) :crit, 2026-03-13, 2026-03-13
    Define CNN/YOLO model architecture for fabric defect detection :crit, 2026-03-13, 2026-03-17
    Backend FastAPI playback API (Plan B) — endpoints for defect results + annotations :crit, 2026-03-16, 2026-03-18
    Frontend PlaybackAnnotator UI — defect review and validation interface :crit, 2026-03-16, 2026-03-18
    Integrate model explainability Grad-CAM + SHAP pentru vizualizare decizii AI :crit, 2026-03-17, 2026-03-18
    Backend PostgreSQL/Supabase schema for defect events and annotations :crit, 2026-03-19, 2026-03-20
    Frontend TextileViewer component — live WebRTC defect stream view :crit, 2026-03-19, 2026-03-20
    Jetson setup YOLO multiprocess detector (4x parallel, 100+ FPS target) :crit, 2026-03-19, 2026-03-20
    Define S3 storage strategy MinIO on-premise (active) + Cloudflare R2 (archive) :crit, 2026-03-20, 2026-03-20
    Define ELK stack monitoring model prediction logs + feedback loop :crit, 2026-03-20, 2026-03-20
    Create architecture diagrams and technical documentation :crit, 2026-03-20, 2026-03-20
    Prepare KPI tracking dashboard (F1 ≥70-80%, inferență ≤1000ms, deșeuri -20%) :crit, 2026-03-21, 2026-03-21
    Define model retraining pipeline (target retraining within 48h of new data) :crit, 2026-03-23, 2026-03-24
    Prepare dissemination content LinkedIn technical deep-dive post (mid-implementation) :crit, 2026-03-25, 2026-03-25
```

<p class="gantt-legend"><span class="pill pill--planned">Planned</span><span class="pill pill--active">In work</span><span class="pill pill--late">Late / At risk</span><span class="pill pill--done">Done</span></p>

## Links

- [Edit Kanban]({{ '/kanban-builder/' | relative_url }}?project=AIRise-ai-fabric-inspection) ·&nbsp;[raw](https://github.com/katty-fashion/AIRise-ai-fabric-inspection/edit/main/kanban.md)
- [Repository](https://github.com/katty-fashion/AIRise-ai-fabric-inspection)
- [Kanban Board](https://github.com/katty-fashion/AIRise-ai-fabric-inspection/blob/main/kanban.md)

---

*Auto-generated by KF Aggregator*