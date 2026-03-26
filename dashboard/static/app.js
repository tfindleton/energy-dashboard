const METRICS = [
  { key: "solar_generation", label: "Solar generation", color: "#d97706" },
  { key: "home_usage", label: "Home usage", color: "#1d4ed8" },
  { key: "grid_export", label: "Grid export", color: "#059669" },
  { key: "grid_import", label: "Grid import", color: "#dc2626" }
];

const DAY_COMPARE_METRICS = [
  { key: "load_power", label: "Home usage", color: "#1d4ed8" },
  { key: "solar_power", label: "Solar generation", color: "#d97706" },
  { key: "grid_import_power", label: "Grid import", color: "#dc2626" },
  { key: "grid_export_power", label: "Grid export", color: "#059669" }
];

const DAY_COMPARE_SERIES_COLORS = [
  "#312e81",
  "#4338ca",
  "#1d4ed8",
  "#2563eb",
  "#0284c7",
  "#06b6d4",
  "#0f766e",
  "#10b981",
  "#22c55e",
  "#65a30d",
  "#a3e635",
  "#eab308",
  "#f59e0b",
  "#f97316",
  "#ef4444",
  "#e11d48"
];

const CHART_COLORS = {
  text: "#d4dde7",
  muted: "#95a1b2",
  grid: "rgba(149, 161, 178, 0.16)",
  axis: "rgba(149, 161, 178, 0.32)"
};

const ICONS = {
  sun: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="M4.93 4.93l1.41 1.41"></path><path d="M17.66 17.66l1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="M4.93 19.07l1.41-1.41"></path><path d="M17.66 6.34l1.41-1.41"></path></svg>`,
  home: `<svg viewBox="0 0 24 24"><path d="M3 10.5L12 3l9 7.5"></path><path d="M5 10v10h14V10"></path><path d="M10 20v-5h4v5"></path></svg>`,
  gridImport: `<svg viewBox="0 0 24 24"><path d="M20 6v12"></path><path d="M20 12H7"></path><path d="M11 8l-4 4 4 4"></path></svg>`,
  gridExport: `<svg viewBox="0 0 24 24"><path d="M4 6v12"></path><path d="M4 12h13"></path><path d="M13 8l4 4-4 4"></path></svg>`,
  bolt: `<svg viewBox="0 0 24 24"><path d="M13 2L6 13h5l-1 9 8-12h-5l0-8z"></path></svg>`,
  plus: `<svg viewBox="0 0 24 24"><path d="M12 5v14"></path><path d="M5 12h14"></path></svg>`,
  refresh: `<svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 0 1-15.36 6.36"></path><path d="M3 12A9 9 0 0 1 18.36 5.64"></path><path d="M3 17v-4h4"></path><path d="M21 7v4h-4"></path></svg>`,
  shield: `<svg viewBox="0 0 24 24"><path d="M12 3l7 3v5c0 5-3.4 8.6-7 10-3.6-1.4-7-5-7-10V6l7-3z"></path><path d="M9.5 12.5l1.8 1.8 3.7-4.1"></path></svg>`,
  clock: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg>`,
  chart: `<svg viewBox="0 0 24 24"><path d="M4 19V5"></path><path d="M4 19h16"></path><path d="M7 15l3-3 3 2 4-5"></path></svg>`,
  chevronLeft: `<svg viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"></path></svg>`,
  chevronRight: `<svg viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"></path></svg>`,
  x: `<svg viewBox="0 0 24 24"><path d="M6 6l12 12"></path><path d="M18 6L6 18"></path></svg>`,
  calendar: `<svg viewBox="0 0 24 24"><path d="M8 2v4"></path><path d="M16 2v4"></path><path d="M3 9h18"></path><rect x="3" y="4" width="18" height="17" rx="0"></rect></svg>`,
  trophy: `<svg viewBox="0 0 24 24"><path d="M8 21h8"></path><path d="M12 17v4"></path><path d="M7 4h10v5a5 5 0 0 1-10 0V4z"></path><path d="M17 4h2a1 1 0 0 1 1 1v1a3 3 0 0 1-3 3"></path><path d="M7 4H5a1 1 0 0 0-1 1v1a3 3 0 0 0 3 3"></path></svg>`,
  crown: `<svg viewBox="0 0 24 24"><path d="M4 18h16"></path><path d="M4 18l2-10 4 4 2-8 2 8 4-4 2 10"></path></svg>`,
  medal: `<svg viewBox="0 0 24 24"><circle cx="12" cy="15" r="5"></circle><path d="M9 3h6"></path><path d="M9 3l1.5 7"></path><path d="M15 3l-1.5 7"></path></svg>`,
  star: `<svg viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14l-5-4.87 6.91-1.01L12 2z"></path></svg>`,
  flame: `<svg viewBox="0 0 24 24"><path d="M12 2c-2 4-6 6-6 11a6 6 0 0 0 12 0c0-5-4-7-6-11z"></path><path d="M10 17a2.5 2.5 0 0 1 2-4c1 2 2 2.5 2 4a2 2 0 0 1-4 0z"></path></svg>`,
  gauge: `<svg viewBox="0 0 24 24"><path d="M4.5 16.5a9 9 0 1 1 15 0"></path><path d="M12 12l-3.5-3.5"></path><circle cx="12" cy="12" r="1.5"></circle></svg>`,
  target: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>`,
  trendUp: `<svg viewBox="0 0 24 24"><path d="M22 7l-8.5 8.5-5-5L2 17"></path><path d="M16 7h6v6"></path></svg>`,
  trendDown: `<svg viewBox="0 0 24 24"><path d="M22 17l-8.5-8.5-5 5L2 7"></path><path d="M16 17h6v-6"></path></svg>`,
  mountain: `<svg viewBox="0 0 24 24"><path d="M2 20l7-14 4 6 5-10 4 8"></path><path d="M2 20h20"></path></svg>`,
  check: `<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"></path></svg>`
};

const DEFAULT_CHART_VIEW = "diagnostics";
const VALID_CHART_VIEWS = new Set(["diagnostics", "daycompare", "performance", "comparison", "pattern", "trend"]);
const DEFAULT_SECTION_VIEW = "charts";
const VALID_SECTION_VIEWS = new Set(["signin", "sync", "insights", "charts"]);

const PREFERENCE_KEYS = {
  dayCompareYMax: "teslaSolar.dayCompareYMax",
  panelCollapsedPrefix: "energyDashboard.panelCollapsed",
  insightCollapsedPrefix: "energyDashboard.insightCollapsed",
  chartView: "energyDashboard.chartView",
  sectionView: "energyDashboard.sectionView"
};

const state = {
  status: null,
  sectionView: DEFAULT_SECTION_VIEW,
  sectionViewResolved: false,
  chartView: DEFAULT_CHART_VIEW,
  dayComparePayload: null,
  dayCompareDates: [],
  dayCompareInitialized: false,
  dayComparePreset: "same-day-years",
  diagnosticsPayload: null,
  comparisonPayload: null,
  performancePayload: null,
  patternPayload: null,
  trendPayload: null,
  generatedAuthUrl: "",
  performanceScope: "month",
  revealEmail: false,
  syncPollTimer: null,
  syncRequestActive: false,
  resizeTimer: null,
  bootstrapping: true
};

let chartTooltipNode = null;

function $(id) {
  return document.getElementById(id);
}

function showBootOverlay(title, message) {
  const overlay = $("bootOverlay");
  if (!overlay) {
    return;
  }
  $("bootTitle").textContent = title || "Loading dashboard";
  $("bootMessage").textContent = message || "Checking local status and preparing your views.";
  overlay.hidden = false;
  document.body.classList.add("boot-loading");
}

function hideBootOverlay() {
  const overlay = $("bootOverlay");
  if (!overlay) {
    return;
  }
  overlay.hidden = true;
  document.body.classList.remove("boot-loading");
}

function updateBootOverlayForStatus(status) {
  if (!state.bootstrapping) {
    return;
  }
  if (status.sync_in_progress) {
    showBootOverlay(
      "Loading dashboard",
      status.sync_progress?.message || "Initial sync is running in the background while the dashboard prepares local data."
    );
    return;
  }
  if ((status.sites || []).length) {
    showBootOverlay("Loading charts", "Preparing summaries, insights, and chart views from the local cache.");
    return;
  }
  if (status.auth_configured) {
    showBootOverlay("Loading dashboard", "Tesla is connected. Checking local data availability and sync state.");
    return;
  }
  if (status.auth_pending || (status.config?.email || "").trim()) {
    showBootOverlay("Loading dashboard", "Restoring your Tesla sign-in setup and local dashboard state.");
    return;
  }
  showBootOverlay("Loading dashboard", "Checking local status and preparing your views.");
}

function loadPreference(key, fallback = "") {
  try {
    return window.localStorage.getItem(key) ?? fallback;
  } catch (error) {
    return fallback;
  }
}

function savePreference(key, value) {
  try {
    if (value === null || value === undefined || value === "") {
      window.localStorage.removeItem(key);
      return;
    }
    window.localStorage.setItem(key, String(value));
  } catch (error) {
    // Ignore storage errors and keep the page functional.
  }
}

function normalizedStorageToken(value, fallback) {
  return String(value || fallback || "section")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || fallback || "section";
}

function panelStorageKey(panel, fallbackIndex = 0) {
  const titleNode = panel.querySelector(":scope > .panel-header .panel-title") || panel.querySelector(":scope > .panel-title");
  const raw = panel.id || panel.dataset.panelKey || titleNode?.textContent;
  return `${PREFERENCE_KEYS.panelCollapsedPrefix}.${normalizedStorageToken(raw, `panel-${fallbackIndex + 1}`)}`;
}

function insightStorageKey(group, fallbackIndex = 0) {
  const scope = group.closest(".insight-sections")?.id || group.dataset.groupScope || "sections";
  return `${PREFERENCE_KEYS.insightCollapsedPrefix}.${normalizedStorageToken(scope, "sections")}.${normalizedStorageToken(group.dataset.groupKey, `group-${fallbackIndex + 1}`)}`;
}

function updatePanelToggleButton(button, collapsed) {
  button.innerHTML = '<span class="panel-toggle-glyph" aria-hidden="true"></span>';
  button.classList.toggle("is-collapsed", collapsed);
  button.setAttribute("aria-expanded", String(!collapsed));
  button.setAttribute("aria-label", collapsed ? "Expand section" : "Collapse section");
  button.title = collapsed ? "Expand section" : "Collapse section";
}

function wireToggleHitbox(node, toggle) {
  if (!node || node.dataset.toggleBound === "1") {
    return;
  }
  node.dataset.toggleBound = "1";
  node.classList.add("panel-toggle-hitbox");
  node.setAttribute("role", "button");
  node.setAttribute("tabindex", "0");
  node.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest(".panel-toggle")) {
      return;
    }
    toggle();
  });
  node.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggle();
    }
  });
}

function setPanelCollapsed(panel, collapsed, options = {}) {
  panel.classList.toggle("panel-collapsed", collapsed);
  const button = panel.querySelector(":scope > .panel-toggle");
  if (button) {
    updatePanelToggleButton(button, collapsed);
  }
  const trigger = panel.querySelector(":scope > .panel-header") || panel.querySelector(":scope > .panel-title");
  if (trigger) {
    trigger.setAttribute("aria-expanded", String(!collapsed));
  }
  if (options.persist !== false) {
    savePreference(panelStorageKey(panel), collapsed ? "1" : "0");
  }
  if (!collapsed) {
    window.requestAnimationFrame(() => rerenderChartsFromCache());
  }
}

function updateInsightToggleButton(button, collapsed) {
  button.classList.toggle("is-collapsed", collapsed);
  button.setAttribute("aria-expanded", String(!collapsed));
  button.setAttribute("aria-label", collapsed ? "Expand section" : "Collapse section");
  button.title = collapsed ? "Expand section" : "Collapse section";
}

function setInsightGroupCollapsed(group, collapsed, options = {}) {
  group.classList.toggle("insight-group-collapsed", collapsed);
  const button = group.querySelector(":scope > .subsection-toggle");
  if (button) {
    updateInsightToggleButton(button, collapsed);
  }
  if (options.persist !== false) {
    savePreference(insightStorageKey(group), collapsed ? "1" : "0");
  }
}

function initializeInsightGroupToggles(containerId) {
  const root = $(containerId);
  if (!root) {
    return;
  }
  root.querySelectorAll(".insight-group[data-group-key]").forEach((group, index) => {
    const button = group.querySelector(":scope > .subsection-toggle");
    if (!button) {
      return;
    }
    const saved = loadPreference(insightStorageKey(group, index), "");
    setInsightGroupCollapsed(group, saved === "1", { persist: false });
    if (button.dataset.toggleBound === "1") {
      return;
    }
    button.dataset.toggleBound = "1";
    button.addEventListener("click", () => {
      const collapsed = !group.classList.contains("insight-group-collapsed");
      setInsightGroupCollapsed(group, collapsed);
    });
  });
}

