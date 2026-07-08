---
title: Knowledge Graph
description: Interactive OKF knowledge-graph — browse projects, tasks, metrics and milestones and their relationships.
---

# OKF Knowledge Graph

We track every project, task, metric and milestone as a node in our Open Knowledge Format bundle. This page renders those concepts and their relationships as an interactive graph — pan, zoom, search, filter by type, and click any node to follow it through to the source.

**Node types:** Projects are compound containers; their tasks are nested inside. Metrics and Milestones are top-level nodes. Click any node to highlight its neighbourhood and open the info panel with an external link.

**Edge kinds:** `depends` (project depends on another project) · `contains` edges are replaced by compound nesting.

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

<div class="okf-graph-controls" style="display:flex;flex-wrap:wrap;gap:0.75rem;align-items:center;margin-bottom:0.75rem;padding:0.5rem 0.75rem;background:var(--pico-card-background-color);border:1px solid var(--pico-muted-border-color);border-radius:6px;">
  <label style="display:flex;align-items:center;gap:0.4rem;font-size:0.85rem;">
    Layout:
    <select id="okf-layout" style="padding:0.25rem 0.4rem;border:1px solid var(--pico-muted-border-color);border-radius:4px;font-size:0.85rem;">
      <option value="fcose" selected>fcose (compound)</option>
      <option value="cose">cose</option>
      <option value="concentric">concentric</option>
      <option value="breadthfirst">breadthfirst</option>
      <option value="grid">grid</option>
      <option value="circle">circle</option>
    </select>
  </label>
  <label style="display:flex;align-items:center;gap:0.4rem;font-size:0.85rem;">
    Node repulsion:
    <input id="okf-repulsion" type="range" min="500" max="20000" step="500" value="4500"
           style="width:100px;vertical-align:middle;">
    <span id="okf-repulsion-val" style="min-width:3em;text-align:right;">4500</span>
  </label>
  <label style="display:flex;align-items:center;gap:0.4rem;font-size:0.85rem;">
    Nesting factor:
    <input id="okf-nesting" type="range" min="0" max="2" step="0.05" value="0.1"
           style="width:80px;vertical-align:middle;">
    <span id="okf-nesting-val" style="min-width:2.5em;text-align:right;">0.10</span>
  </label>
  <button id="okf-rerun" style="padding:0.25rem 0.75rem;font-size:0.85rem;border-radius:4px;cursor:pointer;">Re-run layout</button>
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
<script src="https://cdn.jsdelivr.net/npm/layout-base/layout-base.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cose-base/cose-base.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cytoscape-fcose/cytoscape-fcose.js"></script>
<script>
(function () {
  // Register fcose extension — plain-script UMD mode auto-registers; defensive call for safety.
  try {
    if (typeof cytoscapeFcose !== 'undefined') cytoscape.use(cytoscapeFcose);
    else if (typeof fcose !== 'undefined') cytoscape.use(fcose);
  } catch (e) { /* already registered */ }

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
    var d = { id: n.id, label: n.label, type: n.type, status: n.status, url: n.url };
    // Compound nesting: task nodes carry a parent field pointing to their project node.
    if (n.parent) d.parent = n.parent;
    elements.push({ group: 'nodes', data: d });
  });

  (GRAPH.edges || []).forEach(function (e, i) {
    // Skip 'contains' edges — compound nesting replaces them visually.
    // Only render 'depends' edges (project -> project cross-links).
    if (e.kind === 'contains') return;
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

  // ---- Layout helpers -------------------------------------------------------
  var repulsionSlider = document.getElementById('okf-repulsion');
  var nestingSlider   = document.getElementById('okf-nesting');
  var repulsionVal    = document.getElementById('okf-repulsion-val');
  var nestingVal      = document.getElementById('okf-nesting-val');

  function getRepulsion() { return parseInt(repulsionSlider.value, 10); }
  function getNesting()   { return parseFloat(nestingSlider.value); }

  function buildLayoutOpts(name) {
    if (name === 'fcose') {
      var rep = getRepulsion();
      var nest = getNesting();
      return {
        name: 'fcose',
        quality: 'default',
        animate: true,
        randomize: true,
        packComponents: true,
        nodeRepulsion: function () { return rep; },
        idealEdgeLength: function () { return 60; },
        nestingFactor: nest,
        gravity: 0.25,
        numIter: 2500
      };
    }
    if (name === 'cose') {
      var rep2 = getRepulsion();
      return {
        name: 'cose',
        animate: true,
        nodeRepulsion: function () { return rep2; },
        idealEdgeLength: 60,
        gravity: 25,
        numIter: 1000
      };
    }
    if (name === 'concentric') {
      return { name: 'concentric', animate: true, padding: 30, minNodeSpacing: 20 };
    }
    if (name === 'breadthfirst') {
      return { name: 'breadthfirst', directed: true, padding: 30, spacingFactor: 1.25, avoidOverlap: true, animate: true };
    }
    if (name === 'grid') {
      return { name: 'grid', padding: 30, avoidOverlap: true, animate: true };
    }
    if (name === 'circle') {
      return { name: 'circle', padding: 30, animate: true };
    }
    return { name: name };
  }

  // ---- Initialise Cytoscape ------------------------------------------------
  var cy = cytoscape({
    container: document.getElementById('okf-cy'),
    elements: elements,
    style: [
      {
        // Compound (Project parent) container style
        selector: 'node[type = "Project"]',
        style: {
          'background-color': 'rgba(37, 99, 235, 0.08)',
          'border-color': '#2563eb',
          'border-width': 2,
          'label': 'data(label)',
          'font-size': '10px',
          'font-weight': 'bold',
          'color': '#1e40af',
          'text-valign': 'top',
          'text-halign': 'center',
          'text-margin-y': -4,
          'padding': '12px',
          'border-radius': '6px',
          'text-wrap': 'ellipsis',
          'text-max-width': '120px'
        }
      },
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
    layout: buildLayoutOpts('fcose'),
    minZoom: 0.15,
    maxZoom: 4
  });

  // ---- Layout controls -----------------------------------------------------
  var layoutSelect = document.getElementById('okf-layout');

  repulsionSlider.addEventListener('input', function () {
    repulsionVal.textContent = this.value;
  });
  nestingSlider.addEventListener('input', function () {
    nestingVal.textContent = parseFloat(this.value).toFixed(2);
  });

  function rerunLayout() {
    cy.layout(buildLayoutOpts(layoutSelect.value)).run();
  }

  layoutSelect.addEventListener('change', rerunLayout);
  document.getElementById('okf-rerun').addEventListener('click', rerunLayout);

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
