const TAB_REGISTRY = [
  { id: "dashboard", label: "Dashboard", enabled: true },
  { id: "explorer", label: "Explorer", enabled: true },
  { id: "submit", label: "Submit", enabled: true },
  { id: "logs", label: "Logs", enabled: true },
  { id: "rounds", label: "Rounds", enabled: false },
  { id: "metrics", label: "Metrics", enabled: false },
  { id: "backtest", label: "Backtest", enabled: false },
  { id: "research", label: "Research", enabled: false },
  { id: "autoiterate", label: "Autoiterate", enabled: false },
];

let currentTab = "dashboard";
let selectedSeed = 0;
let statusData = null;
let seedDetail = null;
let logsData = [];

const classColors = {
  0: "#d8c58f",
  1: "#e79328",
  2: "#2ca9d0",
  3: "#be3a3f",
  4: "#3b8d49",
  5: "#8d95ab",
};

const initialTerrainToClass = (code) => {
  if ([10, 11, 0].includes(code)) return 0;
  if ([1, 2, 3, 4, 5].includes(code)) return code;
  return 0;
};

function setAlert(msg, isError = true) {
  const el = document.getElementById("global-alert");
  if (!msg) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.classList.remove("hidden");
  el.style.borderColor = isError ? "var(--danger)" : "var(--accent)";
  el.style.background = isError ? "rgba(220,90,99,0.15)" : "rgba(39,180,143,0.15)";
  el.textContent = msg;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail?.message || data.detail || `HTTP ${res.status}`);
  }
  return data;
}

function renderTabs() {
  const nav = document.getElementById("tab-nav");
  nav.innerHTML = "";
  for (const tab of TAB_REGISTRY) {
    const btn = document.createElement("button");
    btn.className = "tab-btn" + (tab.id === currentTab ? " active" : "") + (!tab.enabled ? " disabled" : "");
    btn.textContent = tab.label;
    btn.disabled = !tab.enabled;
    btn.addEventListener("click", () => {
      if (!tab.enabled) return;
      switchTab(tab.id);
    });
    nav.appendChild(btn);
  }
}

function switchTab(tabId) {
  currentTab = tabId;
  renderTabs();
  for (const el of document.querySelectorAll(".tab-panel")) {
    el.classList.remove("active");
  }
  const activePanel = document.getElementById(`tab-${tabId}`);
  if (activePanel) activePanel.classList.add("active");
}

