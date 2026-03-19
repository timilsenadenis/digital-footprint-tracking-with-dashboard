/**
 * charts.js — Plotly chart generators for the dashboard
 * Each function takes data from the Flask API and renders a chart
 */

const PLOTLY_CFG = { displayModeBar: false, responsive: true };

const PLOTLY_LAYOUT = (overrides = {}) => ({
  margin:         { t: 10, r: 10, b: 40, l: 50 },
  paper_bgcolor:  "rgba(0,0,0,0)",
  plot_bgcolor:   "rgba(0,0,0,0)",
  font: {
    family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    size: 12, color: "#374151"
  },
  showlegend: false,
  ...overrides,
});

// ─── Format helpers ────────────────────────────────────────────────────
export function fmtTime(sec) {
  if (!sec || sec < 0) return "0m";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h ? `${h}h ${m}m` : `${m}m`;
}

export function fmtNumber(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + "k";
  return String(n);
}

// ─── Daily activity bar + line chart ──────────────────────────────────
export function renderDailyChart(elementId, rows) {
  if (!rows?.length) return;
  Plotly.newPlot(elementId, [
    {
      type: "bar",
      name: "Visits",
      x: rows.map(r => r.day),
      y: rows.map(r => r.total_visits || 0),
      marker: { color: "#4f46e5", opacity: 0.85 },
    },
    {
      type: "scatter",
      name: "Minutes online",
      x: rows.map(r => r.day),
      y: rows.map(r => Math.round((r.total_time_sec || 0) / 60)),
      mode: "lines+markers",
      yaxis: "y2",
      line: { color: "#10b981", width: 2 },
      marker: { size: 5, color: "#10b981" },
    },
  ],
  PLOTLY_LAYOUT({
    yaxis:  { title: "Visits",   gridcolor: "#f3f4f6", zeroline: false },
    yaxis2: { title: "Minutes",  overlaying: "y", side: "right",
              gridcolor: "#f3f4f6", zeroline: false },
    showlegend: true,
    legend: { x: 0, y: 1.15, orientation: "h" },
    bargap: 0.3,
  }),
  PLOTLY_CFG);
}

// ─── Category donut chart ──────────────────────────────────────────────
export function renderCategoryChart(elementId, rows) {
  if (!rows?.length) return;
  Plotly.newPlot(elementId, [{
    type: "pie",
    labels: rows.map(r => r.name || "Other"),
    values: rows.map(r => r.visits),
    marker: { colors: rows.map(r => r.color_hex || "#888") },
    hole: 0.42,
    textinfo: "label+percent",
    textfont: { size: 11 },
    hovertemplate: "<b>%{label}</b><br>%{value} visits<br>%{percent}<extra></extra>",
  }],
  PLOTLY_LAYOUT({
    showlegend: true,
    legend: { orientation: "v", x: 1.05, y: 0.5 },
    margin: { t: 10, r: 130, b: 10, l: 10 },
  }),
  PLOTLY_CFG);
}

// ─── Top domains horizontal bar ────────────────────────────────────────
export function renderTopSitesChart(elementId, rows) {
  if (!rows?.length) return;
  const top = rows.slice(0, 10);
  Plotly.newPlot(elementId, [{
    type: "bar",
    orientation: "h",
    y: top.map(r => r.domain).reverse(),
    x: top.map(r => r.visits).reverse(),
    marker: { color: "#4f46e5", opacity: 0.8 },
    hovertemplate: "<b>%{y}</b><br>%{x} visits<extra></extra>",
  }],
  PLOTLY_LAYOUT({
    margin: { t: 10, r: 20, b: 30, l: 130 },
    xaxis: { gridcolor: "#f3f4f6", zeroline: false },
  }),
  PLOTLY_CFG);
}

// ─── Search keyword frequency bar ─────────────────────────────────────
export function renderKeywordsChart(elementId, rows) {
  if (!rows?.length) return;
  const top = rows.slice(0, 20);
  Plotly.newPlot(elementId, [{
    type: "bar",
    orientation: "h",
    y: top.map(r => r.keyword).reverse(),
    x: top.map(r => r.frequency).reverse(),
    marker: { color: "#10b981", opacity: 0.85 },
    hovertemplate: "<b>%{y}</b><br>%{x} searches<extra></extra>",
  }],
  PLOTLY_LAYOUT({
    margin: { t: 10, r: 20, b: 30, l: 110 },
    xaxis: { gridcolor: "#f3f4f6", zeroline: false },
  }),
  PLOTLY_CFG);
}

