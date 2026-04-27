// ai-job-pipeline — Frontend JS
// Wires the v3 glass-dashboard UI to Flask backend (SSE /run, /results, etc.)

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ---------------------------------------------------------------------------
// Theme: auto → light → dark cycle, persisted in localStorage.
// Sets BOTH `data-theme` attribute (for CSS selectors) and `html.light` class
// (for the v3 prototype's convention).
// ---------------------------------------------------------------------------

const THEME_KEY = "aijp-theme";
const THEME_CYCLE = ["auto", "light", "dark"];

function readStoredTheme() {
  try { return localStorage.getItem(THEME_KEY) || "auto"; } catch { return "auto"; }
}
function writeStoredTheme(v) {
  try { localStorage.setItem(THEME_KEY, v); } catch { /* ignore */ }
}

function applyTheme(t) {
  const html = document.documentElement;
  if (t === "light") {
    html.setAttribute("data-theme", "light");
    html.classList.add("light");
  } else if (t === "dark") {
    html.setAttribute("data-theme", "dark");
    html.classList.remove("light");
  } else {
    html.removeAttribute("data-theme");
    html.classList.toggle("light", window.matchMedia("(prefers-color-scheme: light)").matches);
  }
}

function _updateThemeTitle() {
  const btn = document.querySelector(".theme-toggle");
  if (!btn) return;
  const mode = readStoredTheme();
  const nextIdx = (THEME_CYCLE.indexOf(mode) + 1) % THEME_CYCLE.length;
  const label = { auto: "auto (follows OS)", light: "light", dark: "dark" };
  btn.title = `Theme: ${label[mode]}. Click to switch to ${label[THEME_CYCLE[nextIdx]]}.`;
}

function cycleTheme() {
  const cur = readStoredTheme();
  const next = THEME_CYCLE[(THEME_CYCLE.indexOf(cur) + 1) % THEME_CYCLE.length];
  writeStoredTheme(next);
  applyTheme(next);
  _updateThemeTitle();
}

// ---------------------------------------------------------------------------
// Discreet mode — double-Esc panic + visibility toggle + header button.
// ---------------------------------------------------------------------------

const DISCREET_REAL_TITLE = "Ai Job Pipeline — Dashboard";
const DISCREET_FAKE_TITLE = "Quarterly Report - Google Sheets";

let _discreet = false;
let _discreetResetTimer = null;

function _onMouseMoveResetDiscreet() {
  if (document.hidden) return;
  clearTimeout(_discreetResetTimer);
  _discreetResetTimer = setTimeout(() => setDiscreet(false), 2000);
}

function setDiscreet(on) {
  if (_discreet === on) return;
  _discreet = on;
  document.title = on ? DISCREET_FAKE_TITLE : DISCREET_REAL_TITLE;
  document.body.classList.toggle("discreet-mode", on);

  // Update header toggle button icon + active state
  const btn = document.getElementById("discreet-toggle");
  if (btn) {
    btn.classList.toggle("active", on);
    const icon = btn.querySelector(".material-symbols-outlined");
    if (icon) icon.textContent = on ? "visibility_off" : "visibility";
  }

  if (on) document.addEventListener("mousemove", _onMouseMoveResetDiscreet, { passive: true });
  else { document.removeEventListener("mousemove", _onMouseMoveResetDiscreet); clearTimeout(_discreetResetTimer); }
}

function toggleDiscreet() { setDiscreet(!_discreet); }

document.addEventListener("visibilitychange", () => setDiscreet(document.hidden));

// Double-Esc within 300ms → discreet mode ON
let _escCount = 0;
let _escTimer = null;
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  _escCount++;
  clearTimeout(_escTimer);
  if (_escCount >= 2) { setDiscreet(true); _escCount = 0; }
  else { _escTimer = setTimeout(() => (_escCount = 0), 300); }
});

// ---------------------------------------------------------------------------
// Sidebar toggle — slides .v3-sidebar in/out + backdrop.
// Header button icon swaps: tune (closed) ↔ menu_open (opened).
// ---------------------------------------------------------------------------

function toggleSidebar() {
  const sidebar = document.getElementById("config-sidebar");
  const backdrop = document.getElementById("v3-backdrop");
  const toggle = document.getElementById("sidebar-toggle");
  if (!sidebar) return;
  const opening = !sidebar.classList.contains("open");
  sidebar.classList.toggle("open", opening);
  if (backdrop) backdrop.classList.toggle("visible", opening);
  if (toggle) {
    const icon = toggle.querySelector(".material-symbols-outlined");
    if (icon) icon.textContent = opening ? "menu_open" : "tune";
    toggle.title = opening ? "Hide settings" : "Show settings";
  }
}

// ---------------------------------------------------------------------------
// Segmented controls — wire visible .seg-btn buttons to hidden radios.
// Thumb slides via style.left = (index / count) * 100%.
// ---------------------------------------------------------------------------

