---
title: KF Team Dashboard
layout: default
---

# KF Team — Project Dashboard

> **Single Pane of Glass** · GitHub Native · Google Workspace Integration

{% if site.data.sync_status.sheets_export.last_run_status == 'failed' %}
<div class="sync-banner" role="alert">
  <strong>Heads up:</strong> the downstream Google Sheet export failed at
  {{ site.data.sync_status.sheets_export.last_run_at }}.
  <em>The dashboard you're looking at is the canonical view and is current.</em>
  The `LOE` tab in Google Sheets still shows the last successful export — it was
  <strong>not</strong> blanked.
  {% if site.data.sync_status.sheets_export.last_error_issue %}
    See <a href="{{ site.data.sync_status.sheets_export.last_error_issue }}">the sync-failure issue</a> for details.
  {% endif %}
</div>
{% endif %}

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

## Portfolio Effort — Planned vs Done

{% assign done = 0 %}{% assign planned = 0 %}{% for row in site.data.loe.rows %}{% if row.status == "Done" %}{% assign done = done | plus: row.effort_days %}{% else %}{% assign planned = planned | plus: row.effort_days %}{% endif %}{% endfor %}

```mermaid
pie showData title Portfolio Effort — Planned vs Done (person-days)
    "Done" : {{ done }}
    "Planned" : {{ planned }}
```

---

*KF Team · Git-Native Project Management · [GitHub](https://github.com/katty-fashion/kf-cpto)*
