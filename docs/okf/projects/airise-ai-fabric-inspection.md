---
type: Project
title: AIRise-ai-fabric-inspection
description: AIFR-AI – AI-powered fabric defect detection system for Katty Fashion. CNN/YOLO-based real-time quality inspection on Jetson edge devices, integrated with MinIO/NiFi/Spark infrastructure. EU Horizon Europe – AIRISE Open Call 1.
resource:
  - "https://github.com/katty-fashion/AIRise-ai-fabric-inspection"
  - "https://katty-fashion.github.io/kf-cpto/projects/airise-ai-fabric-inspection/"
tags:
  - eu-project
  - ai
  - computer-vision
  - yolo
  - cnn
  - textile
  - defect-detection
  - jetson
  - edge-ai
  - minio
  - fastapi
  - nextjs
  - synthetic-data
  - grad-cam
  - shap
po: "@ps.tech"
lead: "@el.tech"
sprint: S1
---

# AIRise-ai-fabric-inspection

> AIFR-AI – AI-powered fabric defect detection system for Katty Fashion. CNN/YOLO-based real-time quality inspection on Jetson edge devices, integrated with MinIO/NiFi/Spark infrastructure. EU Horizon Europe – AIRISE Open Call 1.

## LOE Rollup

| Metric | Value |
| :--- | :--- |
| Total effort | 38d |
| Done | 2d |
| Remaining | 36d |

> Effort is person-days (`Nd`) as declared in `kanban.md`.
> See [/metrics/loe.md](/metrics/loe.md) for semantics.

## Tasks

| Task | Assignee | Effort | Status |
| :--- | :--- | :--- | :--- |
| Project scope definition & AIRISE initialisation report review | @ps.tech | 1d | Done |
| Setup repository structure and KF-CPTO kanban integration | @alexandru.bejenari | 1d | Done |
| Define system architecture: edge (Jetson) + cloud (MinIO/NiFi/Spark) | @el.tech | 3d | In Progress |
| Define streaming architecture — Plan B (Async Playback) selectat ca variantă recomandată | @el.tech | 1d | In Progress |
| [BLOCKER] Audit dataset existent — evaluare volum și calitate imagini defecte reale disponibile | @ps.tech | 1d | In Progress |
| [BLOCKER] Strategie generare date sintetice — prioritizare GAN/augmentare pentru suplimentare dataset | @el.tech | 2d | Todo |
| Design data ingestion pipeline: Apache NiFi + MinIO on-premise | @razvan.boita | 2d | Todo |
| Design data preprocessing pipeline: Apache Spark + augmentation strategy | @razvan.boita | 2d | Todo |
| Define defect taxonomy and annotation schema (Damage, Hole, Knot, Line, Oil Stain, Stain, Wrinkle) | @ps.tech | 1d | Todo |
| Define CNN/YOLO model architecture for fabric defect detection | @el.tech | 3d | Todo |
| Integrate model explainability: Grad-CAM + SHAP pentru vizualizare decizii AI | @el.tech | 2d | Todo |
| Backend: FastAPI playback API (Plan B) — endpoints for defect results + annotations | @razvan.boita | 3d | Todo |
| Backend: PostgreSQL/Supabase schema for defect events and annotations | @razvan.boita | 2d | Todo |
| Frontend: PlaybackAnnotator UI — defect review and validation interface | @alexandru.bejenari | 3d | Todo |
| Frontend: TextileViewer component — live WebRTC defect stream view | @alexandru.bejenari | 2d | Todo |
| Jetson setup: YOLO multiprocess detector (4x parallel, 100+ FPS target) | @el.tech | 2d | Todo |
| Define S3 storage strategy: MinIO on-premise (active) + Cloudflare R2 (archive) | @razvan.boita | 1d | Todo |
| Define ELK stack monitoring: model prediction logs + feedback loop | @el.tech | 1d | Todo |
| Create architecture diagrams and technical documentation | @alexandru.bejenari | 1d | Todo |
| Prepare KPI tracking dashboard (F1 ≥70-80%, inferență ≤1000ms, deșeuri -20%) | @ps.tech | 1d | Todo |
| Define model retraining pipeline (target: retraining within 48h of new data) | @el.tech | 2d | Todo |
| Prepare dissemination content: LinkedIn technical deep-dive post (mid-implementation) | @ps.tech | 1d | Todo |

See task concepts: [/tasks/airise-ai-fabric-inspection/index.md](/tasks/airise-ai-fabric-inspection/index.md)

## Dependencies

None declared.
