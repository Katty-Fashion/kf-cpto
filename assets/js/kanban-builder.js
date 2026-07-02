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

  // Frontmatter-only mode (rich multi-section boards): validated fields ->
  // a clean YAML block to paste over the file's existing frontmatter.
  function validateMeta(meta) {
    var e = [];
    if (!dateValid(meta.sprint_start || "")) e.push("sprint_start must be YYYY-MM-DD (or empty)");
    if (!dateValid(meta.sprint_end || "")) e.push("sprint_end must be YYYY-MM-DD (or empty)");
    if (DATE_RE.test(meta.sprint_start || "") && DATE_RE.test(meta.sprint_end || "") &&
        meta.sprint_end < meta.sprint_start) e.push("sprint_end is before sprint_start");
    ["po", "lead"].forEach(function (k) {
      var v = String(meta[k] || "").trim();
      if (v && v[0] !== "@") e.push(k + " should be a handle starting with @ (e.g. @el.tech)");
    });
    if (meta.sprint && !/^S\d+$/.test(String(meta.sprint).trim()))
      e.push("sprint should look like S5");
    return e;
  }

  function buildFrontmatter(project, meta, dump, today) {
    var fm = { project: project };
    ["description", "type", "po", "lead", "sprint", "sprint_start",
     "sprint_end"].forEach(function (k) {
      var v = meta && meta[k];
      if (v !== undefined && v !== null && v !== "") fm[k] = v;
    });
    fm.last_updated = today || new Date().toISOString().slice(0, 10);
    ["depends_on", "tags", "team"].forEach(function (k) {
      var v = meta && meta[k];
      var empty = v === undefined || v === null ||
        (Array.isArray(v) && v.length === 0) ||
        (typeof v === "object" && !Array.isArray(v) && Object.keys(v).length === 0);
      if (!empty) fm[k] = v;
    });
    return "---\n" + dump(fm, { lineWidth: -1 }).replace(/\n$/, "") + "\n---";
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
        validateMeta: validateMeta, buildFrontmatter: buildFrontmatter,
      };
    }
    return;
  }

  var jsyaml = window.jsyaml;
  var BOARDS = (window.KB_DATA && window.KB_DATA.boards) || { projects: [] };
  var PLAN = (window.KB_DATA && window.KB_DATA.plan) || null;
  var ORG = "katty-fashion";
  var KF_CPTO_PLAN_EDIT =
    "https://github.com/katty-fashion/kf-cpto/edit/master/docs/_data/migration_plan.yml";
  var TOKEN_KEY = "kb_gh_token";

  // ---- GitHub Contents API (direct save — token stays in the browser) ------
  function b64decodeUtf8(b64) {
    var bin = atob(b64.replace(/\n/g, ""));
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder("utf-8").decode(bytes);
  }
  function b64encodeUtf8(str) {
    var bytes = new TextEncoder().encode(str);
    var bin = "";
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
  }
  function ghFetch(token, method, url, body) {
    return fetch(url, {
      method: method,
      headers: {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: body ? JSON.stringify(body) : undefined,
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) {
          var msg = (j && j.message) || ("HTTP " + r.status);
          if (r.status === 401) msg = "Token rejected (401) — check it has Contents: Read and write.";
          if (r.status === 404) msg = "Not found (404) — token may lack access to this repo.";
          if (r.status === 409) msg = "Conflict (409) — file changed on GitHub; click Save again.";
          throw new Error(msg);
        }
        return j;
      });
    });
  }
  function ghGetFile(token, repo, path, ref) {
    return ghFetch(token, "GET",
      "https://api.github.com/repos/" + ORG + "/" + repo + "/contents/" +
      encodeURIComponent(path).replace(/%2F/g, "/") + "?ref=" + encodeURIComponent(ref));
  }
  function ghPutFile(token, repo, path, branch, content, sha, message) {
    return ghFetch(token, "PUT",
      "https://api.github.com/repos/" + ORG + "/" + repo + "/contents/" +
      encodeURIComponent(path).replace(/%2F/g, "/"),
      { message: message, content: b64encodeUtf8(content), sha: sha, branch: branch });
  }
  // Replace ONLY the leading frontmatter block, preserving the body verbatim.
  var FM_BLOCK_RE = /^---\r?\n[\s\S]*?\r?\n---/;
  function spliceFrontmatter(fileContent, fmBlock) {
    if (!FM_BLOCK_RE.test(fileContent)) return fmBlock + "\n\n" + fileContent;
    return fileContent.replace(FM_BLOCK_RE, fmBlock);
  }

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
    if (state.mode !== "kanban" && state.mode !== "fm") { box.style.display = "none"; return; }
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
    var isFm = state.mode === "fm";
    var metaErrs = validateMeta(effectiveMeta());
    var problems = isFm ? [] : validateAll(state.tasks);
    markFields();

    // validation panel — meta errors count in every mode
    var panel = el("kb-validation");
    var errCount = problems.length + metaErrs.length;
    if (errCount) {
      panel.className = "kb-validation kb-invalid";
      panel.innerHTML = "<strong>" + errCount + " issue(s) need fixing:</strong>";
      var ul = h("ul");
      metaErrs.forEach(function (m) { ul.appendChild(h("li", { text: "Frontmatter: " + m })); });
      problems.forEach(function (p) {
        ul.appendChild(h("li", { text: "Row " + p.row + " (" + (p.task || "untitled") + "): " + p.errs.join("; ") }));
      });
      panel.appendChild(ul);
    } else {
      panel.className = "kb-validation kb-valid";
      panel.textContent = isFm
        ? "✓ Valid frontmatter — clean YAML, no typos possible."
        : "✓ Valid — " + state.tasks.length + " task(s) conform to the kanban DSL.";
    }

    // generated DSL preview + target
    var out, target, note;
    if (board.generated) {
      out = buildPlanYaml(PLAN, board.project, state.tasks, jsyaml.dump);
      target = KF_CPTO_PLAN_EDIT;
      note = "Generated board → edits the migration plan-of-record (kf-cpto · " +
        "docs/_data/migration_plan.yml). After committing, run " +
        "`python scripts/generate_kanban.py --apply` to split it back to the repos.";
    } else if (isFm) {
      out = buildFrontmatter(board.project, effectiveMeta(), jsyaml.dump);
      target = board.edit_url;
      note = "Multi-section board → this replaces ONLY the frontmatter. In the GitHub " +
        "editor, select from the first '---' through the second '---' (inclusive), " +
        "paste, and commit. Body sections stay untouched.";
    } else {
      out = buildKanbanMd(board.project, effectiveMeta(), state.tasks, jsyaml.dump);
      target = board.edit_url;
      note = "Replace the whole file content in GitHub with the text below, then commit.";
    }
    el("kb-note").textContent = note;
    el("kb-output").textContent = out;

    // hand-off + direct-save buttons enabled only when valid
    var btn = el("kb-commit");
    btn.disabled = errCount > 0;
    btn.title = errCount ? "Fix the validation errors first" : "";
    btn.onclick = function () {
      navigator.clipboard.writeText(out).then(function () {
        window.open(target, "_blank", "noopener");
        el("kb-handoff-hint").style.display = "";
      });
    };
    var save = el("kb-save");
    save.disabled = errCount > 0;
    save.title = errCount ? "Fix the validation errors first" : "";
    state.pendingOut = out;
    save.onclick = doSave;
  }

  function saveResult(ok, html) {
    var box = el("kb-save-result");
    box.style.display = "";
    box.style.borderLeftColor = ok ? "#3a7d44" : "#c2682d";
    box.innerHTML = html;
  }

  function doSave() {
    var token = el("kb-token").value.trim() ||
      (window.localStorage && localStorage.getItem(TOKEN_KEY)) || "";
    if (!token) {
      el("kb-token-box").open = true;
      saveResult(false, "Paste a GitHub token first (see <strong>Direct save</strong> above) — " +
        "or use Copy &amp; open GitHub editor.");
      return;
    }
    if (el("kb-token-save").checked && window.localStorage) {
      localStorage.setItem(TOKEN_KEY, token);
    }
    var board = state.board;
    var out = state.pendingOut;
    var save = el("kb-save");
    save.disabled = true;
    saveResult(true, "Saving…");

    var repo, path, branch, message, prepare;
    if (state.mode === "plan") {
      repo = "kf-cpto"; path = "docs/_data/migration_plan.yml"; branch = "master";
      message = "chore(plan): update migration_plan.yml via kanban-builder";
      prepare = function (file) { return out; };
    } else if (state.mode === "fm") {
      repo = board.project; path = "kanban.md"; branch = board.branch || "main";
      message = "chore(kanban): frontmatter update via kanban-builder";
      prepare = function (file) { return spliceFrontmatter(file, out); };
    } else {
      repo = board.project; path = "kanban.md"; branch = board.branch || "main";
      message = "chore(kanban): update via kanban-builder";
      prepare = function (file) { return out; };
    }

    ghGetFile(token, repo, path, branch)
      .then(function (f) {
        var current = b64decodeUtf8(f.content || "");
        var next = prepare(current);
        if (next === current) throw new Error("No changes — file already matches.");
        return ghPutFile(token, repo, path, branch, next, f.sha, message);
      })
      .then(function (r) {
        var url = r.commit && r.commit.html_url;
        saveResult(true, "✓ Committed to <strong>" + repo + "</strong>" +
          (url ? ' — <a href="' + url + '" target="_blank" rel="noopener">view commit</a>.' : ".") +
          (state.mode === "plan"
            ? " Run <code>python scripts/generate_kanban.py --apply</code> to split it to the boards."
            : " The repo dispatch rebuilds the dashboard in ~1 min."));
      })
      .catch(function (e) {
        saveResult(false, "✗ " + String(e.message || e));
      })
      .then(function () { save.disabled = false; });
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

    var rich = !board.generated && !board.simple_board;
    state.mode = board.generated ? "plan" : (rich ? "fm" : "kanban");
    state.tasks = rich ? [] : seedTasks(board);
    state.meta = {}; // overrides only; base stays board.meta

    // Rich boards: frontmatter editor only — task tables live in the body
    // (edited via raw editor or the kanban-groom skill).
    var taskUi = rich ? "none" : "";
    el("kb-tasks-h3").style.display = taskUi;
    el("kb-table").style.display = taskUi;
    el("kb-add-p").style.display = taskUi;
    el("kb-preview-h3").innerHTML = rich
      ? "Generated <code>frontmatter</code> (preview)"
      : "Generated <code>kanban.md</code> (preview)";
    if (rich) {
      el("kb-fallback").style.display = "";
      el("kb-fallback-link").href = board.edit_url;
    }

    el("kb-editor").style.display = "";
    el("kb-badge").textContent = board.generated
      ? "generated → plan-of-record"
      : (rich ? "multi-section → frontmatter editor" : "kanban.md");
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
    // Restore a remembered token (browser-local only); untick + clear removes it.
    var saved = window.localStorage && localStorage.getItem(TOKEN_KEY);
    if (saved) { el("kb-token").value = saved; el("kb-token-save").checked = true; }
    el("kb-token-save").onchange = function () {
      if (!this.checked && window.localStorage) localStorage.removeItem(TOKEN_KEY);
    };
    var q = new URLSearchParams(window.location.search).get("project");
    var initial = (q && boardFor(q)) ? q : (BOARDS.projects[0] && BOARDS.projects[0].project);
    if (initial) { sel.value = initial; selectProject(initial); }
  }

  init();
})();
