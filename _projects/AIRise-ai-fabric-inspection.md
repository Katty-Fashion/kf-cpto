---
title: AIRise-ai-fabric-inspection
description: "AIFR-AI – AI-powered fabric defect detection system for Katty Fashion. CNN/YOLO-based real-time quality inspection on Jetson edge devices, integrated with MinIO/NiFi/Spark infrastructure. EU Horizon Europe – AIRISE Open Call 1."
project: AIRise-ai-fabric-inspection
type: eu-project
edit_url: "https://github.com/katty-fashion/AIRise-ai-fabric-inspection/edit/main/kanban.md"
generated: 2026-03-08T14:55:04.067577
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
| Tags | eu-project, ai, computer-vision, yolo, cnn, textile, defect-detection, jetson, edge-ai, minio, fastapi, nextjs |
| Dependencies | None |

## Current Sprint Kanban &nbsp; [Edit Kanban](https://github.com/katty-fashion/AIRise-ai-fabric-inspection/edit/main/kanban.md)

<div class="status-legend"><span class="status-pill status-pill--todo">Todo</span>
<span class="status-pill status-pill--in-progress">In Progress</span>
<span class="status-pill status-pill--review">Review</span>
<span class="status-pill status-pill--done">Done</span></div>

```mermaid
kanban
  Todo
    t5["Design data ingestion pipeline: Apache NiFi + MinIO on-premise"]
    t6["Design data preprocessing pipeline: Apache Spark + augmentation strategy"]
    t7["Define CNN/YOLO model architecture for fabric defect detection"]
    t8["Define defect taxonomy and annotation schema (Damage, Hole, Knot, Line, Oil Stain, Stain, Wrinkle)"]
    t9["Backend: FastAPI playback API (Plan B) — endpoints for defect results + annotations"]
    t10["Backend: PostgreSQL/Supabase schema for defect events and annotations"]
    t11["Frontend: PlaybackAnnotator UI — defect review and validation interface"]
    t12["Frontend: TextileViewer component — live WebRTC defect stream view"]
    t13["Jetson setup: YOLO multiprocess detector (4x parallel, 100+ FPS target)"]
    t14["Define S3 storage strategy: MinIO on-premise (active) + Cloudflare R2 (archive)"]
    t15["Define ELK stack monitoring: model prediction logs + feedback loop"]
    t16["Create architecture diagrams and technical documentation"]
    t17["Prepare KPI tracking dashboard (F1-score, inference speed, waste reduction)"]
    t18["Define model retraining pipeline (target: retraining within 48h of new data)"]
    t19["Prepare dissemination content: LinkedIn technical deep-dive post (mid-implementation)"]
  In-Progress
    t2["Define system architecture: edge (Jetson) + cloud (MinIO/NiFi/Spark)"]
    t4["Define streaming architecture: Plan A (WebRTC) vs Plan B (Async) vs Plan C (RTSP)"]
  Review
  Done
    t1["Project scope definition & AIRISE initialisation report review"]
    t3["Setup repository structure and KF-CPTO kanban integration"]
```

## Task Summary

| Task | Assignee | Effort | Start | End | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Project scope definition & AIRISE initialisation report review | @ps.tech | 1d | 2026-03-09 | 2026-03-09 | Done |
| Define system architecture: edge (Jetson) + cloud (MinIO/NiFi/Spark) | @el.tech | 3d | 2026-03-09 | 2026-03-11 | In Progress |
| Setup repository structure and KF-CPTO kanban integration | @alexandru.bejenari | 1d | 2026-03-09 | 2026-03-09 | Done |
| Define streaming architecture: Plan A (WebRTC) vs Plan B (Async) vs Plan C (RTSP) | @el.tech | 1d | 2026-03-10 | 2026-03-10 | In Progress |
| Design data ingestion pipeline: Apache NiFi + MinIO on-premise | @razvan.boita | 2d | 2026-03-11 | 2026-03-12 | Todo |
| Design data preprocessing pipeline: Apache Spark + augmentation strategy | @razvan.boita | 2d | 2026-03-13 | 2026-03-14 | Todo |
| Define CNN/YOLO model architecture for fabric defect detection | @el.tech | 3d | 2026-03-13 | 2026-03-17 | Todo |
| Define defect taxonomy and annotation schema (Damage, Hole, Knot, Line, Oil Stain, Stain, Wrinkle) | @ps.tech | 1d | 2026-03-13 | 2026-03-13 | Todo |
| Backend: FastAPI playback API (Plan B) — endpoints for defect results + annotations | @razvan.boita | 3d | 2026-03-16 | 2026-03-18 | Todo |
| Backend: PostgreSQL/Supabase schema for defect events and annotations | @razvan.boita | 2d | 2026-03-19 | 2026-03-20 | Todo |
| Frontend: PlaybackAnnotator UI — defect review and validation interface | @alexandru.bejenari | 3d | 2026-03-16 | 2026-03-18 | Todo |
| Frontend: TextileViewer component — live WebRTC defect stream view | @alexandru.bejenari | 2d | 2026-03-19 | 2026-03-20 | Todo |
| Jetson setup: YOLO multiprocess detector (4x parallel, 100+ FPS target) | @el.tech | 2d | 2026-03-19 | 2026-03-20 | Todo |
| Define S3 storage strategy: MinIO on-premise (active) + Cloudflare R2 (archive) | @razvan.boita | 1d | 2026-03-20 | 2026-03-20 | Todo |
| Define ELK stack monitoring: model prediction logs + feedback loop | @el.tech | 1d | 2026-03-20 | 2026-03-20 | Todo |
| Create architecture diagrams and technical documentation | @alexandru.bejenari | 1d | 2026-03-20 | 2026-03-20 | Todo |
| Prepare KPI tracking dashboard (F1-score, inference speed, waste reduction) | @ps.tech | 1d | 2026-03-21 | 2026-03-21 | Todo |
| Define model retraining pipeline (target: retraining within 48h of new data) | @el.tech | 2d | 2026-03-23 | 2026-03-24 | Todo |
| Prepare dissemination content: LinkedIn technical deep-dive post (mid-implementation) | @ps.tech | 1d | 2026-03-25 | 2026-03-25 | Todo |