function _segSetActive(wrap, value) {
  const btns = wrap.querySelectorAll(".seg-btn");
  const thumb = wrap.querySelector(".seg-thumb");
  const group = wrap.dataset.segGroup;
  let idx = 0;
  btns.forEach((b, i) => {
    const match = b.dataset.value === value;
    b.classList.toggle("active", match);
    if (match) idx = i;
  });
  if (thumb) {
    thumb.style.width = `${100 / btns.length}%`;
    thumb.style.left = `${(idx / btns.length) * 100}%`;
  }
  // Sync hidden radio
  if (group) {
    $$(`input[name="${group}"]`).forEach(r => r.checked = r.value === value);
    // Fire an input event on the form-section so CLI preview refreshes
    $(".form-section")?.dispatchEvent(new Event("input", { bubbles: true }));
  }
}

function initSegmented() {
  $$(".seg-wrap").forEach((wrap) => {
    // Set thumb initial position from whichever button has .active (or first)
    const active = wrap.querySelector(".seg-btn.active") || wrap.querySelector(".seg-btn");
    if (active) _segSetActive(wrap, active.dataset.value);
    wrap.querySelectorAll(".seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => _segSetActive(wrap, btn.dataset.value));
    });
  });
}

// ---------------------------------------------------------------------------
// Chip selector — label-wrapped checkboxes; toggle .active on click.
// The checkbox input is the source of truth (read by buildCLI + runPipeline).
// ---------------------------------------------------------------------------

function initChipSelects() {
  $$(".chip-select").forEach((group) => {
    group.querySelectorAll(".chip-opt").forEach((opt) => {
      const cb = opt.querySelector('input[type="checkbox"]');
      if (!cb) return;
      // Initial state
      opt.classList.toggle("active", cb.checked);
      // Listen on the label (clicks bubble from the checkbox too, but .change fires once)
      cb.addEventListener("change", () => {
        opt.classList.toggle("active", cb.checked);
      });
    });
  });
}

// ---------------------------------------------------------------------------
// Toggle switches — wire visible .toggle-track.on class to hidden checkbox.
// ---------------------------------------------------------------------------

function initToggles() {
  $$(".toggle-row").forEach((row) => {
    const cb = row.querySelector('input[type="checkbox"]');
    const track = row.querySelector(".toggle-track");
    if (!cb || !track) return;
    track.classList.toggle("on", cb.checked);
    cb.addEventListener("change", () => track.classList.toggle("on", cb.checked));
  });
}

// ---------------------------------------------------------------------------
// Advanced section disclosure.
// ---------------------------------------------------------------------------

function toggleAdvanced() {
  const section = $(".advanced-section");
  const toggle = $(".advanced-toggle");
  if (!section || !toggle) return;
  const opening = !section.classList.contains("show");
  section.classList.toggle("show", opening);
  toggle.classList.toggle("open", opening);
  toggle.setAttribute("aria-expanded", opening ? "true" : "false");
}

// ---------------------------------------------------------------------------
// CLI equivalent preview — declarative config + live refresh.
// ---------------------------------------------------------------------------

