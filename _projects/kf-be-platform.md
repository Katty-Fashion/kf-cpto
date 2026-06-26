---
title: kf-be-platform
description: "EU Project"
project: kf-be-platform
type: eu-project
edit_url: "https://github.com/katty-fashion/kf-be-platform/edit/main/kanban.md"
generated: 2026-06-26T12:47:58.996837
---

# kf-be-platform

> EU Project

## Status

| Metric | Value |
| :--- | :--- |
| Status | Active |
| Type | EU Project |
| PO | @ma.tech |
| Lead | @el.tech |
| Current Sprint | S4 |
| Sprint Period | 2026-06-15 to 2026-06-26 |
| Tags | eu-project, circular-textiles, digital-platform, microfactory, dpp, manufacturing |
| Dependencies | [kf-platform]({{ '/projects/kf-platform/' | relative_url }}), [R3-AAS]({{ '/projects/r3-aas/' | relative_url }}) |

## Current Sprint Kanban &nbsp; [Edit Kanban]({{ '/kanban-builder/' | relative_url }}?project=kf-be-platform) <sup>·&nbsp;[raw](https://github.com/katty-fashion/kf-be-platform/edit/main/kanban.md)</sup>

<div class="kanban-board">
  <div class="kanban-col kanban-col--todo">
    <div class="kanban-col__head">Todo <span class="kanban-col__count">8</span></div>
    <div class="kanban-card kanban-card--static">IDP setup (Keycloak/Auth0/logTo) + SMTP server</div>
    <div class="kanban-card kanban-card--static">RBAC system (scopes, claims, middleware)</div>
    <div class="kanban-card kanban-card--static">Tenant management (CRUD, provisioning, S3 prefix)</div>
    <div class="kanban-card kanban-card--static">EPCIS Export (JSON, PDF, GS1 standard, possibly signed)</div>
    <div class="kanban-card kanban-card--static">LLM Ecodesign full integration — WP4 T4.1</div>
    <div class="kanban-card kanban-card--static">IoT Adapter &amp; Event Log (MQTT) — T2.5 ALADIN</div>
    <div class="kanban-card kanban-card--static">Notifications multi-channel (email, SMS, webhook, in-app)</div>
    <div class="kanban-card kanban-card--static">Data migration scripts KF → ALADIN (one-shot + rollback)</div>
  </div>
  <div class="kanban-col kanban-col--in-progress">
    <div class="kanban-col__head">In Progress <span class="kanban-col__count">2</span></div>
    <div class="kanban-card kanban-card--static">Database schema v2 design + migrations (multi-tenant RLS)</div>
    <div class="kanban-card kanban-card--static">CI/CD pipeline (GitHub Actions / GitLab CI)</div>
  </div>
  <div class="kanban-col kanban-col--review">
    <div class="kanban-col__head">Review <span class="kanban-col__count">0</span></div>
  </div>
  <div class="kanban-col kanban-col--done">
    <div class="kanban-col__head">Done <span class="kanban-col__count">0</span></div>
  </div>
</div>

## Task Summary

| Task | Assignee | Effort | Start | End | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Database schema v2 design + migrations (multi-tenant RLS) | @ma.tech | 10d | 2026-05-25 | 2026-06-21 | In Progress |
| CI/CD pipeline (GitHub Actions / GitLab CI) | @ma.tech | 2d | 2026-05-25 | 2026-06-07 | In Progress |
| IDP setup (Keycloak/Auth0/logTo) + SMTP server | @ma.tech | 5d | 2026-06-08 | 2026-06-28 | Todo |
| RBAC system (scopes, claims, middleware) | @ma.tech | 10d | 2026-06-08 | 2026-07-05 | Todo |
| Tenant management (CRUD, provisioning, S3 prefix) | @ma.tech | 10d | 2026-06-29 | 2026-07-19 | Todo |
| EPCIS Export (JSON, PDF, GS1 standard, possibly signed) | @ma.tech | 10d | 2026-10-19 | 2026-11-08 | Todo |
| LLM Ecodesign full integration — WP4 T4.1 | @ma.tech | 10d | 2026-10-26 | 2026-11-15 | Todo |
| IoT Adapter &amp; Event Log (MQTT) — T2.5 ALADIN | @ma.tech | 10d | 2026-11-02 | 2026-11-22 | Todo |
| Notifications multi-channel (email, SMS, webhook, in-app) | @ma.tech | 5d | 2026-11-23 | 2026-12-06 | Todo |
| Data migration scripts KF → ALADIN (one-shot + rollback) | @ma.tech | 5d | 2026-12-14 | 2026-12-27 | Todo |

## LOE Summary

| Metric | Value |
| :--- | :--- |
| Total Effort | 77.0d |
| In Progress | 12.0d |
| Completed | 0d |
| Remaining | 77.0d |

## Sprint Timeline

```mermaid
gantt
    title S4 — kf-be-platform
    dateFormat YYYY-MM-DD
    excludes weekends

    Database schema v2 design + migrations (multi-tenant RLS) :active, 2026-05-25, 2026-06-21
    CI/CD pipeline (GitHub Actions / GitLab CI) :active, 2026-05-25, 2026-06-07
    IDP setup (Keycloak/Auth0/logTo) + SMTP server :2026-06-08, 2026-06-28
    RBAC system (scopes, claims, middleware) :2026-06-08, 2026-07-05
    Tenant management (CRUD, provisioning, S3 prefix) :2026-06-29, 2026-07-19
    EPCIS Export (JSON, PDF, GS1 standard, possibly signed) :2026-10-19, 2026-11-08
    LLM Ecodesign full integration — WP4 T4.1 :2026-10-26, 2026-11-15
    IoT Adapter & Event Log (MQTT) — T2.5 ALADIN :2026-11-02, 2026-11-22
    Notifications multi-channel (email, SMS, webhook, in-app) :2026-11-23, 2026-12-06
    Data migration scripts KF → ALADIN (one-shot + rollback) :2026-12-14, 2026-12-27
```

## Links

- [Edit Kanban]({{ '/kanban-builder/' | relative_url }}?project=kf-be-platform) ·&nbsp;[raw](https://github.com/katty-fashion/kf-be-platform/edit/main/kanban.md)
- [Repository](https://github.com/katty-fashion/kf-be-platform)
- [Kanban Board](https://github.com/katty-fashion/kf-be-platform/blob/main/kanban.md)

---

*Auto-generated by KF Aggregator*