## LOE Summary

| Metric | Value |
| :--- | :--- |
| Total Effort | 33.0d |
| In Progress | 4.0d |
| Completed | 2.0d |
| Remaining | 31.0d |

## Sprint Timeline

```mermaid
gantt
    title S1 — AIRise-ai-fabric-inspection
    dateFormat YYYY-MM-DD
    excludes weekends

    Project scope definition & AIRISE initialisation report review :done, 2026-03-09, 2026-03-09
    Setup repository structure and KF-CPTO kanban integration :done, 2026-03-09, 2026-03-09
    Define system architecture  edge (Jetson) + cloud (MinIO/NiFi/Spark) :active, 2026-03-09, 2026-03-11
    Define streaming architecture  Plan A (WebRTC) vs Plan B (Async) vs Plan C (RTSP) :active, 2026-03-10, 2026-03-10
    Design data ingestion pipeline  Apache NiFi + MinIO on-premise :2026-03-11, 2026-03-12
    Design data preprocessing pipeline  Apache Spark + augmentation strategy :2026-03-13, 2026-03-14
    Define CNN/YOLO model architecture for fabric defect detection :2026-03-13, 2026-03-17
    Define defect taxonomy and annotation schema (Damage, Hole, Knot, Line, Oil Stain, Stain, Wrinkle) :2026-03-13, 2026-03-13
    Backend  FastAPI playback API (Plan B) — endpoints for defect results + annotations :2026-03-16, 2026-03-18
    Backend  PostgreSQL/Supabase schema for defect events and annotations :2026-03-19, 2026-03-20
    Frontend  PlaybackAnnotator UI — defect review and validation interface :2026-03-16, 2026-03-18
    Frontend  TextileViewer component — live WebRTC defect stream view :2026-03-19, 2026-03-20
    Jetson setup  YOLO multiprocess detector (4x parallel, 100+ FPS target) :2026-03-19, 2026-03-20
    Define S3 storage strategy  MinIO on-premise (active) + Cloudflare R2 (archive) :2026-03-20, 2026-03-20
    Define ELK stack monitoring  model prediction logs + feedback loop :2026-03-20, 2026-03-20
    Create architecture diagrams and technical documentation :2026-03-20, 2026-03-20
    Prepare KPI tracking dashboard (F1-score, inference speed, waste reduction) :2026-03-21, 2026-03-21
    Define model retraining pipeline (target  retraining within 48h of new data) :2026-03-23, 2026-03-24
    Prepare dissemination content  LinkedIn technical deep-dive post (mid-implementation) :2026-03-25, 2026-03-25
```

## Effort Distribution

```mermaid
pie title Effort by Status
    "Todo" : 27.0
    "In Progress" : 4.0
    "Done" : 2.0
```

## Links

- [Edit Kanban](https://github.com/katty-fashion/AIRise-ai-fabric-inspection/edit/main/kanban.md)
- [Repository](https://github.com/katty-fashion/AIRise-ai-fabric-inspection)
- [Kanban Board](https://github.com/katty-fashion/AIRise-ai-fabric-inspection/blob/main/kanban.md)

---

*Auto-generated by KF Aggregator*