const shellQuote = (s) => `'${String(s).replace(/'/g, `'\\''`)}'`;

const CLI_FIELDS = [
  { flag: "--keywords",       type: "text",   sel: "#keywords"       },
  { flag: "--location",       type: "text",   sel: "#location"       },
  { flag: "--pages",          type: "num",    sel: "#pages"          },
  { flag: "--scrapers",       type: "multi",  name: "scrapers"       },
  { flag: "--scorer",         type: "radio",  name: "scorer"         },
  { flag: "--pdf-style",      type: "radio",  name: "pdf_style"      },
  { flag: "--min-salary",     type: "num",    sel: "#min_salary"     },
  { flag: "--threshold",      type: "num",    sel: "#threshold"      },
  { flag: "--include-remote", type: "bool",   sel: "#include_remote" },
  { flag: "--force",          type: "bool",   sel: "#force"          },
  { flag: "--dry-run",        type: "bool",   sel: "#dry_run"        },
];

const CLI_ONLY_FOOTER = [
  "# CLI-only flags (not in GUI):",
  "#   --schedule daily     # install recurring task (crontab / Task Scheduler)",
  "#   --output path.xlsx   # custom Excel output path",
  "#   --open-top 10        # CLI equivalent of the 'Open top' button above",
].join("\n");

function buildCLI() {
  const flags = [];
  CLI_FIELDS.forEach((f) => {
    if (f.type === "text") {
      const el = document.querySelector(f.sel);
      const v = el?.value.trim();
      if (v) flags.push(`  ${f.flag} ${shellQuote(v)}`);
    } else if (f.type === "num") {
      const el = document.querySelector(f.sel);
      const v = el?.value;
      if (v && v !== (el.defaultValue || "")) flags.push(`  ${f.flag} ${v}`);
    } else if (f.type === "multi") {
      const checked = Array.from(document.querySelectorAll(`input[name="${f.name}"]:checked`)).map(c => c.value);
      if (checked.length) flags.push(`  ${f.flag} ${checked.join(" ")}`);
    } else if (f.type === "radio") {
      const sel = document.querySelector(`input[name="${f.name}"]:checked`);
      if (!sel) return;
      const def = document.querySelector(`input[name="${f.name}"][checked]`);
      if (sel.value === def?.value) return;
      if (sel.value === "none") return;
      flags.push(`  ${f.flag} ${sel.value}`);
    } else if (f.type === "bool") {
      if (document.querySelector(f.sel)?.checked) flags.push(`  ${f.flag}`);
    }
  });

  const envPrefix = [];
  const minSal = document.getElementById("min_salary");
  const thr = document.getElementById("threshold");
  if (minSal?.value && minSal.value !== (minSal.defaultValue || "8")) envPrefix.push(`MIN_SALARY_LPA=${minSal.value}`);
  if (thr?.value && thr.value !== (thr.defaultValue || "70"))        envPrefix.push(`MATCH_THRESHOLD=${thr.value}`);
  const head = (envPrefix.length ? envPrefix.join(" ") + " " : "") + "python -m src.main";

  const command = flags.length ? `${head} \\\n${flags.join(" \\\n")}` : head;
  return `${command}\n\n${CLI_ONLY_FOOTER}`;
}

function refreshCLI() {
  const el = $("#cli-preview");
  if (el) el.textContent = buildCLI();
}

let _copyResetTimer = null;
function copyCLI() {
  if (!navigator.clipboard) return;
  navigator.clipboard.writeText(buildCLI()).then(() => {
    const btn = $(".btn-copy");
    const label = btn?.querySelector(".btn-copy__label");
    if (!btn || !label) return;
    if (_copyResetTimer) clearTimeout(_copyResetTimer);
    else label.dataset.orig = label.textContent;
    btn.classList.add("copied");
    label.textContent = "Copied";
    _copyResetTimer = setTimeout(() => {
      btn.classList.remove("copied");
      label.textContent = label.dataset.orig || "Copy";
      _copyResetTimer = null;
    }, 1500);
  }).catch(() => { /* clipboard rejected — user can still select the <pre> */ });
}

// ---------------------------------------------------------------------------
// Progress log collapse/expand.
// ---------------------------------------------------------------------------

function toggleProgress() {
  $(".progress-section")?.classList.toggle("collapsed");
}
document.addEventListener("click", (e) => {
  const header = e.target.closest(".progress-header");
  if (header && header.closest(".progress-section")) toggleProgress();
});

// ---------------------------------------------------------------------------
// Pipeline run (SSE).
// ---------------------------------------------------------------------------

let _runStart = null;

function runPipeline(demo = false) {
  const btn = document.getElementById("btn-run");
  if (btn) btn.disabled = true;

  const params = new URLSearchParams();
  if (demo) {
    params.set("demo", "true");
  } else {
    params.set("keywords", $("#keywords").value);
    params.set("location", $("#location").value);
    params.set("pages", $("#pages").value);
    params.set("scorer", document.querySelector('input[name="scorer"]:checked')?.value || "none");
    params.set("pdf_style", document.querySelector('input[name="pdf_style"]:checked')?.value || "modern");
    params.set("min_salary", $("#min_salary").value);
    params.set("threshold", $("#threshold").value);
    params.set("include_remote", $("#include_remote").checked);
    params.set("force", $("#force")?.checked || false);
    params.set("dry_run", $("#dry_run")?.checked || false);
    $$('input[name="scrapers"]:checked').forEach((cb) => params.append("scrapers", cb.value));
  }

  // Clear previous results
  $(".results-cards").innerHTML = "";
  const statsBar = $(".stats-bar");
  if (statsBar) { statsBar.classList.remove("show"); statsBar.innerHTML = ""; }
  const resultsHeader = $("#results-header");
  if (resultsHeader) { resultsHeader.hidden = true; resultsHeader.innerHTML = ""; }

  // Show progress
  const progress = $(".progress-section");
  progress.classList.add("show");
  progress.classList.remove("collapsed");
  $(".progress-log").innerHTML = "";
  const phaseEl = $(".progress-phase");
  if (phaseEl) phaseEl.innerHTML = `<span class="v3-spinner"></span>Starting...`;
  $(".progress-counter").textContent = "";

  const placeholder = $(".placeholder-msg");
  if (placeholder) placeholder.style.display = "none";

  _runStart = Date.now();

  // Close sidebar on desktop when running (user wants to see output)
  const sidebar = document.getElementById("config-sidebar");
  if (sidebar?.classList.contains("open")) toggleSidebar();

  const source = new EventSource(`/run?${params.toString()}`);
  source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleSSE(data, source, btn);
  };
  source.onerror = () => {
    source.close();
    if (btn) btn.disabled = false;
    addLogLine("Connection lost", "error");
  };
}

function handleSSE(data, source, btn) {
  switch (data.type) {
    case "phase":
      $(".progress-phase").innerHTML = `<span class="v3-spinner"></span>${esc(data.name)}`;
      addLogLine(`═══ ${data.name} ═══`, "phase");
      break;

    case "progress": {
      let counter = `[${data.current}/${data.total}]`;
      if (_runStart && data.current >= 3 && data.total > data.current) {
        const perItem = (Date.now() - _runStart) / data.current;
        const eta = _formatEta(perItem * (data.total - data.current));
        if (eta) counter += ` · ${eta}`;
      }
      $(".progress-counter").textContent = counter;
      const cls = data.message.includes("SKIP") ? "skip" : "";
      addLogLine(`[${data.current}/${data.total}] ${data.message}`, cls);
      break;
    }

    case "log":
      addLogLine(data.message);
      break;

    case "done":
      source.close();
      if (btn) btn.disabled = false;
      $(".progress-phase").innerHTML = `<span class="material-symbols-outlined" style="color:var(--clr-green);font-size:16px">check_circle</span>Done · ${esc(data.time)}`;
      $(".progress-counter").textContent = `${data.total} jobs · ${data.matched} matched · ${data.tailored} tailored`;
      addLogLine(`Done! ${data.total} jobs, ${data.matched} matched, ${data.tailored} tailored`, "phase");
      loadResults();
      setTimeout(() => $(".progress-section")?.classList.add("collapsed"), 2000);
      break;

    case "error":
      source.close();
      if (btn) btn.disabled = false;
      addLogLine(`ERROR: ${data.message}`, "error");
      break;

    case "heartbeat":
      break;
  }
}

function addLogLine(text, cls = "") {
  const log = $(".progress-log");
  if (!log) return;
  const line = document.createElement("div");
  line.className = `line ${cls}`;
  line.textContent = text;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

// ---------------------------------------------------------------------------
// Results loading + sort state
// ---------------------------------------------------------------------------

let _currentJobs = [];
let _sortCol = "Match Score";
let _sortAsc = false;

// Open top N URLs in new tabs — synchronous window.open loop.
function openTopNInTabs() {
  if (!_currentJobs.length) return;
  const raw = parseInt(document.getElementById("open-top-n")?.value, 10);
  const n = Math.max(1, Math.min(20, isNaN(raw) ? 10 : raw));
  const urls = _currentJobs.slice(0, n).map(j => j["URL"]).filter(Boolean);
  if (!urls.length) { announce("No URLs to open"); return; }
  urls.forEach(url => window.open(url, "_blank", "noopener"));
  announce(`Opened ${urls.length} job URL${urls.length === 1 ? "" : "s"} in new tabs`);
}

// ---------------------------------------------------------------------------
// Friction helpers — resume banner, inline warnings, ETA.
// ---------------------------------------------------------------------------

function checkResumeExists() {
  if (sessionStorage.getItem("aijp-resume-banner-dismissed") === "1") return;
  fetch("/resume/exists").then(r => r.json()).then(data => {
    if (data.ok) return;
    const b = document.getElementById("resume-banner");
    const msg = document.getElementById("resume-banner-msg");
    if (msg && data.path) {
      msg.innerHTML = `No <code>resume.json</code> found at <code>${esc(data.path)}</code>. Copy <code>examples/resume.example.json</code> and edit with your details to get started.`;
    }
    if (b) b.hidden = false;
  }).catch(() => { /* endpoint missing — stay quiet */ });
}

function dismissResumeBanner() {
  sessionStorage.setItem("aijp-resume-banner-dismissed", "1");
  const b = document.getElementById("resume-banner");
  if (b) b.hidden = true;
}

function _setInlineWarning(msg) {
  const el = document.getElementById("inline-warning");
  if (!el) return;
  if (!msg) { el.hidden = true; el.textContent = ""; return; }
  el.innerHTML = `<svg class="icon" aria-hidden="true"><use href="#icon-alert-triangle"/></svg><span>${msg}</span>`;
  el.hidden = false;
}

function refreshInlineWarnings() {
  const parts = [];
  if (document.getElementById("force")?.checked) {
    parts.push("Force re-process is ON — previous scores will be re-computed (can take 10-20 min).");
  }
  const scorer = document.querySelector('input[name="scorer"]:checked')?.value;
  if (scorer === "api" && window._apiKeySet === false) {
    parts.push("No ANTHROPIC_API_KEY detected — pick the 'CLI' scorer or add a key to .env.");
  }
  _setInlineWarning(parts.length ? parts.join(" · ") : "");
}

function _formatEta(ms) {
  if (!isFinite(ms) || ms <= 0) return "";
  const s = Math.round(ms / 1000);
  if (s < 60) return `~${s}s left`;
  const m = Math.floor(s / 60), r = s % 60;
  return r === 0 ? `~${m}m left` : `~${m}m ${r}s left`;
}

// ---------------------------------------------------------------------------
// Sort helpers
// ---------------------------------------------------------------------------

function _sortValue(job, colKey) {
  const cfg = _colConfig(colKey);
  const field = cfg?.sortKey || colKey;
  const raw = job[field];
  if (cfg?.ordinal) return cfg.ordinal[raw] ?? 99;
  if (cfg?.date)    { const t = Date.parse(raw); return isNaN(t) ? -Infinity : t; }
  if (cfg?.numeric) { const n = Number(raw); return isNaN(n) ? -Infinity : n; }
  return String(raw ?? "").toLowerCase();
}

function sortJobsBy(jobs, col, asc) {
  return jobs.sort((a, b) => {
    const va = _sortValue(a, col), vb = _sortValue(b, col);
    if (typeof va === "number" && typeof vb === "number") return asc ? va - vb : vb - va;
    return asc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });
}

function setSortMode(col) {
  if (!_currentJobs.length) return;
  if (_sortCol === col) _sortAsc = !_sortAsc;
  else { _sortCol = col; _sortAsc = false; }
  sortJobsBy(_currentJobs, _sortCol, _sortAsc);
  renderCards(_currentJobs);
  renderResultsHeader(_currentJobs, _sortCol);
}

// ---------------------------------------------------------------------------
// Results header — title + count + sort pills (v3 style)
// ---------------------------------------------------------------------------

function renderResultsHeader(jobs, activeCol) {
  const header = document.getElementById("results-header");
  if (!header) return;
  const matched = jobs.filter(j => (j["Match Score"] || 0) >= 70).length;
  const pills = [
    { key: "Match Score", label: "Score" },
    { key: "Salary",      label: "Salary" },
    { key: "Posted Date", label: "Recent" },
  ];
  header.innerHTML = `
    <div>
      <span class="v3-results-title">Results</span>
      <span class="v3-results-count">${jobs.length} jobs · ${matched} matched</span>
    </div>
    <div class="v3-sort-row">
      <span class="v3-sort-label">Sort:</span>
      ${pills.map(p => `<button class="v3-sort-btn ${activeCol === p.key ? "active" : ""}" onclick="setSortMode('${p.key}')">${p.label}</button>`).join("")}
    </div>`;
  header.hidden = false;
}

function renderResults(jobs) {
  renderStats(jobs);
  renderCards(jobs);
  renderResultsHeader(jobs, _sortCol);
}

function loadResults() {
  _currentJobs = [];
  _sortCol = "Match Score"; _sortAsc = false;
  renderSkeletons(3);

  fetch("/results").then(r => r.json()).then((jobs) => {
    if (!jobs.length) {
      $(".results-cards").innerHTML = "";
      announce("No results to display");
      return;
    }
    _currentJobs = sortJobsBy(jobs, _sortCol, _sortAsc);
    renderResults(_currentJobs);
    announce(`${_currentJobs.length} jobs loaded, ${_currentJobs.filter(j => (j["Match Score"] || 0) >= 70).length} matched`);
  }).catch(() => {
    $(".results-cards").innerHTML = "";
    announce("Failed to load results");
  });
}

function announce(msg) {
  const el = document.getElementById("result-announcer");
  if (el) el.textContent = msg;
}

function renderSkeletons(n = 3) {
  const container = $(".results-cards");
  if (!container) return;
  let html = "";
  for (let i = 0; i < n; i++) {
    html += `<div class="job-card skeleton"><span class="skel" style="width:60%">&nbsp;</span><div style="margin-top:6px"><span class="skel" style="width:40%">&nbsp;</span></div></div>`;
  }
  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Stats bar (v3 pills)
// ---------------------------------------------------------------------------

function renderStats(jobs) {
  const total    = jobs.length;
  const matched  = jobs.filter((j) => (j["Match Score"] || 0) >= 70).length;
  const tailored = jobs.filter((j) => j["Tailored Resume"]).length;
  const ghostHi  = jobs.filter((j) => j["Ghost Risk"] === "High").length;

  const bar = $(".stats-bar");
  if (!bar) return;
  bar.innerHTML = `
    <div class="v3-stat" title="Total jobs scraped">
      <span class="material-symbols-outlined" style="color:var(--accent)">search</span>
      <span class="v3-stat-val">${total}</span>
      <span class="v3-stat-label">Total</span>
    </div>
    <div class="v3-stat" title="Jobs with score ≥ 70">
      <span class="material-symbols-outlined" style="color:var(--clr-green)">check_circle</span>
      <span class="v3-stat-val">${matched}</span>
      <span class="v3-stat-label">Matched</span>
    </div>
    <div class="v3-stat" title="Jobs with a tailored resume generated">
      <span class="material-symbols-outlined" style="color:var(--clr-purple)">description</span>
      <span class="v3-stat-val">${tailored}</span>
      <span class="v3-stat-label">Tailored</span>
    </div>
    <div class="v3-stat" title="Jobs flagged as likely ghost postings">
      <span class="material-symbols-outlined" style="color:var(--clr-amber)">warning</span>
      <span class="v3-stat-val">${ghostHi}</span>
      <span class="v3-stat-label">Ghost Risk</span>
    </div>
    <div class="v3-open-row" title="Opens top N job URLs in new browser tabs">
      <span>Open top</span>
      <input type="number" id="open-top-n" value="10" min="1" max="20" aria-label="Number of top URLs to open">
      <button type="button" onclick="openTopNInTabs()" aria-label="Open top N job URLs in new tabs">
        <svg class="icon" aria-hidden="true"><use href="#icon-external-link"/></svg>Open
      </button>
    </div>
    <a href="/download/excel" class="v3-download-link" aria-label="Download Excel workbook">
      <svg class="icon" aria-hidden="true"><use href="#icon-spreadsheet"/></svg>Excel
    </a>
    <a href="/download/all" class="v3-download-link" aria-label="Download ZIP of all outputs">
      <svg class="icon" aria-hidden="true"><use href="#icon-package"/></svg>ZIP
    </a>
  `;
  bar.classList.add("show");
}

// ---------------------------------------------------------------------------
// Helpers for job rows
// ---------------------------------------------------------------------------

function scoreClass(score) {
  if (score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}

function esc(str) {
  if (str == null) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function relativeDate(raw) {
  if (!raw) return "";
  const d = new Date(raw);
  if (isNaN(d.getTime())) return esc(String(raw));
  const diff = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diff < 60)          return "just now";
  if (diff < 3600)        return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)       return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 86400 * 30)  return `${Math.floor(diff / 86400)}d ago`;
  if (diff < 86400 * 365) return `${Math.floor(diff / (86400 * 7))}w ago`;
  return d.toLocaleDateString();
}

// Ghost ordinal map + TABLE_COLS config — preserved for test_app_js_has_sortable_columns.
// Non-sortable columns (Salary, Posted Date, Actions) keep `sortable: false`; the
// legacy table view used a `no-sort` CSS class on their <th> to drop cursor + arrow.
const GHOST_ORDER = { Low: 1, Medium: 2, High: 3 };
const TABLE_COLS = [
  { key: "Title",          label: "Title",    cls: "",         sortable: true },
  { key: "Company",        label: "Company",  cls: "",         sortable: true },
  { key: "Company Type",   label: "Type",     cls: "col-mid",  sortable: true },
  { key: "Location",       label: "Location", cls: "col-mid",  sortable: true },
  { key: "Match Score",    label: "Score",    cls: "",         sortable: true, numeric: true },
  { key: "Recommendation", label: "Match",    cls: "col-wide", sortable: true, sortKey: "Match Score", numeric: true },
  { key: "Ghost Risk",     label: "Ghost",    cls: "col-mid",  sortable: true, ordinal: GHOST_ORDER },
  { key: "Salary",         label: "Salary",   cls: "",         sortable: false },
  { key: "Posted Date",    label: "Posted",   cls: "col-wide", sortable: false },
  { key: "Source",         label: "Source",   cls: "col-mid",  sortable: true },
  { key: "_actions",       label: "Actions",  cls: "",         sortable: false },
];
function _colConfig(key) { return TABLE_COLS.find(c => c.key === key) || null; }

// sortTable is kept for API compat — the results-table is hidden in v3 but some
// flows may still call this; safe no-op rendering of v3-job-list only.
function sortTable(col) {
  const cfg = _colConfig(col);
  if (!cfg?.sortable || !_currentJobs.length) return;
  if (_sortCol === col) _sortAsc = !_sortAsc;
  else { _sortCol = col; _sortAsc = !(cfg.numeric || cfg.date || cfg.ordinal); }
  sortJobsBy(_currentJobs, col, _sortAsc);
  renderCards(_currentJobs);
  renderResultsHeader(_currentJobs, _sortCol);
}

// ---------------------------------------------------------------------------
// Source brand colors for badges
// ---------------------------------------------------------------------------

const _SRC_COLORS = {
  linkedin: '#0A66C2', naukri: '#6366f1', internshala: '#00A5EC', indeed: '#003A9B',
};

// ---------------------------------------------------------------------------
// renderCards — v3 expandable rows with SVG score ring
// ---------------------------------------------------------------------------

function renderCards(jobs) {
  const container = $(".results-cards");
  if (!container) return;

  const RING = 44;
  const rr = (RING - 5) / 2;
  const circ = 2 * Math.PI * rr;

  let html = "";
  jobs.forEach((job, i) => {
    const score     = Math.round(job["Match Score"] || 0);
    const ghost     = job["Ghost Risk"] || "Low";
    const url       = job["URL"] || "";
    const pdf       = job["Tailored Resume"] || "";
    const pdfName   = pdf.split(/[/\\]/).pop();
    const source    = job["Source"] || "";
    const srcKey    = source.toLowerCase().replace(/\s+/g, "");
    const srcColor  = _SRC_COLORS[srcKey] || "#888";
    const salary    = job["Salary"] || "";
    const company   = job["Company"] || "";
    const location  = job["Location"] || "";
    const type      = job["Company Type"] || "";
    const recommend = job["Recommendation"] || (score >= 80 ? "Strong Match" : score >= 70 ? "Good Match" : score >= 40 ? "Possible" : "Skip");
    const recBucket = score >= 80 ? "strong" : score >= 70 ? "good" : score >= 40 ? "maybe" : "skip";
    const matched   = job["Matched Keywords"] || "";
    const missing   = job["Missing Keywords"] || "";
    const matchList = matched ? String(matched).split(/[,|]/).map(s => s.trim()).filter(Boolean) : [];
    const missList  = missing ? String(missing).split(/[,|]/).map(s => s.trim()).filter(Boolean) : [];
    const posted    = relativeDate(job["Posted Date"]);

    // Score ring SVG
    const ringOffset = circ * (1 - score / 100);
    const ringColor  = score >= 70 ? "var(--clr-green)" : score >= 40 ? "var(--clr-amber)" : "var(--clr-red)";
    const ring = `<svg width="${RING}" height="${RING}" class="score-ring" aria-label="Match score ${score}">`
      + `<circle cx="${RING/2}" cy="${RING/2}" r="${rr.toFixed(2)}" fill="none" stroke="var(--surface-1)" stroke-width="2.5"/>`
      + `<circle cx="${RING/2}" cy="${RING/2}" r="${rr.toFixed(2)}" fill="none" stroke="${ringColor}" stroke-width="2.5"`
      + ` stroke-dasharray="${circ.toFixed(2)}" stroke-dashoffset="${ringOffset.toFixed(2)}" stroke-linecap="round"`
      + ` transform="rotate(-90 ${RING/2} ${RING/2})" class="ring-progress"/>`
      + `<text x="${RING/2}" y="${RING/2}" text-anchor="middle" dominant-baseline="central"`
      + ` fill="var(--fg-1)" font-size="13" font-weight="600" font-family="var(--font-sans)"`
      + ` style="font-variant-numeric:tabular-nums">${score}</text>`
      + `</svg>`;

    // Meta line: company · location · salary
    const metaParts = [];
    if (company)  metaParts.push(`<span class="v3-job-company">${esc(company)}</span>`);
    if (location) metaParts.push(`<span class="v3-dot"></span><span>${esc(location)}</span>`);
    if (salary)   metaParts.push(`<span class="v3-dot"></span><span>${esc(salary)}</span>`);

    let row = `<div class="v3-job-row" data-job-idx="${i}" role="button" tabindex="0" aria-expanded="false">`;
    row += `<div class="v3-job-main">`;
    row += ring;
    row += `<div class="v3-job-info">`;
    row += `<div class="v3-job-title">${esc(job["Title"] || "Untitled")}</div>`;
    row += `<div class="v3-job-meta">${metaParts.join("")}</div>`;
    row += `</div>`;
    row += `<div class="v3-job-right">`;
    if (source) row += `<span class="v3-badge-source" style="background:${srcColor}1a;color:${srcColor}">${esc(source)}</span>`;
    row += `<span class="v3-badge-rec v3-rec-${recBucket}">${esc(recommend)}</span>`;
    row += `<span class="material-symbols-outlined v3-job-chevron" aria-hidden="true">expand_more</span>`;
    row += `</div>`; // v3-job-right
    row += `</div>`; // v3-job-main

    // Expanded detail body (hidden by default)
    row += `<div class="v3-job-detail" hidden>`;

    if (matchList.length) {
      row += `<div class="v3-detail-section"><span class="v3-detail-label">Matched</span><div class="v3-detail-chips">`;
      matchList.forEach(k => { row += `<span class="v3-chip-match">${esc(k)}</span>`; });
      row += `</div></div>`;
    }
    if (missList.length) {
      row += `<div class="v3-detail-section"><span class="v3-detail-label">Missing</span><div class="v3-detail-chips">`;
      missList.forEach(k => { row += `<span class="v3-chip-miss">${esc(k)}</span>`; });
      row += `</div></div>`;
    }

    const ghostColor = ghost === "Low" ? "var(--clr-green)" : ghost === "Medium" ? "var(--clr-amber)" : "var(--clr-red)";
    row += `<div class="v3-detail-row">`;
    row += `<span class="v3-detail-item"><span class="v3-detail-label">Ghost Risk</span>`
         + `<span style="color:${ghostColor}">${esc(ghost)}</span></span>`;
    if (type) row += `<span class="v3-detail-item"><span class="v3-detail-label">Type</span><span>${esc(type)}</span></span>`;
    if (posted) row += `<span class="v3-detail-item"><span class="v3-detail-label">Posted</span><span style="color:var(--fg-3)">${esc(posted)}</span></span>`;
    row += `</div>`;

    row += `<div class="v3-detail-actions">`;
    if (pdfName) {
      row += `<a href="/download/file/${encodeURIComponent(pdfName)}" class="v3-btn-pdf" aria-label="Download tailored resume PDF">`
           + `<svg class="icon" aria-hidden="true"><use href="#icon-file-text"/></svg>Download PDF</a>`;
    }
    if (url) {
      row += `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer" class="v3-btn-apply" aria-label="Open job listing in new tab">`
           + `Apply <span class="material-symbols-outlined">open_in_new</span></a>`;
    }
    row += `</div>`;

    row += `</div>`; // v3-job-detail
    row += `</div>`; // v3-job-row

    html += row;
  });

  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  // Apply stored theme (FOUC script already did data-theme/html.light; we do one more
  // pass so matchMedia-based "auto" also updates html.light on re-entry).
  applyTheme(readStoredTheme());

  initSegmented();
  initChipSelects();
  initToggles();

  // Delegated expand/collapse for job rows
  const cardsEl = $(".results-cards");
  if (cardsEl) {
    cardsEl.addEventListener("click", (e) => {
      // Avoid toggling when the click bubbled from an internal anchor/button
      if (e.target.closest("a, button")) return;
      const row = e.target.closest(".v3-job-row");
      if (!row) return;
      const body = row.querySelector(".v3-job-detail");
      if (!body) return;
      const expanding = body.hidden;
      body.hidden = !expanding;
      row.classList.toggle("expanded", expanding);
      row.setAttribute("aria-expanded", String(expanding));
    });
    cardsEl.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      const row = e.target.closest(".v3-job-row");
      if (row) { e.preventDefault(); row.click(); }
    });
  }

  // Theme toggle click
  document.querySelector(".theme-toggle")?.addEventListener("click", cycleTheme);
  _updateThemeTitle();

  // Touch + mouse gestures — swipe right from left edge opens sidebar; swipe left closes.
  let _touchStartX = 0;
  document.addEventListener("touchstart", (e) => { _touchStartX = e.touches[0].clientX; }, { passive: true });
  document.addEventListener("touchend", (e) => {
    const dx = e.changedTouches[0].clientX - _touchStartX;
    const sidebar = document.getElementById("config-sidebar");
    if (!sidebar) return;
    if (dx > 80 && _touchStartX < 40 && !sidebar.classList.contains("open")) toggleSidebar();
    else if (dx < -80 && sidebar.classList.contains("open")) toggleSidebar();
  }, { passive: true });

  // Mouse drag — only initiate near left edge (clientX < 16) to avoid hijacking normal clicks
  let _mouseStart = null;
  document.addEventListener("mousedown", (e) => {
    if (e.clientX < 16) _mouseStart = e.clientX;
  });
  document.addEventListener("mouseup", (e) => {
    if (_mouseStart === null) return;
    const dx = e.clientX - _mouseStart;
    const sidebar = document.getElementById("config-sidebar");
    if (sidebar) {
      if (dx > 80 && _mouseStart < 16 && !sidebar.classList.contains("open")) toggleSidebar();
      else if (dx < -80 && sidebar.classList.contains("open")) toggleSidebar();
    }
    _mouseStart = null;
  });

  // Live CLI preview + inline warnings on any form change
  const formSection = $(".form-section");
  if (formSection) {
    formSection.addEventListener("input", () => { refreshCLI(); refreshInlineWarnings(); });
    formSection.addEventListener("change", () => { refreshCLI(); refreshInlineWarnings(); });
    refreshCLI();
  }

  // Friction checks — missing resume, API key status
  checkResumeExists();
  fetch("/status").then(r => r.json()).then(s => {
    window._apiKeySet = !!s.api_key_set;
    refreshInlineWarnings();
  }).catch(() => { /* ignore */ });

  // Auto-load results if the server says they exist
  if (document.body.dataset.hasResults === "true") loadResults();
});
