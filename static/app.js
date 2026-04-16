// AI Job Pipeline — Frontend JS

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ---------------------------------------------------------------------------
// Form handling
// ---------------------------------------------------------------------------

function toggleAdvanced() {
  const section = $(".advanced-section");
  const toggle = $(".advanced-toggle");
  section.classList.toggle("show");
  toggle.classList.toggle("open");
}

function runPipeline(demo = false) {
  const btn = $(".btn-run");
  btn.disabled = true;

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

    $$('input[name="scrapers"]:checked').forEach((cb) => {
      params.append("scrapers", cb.value);
    });
  }

  // Clear previous results
  $(".results-table-wrapper").innerHTML = "";
  $(".results-cards").innerHTML = "";
  const statsBar = $(".stats-bar");
  if (statsBar) { statsBar.classList.remove("show"); statsBar.innerHTML = ""; }

  // Show progress
  const progress = $(".progress-section");
  progress.classList.add("show");
  $(".progress-log").innerHTML = "";
  $(".progress-phase").textContent = "Starting...";
  $(".progress-counter").textContent = "";

  // Hide placeholder
  const placeholder = $(".placeholder-msg");
  if (placeholder) placeholder.style.display = "none";

  // Connect SSE
  const source = new EventSource(`/run?${params.toString()}`);

  source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleSSE(data, source, btn);
  };

  source.onerror = () => {
    source.close();
    btn.disabled = false;
    addLogLine("Connection lost", "error");
  };
}

function handleSSE(data, source, btn) {
  switch (data.type) {
    case "phase":
      $(".progress-phase").textContent = `═══ ${data.name} ═══`;
      addLogLine(`═══ ${data.name} ═══`, "phase");
      break;

    case "progress":
      $(".progress-counter").textContent = `[${data.current}/${data.total}]`;
      const cls = data.message.includes("SKIP") ? "skip" : "";
      addLogLine(`[${data.current}/${data.total}] ${data.message}`, cls);
      break;

    case "log":
      addLogLine(data.message);
      break;

    case "done":
      source.close();
      btn.disabled = false;
      $(".progress-phase").textContent = `DONE (${data.time})`;
      $(".progress-counter").textContent = `${data.total} jobs · ${data.matched} matched · ${data.tailored} tailored`;
      addLogLine(`Done! ${data.total} jobs, ${data.matched} matched, ${data.tailored} tailored`, "phase");
      loadResults();
      break;

    case "error":
      source.close();
      btn.disabled = false;
      addLogLine(`ERROR: ${data.message}`, "error");
      break;

    case "heartbeat":
      break;
  }
}

