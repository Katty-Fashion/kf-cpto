/*
 * Kanban Builder — a DSL-aware editor for the kanban.md "mini language".
 *
 * The kanban file is a tiny DSL: YAML frontmatter + a 6-column task table whose
 * cells obey strict rules (status enum, `Nd` effort, ISO dates). This page lets
 * you edit it with structured controls that CAN'T produce invalid syntax, shows
 * a live preview of the exact kanban.md it will write, and validates every rule
 * before you commit. The commit itself is a hand-off: Copy → open GitHub editor.
 *
 * Routing by board type (from site.data.boards):
 *   - generated platform repos -> edit the migration plan-of-record (migration_plan.yml)
 *   - simple direct repos       -> edit the whole kanban.md (frontmatter + tasks)
 *   - rich/custom boards        -> fall back to the raw GitHub editor
 *
 * Pure functions (no DOM/globals) are exported for Node tests at the bottom.
 */
(function () {
  "use strict";

  var STATUSES = ["Todo", "In Progress", "Review", "Done"];
  var EFFORT_RE = /^\d+(\.\d+)?d$/;
  var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  // Editable frontmatter fields for simple direct repos (others preserved as-is).
  var META_FIELDS = [
    ["description", "text"], ["sprint", "text"],
    ["sprint_start", "date"], ["sprint_end", "date"],
    ["po", "text"], ["lead", "text"],
    ["tags", "list"], ["depends_on", "list"],
  ];

  // ---- pure helpers --------------------------------------------------------

  function mdCell(s) {
    return String(s == null ? "" : s).replace(/\r?\n/g, " ").replace(/\|/g, "/").trim();
  }
  function effortValid(s) { return s === "" || EFFORT_RE.test(s); }
  function dateValid(s) { return s === "" || DATE_RE.test(s); }

  // DSL validation — returns a list of {row, task, errs[]} for invalid rows.
  function validateTask(t) {
    var e = [];
    if (!String(t.task || "").trim()) e.push("task name is required");
    if (STATUSES.indexOf(t.status) < 0) e.push("status must be one of " + STATUSES.join(" / "));
    if (!effortValid(t.effort)) e.push("effort must look like 3d / 0.5d (or empty)");
    if (!dateValid(t.start)) e.push("start must be YYYY-MM-DD (or empty)");
    if (!dateValid(t.end)) e.push("end must be YYYY-MM-DD (or empty)");
    if (DATE_RE.test(t.start) && DATE_RE.test(t.end) && t.end < t.start)
      e.push("end is before start");
    return e;
  }
  function validateAll(tasks) {
    var out = [];
    tasks.forEach(function (t, i) {
      var errs = validateTask(t);
      if (errs.length) out.push({ row: i + 1, task: t.task, errs: errs });
    });
    return out;
  }

  function buildTaskTable(tasks) {
    var lines = [
      "| Task | Assignee | Effort | Start | End | Status |",
      "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ];
    tasks.forEach(function (t) {
      lines.push("| " + mdCell(t.task) + " | " + mdCell(t.assignee) + " | " +
        mdCell(t.effort) + " | " + mdCell(t.start) + " | " + mdCell(t.end) +
        " | " + mdCell(t.status) + " |");
    });
    return lines.join("\n");
  }

  function buildKanbanMd(project, meta, tasks, dump) {
    var fm = { project: project };
    ["description", "type", "po", "lead", "sprint", "sprint_start",
     "sprint_end", "depends_on", "tags", "team"].forEach(function (k) {
      var v = meta && meta[k];
      var empty = v === undefined || v === null || v === "" ||
        (Array.isArray(v) && v.length === 0) ||
        (typeof v === "object" && !Array.isArray(v) && Object.keys(v).length === 0);
      if (!empty) fm[k] = v;
    });
    var frontmatter = dump(fm, { lineWidth: -1 }).replace(/\n$/, "");
    return "---\n" + frontmatter + "\n---\n\n# Project Kanban\n\n" +
      "<!-- Valid statuses: Todo, In Progress, Review, Done -->\n" +
      "<!-- Effort format: Nd (e.g. 1d, 0.5d, 3d) -->\n\n" +
      buildTaskTable(tasks) + "\n";
  }

  function buildPlanYaml(plan, project, tasks, dump) {
    var next = JSON.parse(JSON.stringify(plan));
    var edited = tasks.map(function (t) {
      return { task: t.task, assignee: t.assignee, effort: t.effort,
        start: t.start, end: t.end, status: t.status, repo: project };
    });
    var out = [], i = 0;
    (next.tasks || []).forEach(function (t) {
      if (t.repo === project) { if (i < edited.length) out.push(edited[i++]); }
      else out.push(t);
    });
    while (i < edited.length) out.push(edited[i++]);
    next.tasks = out;
    next.row_count = out.length;
    return dump(next, { lineWidth: -1 });
  }

  // ---- DOM app (skipped under Node) ---------------------------------------

  if (typeof document === "undefined" || !document.getElementById("kb-app")) {
    if (typeof module !== "undefined" && module.exports) {
      module.exports = {
        mdCell: mdCell, effortValid: effortValid, dateValid: dateValid,
        validateTask: validateTask, validateAll: validateAll,
        buildTaskTable: buildTaskTable, buildKanbanMd: buildKanbanMd,
        buildPlanYaml: buildPlanYaml, STATUSES: STATUSES,
      };
    }
    return;
  }

  var jsyaml = window.jsyaml;
  var BOARDS = (window.KB_DATA && window.KB_DATA.boards) || { projects: [] };
  var PLAN = (window.KB_DATA && window.KB_DATA.plan) || null;
  var KF_CPTO_PLAN_EDIT =
    "https://github.com/katty-fashion/kf-cpto/edit/master/docs/_data/migration_plan.yml";

  var el = function (id) { return document.getElementById(id); };
  function h(tag, attrs, kids) {
    var n = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { n.appendChild(c); });
    return n;
  }

  var state = { project: null, board: null, mode: null, tasks: [], meta: {} };

  function boardFor(name) {
    return BOARDS.projects.filter(function (p) { return p.project === name; })[0];
  }
  function cloneTask(t) {
    return { task: t.task || "", assignee: t.assignee || "", effort: t.effort || "",
      start: t.start || "", end: t.end || "", status: t.status || "Todo" };
  }
  function seedTasks(board) {
    if (board.generated && PLAN) {
      return (PLAN.tasks || []).filter(function (t) { return t.repo === board.project; }).map(cloneTask);
    }
    return (board.tasks || []).map(cloneTask);
  }

  // ---- frontmatter editor (kanban.md mode) --------------------------------
  function renderMeta() {
    var box = el("kb-meta");
    box.innerHTML = "";
    if (state.mode !== "kanban") { box.style.display = "none"; return; }
    box.style.display = "";
    box.appendChild(h("h3", { text: "Frontmatter" }));
    var grid = h("div", { class: "kb-meta-grid" });
    META_FIELDS.forEach(function (f) {
      var key = f[0], type = f[1];
      var val = state.meta[key];
      var shown = (type === "list") ? (Array.isArray(val) ? val.join(", ") : (val || "")) : (val || "");
      var lbl = h("label", { text: key });
      var inp = h("input", { type: type === "date" ? "date" : "text", value: shown });
      inp.oninput = function () {
        if (type === "list") {
          state.meta[key] = inp.value.split(",").map(function (s) { return s.trim(); }).filter(Boolean);
        } else { state.meta[key] = inp.value; }
        refresh();
      };
      lbl.appendChild(inp);
      grid.appendChild(lbl);
    });
    box.appendChild(grid);
  }

  // ---- task table editor ---------------------------------------------------
  function renderRows() {
    var tbody = el("kb-rows");
    tbody.innerHTML = "";
    state.tasks.forEach(function (t, idx) {
      var tr = h("tr");
      tr.appendChild(cellInput(t, "task", idx, "text"));
      tr.appendChild(cellInput(t, "assignee", idx, "text"));
      tr.appendChild(cellInput(t, "effort", idx, "text"));
      tr.appendChild(cellInput(t, "start", idx, "date"));
      tr.appendChild(cellInput(t, "end", idx, "date"));
      tr.appendChild(statusCell(t, idx));
      var rm = h("button", { class: "kb-rm", type: "button", text: "✕", title: "remove" });
      rm.onclick = function () { state.tasks.splice(idx, 1); renderRows(); refresh(); };
      var td = h("td"); td.appendChild(rm); tr.appendChild(td);
      tbody.appendChild(tr);
    });
  }
  function cellInput(t, field, idx, type) {
    var td = h("td");
    var inp = h("input", { type: type, value: t[field] || "" });
    if (field === "effort") inp.placeholder = "3d";
    inp.oninput = function () {
      state.tasks[idx][field] = inp.value;
      refresh();
    };
    td.appendChild(inp);
    return td;
  }
  function statusCell(t, idx) {
    var td = h("td"), sel = h("select");
    STATUSES.forEach(function (s) { sel.appendChild(h("option", { value: s, text: s })); });
    sel.value = STATUSES.indexOf(t.status) >= 0 ? t.status : "Todo";
    if (sel.value !== t.status) { state.tasks[idx].status = sel.value; }
    sel.onchange = function () { state.tasks[idx].status = sel.value; refresh(); };
    td.appendChild(sel);
    return td;
  }

  // ---- live preview + validation ------------------------------------------
  function markFields() {
    var rows = el("kb-rows").children;
    state.tasks.forEach(function (t, i) {
      var tr = rows[i]; if (!tr) return;
      var cells = tr.children; // task,assignee,effort,start,end,status,rm
      function mark(ci, bad) {
        var inp = cells[ci] && cells[ci].firstChild;
        if (inp) inp.classList.toggle("kb-bad", !!bad);
      }
      mark(0, !String(t.task).trim());
      mark(2, !effortValid(t.effort));
      mark(3, !dateValid(t.start) || (DATE_RE.test(t.start) && DATE_RE.test(t.end) && t.end < t.start));
      mark(4, !dateValid(t.end) || (DATE_RE.test(t.start) && DATE_RE.test(t.end) && t.end < t.start));
    });
  }

  function refresh() {
    var board = state.board;
    var problems = validateAll(state.tasks);
    markFields();

    // validation panel
    var panel = el("kb-validation");
    if (problems.length) {
      panel.className = "kb-validation kb-invalid";
      panel.innerHTML = "<strong>" + problems.length + " row(s) need fixing:</strong>";
      var ul = h("ul");
      problems.forEach(function (p) {
        ul.appendChild(h("li", { text: "Row " + p.row + " (" + (p.task || "untitled") + "): " + p.errs.join("; ") }));
      });
      panel.appendChild(ul);
    } else {
      panel.className = "kb-validation kb-valid";
      panel.textContent = "✓ Valid — " + state.tasks.length + " task(s) conform to the kanban DSL.";
    }

    // generated DSL preview + target
    var out, target, note;
    if (board.generated) {
      out = buildPlanYaml(PLAN, board.project, state.tasks, jsyaml.dump);
      target = KF_CPTO_PLAN_EDIT;
      note = "Generated board → edits the migration plan-of-record (kf-cpto · " +
        "docs/_data/migration_plan.yml). After committing, run " +
        "`python scripts/generate_kanban.py --apply` to split it back to the repos.";
    } else {
      out = buildKanbanMd(board.project, effectiveMeta(), state.tasks, jsyaml.dump);
      target = board.edit_url;
      note = "Replace the whole file content in GitHub with the text below, then commit.";
    }
    el("kb-note").textContent = note;
    el("kb-output").textContent = out;

    // hand-off button enabled only when valid
    var btn = el("kb-commit");
    btn.disabled = problems.length > 0;
    btn.title = problems.length ? "Fix the validation errors first" : "";
    btn.onclick = function () {
      navigator.clipboard.writeText(out).then(function () {
        window.open(target, "_blank", "noopener");
        el("kb-handoff-hint").style.display = "";
      });
    };
  }

  function effectiveMeta() {
    // base meta from the board, overlaid with edited fields
    var base = JSON.parse(JSON.stringify(state.board.meta || {}));
    Object.keys(state.meta).forEach(function (k) { base[k] = state.meta[k]; });
    return base;
  }

  function selectProject(name) {
    var board = boardFor(name);
    state.project = name; state.board = board;
    el("kb-editor").style.display = "none";
    el("kb-fallback").style.display = "none";
    if (!board) return;

    if (!board.generated && !board.simple_board) {
      el("kb-fallback").style.display = "";
      el("kb-fallback-link").href = board.edit_url;
      return;
    }
    state.mode = board.generated ? "plan" : "kanban";
    state.tasks = seedTasks(board);
    state.meta = {}; // overrides only; base stays board.meta
    el("kb-editor").style.display = "";
    el("kb-badge").textContent = board.generated
      ? "generated → plan-of-record" : "kanban.md";
    renderMeta();
    renderRows();
    refresh();
  }

  function init() {
    var sel = el("kb-project");
    BOARDS.projects.forEach(function (p) {
      sel.appendChild(h("option", { value: p.project,
        text: p.project + (p.generated ? "  (generated)" : "") }));
    });
    sel.onchange = function () { selectProject(sel.value); };
    el("kb-add").onclick = function () {
      state.tasks.push({ task: "", assignee: "", effort: "", start: "", end: "", status: "Todo" });
      renderRows(); refresh();
    };
    var q = new URLSearchParams(window.location.search).get("project");
    var initial = (q && boardFor(q)) ? q : (BOARDS.projects[0] && BOARDS.projects[0].project);
    if (initial) { sel.value = initial; selectProject(initial); }
  }

  init();
})();