function initializeCollapsiblePanels() {
  document.querySelectorAll("main > .panel").forEach((panel, index) => {
    if (panel.classList.contains("section-panel")) {
      panel.classList.remove("collapsible-panel", "panel-collapsed");
      const existingToggle = panel.querySelector(":scope > .panel-toggle");
      existingToggle?.remove();
      return;
    }
    panel.classList.add("collapsible-panel");
    if (!panel.id) {
      panel.dataset.panelKey = `panel-${index + 1}`;
    }
    const toggle = () => {
      const collapsed = !panel.classList.contains("panel-collapsed");
      setPanelCollapsed(panel, collapsed);
    };
    let button = panel.querySelector(":scope > .panel-toggle");
    if (!button) {
      button = document.createElement("button");
      button.type = "button";
      button.className = "panel-toggle";
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        toggle();
      });
      panel.appendChild(button);
    }
    const trigger = panel.querySelector(":scope > .panel-header") || panel.querySelector(":scope > .panel-title");
    wireToggleHitbox(trigger, toggle);
    const saved = loadPreference(panelStorageKey(panel, index), "");
    setPanelCollapsed(panel, saved === "1", { persist: false });
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function iconMarkup(name, extraClass = "") {
  const classes = ["ui-icon"];
  if (extraClass) {
    classes.push(extraClass);
  }
  return `<span class="${classes.join(" ")}" aria-hidden="true">${ICONS[name] || ICONS.bolt}</span>`;
}

function iconButtonMarkup(iconName, label) {
  return `${iconMarkup(iconName)}<span>${escapeHtml(label)}</span>`;
}

function metricIconName(metricKey) {
  switch (metricKey) {
    case "solar_generation":
    case "solar_power":
      return "sun";
    case "home_usage":
    case "load_power":
      return "home";
    case "grid_import":
    case "grid_import_power":
      return "gridImport";
    case "grid_export":
    case "grid_export_power":
      return "gridExport";
    default:
      return "bolt";
  }
}

function insightIconSpec(sectionTitle, itemLabel = "", accent = "") {
  const text = `${sectionTitle} ${itemLabel} ${accent}`.toLowerCase();
  if (text.includes("solar")) {
    return { icon: "sun", tone: "solar" };
  }
  if (text.includes("usage") || text.includes("load") || text.includes("home") || text.includes("self-powered")) {
    return { icon: "home", tone: "load" };
  }
  if (text.includes("export")) {
    return { icon: "gridExport", tone: "grid-export" };
  }
  if (text.includes("import")) {
    return { icon: "gridImport", tone: "grid-import" };
  }
  if (accent === "solar") {
    return { icon: "sun", tone: "solar" };
  }
  if (accent === "load") {
    return { icon: "home", tone: "load" };
  }
  return { icon: "bolt", tone: "signal" };
}

function insightItemIconSpec(sectionTitle, itemLabel, accent) {
  const text = (itemLabel || "").toLowerCase();
  const isSolar = accent === "solar" || text.includes("solar");
  const isLoad = accent === "load" || text.includes("usage") || text.includes("load");
  const tone = isSolar ? "solar" : isLoad ? "load" : accent === "signal" ? "signal" : "signal";

  // Day/week/month/year bests and highests share icons; tone (color) differentiates solar vs load
  if (text.includes("day")) return { icon: "trophy", tone };
  if (text.includes("week")) return { icon: "medal", tone };
  if (text.includes("month")) return { icon: "crown", tone };
  if (text.includes("year") && !text.includes("vs")) return { icon: "star", tone };

  if (text.includes("solar ytd") && !text.includes("vs")) return { icon: "target", tone: "solar" };
  if (text.includes("usage ytd")) return { icon: "target", tone: "load" };

  if (text.includes("self-powered")) return { icon: "shield", tone: "signal" };
  if (text.includes("vs last year")) return { icon: "trendUp", tone: "signal" };
  if (text.includes("export share")) return { icon: "gridExport", tone: "grid-export" };

  return insightIconSpec(sectionTitle, itemLabel, accent);
}

function setControlButtonLabel(button, iconName, label) {
  if (!button) {
    return;
  }
  button.classList.add("button-with-icon");
  button.innerHTML = iconButtonMarkup(iconName, label);
  button.dataset.originalHtml = button.innerHTML;
  button.dataset.originalLabel = label;
}

function formatNumber(value) {
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 1,
    minimumFractionDigits: value >= 100 ? 0 : 1
  }).format(value);
}

function formatPeakTime(value) {
  const normalized = String(value || "").trim();
  return normalized || "N/A";
}

function dayCompareSourceLabel(source) {
  return source === "energy" ? "Tesla daily total" : "Estimated from intraday power";
}

function formatDateTime(value) {
  if (!value) {
    return "Not synced yet";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function formatDateTimeLines(value) {
  if (!value) {
    return { dateLine: "Scheduled", timeLine: "" };
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return { dateLine: value, timeLine: "" };
  }
  return {
    dateLine: parsed.toLocaleDateString(),
    timeLine: parsed.toLocaleTimeString()
  };
}

function paletteColor(index, total, palette) {
  if (!palette.length) {
    return "#d97706";
  }
  if (total <= 1) {
    return palette[Math.floor(palette.length / 2)];
  }
  const position = Math.round((index * (palette.length - 1)) / Math.max(total - 1, 1));
  return palette[Math.max(0, Math.min(position, palette.length - 1))];
}

function formatCompactEnergy(value) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric)) {
    return "N/A";
  }
  if (Math.abs(numeric) >= 1000) {
    return `${formatNumber(numeric / 1000)} MWh`;
  }
  return `${formatNumber(numeric)} kWh`;
}

function formatSignalValue(value, kind) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "N/A";
  }
  if (kind === "percent") {
    return `${formatNumber(numeric)}%`;
  }
  if (kind === "delta_percent") {
    const prefix = numeric > 0 ? "+" : "";
    return `${prefix}${formatNumber(numeric)}%`;
  }
  if (kind === "count") {
    return `${Math.round(numeric)} day${Math.round(numeric) === 1 ? "" : "s"}`;
  }
  if (kind === "runs") {
    return `${Math.round(numeric)} run${Math.round(numeric) === 1 ? "" : "s"}`;
  }
  return formatCompactEnergy(numeric);
}

function ensureChartTooltip() {
  if (chartTooltipNode) {
    return chartTooltipNode;
  }
  chartTooltipNode = document.createElement("div");
  chartTooltipNode.className = "chart-tooltip";
  chartTooltipNode.hidden = true;
  document.body.appendChild(chartTooltipNode);
  return chartTooltipNode;
}

function hideChartTooltip() {
  const node = ensureChartTooltip();
  node.hidden = true;
}

function moveChartTooltip(event) {
  const node = ensureChartTooltip();
  if (node.hidden) {
    return;
  }
  const offset = 14;
  const rect = node.getBoundingClientRect();
  let left = event.clientX + offset;
  let top = event.clientY + offset;
  if (left + rect.width > window.innerWidth - 12) {
    left = event.clientX - rect.width - offset;
  }
  if (top + rect.height > window.innerHeight - 12) {
    top = event.clientY - rect.height - offset;
  }
  node.style.left = `${Math.max(12, left)}px`;
  node.style.top = `${Math.max(12, top)}px`;
}

function showChartTooltip(target, event) {
  const node = ensureChartTooltip();
  if (target.dataset.tooltipItems) {
    let items = [];
    try {
      items = JSON.parse(target.dataset.tooltipItems);
    } catch (error) {
      items = [];
    }
    const unit = target.dataset.tooltipUnit || "kWh";
    node.innerHTML = `
      <div class="chart-tooltip-label">${escapeHtml(target.dataset.tooltipLabel || "")}</div>
      <div class="chart-tooltip-list">
        ${items.map((item) => `
          <div class="chart-tooltip-row">
            <div class="chart-tooltip-series">
              <span class="chart-tooltip-swatch" style="background:${escapeHtml(item.color || "#fff")}"></span>
              <span>${escapeHtml(item.label || "")}</span>
            </div>
            <div class="chart-tooltip-value">${formatNumber(Number(item.value || 0))} ${escapeHtml(unit)}</div>
          </div>
        `).join("")}
      </div>
    `;
    node.hidden = false;
    moveChartTooltip(event);
    return;
  }
  const unit = target.dataset.tooltipUnit || "kWh";
  node.innerHTML = `
    <div class="chart-tooltip-label">${escapeHtml(target.dataset.tooltipLabel || "")}</div>
    <div class="chart-tooltip-series">
      <span class="chart-tooltip-swatch" style="background:${escapeHtml(target.dataset.tooltipColor || "#fff")}"></span>
      <span>${escapeHtml(target.dataset.tooltipSeries || "")}</span>
    </div>
    <div class="chart-tooltip-value">${formatNumber(Number(target.dataset.tooltipValue || 0))} ${escapeHtml(unit)}</div>
  `;
  node.hidden = false;
  moveChartTooltip(event);
}

function bindChartTooltips(svg) {
  hideChartTooltip();
  svg.querySelectorAll("[data-tooltip-series], [data-tooltip-items]").forEach((target) => {
    target.addEventListener("pointerenter", (event) => showChartTooltip(target, event));
    target.addEventListener("pointermove", (event) => moveChartTooltip(event));
    target.addEventListener("pointerleave", hideChartTooltip);
  });
  svg.onpointerleave = hideChartTooltip;
}

