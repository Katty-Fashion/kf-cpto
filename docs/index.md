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
{% include card.html title="Dependencies" description="Inter-project dependency graph" link="dependency-graph.html" %}

</div>

---

## Projects

<div class="card-grid">

{% assign sorted_projects = site.projects | sort: "title" %}
{% for proj in sorted_projects %}
{% capture edit_footer %}<a href="{{ proj.edit_url }}">Edit Kanban</a>{% endcapture %}
{% include card.html title=proj.title description=proj.description status="Active" link=proj.url footer=edit_footer %}
{% endfor %}

</div>

{% if site.projects.size == 0 %}
*No projects found yet. Add a `kanban.md` to any repo in the katty-fashion org to get started.*
{% endif %}

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

*KF Team · Git-Native Project Management · [GitHub](https://github.com/katty-fashion/kf-cpto)*
