---
title: Knowledge Graph
description: Interactive OKF knowledge-graph — browse projects, tasks, metrics and milestones and their relationships.
---

# OKF Knowledge Graph

We track every project, task, metric and milestone as a node in our Open Knowledge Format bundle. This page renders those concepts and their relationships as an interactive graph — pan, zoom, search, filter by type, and click any node to follow it through to the source.

**Node types:** Projects link to the dashboard project page; Tasks, Metrics and Milestones link to their OKF concept file on GitHub.

**Edge kinds:** `depends` (project depends on another project) · `contains` (project owns a task concept).

---

<div class="okf-graph-toolbar" style="display:flex;flex-wrap:wrap;gap:0.75rem;align-items:center;margin-bottom:0.75rem;">
  <input id="okf-search" type="search" placeholder="Search nodes…"
         style="flex:1;min-width:160px;max-width:280px;padding:0.35rem 0.6rem;border:1px solid var(--pico-muted-border-color);border-radius:4px;font-size:0.9rem;">
  <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.85rem;">
    <input type="checkbox" id="okf-filter-project" checked> <span class="okf-legend okf-legend--project"></span> Project
  </label>
  <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.85rem;">
    <input type="checkbox" id="okf-filter-task" checked> <span class="okf-legend okf-legend--task"></span> Task
  </label>
  <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.85rem;">
    <input type="checkbox" id="okf-filter-metric" checked> <span class="okf-legend okf-legend--metric"></span> Metric
  </label>
  <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.85rem;">
    <input type="checkbox" id="okf-filter-milestone" checked> <span class="okf-legend okf-legend--milestone"></span> Milestone
  </label>
</div>

<div id="okf-cy" style="width:100%;height:70vh;border:1px solid var(--pico-muted-border-color);border-radius:6px;background:#fafaf9;"></div>

<div id="okf-info" style="margin-top:0.75rem;padding:0.75rem 1rem;border:1px solid var(--pico-muted-border-color);border-radius:6px;background:var(--pico-card-background-color);min-height:3rem;font-size:0.9rem;display:none;">
  <em>Click a node to see details.</em>
</div>

