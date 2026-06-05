/*
 * Kanban Builder — client-side, no backend.
 *
 * Seeds a validated form from the dashboard's own build-time data
 * (site.data.boards + site.data.migration_plan, embedded by kanban-builder.html),
 * then GENERATES correctly-formatted output so the editor never mistypes a
 * status / effort / date:
 *
 *   - generated platform repos  -> edits the migration plan-of-record
 *                                  (full docs/_data/migration_plan.yml YAML)
 *   - simple direct repos       -> rebuilds the whole kanban.md
 *   - rich/custom-layout repos  -> falls back to the raw GitHub editor
 *
 * The actual commit is a hand-off: "Copy" + "Open GitHub editor" (paste + commit).
 *
 * Pure builders (no DOM / no globals) are exported for Node tests at the bottom.
 */
(function () {
  "use strict";

  var STATUSES = ["Todo", "In Progress", "Review", "Done"];
  var EFFORT_RE = /^\d+(\.\d+)?d$/;
  var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

  // ---- pure helpers --------------------------------------------------------

  function mdCell(s) {
    // A literal '|' or newline would break the markdown table row.
    return String(s == null ? "" : s)
      .replace(/\r?\n/g, " ")
      .replace(/\|/g, "/")
      .trim();
  }

  function effortValid(s) {
    return s === "" || EFFORT_RE.test(s);
  }
  function dateValid(s) {
    return s === "" || DATE_RE.test(s);
  }

  // Build the canonical 6-column task table (matches scripts/utils.py parser
  // and scripts/generate_kanban.py build_body exactly).
  function buildTaskTable(tasks) {
    var lines = [
      "| Task | Assignee | Effort | Start | End | Status |",
      "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ];
    tasks.forEach(function (t) {
      lines.push(
        "| " + mdCell(t.task) +
        " | " + mdCell(t.assignee) +
        " | " + mdCell(t.effort) +
        " | " + mdCell(t.start) +
        " | " + mdCell(t.end) +
        " | " + mdCell(t.status) + " |"
      );
    });
    return lines.join("\n");
  }

  // Full kanban.md for a SIMPLE board (frontmatter + one table). `dump` is a
  // YAML serializer (js-yaml in the browser; injected in tests).
  function buildKanbanMd(project, meta, tasks, dump) {
    var fm = { project: project };
    ["description", "type", "po", "lead", "sprint", "sprint_start",
     "sprint_end", "depends_on", "tags", "team"].forEach(function (k) {
      if (meta && meta[k] !== undefined && meta[k] !== null &&
          !(Array.isArray(meta[k]) && meta[k].length === 0) &&
          !(typeof meta[k] === "object" && !Array.isArray(meta[k]) && Object.keys(meta[k]).length === 0)) {
        fm[k] = meta[k];
      }
    });
    var frontmatter = dump(fm, { lineWidth: -1 }).replace(/\n$/, "");
    return (
      "---\n" + frontmatter + "\n---\n\n" +
      "# Project Kanban\n\n" +
      "<!-- Valid statuses: Todo, In Progress, Review, Done -->\n" +
      "<!-- Effort format: Nd (e.g. 1d, 0.5d, 3d) -->\n\n" +
      buildTaskTable(tasks) + "\n"
    );
  }

  // Full migration_plan.yml with this repo's task slice replaced in place.
  function buildPlanYaml(plan, project, tasks, dump) {
    var next = JSON.parse(JSON.stringify(plan)); // deep clone
    var edited = tasks.map(function (t) {
      return {
        task: t.task, assignee: t.assignee, effort: t.effort,
        start: t.start, end: t.end, status: t.status, repo: project,
      };
    });
    var out = [];
    var i = 0;
    (next.tasks || []).forEach(function (t) {
      if (t.repo === project) {
        if (i < edited.length) out.push(edited[i++]);
        // dropped rows (i past edited length) are removed
      } else {
        out.push(t);
      }
    });
    // appended new rows beyond the original count for this repo
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
  function h(tag, attrs, children) {
    var n = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { n.appendChild(c); });
    return n;
  }

  var state = { project: null, tasks: [], mode: null };

  function boardFor(name) {
    return BOARDS.projects.filter(function (p) { return p.project === name; })[0];
  }

  function seedTasks(board) {
    if (board.generated && PLAN) {
      return (PLAN.tasks || [])
        .filter(function (t) { return t.repo === board.project; })
        .map(cloneTask);
    }
    return (board.tasks || []).map(cloneTask);
  }
  function cloneTask(t) {
    return {
      task: t.task || "", assignee: t.assignee || "", effort: t.effort || "",
      start: t.start || "", end: t.end || "", status: t.status || "Todo",
    };
  }

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
      var rm = h("button", { class: "kb-rm", type: "button", text: "✕" });
      rm.onclick = function () { state.tasks.splice(idx, 1); renderRows(); refresh(); };
      var td = h("td"); td.appendChild(rm); tr.appendChild(td);
      tbody.appendChild(tr);
    });
  }

  function cellInput(t, field, idx, type) {
    var td = h("td");
    var inp = h("input", { type: type, value: t[field] || "" });
    inp.oninput = function () {
      state.tasks[idx][field] = inp.value;
      inp.classList.toggle("kb-bad",
        (field === "effort" && !effortValid(inp.value)) ||
        ((field === "start" || field === "end") && !dateValid(inp.value)));
      refresh();
    };
    if (field === "effort") inp.placeholder = "3d";
    td.appendChild(inp);
    return td;
  }

  function statusCell(t, idx) {
    var td = h("td");
    var sel = h("select");
    STATUSES.forEach(function (s) {
      var o = h("option", { value: s, text: s });
      if (s === t.status) o.setAttribute("selected", "selected");
      sel.appendChild(o);
    });
    sel.value = STATUSES.indexOf(t.status) >= 0 ? t.status : "Todo";
    sel.onchange = function () { state.tasks[idx].status = sel.value; refresh(); };
    td.appendChild(sel);
    return td;
  }

  function refresh() {
    var board = boardFor(state.project);
    if (!board) return;
    var out, target, note;
    if (board.generated) {
      out = buildPlanYaml(PLAN, board.project, state.tasks, jsyaml.dump);
      target = KF_CPTO_PLAN_EDIT;
      note = "This is a GENERATED board. Edits go to the migration plan-of-record " +
             "(kf-cpto · docs/_data/migration_plan.yml). After committing, run " +
             "`python scripts/generate_kanban.py --apply` to split it back to the repos.";
    } else {
      out = buildKanbanMd(board.project, board.meta, state.tasks, jsyaml.dump);
      target = board.edit_url;
      note = "Replace the whole file content with the generated text below, then commit.";
    }
    el("kb-note").textContent = note;
    el("kb-output").textContent = out;
    el("kb-open").href = target;
    var bad = state.tasks.some(function (t) {
      return !effortValid(t.effort) || !dateValid(t.start) || !dateValid(t.end) || !t.task.trim();
    });
    el("kb-warn").textContent = bad
      ? "⚠ Some rows have an invalid effort (Nd), date (YYYY-MM-DD), or empty task."
      : "";
  }

  function selectProject(name) {
    state.project = name;
    var board = boardFor(name);
    el("kb-editor").style.display = "";
    el("kb-fallback").style.display = "none";
    if (!board) return;
    if (!board.generated && !board.simple_board) {
      // Rich custom layout — don't risk a destructive rebuild.
      el("kb-editor").style.display = "none";
      el("kb-fallback").style.display = "";
      el("kb-fallback-link").href = board.edit_url;
      return;
    }
    state.tasks = seedTasks(board);
    el("kb-badge").textContent = board.generated ? "generated → plan-of-record" : "kanban.md";
    renderRows();
    refresh();
  }

  function init() {
    var sel = el("kb-project");
    BOARDS.projects.forEach(function (p) {
      sel.appendChild(h("option", { value: p.project, text: p.project +
        (p.generated ? "  (generated)" : "") }));
    });
    sel.onchange = function () { selectProject(sel.value); };

    el("kb-add").onclick = function () {
      state.tasks.push({ task: "", assignee: "", effort: "", start: "", end: "", status: "Todo" });
      renderRows(); refresh();
    };
    el("kb-copy").onclick = function () {
      navigator.clipboard.writeText(el("kb-output").textContent).then(function () {
        el("kb-copy").textContent = "Copied ✓";
        setTimeout(function () { el("kb-copy").textContent = "Copy"; }, 1500);
      });
    };

    // Preselect from ?project=
    var q = new URLSearchParams(window.location.search).get("project");
    var initial = (q && boardFor(q)) ? q : (BOARDS.projects[0] && BOARDS.projects[0].project);
    if (initial) { sel.value = initial; selectProject(initial); }
  }

  init();
})();