async function fetchJson(url, options = {}) {
  const { timeoutMs = 0, ...fetchOptions } = options;
  const controller = timeoutMs > 0 && !fetchOptions.signal ? new AbortController() : null;
  const timeoutId = controller
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : null;
  if (controller) {
    fetchOptions.signal = controller.signal;
  }
  try {
    const response = await fetch(url, fetchOptions);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Request failed: ${response.status}`);
    }
    return payload;
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error(`Request timed out after ${Math.ceil(timeoutMs / 1000)}s.`);
    }
    throw error;
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
  }
}

function setStatus(message, tone = "") {
  const node = $("syncStatus");
  node.textContent = message || "";
  node.className = tone ? `status ${tone}` : "status";
}

function setSetupStatus(message, tone = "") {
  const node = $("setupStatus");
  node.textContent = message || "";
  node.className = tone ? `status ${tone}` : "status";
}

function setButtonBusy(button, busy, label) {
  button.disabled = busy;
  button.dataset.originalLabel = button.dataset.originalLabel || button.textContent || "";
  button.dataset.originalHtml = button.dataset.originalHtml || button.innerHTML;
  if (busy) {
    if (label) {
      button.textContent = label;
    }
    return;
  }
  button.innerHTML = button.dataset.originalHtml || button.dataset.originalLabel;
}

function setGeneratedAuthUrl(url) {
  state.generatedAuthUrl = url || "";
  $("generatedAuthUrl").value = state.generatedAuthUrl;
  $("openLoginLinkButton").disabled = !state.generatedAuthUrl;
  $("copyLoginLinkButton").disabled = !state.generatedAuthUrl;
}

function maskEmail(email, reveal = false) {
  const normalized = String(email || "").trim();
  if (!normalized) {
    return "";
  }
  if (reveal) {
    return normalized;
  }
  const [localPart, domainPart = ""] = normalized.split("@");
  const domainPieces = domainPart.split(".");
  const domainName = domainPieces.shift() || "";
  const domainSuffix = domainPieces.length ? `.${domainPieces.join(".")}` : "";
  const maskedLocal = `${localPart.slice(0, Math.min(2, localPart.length))}${localPart.length > 2 ? "***" : "*"}`;
  const maskedDomain = `${domainName.slice(0, Math.min(2, domainName.length))}${domainName.length > 2 ? "***" : "*"}`;
  return `${maskedLocal}@${maskedDomain}${domainSuffix}`;
}

function compactPath(path) {
  const normalized = String(path || "").trim();
  if (!normalized) {
    return "";
  }
  const parts = normalized.split(/[\\/]+/).filter(Boolean);
  if (parts.length <= 4) {
    return normalized;
  }
  return `.../${parts.slice(-4).join("/")}`;
}

function axisLabelStep(labelCount, innerWidth, minSpacing) {
  if (labelCount <= 1) {
    return 1;
  }
  const maxLabels = Math.max(2, Math.floor(innerWidth / minSpacing));
  return Math.max(1, Math.ceil(labelCount / maxLabels));
}

function markerStride(pointCount, innerWidth) {
  if (pointCount <= 1) {
    return 1;
  }
  const maxMarkers = Math.max(18, Math.floor(innerWidth / 18));
  return Math.max(1, Math.ceil(pointCount / maxMarkers));
}

function chartShellWidth(svg, fallback = 760) {
  const shell = svg.closest(".chart-shell");
  const measured = shell?.clientWidth || 0;
  return Math.max(fallback, Math.floor(measured || fallback));
}

function setStepState(id, { active = false, completed = false } = {}) {
  const node = $(id);
  node.classList.toggle("active", active);
  node.classList.toggle("completed", completed);
}

function updateSignInPanel(status) {
  const connected = Boolean(status.auth_configured);
  const details = $("signInDetails");
  const email = (status.config?.email || "").trim();
  const accountPanel = $("connectedAccountPanel");
  const revealButton = $("revealEmailButton");
  const hideButton = $("hideEmailButton");

  details.hidden = false;
  if (!connected) {
    accountPanel.hidden = true;
    state.revealEmail = false;
    return;
  }

  $("connectedAccountEmail").textContent = email ? maskEmail(email, state.revealEmail) : "Masked for screenshots";
  accountPanel.hidden = false;
  revealButton.hidden = state.revealEmail;
  hideButton.hidden = !state.revealEmail;
}

function updateWizard(status) {
  const hasEmail = Boolean((status.config?.email || "").trim());
  const hasAuthUrl = Boolean(state.generatedAuthUrl || status.config?.pending_auth_url);
  const pending = Boolean(status.auth_pending);
  const connected = Boolean(status.auth_configured);
  $("wizardIntro").hidden = connected;
  $("wizardContainer").hidden = connected;
  $("wizardHint").hidden = connected;

  setStepState("wizardStepAccount", {
    active: !connected && !hasAuthUrl,
    completed: hasEmail || pending || connected
  });
  setStepState("wizardStepLoginLink", {
    active: !connected && hasAuthUrl,
    completed: pending || connected
  });
  setStepState("wizardStepFinish", {
    active: !connected && pending,
    completed: connected
  });

  $("authorizationResponse").disabled = !pending;
  $("finishLoginButton").disabled = !pending;
  $("logoutButton").disabled = !pending && !connected;
  $("startLoginButton").disabled = connected;
  $("teslaEmail").disabled = connected;
  $("energySiteId").disabled = connected;

  if (connected) {
    $("wizardHint").textContent = "Tesla sign-in is complete. You can sync new data whenever you want, and the scheduled sync will only fetch what is missing.";
  } else if (pending) {
    $("wizardHint").innerHTML = "Tesla will finish on a <code>Page Not Found</code> screen at <code>auth.tesla.com</code>. Copy that final URL and paste it into Step 3.";
  } else {
    $("wizardHint").innerHTML = "Generate the Tesla login link first. The Tesla page will end on a <code>Page Not Found</code> screen at <code>auth.tesla.com</code>, which is expected.";
  }
}

async function copyText(value) {
  if (!value) {
    throw new Error("Nothing is available to copy yet.");
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const helper = document.createElement("textarea");
  helper.value = value;
  helper.setAttribute("readonly", "readonly");
  helper.style.position = "absolute";
  helper.style.left = "-9999px";
  document.body.appendChild(helper);
  helper.select();
  document.execCommand("copy");
  helper.remove();
}

function currentSiteId() {
  return $("siteSelect").value || "";
}

function currentSite() {
  return (state.status?.sites || []).find((site) => site.site_id === currentSiteId()) || (state.status?.sites || [])[0] || null;
}

function hasSelectedSite() {
  return Boolean((state.status?.sites || []).length && currentSiteId());
}

function setDisabled(ids, disabled) {
  ids.forEach((id) => {
    $(id).disabled = disabled;
  });
}

function setDisabledBySelector(selector, disabled) {
  document.querySelectorAll(selector).forEach((node) => {
    node.disabled = disabled;
  });
}

function parseDateInput(value) {
  const parts = String(value || "").split("-").map((piece) => Number(piece));
  if (parts.length !== 3 || parts.some((piece) => !Number.isFinite(piece))) {
    return null;
  }
  return new Date(parts[0], parts[1] - 1, parts[2]);
}

function formatDateInput(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date, days) {
  const next = new Date(date.getTime());
  next.setDate(next.getDate() + days);
  return next;
}

function addMonths(date, months) {
  const next = new Date(date.getTime());
  next.setDate(1);
  next.setMonth(next.getMonth() + months);
  return next;
}

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function startOfYear(date) {
  return new Date(date.getFullYear(), 0, 1);
}

function clampMonthDay(year, monthIndex, day) {
  const lastDay = new Date(year, monthIndex + 1, 0).getDate();
  return new Date(year, monthIndex, Math.min(day, lastDay));
}

function maxDate(left, right) {
  return left > right ? left : right;
}

function minDate(left, right) {
  return left < right ? left : right;
}

function normalizeDayCompareDates(dates) {
  const unique = Array.from(new Set((dates || []).filter(Boolean)));
  unique.sort();
  return unique.slice(0, 10);
}

function dayCompareRangeBounds() {
  if (!state.dayCompareDates.length) {
    return null;
  }
  const start = parseDateInput(state.dayCompareDates[0]);
  const end = parseDateInput(state.dayCompareDates[state.dayCompareDates.length - 1]);
  if (!start || !end) {
    return null;
  }
  return { start, end };
}

function latestComparableDay(site) {
  return parseDateInput(site?.data_end || state.status?.default_anchor_date || "");
}

function currentDayCompareAnchor() {
  const fallback = parseDateInput($("dayCompareDate")?.value || state.status?.default_anchor_date);
  if (!state.dayCompareDates.length) {
    return fallback;
  }
  if (state.dayComparePreset === "last7" || state.dayComparePreset === "same-day-years") {
    return parseDateInput(state.dayCompareDates[state.dayCompareDates.length - 1]) || fallback;
  }
  return fallback;
}

function shouldAutoApplyDayCompareAnchor() {
  return state.dayComparePreset === "last7" || state.dayComparePreset === "same-day-years";
}

function setDayCompareAnchor(date) {
  if (!date) {
    return;
  }
  $("dayCompareDate").value = formatDateInput(date);
}

function applyDayCompareAnchorSelection() {
  const anchor = parseDateInput($("dayCompareDate").value);
  if (!anchor) {
    renderDayCompareWindowNav();
    return;
  }
  if (shouldAutoApplyDayCompareAnchor()) {
    applyDayCompareQuick(state.dayComparePreset);
    return;
  }
  renderDayCompareWindowNav();
}

function selectedDayCompareAxisMax() {
  const raw = Number($("dayCompareYMax").value);
  return Number.isFinite(raw) && raw > 0 ? raw : null;
}

function applyDayCompareAxisMax(payload) {
  if (!payload) {
    return payload;
  }
  const axisMax = selectedDayCompareAxisMax();
  if (axisMax !== null) {
    payload.y_axis_max = axisMax;
  } else {
    delete payload.y_axis_max;
  }
  return payload;
}

function setDayComparePreset(preset) {
  state.dayComparePreset = preset || "custom";
  document.querySelectorAll(".day-quick-chip").forEach((button) => {
    const quick = button.dataset.dayQuick || "";
    button.classList.toggle("active", quick !== "clear" && quick === state.dayComparePreset);
  });
  renderDayCompareWindowNav();
}

function dayCompareNavConfig() {
  if (state.dayComparePreset === "last7") {
    return {
      prevLabel: "Prev Week",
      nextLabel: "Next Week",
      message: "Showing a rolling 7-day window.",
      dayShift: 7,
      shiftAnchor(anchor, direction) {
        return addDays(anchor, direction * 7);
      }
    };
  }
  if (state.dayComparePreset === "same-day-years") {
    return {
      prevLabel: "Prev Day",
      nextLabel: "Next Day",
      message: "Comparing the same calendar day across selected years.",
      dayShift: 1,
      shiftAnchor(anchor, direction) {
        return addDays(anchor, direction);
      }
    };
  }
  return null;
}

function shiftDayCompareDates(dates, nav, direction) {
  if (!nav) {
    return [];
  }
  return normalizeDayCompareDates(
    (dates || []).map((dateText) => {
      const parsed = parseDateInput(dateText);
      if (!parsed) {
        return "";
      }
      return formatDateInput(addDays(parsed, direction * nav.dayShift));
    }).filter(Boolean)
  );
}

function canShiftDayCompareDates(dates, nav, direction, earliestStart, latestEnd) {
  if (!nav || !dates.length || !earliestStart || !latestEnd) {
    return false;
  }
  const shifted = shiftDayCompareDates(dates, nav, direction);
  if (!shifted.length) {
    return false;
  }
  return shifted.every((dateText) => {
    const parsed = parseDateInput(dateText);
    return parsed && parsed >= earliestStart && parsed <= latestEnd;
  });
}

function renderDayCompareWindowNav() {
  const prevButton = $("dayComparePrevButton");
  const nextButton = $("dayCompareNextButton");
  const labelNode = $("dayCompareWindowLabel");
  const site = currentSite();
  const bounds = dayCompareRangeBounds();
  const nav = dayCompareNavConfig();

  setControlButtonLabel(prevButton, "chevronLeft", nav?.prevLabel || "Prev");
  setControlButtonLabel(nextButton, "chevronRight", nav?.nextLabel || "Next");

  if (!nav || !site) {
    prevButton.disabled = true;
    nextButton.disabled = true;
    labelNode.textContent = "Prev and next work with Same Day Prior Years or Last 7 Days.";
    return;
  }

  const earliestStart = parseDateInput(site.data_start || "");
  const latestEnd = latestComparableDay(site);
  const anchor = currentDayCompareAnchor();

  if (!anchor) {
    prevButton.disabled = true;
    nextButton.disabled = true;
    labelNode.textContent = nav.message;
    return;
  }

  if (state.dayCompareDates.length) {
    prevButton.disabled = !canShiftDayCompareDates(state.dayCompareDates, nav, -1, earliestStart, latestEnd);
    nextButton.disabled = !canShiftDayCompareDates(state.dayCompareDates, nav, 1, earliestStart, latestEnd);
  } else {
    const previousAnchor = nav.shiftAnchor(anchor, -1);
    const nextAnchor = nav.shiftAnchor(anchor, 1);
    prevButton.disabled = !earliestStart || previousAnchor < earliestStart;
    nextButton.disabled = !latestEnd || nextAnchor > latestEnd;
  }

  if (state.dayComparePreset === "last7" && bounds) {
    labelNode.textContent = `Showing ${formatDateInput(bounds.start)} to ${formatDateInput(bounds.end)}.`;
    return;
  }

  labelNode.textContent = `${nav.message} Anchor ${formatDateInput(anchor)}.`;
}

function renderDayCompareSelection() {
  const container = $("dayCompareSelection");
  if (!state.dayCompareDates.length) {
    container.innerHTML = `<div class="subtle">Pick up to 10 days, or use a quick preset to load a comparison set.</div>`;
    renderDayCompareWindowNav();
    return;
  }
  const seriesCount = state.dayCompareDates.length;
  const payloadDates = state.dayComparePayload?.selected_dates || [];
  const payloadMatchesSelection = payloadDates.length === state.dayCompareDates.length
    && payloadDates.every((date, index) => date === state.dayCompareDates[index]);
  const payloadSeries = payloadMatchesSelection
    ? new Map((state.dayComparePayload?.series || []).map((item) => [item.metric, item]))
    : new Map();
  const missingDates = payloadMatchesSelection
    ? new Set(state.dayComparePayload?.missing_dates || [])
    : new Set();
  container.innerHTML = state.dayCompareDates.map((date, index) => {
    const loadedSeries = payloadSeries.get(date);
    const fallbackColor = paletteColor(index, seriesCount, DAY_COMPARE_SERIES_COLORS);
    const swatchColor = loadedSeries?.color || fallbackColor;
    const isMissing = missingDates.has(date);
    const chipClasses = ["selection-chip"];
    if (isMissing) {
      chipClasses.push("missing");
    }
    const label = isMissing ? `${date} (missing)` : date;
    const title = isMissing
      ? `${date} is missing intraday power data, so it is excluded from the chart.`
      : loadedSeries
        ? `${date} is loaded and color-matched to the chart.`
        : `${date} is selected.`;
    return `
      <span class="${chipClasses.join(" ")}" title="${escapeHtml(title)}">
        <span class="selection-chip-swatch" style="background:${escapeHtml(swatchColor)}"></span>
        <span>${escapeHtml(label)}</span>
        <button type="button" class="day-compare-remove" data-date="${escapeHtml(date)}" aria-label="Remove ${escapeHtml(date)}">×</button>
      </span>
    `;
  }).join("");
  renderDayCompareWindowNav();
}

function setDayCompareDates(dates) {
  state.dayCompareDates = normalizeDayCompareDates(dates);
  state.dayCompareInitialized = true;
  renderDayCompareSelection();
}

function addDayCompareDate(dateText) {
  const normalized = String(dateText || "").trim();
  if (!normalized) {
    setStatus("Choose a day to add first.", "error");
    return;
  }
  if (!state.dayCompareDates.includes(normalized) && state.dayCompareDates.length >= 10) {
    setStatus("Day Compare supports up to 10 selected days.", "error");
    return;
  }
  setDayComparePreset("custom");
  setDayCompareDates([...state.dayCompareDates, normalized]);
}

function buildSameDayPreviousYearsDates(anchorDate, site) {
  if (!anchorDate || !site?.data_start) {
    return [];
  }
  const startBound = parseDateInput(site.data_start);
  if (!startBound) {
    return [];
  }
  const dates = [];
  const firstYear = Math.max(startBound.getFullYear(), anchorDate.getFullYear() - 9);
  for (let year = firstYear; year <= anchorDate.getFullYear(); year += 1) {
    const candidate = clampMonthDay(year, anchorDate.getMonth(), anchorDate.getDate());
    if (candidate < startBound) {
      continue;
    }
    dates.push(formatDateInput(candidate));
  }
  return dates;
}

function applyDayCompareQuick(preset) {
  const site = currentSite();
  const anchor = parseDateInput($("dayCompareDate").value || state.status?.default_anchor_date);
  if (!site || !anchor) {
    return;
  }
  if (preset === "clear") {
    setDayComparePreset("custom");
    setDayCompareDates([]);
    state.dayComparePayload = null;
    $("dayCompareMeta").textContent = "Pick days to compare across the same 24-hour shape.";
    renderDayCompareHighlights(null);
    renderLegend("dayCompareLegend", []);
    emptySvg($("dayCompareChart"), "Pick days or use a quick preset to compare intraday power.");
    $("dayCompareTable").innerHTML = "";
    return;
  }
  if (preset === "last7") {
    const dates = [];
    for (let offset = 6; offset >= 0; offset -= 1) {
      dates.push(formatDateInput(addDays(anchor, -offset)));
    }
    setDayComparePreset("last7");
    setDayCompareDates(dates);
    setDayCompareAnchor(anchor);
  } else if (preset === "same-day-years") {
    setDayComparePreset("same-day-years");
    setDayCompareDates(buildSameDayPreviousYearsDates(anchor, site));
    setDayCompareAnchor(anchor);
  }
  loadDayCompare().catch((error) => setStatus(error.message, "error"));
}

function ensureDayCompareSelection() {
  if (!$("dayCompareDate").value && state.status?.default_anchor_date) {
    $("dayCompareDate").value = state.status.default_anchor_date;
  }
  if (state.dayCompareDates.length) {
    renderDayCompareSelection();
    return;
  }
  if (state.dayCompareInitialized) {
    renderDayCompareSelection();
    return;
  }
  const anchor = parseDateInput($("dayCompareDate").value);
  const site = currentSite();
  if (!anchor || !site) {
    renderDayCompareSelection();
    return;
  }
  setDayComparePreset("same-day-years");
  setDayCompareDates(buildSameDayPreviousYearsDates(anchor, site));
}

function pageDayCompareWindow(direction) {
  const nav = dayCompareNavConfig();
  if (!nav) {
    setStatus("Use This Day Previous Years or Last 7 Days to page through Day Compare.", "warning");
    return;
  }
  const site = currentSite();
  const anchor = currentDayCompareAnchor();
  if (!site || !anchor) {
    return;
  }
  const earliestStart = parseDateInput(site.data_start || "");
  const latestEnd = latestComparableDay(site);
  if (state.dayCompareDates.length) {
    const nextDates = shiftDayCompareDates(state.dayCompareDates, nav, direction);
    if (!nextDates.length || !canShiftDayCompareDates(state.dayCompareDates, nav, direction, earliestStart, latestEnd)) {
      return;
    }
    setDayCompareDates(nextDates);
    $("dayCompareDate").value = formatDateInput(nav.shiftAnchor(anchor, direction));
    loadDayCompare().catch((error) => setStatus(error.message, "error"));
    return;
  }
  let nextAnchor = nav.shiftAnchor(anchor, direction);
  if (earliestStart && nextAnchor < earliestStart) {
    nextAnchor = earliestStart;
  }
  if (latestEnd && nextAnchor > latestEnd) {
    nextAnchor = latestEnd;
  }
  $("dayCompareDate").value = formatDateInput(nextAnchor);
  applyDayCompareQuick(state.dayComparePreset);
}

function renderSyncProgress(status) {
  const progress = status.sync_progress || {};
  const shell = $("syncProgressShell");
  const label = $("syncProgressLabel");
  const count = $("syncProgressCount");
  const bar = $("syncProgressBar");
  const message = $("syncProgressMessage");
  const hasProgress = Boolean(progress.active || progress.label || progress.message || progress.finished_at || progress.error);

  shell.hidden = !hasProgress;
  if (!hasProgress) {
    bar.style.width = "0%";
    setButtonBusy($("syncButton"), false);
    return;
  }

  const percent = Math.max(0, Math.min(Number(progress.percent || 0), 100));
  const roundedPercent = Number.isInteger(percent) ? `${percent}%` : `${percent.toFixed(1)}%`;
  const phaseText = progress.phase_total ? ` · ${progress.phase_current}/${progress.phase_total}` : "";

  label.textContent = progress.label || "Sync";
  count.textContent = progress.stage === "error" ? "Error" : `${roundedPercent}${phaseText}`;
  bar.style.width = `${percent}%`;
  bar.style.background = progress.stage === "error"
    ? "var(--bad)"
    : progress.stage === "complete"
      ? "var(--good)"
      : "var(--accent)";
  message.textContent = progress.message || "";

  if (progress.active) {
    const buttonLabel = progress.stage === "downloading"
      ? "Downloading Data"
      : progress.stage === "importing"
        ? "Importing Data"
        : progress.label || "Syncing...";
    setButtonBusy($("syncButton"), true, buttonLabel);
  } else {
    setButtonBusy($("syncButton"), false);
  }
}

function hydrateSetupForm(status) {
  const config = status.config || {};
  $("teslaEmail").value = config.email || "";
  $("energySiteId").value = config.energy_site_id || "";
  setGeneratedAuthUrl(config.pending_auth_url || state.generatedAuthUrl);
}

function hydrateSyncControls(status) {
  const input = $("syncCron");
  const nextValue = status.config?.sync_cron || status.auto_sync_cron || "";
  if (document.activeElement !== input || !input.value.trim()) {
    input.value = nextValue;
  }
}

const DISABLED_SYNC_VALUES = new Set(["", "0", "off", "none", "disabled", "manual"]);

function normalizeSyncCronInput(value) {
  return String(value || "").trim().split(/\s+/).join(" ");
}

function parseCronFieldValue(raw, minimum, maximum, name, allowSundaySeven = false) {
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || String(parsed) !== raw) {
    throw new Error(`Invalid ${name} value '${raw}'.`);
  }
  const normalized = allowSundaySeven && parsed === 7 ? 0 : parsed;
  if (normalized < minimum || normalized > maximum) {
    throw new Error(`${name} values must be between ${minimum} and ${maximum}.`);
  }
  return normalized;
}

function validateCronField(raw, minimum, maximum, name, allowSundaySeven = false) {
  raw.split(",").forEach((part) => {
    const token = part.trim();
    if (!token) {
      throw new Error(`Invalid ${name} field in cron expression.`);
    }
    let base = token;
    if (token.includes("/")) {
      const pieces = token.split("/");
      if (pieces.length !== 2) {
        throw new Error(`Invalid ${name} field in cron expression.`);
      }
      base = pieces[0];
      const step = Number.parseInt(pieces[1], 10);
      if (!Number.isFinite(step) || String(step) !== pieces[1]) {
        throw new Error(`Invalid step '${pieces[1]}' in ${name} field.`);
      }
      if (step <= 0) {
        throw new Error(`${name} field step must be above 0.`);
      }
    }
    if (base === "*") {
      return;
    }
    if (base.includes("-")) {
      const rangePieces = base.split("-");
      if (rangePieces.length !== 2) {
        throw new Error(`Invalid ${name} field in cron expression.`);
      }
      const start = parseCronFieldValue(rangePieces[0], minimum, maximum, name, allowSundaySeven);
      const end = parseCronFieldValue(rangePieces[1], minimum, maximum, name, allowSundaySeven);
      if (start > end) {
        throw new Error(`Invalid range '${base}' in ${name} field.`);
      }
      return;
    }
    parseCronFieldValue(base, minimum, maximum, name, allowSundaySeven);
  });
}

function validateSyncCronInput(value) {
  const normalized = normalizeSyncCronInput(value);
  if (DISABLED_SYNC_VALUES.has(normalized.toLowerCase())) {
    return { valid: true, value: "off" };
  }
  const parts = normalized.split(" ");
  if (parts.length !== 5) {
    return {
      valid: false,
      message: "Sync cron must use five fields like '0 1 * * *', or 'off' to disable."
    };
  }
  try {
    validateCronField(parts[0], 0, 59, "minute");
    validateCronField(parts[1], 0, 23, "hour");
    validateCronField(parts[2], 1, 31, "day-of-month");
    validateCronField(parts[3], 1, 12, "month");
    validateCronField(parts[4], 0, 6, "day-of-week", true);
    return { valid: true, value: normalized };
  } catch (error) {
    return { valid: false, message: error.message || "Invalid cron expression." };
  }
}

function setSyncCronValidation(message = "", tone = "") {
  const input = $("syncCron");
  const node = $("syncCronValidation");
  const invalid = tone === "error" && Boolean(message);
  input.classList.toggle("input-invalid", invalid);
  input.setAttribute("aria-invalid", invalid ? "true" : "false");
  if (!message) {
    node.hidden = true;
    node.textContent = "";
    node.className = "sync-cron-feedback";
    return;
  }
  node.hidden = false;
  node.textContent = message;
  node.className = tone ? `sync-cron-feedback ${tone}` : "sync-cron-feedback";
}

function applyStaticButtonIcons() {
  setControlButtonLabel($("syncButton"), "refresh", "Sync Now");
  setControlButtonLabel($("saveSyncCronButton"), "check", "Save Schedule");
  setControlButtonLabel($("dayCompareAddButton"), "plus", "Add Day");
  setControlButtonLabel($("dayCompareRefreshButton"), "refresh", "Refresh");
  setControlButtonLabel($("dayCompareTodayButton"), "calendar", "Today");
  setControlButtonLabel($("anchorTodayButton"), "calendar", "Today");
  document.querySelectorAll(".section-tab").forEach((button) => {
    const sectionView = button.dataset.sectionView || "charts";
    const iconName = sectionView === "signin"
      ? "shield"
      : sectionView === "sync"
        ? "refresh"
        : sectionView === "insights"
          ? "trophy"
          : "chart";
    const label = button.textContent || "";
    button.classList.add("button-with-icon");
    button.innerHTML = iconButtonMarkup(iconName, label.trim());
    button.dataset.originalHtml = button.innerHTML;
    button.dataset.originalLabel = label.trim();
  });
  document.querySelectorAll(".day-quick-chip").forEach((button) => {
    const quick = button.dataset.dayQuick || "";
    const iconName = quick === "clear" ? "x" : "calendar";
    const label = button.textContent || "";
    button.classList.add("button-with-icon");
    button.innerHTML = iconButtonMarkup(iconName, label.trim());
    button.dataset.originalHtml = button.innerHTML;
    button.dataset.originalLabel = label.trim();
  });
}

function buildTrendMetricPills() {
  $("metricPills").innerHTML = METRICS.map((metric, index) => `
    <label class="pill">
      <input type="checkbox" class="metricCheck" value="${metric.key}" ${index < 2 ? "checked" : ""}>
      <span class="metric-pill-content">${iconMarkup(metricIconName(metric.key))}<span>${escapeHtml(metric.label)}</span></span>
    </label>
  `).join("");
}

function selectedMetrics() {
  const values = Array.from(document.querySelectorAll(".metricCheck:checked")).map((node) => node.value);
  return values.length ? values : ["home_usage"];
}

function buildComparisonMetricPills() {
  $("comparisonMetricPills").innerHTML = METRICS.map((metric) => `
    <label class="pill">
      <input type="checkbox" class="comparisonMetricCheck" value="${metric.key}" checked>
      <span class="metric-pill-content">${iconMarkup(metricIconName(metric.key))}<span>${escapeHtml(metric.label)}</span></span>
    </label>
  `).join("");
}

function selectedComparisonMetrics() {
  const values = Array.from(document.querySelectorAll(".comparisonMetricCheck:checked")).map((node) => node.value);
  return values.length ? values : ["solar_generation"];
}

function buildPatternMetricPills() {
  $("patternMetricPills").innerHTML = METRICS.map((metric, index) => `
    <label class="pill">
      <input type="checkbox" class="patternMetricCheck" value="${metric.key}" ${index < 2 ? "checked" : ""}>
      <span class="metric-pill-content">${iconMarkup(metricIconName(metric.key))}<span>${escapeHtml(metric.label)}</span></span>
    </label>
  `).join("");
}

function selectedPatternMetrics() {
  const values = Array.from(document.querySelectorAll(".patternMetricCheck:checked")).map((node) => node.value);
  return values.length ? values : ["solar_generation", "home_usage"];
}

function buildDayCompareMetricPills() {
  const current = $("dayCompareMetric").value || "load_power";
  $("dayCompareMetricPills").innerHTML = DAY_COMPARE_METRICS.map((metric) => `
    <button
      type="button"
      class="pill-toggle day-metric-pill ${metric.key === current ? "active" : ""}"
      data-metric="${metric.key}">
      <span class="metric-pill-content">${iconMarkup(metricIconName(metric.key))}<span>${escapeHtml(metric.label)}</span></span>
    </button>
  `).join("");
}

function setDayCompareMetric(metricKey) {
  const nextMetric = DAY_COMPARE_METRICS.find((metric) => metric.key === metricKey)?.key || "load_power";
  $("dayCompareMetric").value = nextMetric;
  document.querySelectorAll(".day-metric-pill").forEach((button) => {
    button.classList.toggle("active", button.dataset.metric === nextMetric);
  });
}

function filterSeries(payload, metricKeys) {
  return {
    ...payload,
    series: (payload.series || []).filter((item) => metricKeys.includes(item.metric))
  };
}

function currentPerformanceScope() {
  return state.performanceScope || "month";
}

function comparisonNavConfig(mode) {
  const currentMode = mode || $("compareMode").value || "day";
  if (currentMode === "week") {
    return {
      prevLabel: "Prev Week",
      nextLabel: "Next Week",
      shiftAnchor(anchor, direction) {
        return addDays(anchor, direction * 7);
      }
    };
  }
  if (currentMode === "month") {
    return {
      prevLabel: "Prev Month",
      nextLabel: "Next Month",
      shiftAnchor(anchor, direction) {
        return addMonths(anchor, direction);
      }
    };
  }
  return {
    prevLabel: "Prev Day",
    nextLabel: "Next Day",
    shiftAnchor(anchor, direction) {
      return addDays(anchor, direction);
    }
  };
}

function setPerformanceScope(scope) {
  state.performanceScope = scope || "month";
  document.querySelectorAll(".scope-chip").forEach((button) => {
    button.classList.toggle("active", button.dataset.scope === state.performanceScope);
  });
}

function defaultSectionViewForStatus(status) {
  if ((status?.sites || []).length) {
    return "charts";
  }
  if (status?.auth_configured) {
    return "sync";
  }
  return "signin";
}

function updateChartPanelVisibility() {
  const chartsVisible = state.sectionView === "charts";
  document.querySelectorAll("[data-chart-panel]").forEach((panel) => {
    const active = chartsVisible && panel.dataset.chartPanel === state.chartView;
    panel.hidden = !active;
    panel.classList.toggle("chart-panel-active", active);
  });
}

function setSectionView(view, options = {}) {
  const nextView = VALID_SECTION_VIEWS.has(view) ? view : DEFAULT_SECTION_VIEW;
  state.sectionView = nextView;
  if (options.persist !== false) {
    savePreference(PREFERENCE_KEYS.sectionView, nextView);
    state.sectionViewResolved = true;
  }
  document.querySelectorAll(".section-tab").forEach((button) => {
    const active = button.dataset.sectionView === state.sectionView;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll("[data-section-view]").forEach((panel) => {
    if (panel.hasAttribute("data-chart-panel")) {
      return;
    }
    panel.hidden = panel.dataset.sectionView !== state.sectionView;
  });
  updateChartPanelVisibility();
  if (state.sectionView === "charts") {
    window.requestAnimationFrame(() => rerenderChartsFromCache());
  }
}

function setChartView(view, options = {}) {
  const nextView = VALID_CHART_VIEWS.has(view) ? view : DEFAULT_CHART_VIEW;
  state.chartView = nextView;
  if (options.persist !== false) {
    savePreference(PREFERENCE_KEYS.chartView, nextView);
  }
  document.querySelectorAll(".chart-tab").forEach((button) => {
    const active = button.dataset.chartView === state.chartView;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  updateChartPanelVisibility();
  if (state.sectionView === "charts") {
    window.requestAnimationFrame(() => rerenderChartsFromCache());
  }
}

function populateSites(status) {
  const select = $("siteSelect");
  const sites = status.sites || [];
  if (!sites.length) {
    select.innerHTML = "<option value=''>No data yet</option>";
    return;
  }
  select.innerHTML = sites.map((site) => `
    <option value="${escapeHtml(site.site_id)}">${escapeHtml(site.site_name || site.site_id)}</option>
  `).join("");
  if (status.selected_site_id) {
    select.value = status.selected_site_id;
  }
  if (!select.value && sites[0]) {
    select.value = sites[0].site_id;
  }
}

function updateDataAvailability(status) {
  const hasData = Boolean((status.sites || []).length);
  $("insightsPanel").classList.toggle("locked", !hasData);
  $("chartWorkspacePanel").classList.toggle("locked", !hasData);
  $("diagnosticsPanel").classList.toggle("locked", !hasData);
  $("dayComparePanel").classList.toggle("locked", !hasData);
  $("comparisonPanel").classList.toggle("locked", !hasData);
  $("performancePanel").classList.toggle("locked", !hasData);
  $("patternPanel").classList.toggle("locked", !hasData);
  $("trendPanel").classList.toggle("locked", !hasData);
  setDisabled(["dayCompareDate", "dayCompareMetric", "dayCompareAddButton", "dayCompareRefreshButton", "dayComparePrevButton", "dayCompareNextButton", "dayCompareYMax", "dayCompareYMaxAutoButton"], !hasData);
  setDisabled(["comparisonPrevButton", "comparisonNextButton"], !hasData);
  setDisabled(["compareMode", "anchorDate", "compareYears", "compareButton"], !hasData);
  setDisabled(["patternStart", "patternEnd", "patternValueMode", "patternButton"], !hasData);
  setDisabled(["trendStart", "trendEnd", "trendGranularity", "trendChartType", "trendButton"], !hasData);
  setDisabledBySelector(".day-quick-chip", !hasData);
  setDisabledBySelector(".day-metric-pill", !hasData);
  setDisabledBySelector(".day-compare-remove", !hasData);
  setDisabledBySelector(".range-chip", !hasData);
  setDisabledBySelector(".chart-tab", !hasData);
  setDisabledBySelector(".comparisonMetricCheck", !hasData);
  setDisabledBySelector(".patternMetricCheck", !hasData);
  setDisabledBySelector(".scope-chip", !hasData);
}

function renderHeroStatus(status) {
  const node = $("heroStatusGrid");
  if (!node) {
    return;
  }
  const email = (status.config?.email || "").trim();
  const signInCard = !status.library_ready
    ? {
        label: "Sign-In Status",
        value: "Install Required",
        detail: status.message || "Install the Tesla dependency set before signing in.",
        tone: "error",
        icon: "shield"
      }
    : status.auth_configured
      ? {
          label: "Sign-In Status",
          value: "Connected",
          detail: email ? `Tesla session cached for ${maskEmail(email)}.` : "Local Tesla session is cached and ready.",
          tone: "good",
          icon: "shield"
        }
      : status.auth_pending
        ? {
            label: "Sign-In Status",
            value: "Pending",
            detail: "Paste the final Tesla URL to finish the Tesla sign-in flow.",
            tone: "warning",
            icon: "shield"
          }
        : email
          ? {
              label: "Sign-In Status",
              value: "Setup Started",
              detail: "Generate the Tesla login link and finish sign-in to unlock syncing.",
              tone: "warning",
              icon: "shield"
            }
          : {
              label: "Sign-In Status",
              value: "Not Connected",
              detail: "Enter your Tesla account email to start local sign-in.",
              tone: "error",
              icon: "shield"
            };

  const syncCard = status.sync_in_progress
    ? {
        label: "Sync Status",
        value: "Syncing Now",
        detail: status.sync_progress?.message || "Updating the local Tesla cache and SQLite data.",
        tone: "info",
        icon: "refresh"
      }
    : status.last_sync_error
      ? {
          label: "Sync Status",
          value: "Needs Attention",
          detail: status.last_sync_error,
          tone: "error",
          icon: "refresh"
        }
      : status.auto_sync_missed
        ? {
            label: "Sync Status",
            value: "Behind Schedule",
            detail: `Missed scheduled sync at ${formatDateTime(status.auto_sync_missed_since)}.`,
            tone: "warning",
            icon: "refresh"
          }
        : status.last_sync
          ? {
              label: "Sync Status",
              value: "Ready",
              detail: `Last sync ${formatDateTime(status.last_sync)}.`,
              tone: "good",
              icon: "refresh"
            }
          : status.auth_configured
            ? {
                label: "Sync Status",
                value: "Ready to Sync",
                detail: "No cached data yet. Run a sync to import Tesla history.",
                tone: "warning",
                icon: "refresh"
              }
            : {
                label: "Sync Status",
                value: "Waiting on Sign-In",
                detail: "Complete Tesla sign-in before syncing data.",
                tone: "warning",
                icon: "refresh"
              };

  const nextSyncLines = status.auto_sync_enabled
    ? formatDateTimeLines(status.auto_sync_next_run)
    : { dateLine: "Manual Only", timeLine: "" };
  const nextSyncCard = {
    label: "Next Sync",
    dateLine: nextSyncLines.dateLine,
    timeLine: nextSyncLines.timeLine,
    detail: status.auto_sync_enabled
      ? (status.auto_sync_description || "Automatic sync is enabled.")
      : "Automatic sync is disabled. Manual sync is still available.",
    tone: status.auto_sync_enabled ? "info" : "warning",
    icon: "clock"
  };

  node.innerHTML = `
    ${[signInCard, syncCard].map((card) => `
      <article
        class="hero-status-icon-badge ${escapeHtml(card.tone || "")}" tabindex="0"
        aria-label="${escapeHtml(`${card.label}: ${card.value}`)}">
        <div class="hero-status-icon-shell ${escapeHtml(card.tone || "")}">
          ${iconMarkup(card.icon, "hero-status-icon")}
        </div>
        <div class="hero-status-tooltip" role="tooltip">
          <div class="hero-status-tooltip-label">${escapeHtml(card.label)}</div>
          <div class="hero-status-tooltip-value">${escapeHtml(card.value)}</div>
          <div class="hero-status-tooltip-body">${escapeHtml(card.detail)}</div>
        </div>
      </article>
    `).join("")}
    <article class="hero-status-next-badge ${escapeHtml(nextSyncCard.tone || "")}">
      <div class="hero-status-next-head">
        <div class="hero-status-icon-shell ${escapeHtml(nextSyncCard.tone || "")}">
          ${iconMarkup(nextSyncCard.icon, "hero-status-icon")}
        </div>
        <div class="hero-status-label">${escapeHtml(nextSyncCard.label)}</div>
      </div>
      <div class="hero-status-next-lines">
        <span class="hero-status-date-line">${escapeHtml(nextSyncCard.dateLine)}</span>
        ${nextSyncCard.timeLine ? `<span class="hero-status-time-line">${escapeHtml(nextSyncCard.timeLine)}</span>` : ""}
      </div>
    </article>
  `;
}

function renderSummary(status) {
  const cards = [];
  const selected = currentSite();
  cards.push({
    label: "Last Sync",
    value: status.last_sync ? formatDateTime(status.last_sync) : "Never",
    hint: status.sync_in_progress ? "Sync in progress" : "Local SQLite cache",
    tone: status.auto_sync_missed ? "warning" : ""
  });
  cards.push({
    label: "Auto Sync",
    value: status.auto_sync_enabled ? (status.auto_sync_description || "Enabled") : "Disabled",
    hint: status.auto_sync_missed
      ? `Missed scheduled sync at ${formatDateTime(status.auto_sync_missed_since)}`
      : status.auto_sync_next_run
        ? `Next run ${formatDateTime(status.auto_sync_next_run)}`
        : "Manual sync still available",
    tone: status.auto_sync_missed ? "warning" : ""
  });
  if (status.config?.download_root) {
    cards.push({
      label: "Archive",
      value: compactPath(status.config.download_root),
      hint: "CSV backup root"
    });
  }
  if (selected) {
    cards.push({
      label: "Site",
      value: selected.site_name || selected.site_id,
      hint: selected.time_zone || "Timezone unknown"
    });
    cards.push({
      label: "Coverage",
      value: selected.data_start && selected.data_end ? `${selected.data_start} to ${selected.data_end}` : "No cached data",
      hint: selected.row_count ? `${selected.row_count} daily rows cached` : "Run sync to import history"
    });
  }
  $("summaryGrid").innerHTML = cards.map((card) => `
    <article class="summary-card ${escapeHtml(card.tone || "")}">
      <div class="label">${escapeHtml(card.label)}</div>
      <div class="value">${escapeHtml(card.value)}</div>
      <div class="hint">${escapeHtml(card.hint)}</div>
    </article>
  `).join("");
}

function renderComparisonWindowNav() {
  const prevButton = $("comparisonPrevButton");
  const nextButton = $("comparisonNextButton");
  const labelNode = $("comparisonWindowLabel");
  const site = currentSite();
  const anchor = parseDateInput($("anchorDate").value || state.status?.default_anchor_date);
  const nav = comparisonNavConfig($("compareMode").value);

  prevButton.textContent = nav.prevLabel;
  nextButton.textContent = nav.nextLabel;

  if (!site || !anchor) {
    prevButton.disabled = true;
    nextButton.disabled = true;
    labelNode.textContent = "Jump day, week, month, or YTD window from the anchor date.";
    return;
  }

  const earliestStart = parseDateInput(site.data_start || "");
  const latestEnd = latestComparableDay(site);
  const previousAnchor = nav.shiftAnchor(anchor, -1);
  const nextAnchor = nav.shiftAnchor(anchor, 1);

  prevButton.disabled = !earliestStart || previousAnchor < earliestStart;
  nextButton.disabled = !latestEnd || nextAnchor > latestEnd;
  labelNode.textContent = `${nav.prevLabel.replace("Prev ", "")} navigation from anchor ${formatDateInput(anchor)}.`;
}

function renderInsights(payload) {
  const container = $("insightsSections");
  const meta = $("insightsMeta");
  if (!payload || !payload.sections || !payload.sections.length) {
    meta.textContent = "No insight data is available yet.";
    container.innerHTML = `
      <div class="insight-card">
        <div class="insight-label">No Data</div>
        <div class="insight-hint">Finish sign-in and sync data to calculate lifetime peaks and current-year signals.</div>
      </div>
    `;
    return;
  }

  meta.textContent = payload.summary || "";
  container.innerHTML = payload.sections.map((section) => {
    const sectionSpec = insightIconSpec(section.title || "", "", section.accent || "");
    return `
      <section class="insight-group" data-group-key="${escapeHtml(section.title || "")}">
        <div class="subsection-heading">
          <div class="subsection-toggle-head">
            ${iconMarkup(sectionSpec.icon, `subsection-icon-badge ${sectionSpec.tone}`)}
            <span class="subsection-toggle-title">${escapeHtml(section.title || "")}</span>
          </div>
        </div>
        <div class="subsection-body">
          <div class="insight-grid">
            ${(section.items || []).map((item) => {
              const itemSpec = insightItemIconSpec(section.title || "", item.label || "", section.accent || "");
              return `
                <article class="insight-card ${escapeHtml(section.accent || "")} ${escapeHtml(item.tone || "")}">
                  <div class="insight-card-head">
                    ${iconMarkup(itemSpec.icon, `insight-card-icon ${itemSpec.tone}`)}
                    <div class="insight-label-wrap">
                      <div class="insight-label">${escapeHtml(item.label || "")}</div>
                    </div>
                  </div>
                  <div class="insight-value">${escapeHtml(formatSignalValue(item.value, item.kind || "energy"))}</div>
                  <div class="insight-hint">${escapeHtml(item.hint || "")}</div>
                </article>
              `;
            }).join("")}
          </div>
        </div>
      </section>
    `;
  }).join("");
}

function renderDiagnostics(payload) {
  const meta = $("diagnosticsMeta");
  const alertsNode = $("diagnosticsAlerts");
  const sectionsNode = $("diagnosticsSections");
  const tablesNode = $("diagnosticsTables");

  if (!payload || !payload.sections || !payload.sections.length) {
    meta.textContent = "No troubleshooting data is available yet.";
    alertsNode.innerHTML = "";
    sectionsNode.innerHTML = `
      <div class="insight-card">
        <div class="insight-label">No Data</div>
        <div class="insight-hint">Finish sign-in and sync data to flag low-solar and high-usage patterns against prior years.</div>
      </div>
    `;
    tablesNode.innerHTML = "";
    return;
  }

  meta.textContent = payload.summary || "";
  alertsNode.innerHTML = (payload.alerts || []).map((alert) => `
    <article class="diagnostic-alert ${escapeHtml(alert.tone || "")}">
      <div class="diagnostic-alert-title">${escapeHtml(alert.title || "")}</div>
      <div class="diagnostic-alert-body">${escapeHtml(alert.body || "")}</div>
    </article>
  `).join("");

  sectionsNode.innerHTML = payload.sections.map((section) => {
    const sectionSpec = insightIconSpec(section.title || "", "", section.accent || "");
    return `
      <section class="insight-group" data-group-key="${escapeHtml(section.title || "")}">
        <div class="subsection-heading">
          <div class="subsection-toggle-head">
            ${iconMarkup(sectionSpec.icon, `subsection-icon-badge ${sectionSpec.tone}`)}
            <span class="subsection-toggle-title">${escapeHtml(section.title || "")}</span>
          </div>
        </div>
        <div class="subsection-body">
          <div class="insight-grid">
            ${(section.items || []).map((item) => {
              const itemSpec = insightItemIconSpec(section.title || "", item.label || "", section.accent || "");
              return `
                <article class="insight-card ${escapeHtml(section.accent || "")} ${escapeHtml(item.tone || "")}">
                  <div class="insight-card-head">
                    ${iconMarkup(itemSpec.icon, `insight-card-icon ${itemSpec.tone}`)}
                    <div class="insight-label-wrap">
                      <div class="insight-label">${escapeHtml(item.label || "")}</div>
                    </div>
                  </div>
                  <div class="insight-value">${escapeHtml(formatSignalValue(item.value, item.kind || "energy"))}</div>
                  <div class="insight-hint">${escapeHtml(item.hint || "")}</div>
                </article>
              `;
            }).join("")}
          </div>
        </div>
      </section>
    `;
  }).join("");

  tablesNode.innerHTML = (payload.tables || []).map((table) => `
    <details class="table-panel">
      <summary>${escapeHtml(table.title || "Details")}</summary>
      <div class="table-wrap">
        ${table.description ? `<div class="table-description">${escapeHtml(table.description)}</div>` : ""}
        ${!table.rows || !table.rows.length ? `<div class="empty-detail">No flagged days right now.</div>` : `
          <table>
            <thead>
              <tr>
                ${(table.columns || []).map((column) => `<th>${escapeHtml(column.label || "")}</th>`).join("")}
              </tr>
            </thead>
            <tbody>
              ${(table.rows || []).map((row) => `
                <tr>
                  ${(table.columns || []).map((column) => {
                    const value = row[column.key];
                    if (column.type === "history") {
                      return `
                        <td>
                          <div class="diagnostic-history">${escapeHtml(value ?? "")}</div>
                          <div class="diagnostic-history-hint">${escapeHtml(row.history_hint ?? "")}</div>
                        </td>
                      `;
                    }
                    if (column.type === "action") {
                      return `
                        <td>
                          <button
                            type="button"
                            class="secondary compact-button diagnostic-inspect-button"
                            data-date="${escapeHtml(row.date ?? "")}"
                            data-metric="${escapeHtml(value ?? "")}">
                            Inspect
                          </button>
                        </td>
                      `;
                    }
                    if (column.unit === "kWh") {
                      const numeric = Number(value);
                      return `<td>${Number.isFinite(numeric) ? formatNumber(numeric) : escapeHtml(value ?? "")}</td>`;
                    }
                    return `<td>${escapeHtml(value ?? "")}</td>`;
                  }).join("")}
                </tr>
              `).join("")}
            </tbody>
          </table>
        `}
      </div>
    </details>
  `).join("");
}

function inspectDiagnosticDay(dateText, metricKey) {
  if (!dateText) {
    return;
  }
  $("dayCompareDate").value = dateText;
  setDayCompareMetric(metricKey || "solar_power");
  $("anchorDate").value = dateText;
  $("compareMode").value = "day";
  setSectionView("charts");
  setChartView("daycompare");
  applyDayCompareQuick("same-day-years");
  loadComparison().catch((error) => setStatus(error.message, "error"));
  $("chartWorkspacePanel").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderLegend(nodeId, series) {
  $(nodeId).innerHTML = (series || []).map((item) => `
    <div class="legend-item">
      <span class="legend-swatch" style="background:${escapeHtml(item.color)}"></span>
      <span>${escapeHtml(item.label)}</span>
    </div>
  `).join("");
}

function emptySvg(svg, message) {
  hideChartTooltip();
  svg.setAttribute("viewBox", "0 0 960 420");
  svg.style.width = "100%";
  svg.style.minWidth = "720px";
  svg.style.height = "420px";
  svg.innerHTML = `
    <rect x="0" y="0" width="960" height="420" rx="0" fill="transparent"></rect>
    <text x="480" y="210" text-anchor="middle" fill="${CHART_COLORS.muted}" font-size="16">${escapeHtml(message)}</text>
  `;
}

function renderNoSiteState(metaId, legendId, chartId, tableId, message) {
  $(metaId).textContent = message;
  renderLegend(legendId, []);
  emptySvg($(chartId), message);
  renderTable(tableId, []);
}

function niceMax(value) {
  if (value <= 0) {
    return 1;
  }
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
  const normalized = value / magnitude;
  if (normalized <= 1) return magnitude;
  if (normalized <= 2) return 2 * magnitude;
  if (normalized <= 5) return 5 * magnitude;
  return 10 * magnitude;
}

function setChartViewport(svg, width, height) {
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.style.width = "100%";
  svg.style.minWidth = `${Math.max(680, Math.min(width, 1280))}px`;
  svg.style.height = `${height}px`;
}

function renderGroupedBarChart(svgId, payload) {
  const svg = $(svgId);
  const labels = payload.labels || [];
  const series = payload.series || [];
  const unit = payload.unit || "kWh";
  const axisLabel = payload.axis_label || unit;
  const values = series.flatMap((item) => item.values || []);
  const maxValue = niceMax(Math.max(...values, 0));
  if (!labels.length || !series.length) {
    emptySvg(svg, "No comparison data in the selected range.");
    return;
  }

  const shellWidth = chartShellWidth(svg, 760);
  const width = Math.min(Math.max(shellWidth, 760, 180 + labels.length * Math.max(24, series.length * 14)), 1440);
  const height = 420;
  const margin = { top: 20, right: 24, bottom: 72, left: 72 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const groupWidth = innerWidth / labels.length;
  const barWidth = Math.max(12, (groupWidth - 18) / series.length);
  const baseline = height - margin.bottom;
  const ticks = 4;
  const labelStep = axisLabelStep(labels.length, innerWidth, 84);
  const parts = [];

  parts.push(`<rect x="0" y="0" width="${width}" height="${height}" rx="0" fill="transparent"></rect>`);

  for (let i = 0; i <= ticks; i += 1) {
    const value = (maxValue / ticks) * i;
    const y = baseline - (value / maxValue) * innerHeight;
    parts.push(`<line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" stroke="${CHART_COLORS.grid}" stroke-width="1"></line>`);
    parts.push(`<text x="${margin.left - 10}" y="${y + 4}" text-anchor="end" fill="${CHART_COLORS.muted}" font-size="12">${formatNumber(value)}</text>`);
  }

  labels.forEach((label, groupIndex) => {
    const groupStart = margin.left + groupIndex * groupWidth;
    const offset = (groupWidth - (barWidth * series.length)) / 2;
    series.forEach((metric, metricIndex) => {
      const value = metric.values[groupIndex] || 0;
      const barHeight = (value / maxValue) * innerHeight;
      const x = groupStart + offset + metricIndex * barWidth;
      const y = baseline - barHeight;
      parts.push(`
        <rect
          class="chart-bar"
          x="${x}"
          y="${y}"
          width="${barWidth - 4}"
          height="${Math.max(barHeight, 0)}"
          rx="0"
          fill="${metric.color}"
          data-tooltip-series="${escapeHtml(metric.label)}"
          data-tooltip-label="${escapeHtml(label)}"
          data-tooltip-value="${value}"
          data-tooltip-unit="${escapeHtml(unit)}"
          data-tooltip-color="${escapeHtml(metric.color)}"></rect>
        `);
    });
    if (groupIndex % labelStep === 0 || groupIndex === labels.length - 1) {
      parts.push(`<text x="${groupStart + groupWidth / 2}" y="${height - 28}" text-anchor="middle" fill="${CHART_COLORS.text}" font-size="12">${escapeHtml(label)}</text>`);
    }
  });

  parts.push(`<line x1="${margin.left}" y1="${baseline}" x2="${width - margin.right}" y2="${baseline}" stroke="${CHART_COLORS.axis}" stroke-width="1.2"></line>`);
  parts.push(`<text x="${margin.left}" y="16" fill="${CHART_COLORS.muted}" font-size="12">${escapeHtml(axisLabel)}</text>`);
  setChartViewport(svg, width, height);
  svg.innerHTML = parts.join("");
  bindChartTooltips(svg);
}

