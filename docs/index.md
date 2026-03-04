---
title: KF Team Dashboard
layout: default
---

# KF Team — Project Dashboard

> **Single Pane of Glass** · GitHub Native · Google Workspace Integration

---

## Quick Links

<div class="card-grid">

{% include card.html title="Kanban" description="All projects in one view" link="unified-kanban.html" %}
{% include card.html title="Calendar" description="CPTO 50h allocation" link="unified-calendar.html" %}
{% include card.html title="LOE Report" description="Level of Effort tracking" link="loe-report.html" %}

</div>

---

## Projects

<div class="card-grid">

{% include card.html title="AI-RISE" description="EU AI Project" status="Active" link="projects/ai-rise.html" %}
{% include card.html title="AIREGIO" description="EU Regional AI" status="Active" link="projects/airegio.html" %}
{% include card.html title="NuoForm" description="SaaS Platform" status="Active" link="projects/nuoform.html" %}
{% include card.html title="Waist Management" description="Health SaaS" status="Active" link="projects/waist-mgmt.html" %}

</div>

---

## Current Sprint Overview

```mermaid
gantt
    title Sprint Calendar
    dateFormat YYYY-MM-DD
    excludes weekends

    section Scrum
    Sprint 3 Planning        :crit, 2026-03-02, 1d
    Sprint 3 Active          :active, 2026-03-03, 9d
    Sprint 3 Demo + Retro    :crit, 2026-03-13, 1d
```

---

## CPTO Time Allocation

```mermaid
pie title Monthly 50h Allocation
    "Sync & Team Rhythm" : 10
    "Technical Health" : 12
    "Pre-Sales" : 8
    "EU Projects" : 10
    "SaaS Products" : 8
    "Team Events" : 2
```

---

*KF Team · Git-Native Project Management · [GitHub](https://github.com/kf-team/kf-cpto)*
