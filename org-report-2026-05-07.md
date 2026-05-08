# Katty-Fashion Org Review — 2026-05-07
**Baseline:** 2026-04-24 | **Delta period:** 13 days

---

## What Changed

### Summary Table

| Repository | Last Push | Commits (30d) | Branches | Open PRs | Δ Branches | Δ Open PRs | Δ Activity |
|---|---|---|---|---|---|---|---|
| **R3-AAS** | 2026-05-07 | 27 | 1 | 0 | new repo | — | NEW |
| **kf-dashboard** | 2026-05-03 | 11 | 195 | 3 | +95 ↑↑ | -4 ↓ | RESUMED |
| **kf-cpto** | 2026-05-04 | 7 | 2 | 0 | — | — | active |
| **tech_brainstorming** | 2026-05-06 | 4 | 1 | 0 | new repo | — | NEW |
| **nuoform-configs** | 2026-05-03 | 4 | 1 | 0 | — | — | RESUMED |
| **nuoform-config-server** | 2026-05-03 | 1 | 1 | 0 | — | — | RESUMED |
| **order-service** | 2026-05-06 | 3 | 4 | 0 | -21 ↓↓ | -2 ↓ | improved |
| **R3GROUP** | 2026-03-30 | 0 | 1 | 0 | — | — | dormant |
| **AIRise-ai-fabric-inspection** | 2026-03-09 | 0 | 1 | 0 | — | — | dormant |
| **AAS-setup** | 2026-03-02 | 0 | 1 | 0 | — | — | dormant |
| **ai-rise-options** | 2026-02-13 | 0 | 1 | 0 | — | — | dormant |
| **nuoform-docs** | 2025-06-24 | 0 | 1 | 0 | — | — | dormant |
| **nuoform_runner** | 2025-07-31 | 0 | 1 | 0 | — | — | dormant |
| **notification-service** | 2025-10-15 | 0 | 1 | 0 | — | — | dormant |
| **api-gateway** | 2025-04-24 | 0 | 1 | 0 | -1 ↓ | — | dormant |
| **kf-keycloak-config** | 2024-12-04 | 0 | 2 | 0 | — | — | dormant |
| **discovery-service** | 2024-06-06 | 0 | 1 | 0 | — | — | dormant |
| **kf-ai-yolov9** | 2024-05-08 | 0 | 1 | 0 | — | — | dormant |
| **kf-mqtt-broker** | 2024-05-07 | 0 | 1 | 0 | — | — | dormant |
| **kf-devices-ble-gateway** | 2024-04-23 | 0 | 1 | 0 | — | — | dormant |
| **kf-devices-efr-demos** | 2024-04-23 | 0 | 2 | 0 | — | — | dormant |
| **file-service** | 2025-06-02 | 0 | 1 | 0 | — | — | dormant |
| **api-requests** | 2025-04-30 | 0 | 1 | 0 | — | — | dormant |
| **demo-repository** | 2024-01-04 | 0 | 2 | 0 | — | — | dormant |
| **Aladin-01** | 2026-03-08 | 0 | 1 | 0 | — | — | dormant |
| **project-template** | 2026-03-06 | 0 | 1 | 0 | — | — | dormant |
| **NuoForm---GTM** | 2026-03-05 | 0 | 1 | 0 | — | — | dormant |
| **Edi-test** | 2026-03-06 | 0 | 1 | 0 | — | — | dormant |
| **order-service-config** | — | 0 | 0 | 0 | — | — | empty |
| **threejs-test** | — | 0 | 0 | 0 | — | — | empty |

---

## Notable Movements

### Positive
- **order-service branches**: 25 → 4. Significant cleanup — 21 stale branches deleted. 3 remaining (`NUOFORM-189-batches`, `NUOFORM-191-aas-export-fix`, `aas_stations`) are likely in-progress work.
- **order-service PRs**: 2 open → 0. Both closed.
- **kf-dashboard PRs**: 7 open → 3. Four PRs resolved since Apr 24.
- **kf-dashboard activity**: Resumed after weeks of silence. 11 commits by `eduardkf` (May 2–3) — CI/CD pipeline work (Woodpecker, Docker, Zot registry).
- **nuoform-configs + nuoform-config-server**: Both woke up — Supabase connection config changes and Woodpecker CI (May 3).
- **R3-AAS**: New repo, 27 commits in 10 days — most active repo in org right now.
- **tech_brainstorming**: New repo, 4 commits by `MyshaVoidWalker`.