function renderLineChart(svgId, payload) {
  const svg = $(svgId);
  const labels = payload.labels || [];
  const series = payload.series || [];
  const unit = payload.unit || "kWh";
  const axisLabel = payload.axis_label || unit;
  const sharedTooltip = Boolean(payload.shared_tooltip);
  const visibleSeries = series.filter((item) => (item.values || []).some((value) => value > 0));
  const values = visibleSeries.flatMap((item) => item.values || []);
  const naturalMaxValue = Math.max(...values, 0);
  const configuredMax = Number(payload.y_axis_max);
  const maxValue = Number.isFinite(configuredMax) && configuredMax > 0
    ? configuredMax
    : niceMax(naturalMaxValue);
  if (!labels.length || !series.length) {
    emptySvg(svg, "No trend data in the selected range.");
    return;
  }

  const shellWidth = chartShellWidth(svg, 760);
  const width = Math.min(Math.max(760, shellWidth), 1440);
  const height = 420;
  const margin = { top: 20, right: 24, bottom: 72, left: 72 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const stepX = labels.length > 1 ? innerWidth / (labels.length - 1) : 0;
  const baseline = height - margin.bottom;
  const ticks = 4;
  const labelStep = axisLabelStep(labels.length, innerWidth, 88);
  const pointStep = markerStride(labels.length, innerWidth);
  const dense = labels.length > 120;
  const strokeWidth = dense ? 2.1 : 3;
  const parts = [];

  parts.push(`<rect x="0" y="0" width="${width}" height="${height}" rx="0" fill="transparent"></rect>`);

  for (let i = 0; i <= ticks; i += 1) {
    const value = (maxValue / ticks) * i;
    const y = baseline - (value / maxValue) * innerHeight;
    parts.push(`<line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" stroke="${CHART_COLORS.grid}" stroke-width="1"></line>`);
    parts.push(`<text x="${margin.left - 10}" y="${y + 4}" text-anchor="end" fill="${CHART_COLORS.muted}" font-size="12">${formatNumber(value)}</text>`);
  }

  labels.forEach((label, index) => {
    if (index % labelStep !== 0 && index !== labels.length - 1) {
      return;
    }
    const x = margin.left + (index * stepX);
    parts.push(`<text x="${x}" y="${height - 28}" text-anchor="middle" fill="${CHART_COLORS.text}" font-size="12">${escapeHtml(label)}</text>`);
  });

  visibleSeries.forEach((metric) => {
    const points = metric.values.map((value, index) => {
      const x = margin.left + (index * stepX);
      const y = baseline - (Math.min(value || 0, maxValue) / maxValue) * innerHeight;
      return { x, y, value: value || 0, label: labels[index] };
    });
    const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
    parts.push(`<path d="${path}" fill="none" stroke="${metric.color}" stroke-width="${strokeWidth}" stroke-linejoin="round" stroke-linecap="round"></path>`);
    points.forEach((point, pointIndex) => {
      const shouldMark = pointIndex === 0 || pointIndex === points.length - 1 || pointStep === 1 || pointIndex % pointStep === 0;
      if (!shouldMark) {
        return;
      }
      parts.push(`<circle cx="${point.x}" cy="${point.y}" r="3.2" fill="${metric.color}"></circle>`);
      if (!sharedTooltip) {
        parts.push(`
          <circle
            class="chart-point-hit"
            cx="${point.x}"
            cy="${point.y}"
            r="10"
            fill="transparent"
            data-tooltip-series="${escapeHtml(metric.label)}"
            data-tooltip-label="${escapeHtml(point.label)}"
            data-tooltip-value="${point.value}"
            data-tooltip-unit="${escapeHtml(unit)}"
            data-tooltip-color="${escapeHtml(metric.color)}"></circle>
        `);
      }
    });
  });

  if (sharedTooltip) {
    labels.forEach((label, index) => {
      const x = margin.left + (index * stepX);
      const previousX = index === 0 ? margin.left : margin.left + ((index - 1) * stepX);
      const nextX = index === labels.length - 1 ? width - margin.right : margin.left + ((index + 1) * stepX);
      const left = index === 0 ? margin.left : x - ((x - previousX) / 2);
      const right = index === labels.length - 1 ? width - margin.right : x + ((nextX - x) / 2);
      const items = visibleSeries.map((metric) => ({
        label: metric.label,
        color: metric.color,
        value: (metric.values || [])[index] || 0
      }));
      parts.push(`
        <rect
          class="chart-hover-band"
          x="${left}"
          y="${margin.top}"
          width="${Math.max(1, right - left)}"
          height="${innerHeight}"
          fill="transparent"
          data-tooltip-items='${escapeHtml(JSON.stringify(items))}'
          data-tooltip-label="${escapeHtml(label)}"
          data-tooltip-unit="${escapeHtml(unit)}"></rect>
      `);
    });
  }

  parts.push(`<line x1="${margin.left}" y1="${baseline}" x2="${width - margin.right}" y2="${baseline}" stroke="${CHART_COLORS.axis}" stroke-width="1.2"></line>`);
  parts.push(`<text x="${margin.left}" y="16" fill="${CHART_COLORS.muted}" font-size="12">${escapeHtml(axisLabel)}</text>`);
  setChartViewport(svg, width, height);
  svg.innerHTML = parts.join("");
  bindChartTooltips(svg);
}

function trendChartTypeLabel(chartType) {
  return chartType === "bar" ? "bar chart" : "line chart";
}

function rerenderChartsFromCache() {
  if (state.dayComparePayload) {
    applyDayCompareAxisMax(state.dayComparePayload);
    renderDayCompareHighlights(state.dayComparePayload);
    renderLineChart("dayCompareChart", state.dayComparePayload);
  }
  if (state.comparisonPayload) {
    renderGroupedBarChart("comparisonChart", filterSeries(state.comparisonPayload, selectedComparisonMetrics()));
  }
  if (state.performancePayload) {
    renderLineChart("performanceChart", state.performancePayload);
  }
  if (state.patternPayload) {
    renderGroupedBarChart("patternChart", state.patternPayload);
  }
  if (state.trendPayload) {
    renderTrendChart(state.trendPayload, $("trendChartType").value || "line");
  }
}

function renderTrendChart(payload, chartType) {
  if (chartType === "bar") {
    renderGroupedBarChart("trendChart", payload);
    return;
  }
  renderLineChart("trendChart", payload);
}

function renderTable(nodeId, rows) {
  const container = $(nodeId);
  if (!rows || !rows.length) {
    container.innerHTML = "";
    return;
  }
  const headers = ["Period", "Solar", "Usage", "Export", "Import"];
  container.innerHTML = `
    <table>
      <thead>
        <tr>
          ${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}
        </tr>
      </thead>
      <tbody>
        ${rows.map((row) => `
          <tr>
            <td>${escapeHtml(row.label)}</td>
            <td>${formatNumber(row.solar_generation)}</td>
            <td>${formatNumber(row.home_usage)}</td>
            <td>${formatNumber(row.grid_export)}</td>
            <td>${formatNumber(row.grid_import)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderDayCompareSummaryTable(rows) {
  const container = $("dayCompareTable");
  if (!rows || !rows.length) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Total kWh</th>
          <th>Source</th>
          <th>Peak kW</th>
          <th>Peak Time</th>
          <th>Samples</th>
          <th>State</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map((row) => `
          <tr>
            <td>${escapeHtml(row.label || row.date || "")}</td>
            <td>${formatNumber(row.total_kwh)}</td>
            <td>${escapeHtml(dayCompareSourceLabel(row.total_source))}</td>
            <td>${formatNumber(row.peak_kw)}</td>
            <td>${escapeHtml(formatPeakTime(row.peak_time))}</td>
            <td>${escapeHtml(String(row.samples ?? ""))}</td>
            <td>${row.partial ? "Partial" : "Complete"}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderDayCompareHighlights(payload) {
  const container = $("dayCompareHighlights");
  const rows = payload?.rows || [];
  if (!rows.length) {
    container.innerHTML = "";
    return;
  }
  const highestPeak = rows.reduce((best, row) => (!best || Number(row.peak_kw || 0) > Number(best.peak_kw || 0) ? row : best), null);
  const highestTotal = rows.reduce((best, row) => (!best || Number(row.total_kwh || 0) > Number(best.total_kwh || 0) ? row : best), null);
  const completedDays = rows.filter((row) => !row.partial).length;
  const axisMax = selectedDayCompareAxisMax();
  const actualPeak = rows.reduce((best, row) => Math.max(best, Number(row.peak_kw || 0)), 0);
  const clipped = axisMax !== null && actualPeak > axisMax;
  const metricLabel = String(payload?.metric_label || "Metric").trim();

  container.innerHTML = [
    highestPeak ? `
      <article class="day-compare-highlight peak">
        <div class="label">Peak ${escapeHtml(metricLabel)}</div>
        <div class="value">${formatNumber(highestPeak.peak_kw)} kW</div>
        <div class="hint">${escapeHtml(highestPeak.label || highestPeak.date || "")}${highestPeak.peak_time ? ` at ${escapeHtml(highestPeak.peak_time)}` : ""}</div>
      </article>
    ` : "",
    highestTotal ? `
      <article class="day-compare-highlight total">
        <div class="label">Highest Selected ${escapeHtml(metricLabel)} Total</div>
        <div class="value">${formatNumber(highestTotal.total_kwh)} kWh</div>
        <div class="hint">${escapeHtml(highestTotal.label || highestTotal.date || "")} · Highest of the currently selected comparison days · ${escapeHtml(dayCompareSourceLabel(highestTotal.total_source))}</div>
      </article>
    ` : "",
    `
      <article class="day-compare-highlight scale">
        <div class="label">Chart Scale</div>
        <div class="value">${axisMax !== null ? `${formatNumber(axisMax)} kW max` : "Auto"}</div>
        <div class="hint">${clipped ? `Some points exceed the current cap. Peak seen: ${formatNumber(actualPeak)} kW.` : `${completedDays} complete day${completedDays === 1 ? "" : "s"} in this compare set.`}</div>
      </article>
    `
  ].join("");
}

async function loadStatus() {
  const status = await fetchJson("/api/status");
  state.status = status;
  updateBootOverlayForStatus(status);
  populateSites(status);
  hydrateSetupForm(status);
  hydrateSyncControls(status);
  renderHeroStatus(status);
  renderSummary(status);
  renderSyncProgress(status);
  updateWizard(status);
  updateSignInPanel(status);
  updateDataAvailability(status);
  if (!state.sectionViewResolved) {
    setSectionView(defaultSectionViewForStatus(status), { persist: false });
    state.sectionViewResolved = true;
  }
  if (!$("anchorDate").value) {
    $("anchorDate").value = status.default_anchor_date;
  }
  if (!$("trendEnd").value) {
    $("trendEnd").value = status.default_anchor_date;
  }
  if (!$("trendStart").value) {
    $("trendStart").value = status.default_trend_start;
  }
  if (!$("dayCompareDate").value) {
    $("dayCompareDate").value = status.default_anchor_date;
  }
  if (!$("patternEnd").value) {
    $("patternEnd").value = status.default_anchor_date;
  }
  if (!$("patternStart").value) {
    $("patternStart").value = status.default_trend_start;
  }
  renderComparisonWindowNav();
  if (status.sync_in_progress && status.sync_progress?.message) {
    setStatus(status.sync_progress.message, "");
  } else if (status.message) {
    setStatus(status.message, status.auth_configured ? "" : "error");
  } else if (status.last_sync_error) {
    setStatus(status.last_sync_error, "error");
  } else if (status.auto_sync_missed) {
    setStatus(`A scheduled sync was missed at ${formatDateTime(status.auto_sync_missed_since)}. Run a manual sync to catch up.`, "warning");
  } else {
    setStatus("");
  }
  if (status.sync_in_progress || state.syncRequestActive) {
    startSyncStatusPolling();
  } else {
    stopSyncStatusPolling();
  }
  return status;
}

async function loadInsights() {
  if (!hasSelectedSite()) {
    renderInsights(null);
    return;
  }
  const params = new URLSearchParams({
    site_id: currentSiteId()
  });
  const payload = await fetchJson(`/api/insights?${params.toString()}`);
  renderInsights(payload);
}

async function loadDiagnostics() {
  if (!hasSelectedSite()) {
    state.diagnosticsPayload = null;
    renderDiagnostics(null);
    return;
  }
  const params = new URLSearchParams({
    site_id: currentSiteId()
  });
  const payload = await fetchJson(`/api/diagnostics?${params.toString()}`);
  state.diagnosticsPayload = payload;
  renderDiagnostics(payload);
}

async function loadDayCompare() {
  if (!hasSelectedSite()) {
    state.dayComparePayload = null;
    renderNoSiteState(
      "dayCompareMeta",
      "dayCompareLegend",
      "dayCompareChart",
      "dayCompareTable",
      "No Tesla site data yet. Finish sign-in and sync to compare intraday power."
    );
    renderDayCompareHighlights(null);
    return;
  }
  if (!state.dayCompareDates.length) {
    state.dayComparePayload = null;
    $("dayCompareMeta").textContent = "Pick days to compare across the same 24-hour shape.";
    renderDayCompareHighlights(null);
    renderLegend("dayCompareLegend", []);
    emptySvg($("dayCompareChart"), "Pick days or use a quick preset to compare intraday power.");
    renderDayCompareSummaryTable([]);
    return;
  }
  const params = new URLSearchParams({
    site_id: currentSiteId(),
    dates: state.dayCompareDates.join(","),
    metric: $("dayCompareMetric").value || "load_power"
  });
  const payload = await fetchJson(`/api/day-compare?${params.toString()}`);
  state.dayComparePayload = payload;
  state.dayComparePayload.shared_tooltip = true;
  applyDayCompareAxisMax(state.dayComparePayload);
  renderDayCompareSelection();
  const hasEstimatedTotals = (payload.rows || []).some((row) => row.total_source !== "energy");
  const missingText = payload.missing_dates?.length
    ? ` · Missing ${payload.missing_dates.join(", ")}`
    : "";
  $("dayCompareMeta").textContent = `${payload.site.site_name} · ${payload.metric_label} over 24 hours · Totals from ${hasEstimatedTotals ? "Tesla daily history when available, otherwise intraday estimates" : "Tesla daily history"}${missingText}`;
  renderDayCompareHighlights(payload);
  renderLegend("dayCompareLegend", payload.series);
  renderLineChart("dayCompareChart", payload);
  renderDayCompareSummaryTable(payload.rows);
}

async function reloadDataViews() {
  ensureDayCompareSelection();
  await Promise.all([
    loadDiagnostics(),
    loadDayCompare(),
    loadComparison(),
    loadPerformance(),
    loadPattern(),
    loadTrend(),
    loadInsights()
  ]);
}

function performanceRangeForScope(site, scope) {
  const end = parseDateInput(site?.data_end || state.status?.default_anchor_date);
  const startBound = parseDateInput(site?.data_start || state.status?.default_trend_start);
  if (!end || !startBound) {
    return null;
  }
  if (scope === "day") {
    return {
      start: formatDateInput(maxDate(startBound, addDays(end, -41))),
      end: formatDateInput(end),
      granularity: "day",
      description: "Daily solar vs usage over the last 6 weeks"
    };
  }
  if (scope === "week") {
    return {
      start: formatDateInput(maxDate(startBound, addDays(end, -(7 * 25)))),
      end: formatDateInput(end),
      granularity: "week",
      description: "Weekly solar vs usage over the last 26 weeks"
    };
  }
  if (scope === "month") {
    return {
      start: formatDateInput(maxDate(startBound, startOfMonth(addMonths(end, -23)))),
      end: formatDateInput(end),
      granularity: "month",
      description: "Monthly solar vs usage over the last 24 months"
    };
  }
  return {
    start: formatDateInput(maxDate(startBound, startOfYear(new Date(end.getFullYear() - 5, 0, 1)))),
    end: formatDateInput(end),
    granularity: "year",
    description: "Yearly solar vs usage over the last 6 years"
  };
}

async function loadPerformance() {
  if (!hasSelectedSite()) {
    state.performancePayload = null;
    renderNoSiteState(
      "performanceMeta",
      "performanceLegend",
      "performanceChart",
      "performanceTable",
      "No Tesla site data yet. Finish sign-in and sync to compare solar versus usage."
    );
    return;
  }
  const site = currentSite();
  const scope = currentPerformanceScope();
  const range = performanceRangeForScope(site, scope);
  if (!range) {
    state.performancePayload = null;
    renderNoSiteState(
      "performanceMeta",
      "performanceLegend",
      "performanceChart",
      "performanceTable",
      "Performance compare is waiting for site coverage data."
    );
    return;
  }
  const params = new URLSearchParams({
    site_id: currentSiteId(),
    start: range.start,
    end: range.end,
    granularity: range.granularity,
    metrics: "solar_generation,home_usage"
  });
  const payload = await fetchJson(`/api/trend?${params.toString()}`);
  state.performancePayload = payload;
  $("performanceMeta").textContent = `${payload.site.site_name} · ${range.description}`;
  renderLegend("performanceLegend", payload.series);
  renderLineChart("performanceChart", payload);
  renderTable("performanceTable", payload.rows);
}

async function loadPattern() {
  if (!hasSelectedSite()) {
    state.patternPayload = null;
    renderNoSiteState(
      "patternMeta",
      "patternLegend",
      "patternChart",
      "patternTable",
      "No Tesla site data yet. Finish sign-in and sync to inspect weekday patterns."
    );
    return;
  }
  const params = new URLSearchParams({
    site_id: currentSiteId(),
    start: $("patternStart").value,
    end: $("patternEnd").value,
    metrics: selectedPatternMetrics().join(","),
    value_mode: $("patternValueMode").value || "average"
  });
  const payload = await fetchJson(`/api/pattern?${params.toString()}`);
  state.patternPayload = payload;
  const modeLabel = payload.value_mode === "total" ? "Total kWh" : "Average kWh";
  $("patternMeta").textContent = `${payload.site.site_name} · ${payload.start_date} to ${payload.end_date} · ${modeLabel} by weekday`;
  renderLegend("patternLegend", payload.series);
  renderGroupedBarChart("patternChart", payload);
  renderTable("patternTable", payload.rows);
}

function startSyncStatusPolling() {
  if (state.syncPollTimer) {
    return;
  }
  state.syncPollTimer = window.setInterval(() => {
    loadStatus().catch((error) => {
      setStatus(error.message, "error");
      stopSyncStatusPolling();
    });
  }, 1000);
}

function stopSyncStatusPolling() {
  if (!state.syncPollTimer) {
    return;
  }
  window.clearInterval(state.syncPollTimer);
  state.syncPollTimer = null;
}

async function startTeslaLogin() {
  if (state.status?.auth_configured) {
    setSetupStatus("Tesla is already signed in on this server.", "good");
    return;
  }
  const button = $("startLoginButton");
  setButtonBusy(button, true, "Generating...");
  setSetupStatus("Generating Tesla sign-in link...");
  try {
    const payload = await fetchJson("/api/auth/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: $("teslaEmail").value.trim(),
        energy_site_id: $("energySiteId").value.trim()
      })
    });
    if (payload.already_authorized) {
      setGeneratedAuthUrl("");
      setSetupStatus("Tesla is already signed in on this server.", "good");
      await loadStatus();
      await reloadDataViews();
      return;
    }
    if (payload.authorization_url) {
      setGeneratedAuthUrl(payload.authorization_url);
      window.open(payload.authorization_url, "_blank", "noopener");
    }
    setSetupStatus("Tesla login link is ready. Step 2 can open it again, or copy it, then paste the final Tesla URL into Step 3.", "good");
    await loadStatus();
  } catch (error) {
    setSetupStatus(error.message, "error");
  } finally {
    setButtonBusy(button, false);
  }
}

function openGeneratedLoginLink() {
  if (!state.generatedAuthUrl) {
    setSetupStatus("Generate the Tesla login link first.", "error");
    return;
  }
  window.open(state.generatedAuthUrl, "_blank", "noopener");
  setSetupStatus("Tesla login opened in a new tab.", "good");
}

async function copyGeneratedLoginLink() {
  try {
    await copyText(state.generatedAuthUrl);
    setSetupStatus("Tesla login link copied.", "good");
  } catch (error) {
    setSetupStatus(error.message, "error");
  }
}

async function finishTeslaLogin() {
  const button = $("finishLoginButton");
  setButtonBusy(button, true, "Finishing...");
  setSetupStatus("Completing Tesla sign-in...");
  try {
    await fetchJson("/api/auth/finish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        authorization_response: $("authorizationResponse").value.trim()
      })
    });
    setGeneratedAuthUrl("");
    $("authorizationResponse").value = "";
    state.revealEmail = false;
    setSetupStatus("Tesla sign-in completed.", "good");
    await loadStatus();
    await reloadDataViews();
  } catch (error) {
    setSetupStatus(error.message, "error");
  } finally {
    setButtonBusy(button, false);
  }
}

async function logoutTesla(event) {
  const button = event?.currentTarget instanceof HTMLElement ? event.currentTarget : $("logoutButton");
  const otherButton = button.id === "connectedLogoutButton" ? $("logoutButton") : $("connectedLogoutButton");
  setButtonBusy(button, true, "Signing Out...");
  if (otherButton) {
    otherButton.disabled = true;
  }
  setSetupStatus("Clearing Tesla session...");
  try {
    await fetchJson("/api/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    state.revealEmail = false;
    setGeneratedAuthUrl("");
    $("authorizationResponse").value = "";
    setSetupStatus("Tesla session cleared.", "good");
    await loadStatus();
    await reloadDataViews();
  } catch (error) {
    setSetupStatus(error.message, "error");
  } finally {
    setButtonBusy(button, false);
    if (otherButton) {
      otherButton.disabled = false;
    }
  }
}

function revealEmail() {
  state.revealEmail = true;
  if (state.status) {
    updateSignInPanel(state.status);
  }
}

function hideEmail() {
  state.revealEmail = false;
  if (state.status) {
    updateSignInPanel(state.status);
  }
}

async function saveSyncSchedule() {
  const button = $("saveSyncCronButton");
  const validation = validateSyncCronInput($("syncCron").value.trim() || "off");
  if (!validation.valid) {
    setSyncCronValidation(validation.message, "error");
    setStatus(validation.message, "error");
    return;
  }
  const syncCron = validation.value;
  $("syncCron").value = syncCron;
  setSyncCronValidation("");
  setButtonBusy(button, true, "Saving...");
  setStatus("Saving auto sync schedule...");
  try {
    const payload = await fetchJson("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sync_cron: syncCron }),
      timeoutMs: 10000
    });
    const savedCron = payload.sync_cron || syncCron;
    $("syncCron").value = savedCron;
    state.status = {
      ...(state.status || {}),
      auto_sync_cron: savedCron,
      auto_sync_enabled: payload.auto_sync_enabled ?? state.status?.auto_sync_enabled ?? savedCron !== "off",
      auto_sync_description: payload.auto_sync_description || state.status?.auto_sync_description || "",
      config: {
        ...(state.status?.config || {}),
        sync_cron: savedCron
      }
    };
    renderHeroStatus(state.status);
    renderSummary(state.status);
    setStatus(`Auto sync schedule saved. ${payload.auto_sync_description || ""}`.trim(), "good");
    window.setTimeout(() => {
      loadStatus().catch(() => {
        // Keep the saved-state message if the delayed refresh fails.
      });
    }, 2000);
  } catch (error) {
    const message = error.message || "Unable to save auto sync schedule.";
    setSyncCronValidation(message, "error");
    setStatus(message, "error");
  } finally {
    setButtonBusy(button, false);
  }
}

async function runSync() {
  const button = $("syncButton");
  if (!state.status?.auth_configured) {
    const message = !state.status?.library_ready
      ? "Install requirements first: pip install -r requirements.txt"
      : state.status?.auth_login_ready
        ? "Sign in with Tesla before syncing."
        : "Enter your Tesla account email and start sign-in first.";
    setStatus(message, "error");
    return;
  }
  state.syncRequestActive = true;
  setButtonBusy(button, true, "Preparing Sync");
  setStatus("Preparing Tesla download and CSV import...");
  startSyncStatusPolling();
  try {
    await fetchJson("/api/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        site_id: currentSiteId() || null
      })
    });
    setStatus("Sync completed.", "good");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    state.syncRequestActive = false;
    await loadStatus();
    await reloadDataViews();
    if (!state.status?.sync_in_progress) {
      stopSyncStatusPolling();
    }
    if (!state.status?.sync_progress?.active) {
      setButtonBusy(button, false);
    }
  }
}

async function loadComparison() {
  if (!hasSelectedSite()) {
    state.comparisonPayload = null;
    renderNoSiteState(
      "comparisonMeta",
      "comparisonLegend",
      "comparisonChart",
      "comparisonTable",
      "No Tesla site data yet. Finish sign-in and sync to compare years."
    );
    return;
  }
  const params = new URLSearchParams({
    site_id: currentSiteId(),
    mode: $("compareMode").value,
    anchor: $("anchorDate").value,
    years: $("compareYears").value || "6"
  });
  const payload = await fetchJson(`/api/comparison?${params.toString()}`);
  state.comparisonPayload = payload;
  const filteredPayload = filterSeries(payload, selectedComparisonMetrics());
  $("comparisonMeta").textContent = payload.period_label
    ? `${payload.site.site_name} · ${payload.period_label}`
    : payload.site.site_name;
  renderComparisonWindowNav();
  renderLegend("comparisonLegend", filteredPayload.series);
  renderGroupedBarChart("comparisonChart", filteredPayload);
  renderTable("comparisonTable", payload.rows);
}

async function loadTrend() {
  if (!hasSelectedSite()) {
    state.trendPayload = null;
    renderNoSiteState(
      "trendMeta",
      "trendLegend",
      "trendChart",
      "trendTable",
      "No Tesla site data yet. Finish sign-in and sync to graph trends."
    );
    return;
  }
  const params = new URLSearchParams({
    site_id: currentSiteId(),
    start: $("trendStart").value,
    end: $("trendEnd").value,
    granularity: $("trendGranularity").value,
    metrics: selectedMetrics().join(",")
  });
  const payload = await fetchJson(`/api/trend?${params.toString()}`);
  state.trendPayload = payload;
  const chartType = $("trendChartType").value || "line";
  $("trendMeta").textContent = `${payload.site.site_name} · ${payload.start_date} to ${payload.end_date} · ${payload.granularity} · ${trendChartTypeLabel(chartType)}`;
  renderLegend("trendLegend", payload.series);
  renderTrendChart(payload, chartType);
  renderTable("trendTable", payload.rows);
}

async function safeReloadAll(options = {}) {
  const initialLoad = Boolean(options.initialLoad);
  if (initialLoad) {
    state.bootstrapping = true;
    showBootOverlay("Loading dashboard", "Checking local status and preparing your views.");
  }
  try {
    const status = await loadStatus();
    if (initialLoad) {
      if ((status.sites || []).length) {
        showBootOverlay(
          "Loading charts",
          status.sync_in_progress
            ? "Initial sync is running in the background while charts and summaries load from local data."
            : "Preparing summaries, insights, and chart views from the local cache."
        );
      }
    }
    await reloadDataViews();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    if (initialLoad) {
      state.bootstrapping = false;
      hideBootOverlay();
    }
  }
}

function applyTrendRange(range) {
  const site = currentSite();
  if (!site) {
    return;
  }
  const end = parseDateInput(site.data_end || state.status?.default_anchor_date);
  const startBound = parseDateInput(site.data_start || state.status?.default_trend_start);
  if (!end || !startBound) {
    return;
  }

  let start = startBound;
  if (range === "90d") {
    start = maxDate(startBound, addDays(end, -89));
  } else if (range === "1y") {
    start = maxDate(startBound, addDays(end, -364));
  } else if (range === "3y") {
    start = maxDate(startBound, addDays(end, -(365 * 3 - 1)));
  }

  $("trendStart").value = formatDateInput(start);
  $("trendEnd").value = formatDateInput(end);
  loadTrend().catch((error) => setStatus(error.message, "error"));
}

function pageComparisonWindow(direction) {
  const site = currentSite();
  const anchor = parseDateInput($("anchorDate").value || state.status?.default_anchor_date);
  const nav = comparisonNavConfig($("compareMode").value);
  if (!site || !anchor) {
    return;
  }
  const earliestStart = parseDateInput(site.data_start || "");
  const latestEnd = latestComparableDay(site);
  let nextAnchor = nav.shiftAnchor(anchor, direction);
  if (earliestStart && nextAnchor < earliestStart) {
    nextAnchor = earliestStart;
  }
  if (latestEnd && nextAnchor > latestEnd) {
    nextAnchor = latestEnd;
  }
  $("anchorDate").value = formatDateInput(nextAnchor);
  renderComparisonWindowNav();
  loadComparison().catch((error) => setStatus(error.message, "error"));
}

function wireEvents() {
  $("startLoginButton").addEventListener("click", startTeslaLogin);
  $("revealEmailButton").addEventListener("click", revealEmail);
  $("hideEmailButton").addEventListener("click", hideEmail);
  $("connectedLogoutButton").addEventListener("click", logoutTesla);
  $("openLoginLinkButton").addEventListener("click", openGeneratedLoginLink);
  $("copyLoginLinkButton").addEventListener("click", () => {
    copyGeneratedLoginLink().catch((error) => setSetupStatus(error.message, "error"));
  });
  $("finishLoginButton").addEventListener("click", finishTeslaLogin);
  $("logoutButton").addEventListener("click", logoutTesla);
  $("syncButton").addEventListener("click", runSync);
  $("saveSyncCronButton").addEventListener("click", saveSyncSchedule);
  $("syncCron").addEventListener("input", () => setSyncCronValidation(""));
  $("syncCron").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      saveSyncSchedule().catch((error) => setStatus(error.message, "error"));
    }
  });
  $("dayCompareAddButton").addEventListener("click", () => {
    addDayCompareDate($("dayCompareDate").value);
    loadDayCompare().catch((error) => setStatus(error.message, "error"));
  });
  $("dayCompareRefreshButton").addEventListener("click", () => loadDayCompare().catch((error) => setStatus(error.message, "error")));
  $("dayCompareDate").addEventListener("change", applyDayCompareAnchorSelection);
  $("dayCompareTodayButton").addEventListener("click", () => {
    setDayCompareAnchor(new Date());
    applyDayCompareAnchorSelection();
  });
  $("anchorTodayButton").addEventListener("click", () => {
    $("anchorDate").value = formatDateInput(new Date());
    renderComparisonWindowNav();
  });
  $("dayComparePrevButton").addEventListener("click", () => pageDayCompareWindow(-1));
  $("dayCompareNextButton").addEventListener("click", () => pageDayCompareWindow(1));
  $("dayCompareMetric").addEventListener("change", () => loadDayCompare().catch((error) => setStatus(error.message, "error")));
  $("dayCompareYMax").addEventListener("input", () => {
    savePreference(PREFERENCE_KEYS.dayCompareYMax, $("dayCompareYMax").value);
    rerenderChartsFromCache();
  });
  $("dayCompareYMaxAutoButton").addEventListener("click", () => {
    $("dayCompareYMax").value = "";
    savePreference(PREFERENCE_KEYS.dayCompareYMax, "");
    rerenderChartsFromCache();
  });
  $("comparisonPrevButton").addEventListener("click", () => pageComparisonWindow(-1));
  $("comparisonNextButton").addEventListener("click", () => pageComparisonWindow(1));
  $("compareButton").addEventListener("click", () => loadComparison().catch((error) => setStatus(error.message, "error")));
  $("patternButton").addEventListener("click", () => loadPattern().catch((error) => setStatus(error.message, "error")));
  $("trendButton").addEventListener("click", () => loadTrend().catch((error) => setStatus(error.message, "error")));
  $("trendChartType").addEventListener("change", () => loadTrend().catch((error) => setStatus(error.message, "error")));
  $("siteSelect").addEventListener("change", () => {
    renderSummary(state.status || {});
    ensureDayCompareSelection();
    loadDiagnostics().catch((error) => setStatus(error.message, "error"));
    loadDayCompare().catch((error) => setStatus(error.message, "error"));
    loadComparison().catch((error) => setStatus(error.message, "error"));
    loadPerformance().catch((error) => setStatus(error.message, "error"));
    loadPattern().catch((error) => setStatus(error.message, "error"));
    loadTrend().catch((error) => setStatus(error.message, "error"));
    loadInsights().catch((error) => setStatus(error.message, "error"));
  });
  document.addEventListener("change", (event) => {
    if (event.target.classList && event.target.classList.contains("metricCheck")) {
      loadTrend().catch((error) => setStatus(error.message, "error"));
    }
    if (event.target.classList && event.target.classList.contains("patternMetricCheck")) {
      loadPattern().catch((error) => setStatus(error.message, "error"));
    }
    if (event.target.classList && event.target.classList.contains("comparisonMetricCheck")) {
      if (state.comparisonPayload) {
        const filteredPayload = filterSeries(state.comparisonPayload, selectedComparisonMetrics());
        renderLegend("comparisonLegend", filteredPayload.series);
        renderGroupedBarChart("comparisonChart", filteredPayload);
      }
    }
    if (event.target.id === "compareMode" || event.target.id === "anchorDate") {
      renderComparisonWindowNav();
    }
  });
  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }
    const quickButton = event.target.closest(".day-quick-chip");
    if (quickButton instanceof HTMLElement) {
      applyDayCompareQuick(quickButton.dataset.dayQuick || "");
      return;
    }
    const metricButton = event.target.closest(".day-metric-pill");
    if (metricButton instanceof HTMLElement) {
      setDayCompareMetric(metricButton.dataset.metric || "load_power");
      loadDayCompare().catch((error) => setStatus(error.message, "error"));
      return;
    }
    const inspectButton = event.target.closest(".diagnostic-inspect-button");
    if (inspectButton instanceof HTMLElement) {
      inspectDiagnosticDay(inspectButton.dataset.date || "", inspectButton.dataset.metric || "solar_power");
      return;
    }
    const removeButton = event.target.closest(".day-compare-remove");
    if (removeButton instanceof HTMLElement) {
      if (state.dayComparePreset !== "same-day-years") {
        setDayComparePreset("custom");
      }
      setDayCompareDates(state.dayCompareDates.filter((date) => date !== removeButton.dataset.date));
      loadDayCompare().catch((error) => setStatus(error.message, "error"));
    }
  });
  document.querySelectorAll(".range-chip").forEach((button) => {
    button.addEventListener("click", () => applyTrendRange(button.dataset.range || ""));
  });
  document.querySelectorAll(".scope-chip").forEach((button) => {
    button.addEventListener("click", () => {
      setPerformanceScope(button.dataset.scope || "month");
      loadPerformance().catch((error) => setStatus(error.message, "error"));
    });
  });
  document.querySelectorAll(".section-tab").forEach((button) => {
    button.addEventListener("click", () => setSectionView(button.dataset.sectionView || DEFAULT_SECTION_VIEW));
  });
  document.querySelectorAll(".chart-tab").forEach((button) => {
    button.addEventListener("click", () => {
      setSectionView("charts");
      setChartView(button.dataset.chartView || "performance");
    });
  });
  window.addEventListener("resize", () => {
    if (state.resizeTimer) {
      window.clearTimeout(state.resizeTimer);
    }
    state.resizeTimer = window.setTimeout(() => {
      state.resizeTimer = null;
      rerenderChartsFromCache();
    }, 120);
  });
}

buildTrendMetricPills();
buildComparisonMetricPills();
buildPatternMetricPills();
buildDayCompareMetricPills();
applyStaticButtonIcons();
$("dayCompareYMax").value = loadPreference(PREFERENCE_KEYS.dayCompareYMax, "");
setPerformanceScope(state.performanceScope);
const savedSectionView = loadPreference(PREFERENCE_KEYS.sectionView, "");
if (VALID_SECTION_VIEWS.has(savedSectionView)) {
  state.sectionViewResolved = true;
  setSectionView(savedSectionView, { persist: false });
} else {
  setSectionView(DEFAULT_SECTION_VIEW, { persist: false });
}
setChartView(loadPreference(PREFERENCE_KEYS.chartView, state.chartView), { persist: false });
wireEvents();
safeReloadAll({ initialLoad: true });