function fmtSeconds(seconds) {
  if (seconds == null) return "--";
  const s = Math.max(0, Math.floor(seconds));
  const hh = String(Math.floor(s / 3600)).padStart(2, "0");
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function updateDashboard() {
  if (!statusData) return;
  const round = statusData.active_round;
  document.getElementById("round-label").textContent = round
    ? `Round ${round.round_number} (${round.width}x${round.height})`
    : "No active round";
  document.getElementById("round-meta").textContent = round
    ? `status=${round.status} | id=${round.id}`
    : "waiting for active round";

  document.getElementById("deadline-countdown").textContent = fmtSeconds(statusData.seconds_to_close);

  const risk = statusData.deadline_risk || "safe";
  const riskEl = document.getElementById("deadline-risk");
  riskEl.textContent = risk;
  riskEl.className = `pill ${risk}`;

  const q = statusData.queries || { used: 0, max: 50, remaining: 50 };
  document.getElementById("queries-metric").textContent = `${q.used} / ${q.max}`;
  document.getElementById("queries-remaining").textContent = `Remaining: ${q.remaining}`;

  document.getElementById("submission-metric").textContent = `${statusData.submitted_count} / ${statusData.seed_count}`;
  document.getElementById("submission-meta").textContent =
    statusData.submitted_count === statusData.seed_count && statusData.seed_count > 0
      ? "All seeds submitted"
      : "Manual submit preferred; deadline guard at T-20m";

  document.getElementById("run-state").textContent =
    `run=${statusData.run_enabled ? "ON" : "OFF"} | profile=${statusData.profile} | token=${statusData.token_present ? "set" : "missing"}`;

  document.getElementById("profile-select").value = statusData.profile;
  document.getElementById("guard-toggle").checked = statusData.deadline_guard_enabled;

  if (statusData.last_error) {
    setAlert(`${statusData.last_error}. ${statusData.last_error_action || ""}`);
  } else {
    setAlert(null);
  }

  const tbody = document.querySelector("#seed-summary-table tbody");
  tbody.innerHTML = "";
  (statusData.seeds || []).forEach((seed) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${seed.seed_index}</td>
      <td>${seed.coverage_pct.toFixed(1)}%</td>
      <td>${seed.avg_entropy.toFixed(3)}</td>
      <td>${seed.avg_confidence.toFixed(3)}</td>
      <td>${seed.submit_status}</td>
    `;
    tbody.appendChild(tr);
  });

  renderSeedTabs();
  renderSubmitCards();
}

function renderSeedTabs() {
  const tabsEl = document.getElementById("seed-tabs");
  tabsEl.innerHTML = "";
  (statusData?.seeds || []).forEach((seed) => {
    const btn = document.createElement("button");
    btn.className = "seed-tab" + (seed.seed_index === selectedSeed ? " active" : "");
    btn.textContent = `Seed ${seed.seed_index}`;
    btn.addEventListener("click", () => {
      selectedSeed = seed.seed_index;
      renderSeedTabs();
      loadSeedDetail();
    });
    tabsEl.appendChild(btn);
  });
}

function renderSubmitCards() {
  const root = document.getElementById("submit-cards");
  root.innerHTML = "";
  (statusData?.seeds || []).forEach((seed) => {
    const card = document.createElement("div");
    card.className = "card seed-submit-card";
    const validation = seed.validation || {};
    const submitReady = validation.submit_ready;
    card.innerHTML = `
      <h3>Seed ${seed.seed_index}</h3>
      <div>Coverage: ${seed.coverage_pct.toFixed(1)}%</div>
      <div>Entropy: ${seed.avg_entropy.toFixed(3)}</div>
      <div>Validation: ${submitReady ? "ready" : "not ready"}</div>
      <div>Status: ${seed.submit_status}</div>
      <div class="row wrap" style="margin-top:8px;">
        <button data-submit-seed="${seed.seed_index}" ${submitReady ? "" : "disabled"}>Submit Seed ${seed.seed_index}</button>
      </div>
    `;
    root.appendChild(card);
  });
}

async function loadStatus() {
  statusData = await api("/status");
  if ((statusData.seeds || []).length && !(statusData.seeds || []).some((s) => s.seed_index === selectedSeed)) {
    selectedSeed = statusData.seeds[0].seed_index;
  }
  updateDashboard();
}

async function loadSeedDetail() {
  if (!statusData || !(statusData.seeds || []).length) return;
  seedDetail = await api(`/seed/${selectedSeed}`);
  renderSeedCanvas();
  renderSeedMeta();
}

function renderSeedMeta() {
  if (!seedDetail || !statusData) return;
  const seedSummary = (statusData.seeds || []).find((s) => s.seed_index === selectedSeed);
  const detail = [
    `Seed: ${selectedSeed}`,
    `Coverage: ${seedSummary ? seedSummary.coverage_pct.toFixed(1) : "0"}%`,
    `Settlements: ${seedDetail.latest_settlement_count} (${seedDetail.latest_alive_settlement_count} alive)`,
    `Viewport: ${seedSummary?.last_viewport ? JSON.stringify(seedSummary.last_viewport) : "none"}`,
  ].join("\n");
  document.getElementById("seed-detail-meta").textContent = detail;

  const counts = seedDetail.last_viewport_counts || {};
  let countStr = "";
  for (let i = 0; i < 6; i += 1) {
    countStr += `${i}:${counts[String(i)] || 0} ${seedDetail.class_names[i]}\n`;
  }
  document.getElementById("viewport-counts").textContent = countStr;
}

function renderSeedCanvas() {
  const canvas = document.getElementById("seed-canvas");
  if (!canvas || !seedDetail) return;
  const ctx = canvas.getContext("2d");
  const width = seedDetail.width;
  const height = seedDetail.height;
  const cell = Math.floor(Math.min(canvas.width / width, canvas.height / height));
  const layer = document.getElementById("layer-select").value;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      let color = "#000";
      if (layer === "argmax") {
        color = classColors[seedDetail.argmax_grid[y][x]];
      } else if (layer === "initial") {
        color = classColors[initialTerrainToClass(seedDetail.initial_grid[y][x])];
      } else if (layer === "coverage") {
        const visits = seedDetail.observed_visits[y][x];
        const v = Math.min(255, 30 + visits * 28);
        color = `rgb(${Math.floor(v * 0.4)}, ${v}, ${Math.floor(v * 0.9)})`;
      } else {
        const h = seedDetail.uncertainty_grid[y][x];
        const n = Math.max(0, Math.min(1, h / 1.8));
        const r = Math.floor(30 + 220 * n);
        const g = Math.floor(40 + 80 * (1 - n));
        const b = Math.floor(80 + 120 * (1 - n));
        color = `rgb(${r},${g},${b})`;
      }
      ctx.fillStyle = color;
      ctx.fillRect(x * cell, y * cell, cell, cell);
    }
  }

  const vp = seedDetail.last_viewport;
  if (vp) {
    ctx.strokeStyle = "#e05f5f";
    ctx.lineWidth = 2;
    ctx.strokeRect(vp.x * cell + 1, vp.y * cell + 1, vp.w * cell - 2, vp.h * cell - 2);
  }
}

async function loadLogs() {
  const level = document.getElementById("log-level").value;
  const query = level ? `?level=${level}&limit=300` : "?limit=300";
  const data = await api(`/logs/recent${query}`);
  logsData = data.items || [];
  const root = document.getElementById("logs-list");
  root.innerHTML = "";
  logsData.slice().reverse().forEach((item) => {
    const div = document.createElement("div");
    div.className = "log-item";
    const details = JSON.stringify(item.details || {});
    div.textContent = `[${item.ts}] ${item.level.toUpperCase()} ${item.event}: ${item.message} ${details}`;
    root.appendChild(div);
  });
}

async function post(path, body = null) {
  return api(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

function wireActions() {
  document.getElementById("refresh-btn").addEventListener("click", refreshAll);
  document.getElementById("start-run-btn").addEventListener("click", async () => {
    await post("/run/start");
    await refreshAll();
  });
  document.getElementById("stop-run-btn").addEventListener("click", async () => {
    await post("/run/stop");
    await refreshAll();
  });
  document.getElementById("rebuild-btn").addEventListener("click", async () => {
    await post("/draft/rebuild");
    await refreshAll();
  });
  document.getElementById("rebuild-submit-btn").addEventListener("click", async () => {
    await post("/draft/rebuild");
    await refreshAll();
  });
  document.getElementById("submit-all-btn").addEventListener("click", async () => {
    await post("/submit/all");
    await refreshAll();
  });

  document.getElementById("profile-select").addEventListener("change", async (e) => {
    await post("/profile/set", { profile: e.target.value });
    await refreshAll();
  });

  document.getElementById("guard-toggle").addEventListener("change", async (e) => {
    await post("/guard/set", { enabled: Boolean(e.target.checked) });
    await refreshAll();
  });

  document.getElementById("token-save-btn").addEventListener("click", async () => {
    const val = document.getElementById("token-input").value.trim();
    await post("/auth/token", { access_token: val || null });
    document.getElementById("token-input").value = "";
    await refreshAll();
  });

  document.getElementById("layer-select").addEventListener("change", () => {
    renderSeedCanvas();
  });

  document.getElementById("submit-cards").addEventListener("click", async (e) => {
    const button = e.target.closest("button[data-submit-seed]");
    if (!button) return;
    const seedIndex = Number(button.getAttribute("data-submit-seed"));
    await post("/submit/seed", { seed_index: seedIndex });
    await refreshAll();
  });

  document.getElementById("logs-refresh-btn").addEventListener("click", loadLogs);
}

async function refreshAll() {
  try {
    await loadStatus();
    await loadSeedDetail();
    if (currentTab === "logs") {
      await loadLogs();
    }
  } catch (err) {
    setAlert(err.message || String(err));
  }
}

async function boot() {
  renderTabs();
  wireActions();
  await refreshAll();
  setInterval(refreshAll, 3500);
  setInterval(() => {
    if (currentTab === "logs") {
      loadLogs().catch(() => {});
    }
  }, 5000);
}

boot().catch((err) => {
  setAlert(err.message || String(err));
});
