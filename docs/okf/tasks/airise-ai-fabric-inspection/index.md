# Tasks — AIRise-ai-fabric-inspection

> Task concepts for [AIRise-ai-fabric-inspection](/projects/airise-ai-fabric-inspection.md).
> Each file is an addressable OKF ``type: Task`` concept.

- [Project scope definition & AIRISE initialisation report review](/tasks/airise-ai-fabric-inspection/project-scope-definition-airise-initialisation-report-review.md)
- [Setup repository structure and KF-CPTO kanban integration](/tasks/airise-ai-fabric-inspection/setup-repository-structure-and-kf-cpto-kanban-integration.md)
- [Define system architecture: edge (Jetson) + cloud (MinIO/NiFi/Spark)](/tasks/airise-ai-fabric-inspection/define-system-architecture-edge-jetson-cloud-minio-nifi-spark.md)
- [Define streaming architecture — Plan B (Async Playback) selectat ca variantă recomandată](/tasks/airise-ai-fabric-inspection/define-streaming-architecture-plan-b-async-playback-selectat-ca-variant-recomandat.md)
- [[BLOCKER] Audit dataset existent — evaluare volum și calitate imagini defecte reale disponibile](/tasks/airise-ai-fabric-inspection/blocker-audit-dataset-existent-evaluare-volum-i-calitate-imagini-defecte-reale-disponibile.md)
- [[BLOCKER] Strategie generare date sintetice — prioritizare GAN/augmentare pentru suplimentare dataset](/tasks/airise-ai-fabric-inspection/blocker-strategie-generare-date-sintetice-prioritizare-gan-augmentare-pentru-suplimentare-dataset.md)
- [Design data ingestion pipeline: Apache NiFi + MinIO on-premise](/tasks/airise-ai-fabric-inspection/design-data-ingestion-pipeline-apache-nifi-minio-on-premise.md)
- [Design data preprocessing pipeline: Apache Spark + augmentation strategy](/tasks/airise-ai-fabric-inspection/design-data-preprocessing-pipeline-apache-spark-augmentation-strategy.md)
- [Define defect taxonomy and annotation schema (Damage, Hole, Knot, Line, Oil Stain, Stain, Wrinkle)](/tasks/airise-ai-fabric-inspection/define-defect-taxonomy-and-annotation-schema-damage-hole-knot-line-oil-stain-stain-wrinkle.md)
- [Define CNN/YOLO model architecture for fabric defect detection](/tasks/airise-ai-fabric-inspection/define-cnn-yolo-model-architecture-for-fabric-defect-detection.md)
- [Integrate model explainability: Grad-CAM + SHAP pentru vizualizare decizii AI](/tasks/airise-ai-fabric-inspection/integrate-model-explainability-grad-cam-shap-pentru-vizualizare-decizii-ai.md)
- [Backend: FastAPI playback API (Plan B) — endpoints for defect results + annotations](/tasks/airise-ai-fabric-inspection/backend-fastapi-playback-api-plan-b-endpoints-for-defect-results-annotations.md)
- [Backend: PostgreSQL/Supabase schema for defect events and annotations](/tasks/airise-ai-fabric-inspection/backend-postgresql-supabase-schema-for-defect-events-and-annotations.md)
- [Frontend: PlaybackAnnotator UI — defect review and validation interface](/tasks/airise-ai-fabric-inspection/frontend-playbackannotator-ui-defect-review-and-validation-interface.md)
- [Frontend: TextileViewer component — live WebRTC defect stream view](/tasks/airise-ai-fabric-inspection/frontend-textileviewer-component-live-webrtc-defect-stream-view.md)
- [Jetson setup: YOLO multiprocess detector (4x parallel, 100+ FPS target)](/tasks/airise-ai-fabric-inspection/jetson-setup-yolo-multiprocess-detector-4x-parallel-100-fps-target.md)
- [Define S3 storage strategy: MinIO on-premise (active) + Cloudflare R2 (archive)](/tasks/airise-ai-fabric-inspection/define-s3-storage-strategy-minio-on-premise-active-cloudflare-r2-archive.md)
- [Define ELK stack monitoring: model prediction logs + feedback loop](/tasks/airise-ai-fabric-inspection/define-elk-stack-monitoring-model-prediction-logs-feedback-loop.md)
- [Create architecture diagrams and technical documentation](/tasks/airise-ai-fabric-inspection/create-architecture-diagrams-and-technical-documentation.md)
- [Prepare KPI tracking dashboard (F1 ≥70-80%, inferență ≤1000ms, deșeuri -20%)](/tasks/airise-ai-fabric-inspection/prepare-kpi-tracking-dashboard-f1-70-80-inferen-1000ms-de-euri-20.md)
- [Define model retraining pipeline (target: retraining within 48h of new data)](/tasks/airise-ai-fabric-inspection/define-model-retraining-pipeline-target-retraining-within-48h-of-new-data.md)
- [Prepare dissemination content: LinkedIn technical deep-dive post (mid-implementation)](/tasks/airise-ai-fabric-inspection/prepare-dissemination-content-linkedin-technical-deep-dive-post-mid-implementation.md)