// ─── Search engine pie ─────────────────────────────────────────────────
export function renderEnginesChart(elementId, rows) {
  if (!rows?.length) return;
  Plotly.newPlot(elementId, [{
    type: "pie",
    labels: rows.map(r => r.engine),
    values: rows.map(r => r.total_searches),
    hole: 0.38,
    textinfo: "label+percent",
    marker: {
      colors: ["#4f46e5","#10b981","#f59e0b","#ef4444","#8b5cf6"]
    },
  }],
  PLOTLY_LAYOUT({ margin: { t: 10, r: 10, b: 10, l: 10 } }),
  PLOTLY_CFG);
}

// ─── Social platform time bar ──────────────────────────────────────────
export function renderSocialTimeChart(elementId, rows) {
  if (!rows?.length) return;
  Plotly.newPlot(elementId, [{
    type: "bar",
    x: rows.map(r => r.platform),
    y: rows.map(r => Math.round((r.total_sec || 0) / 60)),
    marker: { color: "#4f46e5", opacity: 0.85 },
    hovertemplate: "<b>%{x}</b><br>%{y} minutes<extra></extra>",
  }],
  PLOTLY_LAYOUT({
    yaxis: { title: "Minutes", gridcolor: "#f3f4f6", zeroline: false },
  }),
  PLOTLY_CFG);
}

// ─── Social actions grouped bar ────────────────────────────────────────
export function renderSocialActionsChart(elementId, rows) {
  if (!rows?.length) return;
  Plotly.newPlot(elementId, [
    {
      type: "bar", name: "Posts",
      x: rows.map(r => r.platform),
      y: rows.map(r => r.posts   || 0),
      marker: { color: "#4f46e5" },
    },
    {
      type: "bar", name: "Likes",
      x: rows.map(r => r.platform),
      y: rows.map(r => r.likes   || 0),
      marker: { color: "#10b981" },
    },
    {
      type: "bar", name: "Scrolls",
      x: rows.map(r => r.platform),
      y: rows.map(r => r.scrolls || 0),
      marker: { color: "#f59e0b" },
    },
    {
      type: "bar", name: "Comments",
      x: rows.map(r => r.platform),
      y: rows.map(r => r.comments || 0),
      marker: { color: "#ef4444" },
    },
  ],
  PLOTLY_LAYOUT({
    barmode: "group", showlegend: true,
    legend: { x: 0, y: 1.15, orientation: "h" },
    yaxis: { gridcolor: "#f3f4f6", zeroline: false },
  }),
  PLOTLY_CFG);
}

// ─── Activity heatmap ──────────────────────────────────────────────────
export function renderHeatmapChart(elementId, rows) {
  if (!rows?.length) return;
  const DAYS  = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
  const HOURS = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  const z     = Array.from({ length: 7 }, () => new Array(24).fill(0));

  rows.forEach(r => {
    const d = parseInt(r.day_of_week), h = parseInt(r.hour_of_day);
    if (d >= 0 && d < 7 && h >= 0 && h < 24) {
      z[d][h] = r.visit_count || 0;
    }
  });

  Plotly.newPlot(elementId, [{
    type: "heatmap",
    z, x: HOURS, y: DAYS,
    colorscale: [[0,"#eef2ff"],[0.5,"#6366f1"],[1,"#312e81"]],
    showscale: true,
    hovertemplate: "<b>%{y} %{x}</b><br>%{z} visits<extra></extra>",
  }],
  PLOTLY_LAYOUT({
    margin: { t: 10, r: 80, b: 60, l: 50 },
    xaxis: { tickangle: -45 },
  }),
  PLOTLY_CFG);
}

// ─── App usage horizontal bar ──────────────────────────────────────────
export function renderAppUsageChart(elementId, rows) {
  if (!rows?.length) return;
  const top = rows.slice(0, 10);
  Plotly.newPlot(elementId, [{
    type: "bar",
    orientation: "h",
    y: top.map(r => r.app_name).reverse(),
    x: top.map(r => Math.round((r.total_sec || 0) / 60)).reverse(),
    marker: { color: "#8b5cf6", opacity: 0.85 },
    hovertemplate: "<b>%{y}</b><br>%{x} minutes<extra></extra>",
  }],
  PLOTLY_LAYOUT({
    margin: { t: 10, r: 20, b: 30, l: 120 },
    xaxis: { title: "Minutes", gridcolor: "#f3f4f6", zeroline: false },
  }),
  PLOTLY_CFG);
}
