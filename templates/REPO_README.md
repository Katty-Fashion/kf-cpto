# {PROJECT_NAME}

> {PROJECT_DESCRIPTION}

## Quick Links

- [KF Dashboard](https://katty-fashion.github.io/kf-cpto/) — Unified project view
- [Project Page](https://katty-fashion.github.io/kf-cpto/projects/{project-name}/) — Auto-generated from kanban
- [Unified Kanban](https://katty-fashion.github.io/kf-cpto/unified-kanban.html) — All tasks across KF Team

---

## Architecture

### High-Level Design (HLD) — Sequence Flow

```mermaid
sequenceDiagram
    participant Client
    participant API Gateway
    participant Service
    participant Database
    participant Cache
    participant External API

    Client->>API Gateway: HTTP Request
    API Gateway->>API Gateway: Auth / Rate Limit
    API Gateway->>Service: Forward Request

    Service->>Cache: Check Cache
    alt Cache Hit
        Cache-->>Service: Return Cached Data
    else Cache Miss
        Service->>Database: Query Data
        Database-->>Service: Return Data
        Service->>Cache: Store in Cache
    end

    opt External Integration
        Service->>External API: API Call
        External API-->>Service: Response
    end

    Service-->>API Gateway: Response
    API Gateway-->>Client: HTTP Response
```

### Backend Service Anatomy

Every backend service/container follows this standard architecture:

```mermaid
block-beta
    columns 3

    block:external:3
        A["API Layer (REST/GraphQL)"]
    end

    block:infra:3
        B["Networking"] C["Auth/Security"] D["Config"]
    end

    block:core:3
        E["Business Logic / Feature Code"]
    end

    block:observability:3
        F["Observability"] G["Telemetry"] H["Logging"]
    end

    block:io:3
        I["Database"] J["Cache"] K["Message Queue"]
    end

    block:output:3
        L["stdout"] M["stderr"] N["Metrics Endpoint"]
    end
```

**Layer Responsibilities:**

| Layer | Components | Purpose |
| :--- | :--- | :--- |
| **API Layer** | REST endpoints, GraphQL resolvers | External interface |
| **Infrastructure** | Network config, TLS, CORS, Auth middleware | Cross-cutting concerns |
| **Business Logic** | Domain models, services, handlers | Your feature code |
| **Observability** | OpenTelemetry, Prometheus, structured logs | Monitoring & debugging |
| **I/O** | PostgreSQL, Redis, RabbitMQ/Kafka | Data persistence & messaging |
| **Output** | stdout (logs), stderr (errors), /metrics | Container output streams |

**Minimum Requirements for Production:**

```yaml
# Every service must have:
observability:
  - health_check: /health
  - readiness: /ready
  - metrics: /metrics (Prometheus format)
  - tracing: OpenTelemetry spans

logging:
  - format: JSON structured
  - output: stdout (info), stderr (errors)
  - correlation_id: request tracing

config:
  - env_vars: 12-factor app
  - secrets: mounted from vault/k8s secrets
  - feature_flags: runtime toggles
```

### Frontend (React Web) Anatomy

```mermaid
block-beta
    columns 3

    block:entry:3
        A["Entry Point (main.tsx)"]
    end

    block:routing:3
        B["Router (React Router / Next.js)"]
    end

    block:state:3
        C["State Management"] D["API Client"] E["Auth Context"]
    end

    block:ui:3
        F["Pages / Views"]
    end

    block:components:3
        G["Components"] H["Hooks"] I["Utils"]
    end

    block:infra:3
        J["Design System"] K["i18n"] L["Analytics"]
    end
```

**Frontend Layer Responsibilities:**

| Layer | Components | Purpose |
| :--- | :--- | :--- |
| **Entry** | main.tsx, App.tsx | Bootstrap application |
| **Routing** | React Router, layouts | Navigation & URL mapping |
| **State** | Redux/Zustand, React Query, Context | Data management |
| **Pages** | Route components, views | Screen-level components |
| **Components** | Reusable UI, hooks, utilities | Building blocks |
| **Infrastructure** | Theme, translations, tracking | Cross-cutting concerns |

**Frontend Checklist:**

```yaml
# Every React app must have:
performance:
  - code_splitting: lazy loading routes
  - bundle_size: < 200KB initial JS
  - lighthouse: > 90 score

observability:
  - error_boundary: global error catching
  - analytics: page views, events
  - source_maps: uploaded to error tracker

security:
  - csp: Content Security Policy
  - auth: token refresh, secure storage
  - sanitization: XSS prevention
```

---

## Kanban Management

This repository uses a `kanban.md` file for task tracking that integrates with the [KF-CPTO Dashboard](https://github.com/katty-fashion/kf-cpto).

### Updating Tasks

Edit `kanban.md` in the repository root:

```markdown
---
project: {project-name}
description: "Short project description"
type: saas                # saas | eu-project | internal
po: "@product-owner"
lead: "@tech-lead"
sprint: S3
sprint_start: 2026-03-02
sprint_end: 2026-03-13
depends_on: []            # e.g. [nuoform, ai-rise]
tags: [frontend, mvp]     # free-form tags
---

# Project Kanban

| Task | Assignee | Effort | Status |
| :--- | :--- | :--- | :--- |
| Implement feature X | @developer | 3d | In Progress |
| Code review for Y | @reviewer | 1d | Review |
| Deploy to staging | @devops | 2d | Todo |
```

### Frontmatter Fields

| Field | Required | Description |
| :--- | :--- | :--- |
| `project` | Yes | Repo name (must match GitHub repo) |
| `description` | No | Short description shown on dashboard |
| `type` | No | `saas`, `eu-project`, or `internal` |
| `po` | No | Product owner contact |
| `lead` | No | Technical lead contact |
| `sprint` | Yes | Sprint identifier (S1, S2...) |
| `sprint_start` | Yes | Sprint start date (YYYY-MM-DD) |
| `sprint_end` | Yes | Sprint end date (YYYY-MM-DD) |
| `depends_on` | No | List of project names this depends on |
| `tags` | No | Free-form tags for categorization |

### Task Status Values

Only these four statuses are recognized by the dashboard. Use exact spelling.

| Status | Description | Dashboard Color |
| :--- | :--- | :--- |
| `Todo` | Not started | Blue |
| `In Progress` | Currently being worked on | Red |
| `Review` | Awaiting code review or approval | Orange |
| `Done` | Completed | Green |

### Kanban Columns

The table must have exactly four columns: **Task**, **Assignee**, **Effort**, **Status**. Do not add, remove, or rename columns — the aggregator parses this fixed format.

### Effort Format

Use `Nd` format where N is the number of days:
- `1d` — 1 day
- `0.5d` — Half day
- `3d` — 3 days

### Sprint Updates

Update the frontmatter at the start of each sprint:

```yaml
---
project: {project-name}
description: "Short project description"
type: saas
po: "@product-owner"
lead: "@tech-lead"
sprint: S4              # Increment sprint number
sprint_start: 2026-03-16  # New sprint start
sprint_end: 2026-03-27    # New sprint end
depends_on: [shared-auth]
tags: [frontend, mvp]
---
```

---

## Development

### Prerequisites

```bash
# Required tools
- Python 3.11+ / Node.js 20+
- Docker & Docker Compose
- kubectl (for K8s deployments)
```

### Setup

```bash
# Clone the repository
git clone https://github.com/katty-fashion/{project-name}.git
cd {project-name}

# Install dependencies
# Add project-specific setup commands here
```

### Running Locally

```bash
# Add project-specific run commands here
```

### Testing

```bash
# Add project-specific test commands here
```

---

## Project Structure

```
{project-name}/
├── kanban.md              # Task tracking (synced to KF-CPTO)
├── README.md              # This file
├── .github/
│   └── workflows/
│       └── notify-kf-cpto.yml  # Auto-sync to dashboard
├── src/                   # Source code
│   ├── api/               # API layer (routes, controllers)
│   ├── services/          # Business logic
│   ├── models/            # Data models
│   ├── config/            # Configuration
│   └── utils/             # Utilities
├── tests/                 # Test suites
├── docs/                  # Documentation
├── Dockerfile             # Container definition
└── docker-compose.yml     # Local dev environment
```

---

## KF-CPTO Integration

### Automatic Sync

When you push changes to `kanban.md`, the KF-CPTO dashboard automatically updates via GitHub Actions.

### Manual Trigger

```bash
# Via GitHub CLI
gh workflow run notify-kf-cpto.yml
```

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Update `kanban.md` with your task
3. Make your changes
4. Update task status in `kanban.md`
5. Commit and push
6. Create a Pull Request

---

## Team

| Role | Contact |
| :--- | :--- |
| Project Lead | @{lead} |
| Tech Lead | @{tech-lead} |
| Team | @katty-fashion/{project-name} |

---

*Part of [KF Team](https://github.com/katty-fashion) · Managed via [KF-CPTO](https://github.com/katty-fashion/kf-cpto)*