<style>
  .okf-legend {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 1px solid rgba(0,0,0,0.15);
    flex-shrink: 0;
  }
  .okf-legend--project   { background: #2563eb; }
  .okf-legend--task      { background: #6b7280; }
  .okf-legend--metric    { background: #7c3aed; }
  .okf-legend--milestone { background: #0d9488; }
  #okf-info a { color: var(--pico-primary); }
</style>

<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.umd.js"></script>
<script>
(function () {
  // Raw graph data injected by Jekyll at build time.
  var GRAPH = {{ site.data.okf_graph | jsonify }};

  // ---- colour helpers -------------------------------------------------------
  var TYPE_COLORS = {
    Project:   '#2563eb',
    Metric:    '#7c3aed',
    Milestone: '#0d9488',
    Task:      '#6b7280'   // default; overridden per status below
  };
  var STATUS_COLORS = {
    'Done':        '#16a34a',
    'In Progress': '#d97706',
    'Review':      '#d97706',
    'Todo':        '#6b7280'
  };

  function nodeColor(n) {
    var type = n.data('type');
    if (type === 'Task') {
      var st = n.data('status') || '';
      return STATUS_COLORS[st] || '#9aa0a6';
    }
    return TYPE_COLORS[type] || '#9aa0a6';
  }

  function nodeBorder(n) {
    var type = n.data('type');
    if (type === 'Project') return '#1d4ed8';
    if (type === 'Metric')  return '#5b21b6';
    if (type === 'Milestone') return '#0f766e';
    var st = n.data('status') || '';
    if (st === 'Done')        return '#15803d';
    if (st === 'In Progress' || st === 'Review') return '#b45309';
    return '#4b5563';
  }

  // ---- Build Cytoscape elements from raw graph data -------------------------
  var elements = [];

  (GRAPH.nodes || []).forEach(function (n) {
    elements.push({
      group: 'nodes',
      data: { id: n.id, label: n.label, type: n.type, status: n.status, url: n.url }
    });
  });

  (GRAPH.edges || []).forEach(function (e, i) {
    elements.push({
      group: 'edges',
      data: {
        id: 'e' + i,
        source: e.source,
        target: e.target,
        kind: e.kind
      }
    });
  });

  // ---- Initialise Cytoscape ------------------------------------------------
  var cy = cytoscape({
    container: document.getElementById('okf-cy'),
    elements: elements,
    style: [
      {
        selector: 'node',
        style: {
          'background-color': function (n) { return nodeColor(n); },
          'border-color':     function (n) { return nodeBorder(n); },
          'border-width': 2,
          'label': 'data(label)',
          'font-size': '9px',
          'color': '#1f2937',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 3,
          'width': function (n) { return n.data('type') === 'Project' ? 28 : 18; },
          'height': function (n) { return n.data('type') === 'Project' ? 28 : 18; },
          'text-wrap': 'ellipsis',
          'text-max-width': '80px'
        }
      },
      {
        selector: 'node.faded',
        style: { opacity: 0.15 }
      },
      {
        selector: 'node.highlighted',
        style: { 'border-width': 4, opacity: 1 }
      },
      {
        selector: 'node.hidden',
        style: { display: 'none' }
      },
      {
        selector: 'node.search-dim',
        style: { opacity: 0.2 }
      },
      {
        selector: 'edge',
        style: {
          'width': 1,
          'line-color': '#cbd5e1',
          'target-arrow-color': '#94a3b8',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 0.8,
          'opacity': 0.6
        }
      },
      {
        selector: 'edge[kind="depends"]',
        style: {
          'line-color': '#93c5fd',
          'target-arrow-color': '#3b82f6',
          'line-style': 'dashed'
        }
      },
      {
        selector: 'edge.faded',
        style: { opacity: 0.05 }
      }
    ],
    layout: {
      name: 'breadthfirst',
      directed: true,
      padding: 30,
      spacingFactor: 1.25,
      avoidOverlap: true
    },
    minZoom: 0.15,
    maxZoom: 4
  });

  // ---- Type-filter checkboxes ----------------------------------------------
  var filterIds = {
    project:   document.getElementById('okf-filter-project'),
    task:      document.getElementById('okf-filter-task'),
    metric:    document.getElementById('okf-filter-metric'),
    milestone: document.getElementById('okf-filter-milestone')
  };

  function applyTypeFilter() {
    var hidden = {};
    Object.keys(filterIds).forEach(function (k) {
      if (!filterIds[k].checked) {
        hidden[k.charAt(0).toUpperCase() + k.slice(1)] = true;
      }
    });
    cy.nodes().forEach(function (n) {
      if (hidden[n.data('type')]) {
        n.addClass('hidden');
      } else {
        n.removeClass('hidden');
      }
    });
    cy.edges().forEach(function (e) {
      var srcHidden = e.source().hasClass('hidden');
      var tgtHidden = e.target().hasClass('hidden');
      if (srcHidden || tgtHidden) e.addClass('hidden');
      else e.removeClass('hidden');
    });
  }

  Object.values(filterIds).forEach(function (cb) {
    cb.addEventListener('change', applyTypeFilter);
  });

  // ---- Search input --------------------------------------------------------
  var searchInput = document.getElementById('okf-search');
  searchInput.addEventListener('input', function () {
    var q = this.value.trim().toLowerCase();
    if (!q) {
      cy.elements().removeClass('search-dim');
      return;
    }
    cy.nodes().forEach(function (n) {
      var label = (n.data('label') || '').toLowerCase();
      if (label.indexOf(q) === -1) {
        n.addClass('search-dim');
      } else {
        n.removeClass('search-dim');
      }
    });
    cy.edges().removeClass('search-dim');
  });

  // ---- Click: highlight neighbours + info panel ----------------------------
  var infoPanel = document.getElementById('okf-info');

  cy.on('tap', 'node', function (evt) {
    var node = evt.target;
    var neighbourhood = node.closedNeighborhood();

    // Reset all
    cy.elements().removeClass('faded highlighted');

    // Fade everything not in neighbourhood
    cy.elements().not(neighbourhood).addClass('faded');
    neighbourhood.removeClass('faded');
    node.addClass('highlighted');

    // Info panel
    var label  = node.data('label') || node.id();
    var type   = node.data('type') || '';
    var status = node.data('status');
    var url    = node.data('url') || '';

    var statusHtml = status
      ? ' &middot; <strong>Status:</strong> ' + escHtml(status)
      : '';
    var urlHtml = url
      ? '<br><a href="' + escHtml(url) + '" target="_blank" rel="noopener">' + escHtml(url) + '</a>'
      : '';

    infoPanel.style.display = 'block';
    infoPanel.innerHTML =
      '<strong>' + escHtml(label) + '</strong>'
      + ' &middot; <em>' + escHtml(type) + '</em>'
      + statusHtml
      + urlHtml;
  });

  cy.on('tap', function (evt) {
    if (evt.target === cy) {
      cy.elements().removeClass('faded highlighted');
      infoPanel.style.display = 'none';
    }
  });

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

})();
</script>