### Concern
- **kf-dashboard branches**: 100 → 195. Nearly doubled while PRs were being closed. This suggests old feature branches are accumulating faster than they're being pruned. With only 3 open PRs this is not driven by active work — these are stale.

### Open PRs (3 remaining in kf-dashboard)
| PR | Title | Author | Last Updated | Reviewer |
|---|---|---|---|---|
| #150 | Aas stations integration | RazvanBoitaKf | 2026-04-24 | none assigned |
| #149 | Nuoform 188 onboarding | RazvanBoitaKf | 2026-04-24 | none assigned |
| #148 | Tech proces view | SashaBej | 2026-04-24 | eduardkf |

All three have been stale for 13 days since the nudge. No review has happened. #148 has `eduardkf` as a requested reviewer.

---

## Action Plan

### P1 — Do this week

1. **kf-dashboard: review the 3 stale PRs**
   - #148 (`Tech proces view`, SashaBej) — `eduardkf` is already assigned. Review or close.
   - #149, #150 (RazvanBoitaKf) — assign a reviewer or close if superseded by newer work.
   - If these branches are live in the codebase, merge them. If not, close with a note.

2. **kf-dashboard: purge stale branches (195 → target ~10)**
   - 3 open PRs means at most ~3 branches are active. The other ~190 are dead.
   - Run: `gh api repos/Katty-Fashion/kf-dashboard/branches?per_page=100` across pages, filter branches with no open PR and last commit older than 30 days, delete in bulk.
   - Recommend keeping: `master`/`main`, the 3 PR branches, and any explicitly named release/staging branches.

3. **order-service: resolve remaining 3 branches**
   - `aas_stations` — was the basis for merged PR #52. Likely safe to delete.
   - `NUOFORM-189-batches`, `NUOFORM-191-aas-export-fix` — check if active work or stale; assign PRs or delete.

### P2 — This month

4. **Delete empty repos** (zero content, no value)
   - `order-service-config` — 0 branches, 0 KB
   - `threejs-test` — 0 branches, 0 KB

5. **Delete obvious junk repos**
   - `demo-repository` — GitHub sample HTML repo, 2 KB, last push 2024-01-04
   - `Edi-test` — single-commit test repo, no value

6. **Consolidate Aladin-01 / project-template**
   - Both are public, both described as "Project template w/ reporting & Kanban", both dormant.
   - Decide which is canonical, archive or delete the other.

7. **Archive the Nuoform microservice graveyard** (all private, all dormant, no open PRs/issues)
   - `notification-service` (last push 2025-10)
   - `nuoform-config-server` — just had a CI commit; keep for now, re-evaluate in 30 days
   - `discovery-service` (last push 2024-06)
   - `file-service` (last push 2025-06)
   - `api-gateway` (last push 2025-04)
   - `api-requests` (last push 2025-04)
   - These are microservices from a defunct stack. Archive rather than delete — preserves history.

8. **Archive IoT/device repos** (dormant since April 2024, likely superseded by R3-AAS work)
   - `kf-mqtt-broker`
   - `kf-devices-ble-gateway`
   - `kf-devices-efr-demos`
   - `kf-ai-yolov9`

### P3 — Housekeeping (low urgency)

9. **Add descriptions** to repos missing them: `order-service`, `kf-dashboard`, `AAS-setup`, `nuoform-configs`, `tech_brainstorming`, `R3-AAS`.

10. **nuoform_runner** (Terraform/HCL, 7.5 MB, dormant since 2025-07) — archive if infra is decommissioned.

11. **AAS-setup** (354 MB Dockerfile repo, dormant since Mar 2026) — clarify if superseded by R3-AAS; if so archive.

---

## Health Snapshot

| Status | Repos |
|---|---|
| Active | R3-AAS, kf-cpto, kf-dashboard, order-service, nuoform-configs, nuoform-config-server, tech_brainstorming |
| Stale PRs | kf-dashboard (#148, #149, #150) |
| Branch debt | kf-dashboard (~190 stale), order-service (3 to resolve) |
| Delete | order-service-config, threejs-test, demo-repository, Edi-test |
| Archive candidates | notification-service, discovery-service, file-service, api-gateway, api-requests, kf-mqtt-broker, kf-devices-ble-gateway, kf-devices-efr-demos, kf-ai-yolov9, nuoform_runner, AAS-setup |
| Consolidate | Aladin-01 vs project-template |
| Healthy / monitor | R3GROUP, AIRise-ai-fabric-inspection, nuoform-docs, kf-keycloak-config, NuoForm---GTM |