function addLogLine(text, cls = "") {
  const log = $(".progress-log");
  const line = document.createElement("div");
  line.className = `line ${cls}`;
  line.textContent = text;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

// ---------------------------------------------------------------------------
// Results loading
// ---------------------------------------------------------------------------

function loadResults() {
  fetch("/results")
    .then((r) => r.json())
    .then((jobs) => {
      if (!jobs.length) return;
      renderStats(jobs);
      renderTable(jobs);
      renderCards(jobs);
    });
}

function renderStats(jobs) {
  const total = jobs.length;
  const matched = jobs.filter((j) => (j["Match Score"] || 0) >= 70).length;
  const tailored = jobs.filter((j) => j["Tailored Resume"]).length;
  const ghostHigh = jobs.filter((j) => j["Ghost Risk"] === "High").length;

  const bar = $(".stats-bar");
  bar.innerHTML = `
    <div class="stat"><div class="stat-value">${total}</div><div class="stat-label">Total Jobs</div></div>
    <div class="stat"><div class="stat-value green">${matched}</div><div class="stat-label">Matched</div></div>
    <div class="stat"><div class="stat-value blue">${tailored}</div><div class="stat-label">Tailored</div></div>
    <div class="stat"><div class="stat-value red">${ghostHigh}</div><div class="stat-label">Ghost Risk</div></div>
    <div class="download-btns">
      <a href="/download/excel" class="btn-download">📊 Excel</a>
      <a href="/download/all" class="btn-download">📦 Download All</a>
    </div>
  `;
  bar.classList.add("show");
}

function scoreClass(score) {
  if (score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}

function ghostClass(risk) {
  return (risk || "low").toLowerCase();
}

function renderTable(jobs) {
  const wrapper = $(".results-table-wrapper");
  const cols = ["Title", "Company", "Company Type", "Location", "Match Score", "Recommendation", "Ghost Risk", "Salary", "URL", "Tailored Resume"];

  let html = '<table class="results-table"><thead><tr>';
  cols.forEach((col) => {
    html += `<th onclick="sortTable('${col}')">${col}</th>`;
  });
  html += "</tr></thead><tbody>";

  jobs.sort((a, b) => (b["Match Score"] || 0) - (a["Match Score"] || 0));

  jobs.forEach((job) => {
    const score = job["Match Score"] || 0;
    const ghost = job["Ghost Risk"] || "Low";
    const url = job["URL"] || "";
    const pdf = job["Tailored Resume"] || "";
    const pdfName = pdf.split(/[/\\]/).pop();

    html += "<tr>";
    html += `<td>${job["Title"] || ""}</td>`;
    html += `<td>${job["Company"] || ""}</td>`;
    html += `<td>${job["Company Type"] || ""}</td>`;
    html += `<td>${job["Location"] || ""}</td>`;
    html += `<td><span class="score-badge ${scoreClass(score)}">${score}</span></td>`;
    html += `<td>${job["Recommendation"] || ""}</td>`;
    html += `<td><span class="ghost-badge ${ghostClass(ghost)}">${ghost}</span></td>`;
    html += `<td>${job["Salary"] || ""}</td>`;
    html += `<td>${url ? `<a href="${url}" target="_blank" class="link-btn">Open</a>` : "—"}</td>`;
    html += `<td>${pdfName ? `<a href="/download/file/${pdfName}" class="link-btn">📄 PDF</a>` : "—"}</td>`;
    html += "</tr>";
  });

  html += "</tbody></table>";
  wrapper.innerHTML = html;
}

function renderCards(jobs) {
  const container = $(".results-cards");
  jobs.sort((a, b) => (b["Match Score"] || 0) - (a["Match Score"] || 0));

  let html = "";
  jobs.forEach((job) => {
    const score = job["Match Score"] || 0;
    const ghost = job["Ghost Risk"] || "Low";
    const url = job["URL"] || "";
    const pdf = job["Tailored Resume"] || "";
    const pdfName = pdf.split(/[/\\]/).pop();
    const matchCls = scoreClass(score);

    html += `<div class="job-card match-${matchCls}">`;
    html += `<div class="job-card-header">`;
    html += `<div><div class="job-card-title">${job["Title"] || ""}</div>`;
    html += `<div class="job-card-company">${job["Company"] || ""} · ${job["Location"] || ""}</div></div>`;
    html += `<div class="job-card-score" style="color:var(--${matchCls === "high" ? "green" : matchCls === "medium" ? "yellow" : "red"})">${score}</div>`;
    html += `</div>`;
    html += `<div class="job-card-actions">`;
    if (url) html += `<a href="${url}" target="_blank" class="job-card-action">🔗 Apply</a>`;
    if (pdfName) html += `<a href="/download/file/${pdfName}" class="job-card-action">📄 PDF</a>`;
    if (ghost !== "Low") html += `<span class="job-card-action" style="background:rgba(239,68,68,0.1);color:var(--red)">⚠ ${ghost} Ghost Risk</span>`;
    html += `</div></div>`;
  });

  container.innerHTML = html;
}

// Sort state
let _sortCol = "Match Score";
let _sortAsc = false;

function sortTable(col) {
  if (_sortCol === col) _sortAsc = !_sortAsc;
  else { _sortCol = col; _sortAsc = false; }

  fetch("/results")
    .then((r) => r.json())
    .then((jobs) => {
      jobs.sort((a, b) => {
        let va = a[col] || "", vb = b[col] || "";
        if (typeof va === "number" || typeof vb === "number") {
          return _sortAsc ? (va || 0) - (vb || 0) : (vb || 0) - (va || 0);
        }
        return _sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
      });
      renderTable(jobs);
    });
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  // Load previous results if they exist
  if (document.body.dataset.hasResults === "true") {
    loadResults();
  }
});
