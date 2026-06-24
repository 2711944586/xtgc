const DATA_URL = "assets/data/flightresilience-data.json";
const SVG_NS = "http://www.w3.org/2000/svg";

const STRATEGY_LABELS = {
  baseline: "基准",
  uniform_buffer: "统一缓冲",
  hub_priority: "枢纽优先",
  dynamic_combo: "动态组合",
};

const SCENARIO_LABELS = {
  normal: "常态运行",
  peak: "需求高峰",
  weather: "天气冲击",
  hub_failure: "枢纽容量下降",
  hub_capacity_drop: "枢纽容量下降",
};

const STRATEGY_COLORS = {
  baseline: "#6c7b80",
  uniform_buffer: "#326d92",
  hub_priority: "#c96f2d",
  dynamic_combo: "#147c7c",
};

const state = {
  data: null,
  airport: "DEN",
  scenario: "weather",
  strategy: "dynamic_combo",
  shockAirport: "DEN",
  lambda: 0.9,
  nodePositions: [],
  prefersReducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
};

const $ = (id) => document.getElementById(id);

const fmt = {
  int: (value) => Number(value ?? 0).toLocaleString("zh-CN"),
  pct: (value, digits = 1) => `${(Number(value ?? 0) * 100).toFixed(digits)}%`,
  num: (value, digits = 1) => Number(value ?? 0).toFixed(digits),
  short: (value) => {
    const n = Number(value ?? 0);
    if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1)}k`;
    return n.toFixed(n >= 10 ? 0 : 1);
  },
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function mixHex(a, b, t) {
  const parse = (hex) => hex.replace("#", "").match(/.{1,2}/g).map((v) => parseInt(v, 16));
  const [ar, ag, ab] = parse(a);
  const [br, bg, bb] = parse(b);
  const channel = (start, end) => Math.round(start + (end - start) * clamp(t, 0, 1)).toString(16).padStart(2, "0");
  return `#${channel(ar, br)}${channel(ag, bg)}${channel(ab, bb)}`;
}

function byId(id) {
  return state.data.airportNodes.find((node) => node.airport === id || node.id === id);
}

function svgNode(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value !== undefined && value !== null) node.setAttribute(key, String(value));
  });
  if (text !== undefined) node.textContent = text;
  return node;
}

function clearChart(id, height = 300) {
  const host = $(id);
  if (!host) return null;
  host.innerHTML = "";
  const svg = svgNode("svg", {
    viewBox: `0 0 900 ${height}`,
    preserveAspectRatio: "none",
    role: "img",
  });
  host.appendChild(svg);
  return svg;
}

function emptyState(id, message) {
  const host = $(id);
  if (!host) return;
  host.innerHTML = `<div class="empty">${message}</div>`;
}

function makeScale(values, rangeMin, rangeMax, pad = 0.06) {
  const nums = values.map(Number).filter(Number.isFinite);
  let min = Math.min(...nums);
  let max = Math.max(...nums);
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    min = 0;
    max = 1;
  }
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const span = max - min;
  min -= span * pad;
  max += span * pad;
  return {
    min,
    max,
    map(value) {
      const t = (Number(value) - min) / (max - min);
      return rangeMin + t * (rangeMax - rangeMin);
    },
  };
}

function addGrid(svg, plot, rows = 4) {
  for (let i = 0; i <= rows; i += 1) {
    const y = plot.y + (plot.h * i) / rows;
    svg.appendChild(svgNode("line", {
      x1: plot.x,
      y1: y,
      x2: plot.x + plot.w,
      y2: y,
      stroke: "#dfe8e4",
      "stroke-width": i === rows ? 1.2 : 0.8,
    }));
  }
}

function addText(svg, text, x, y, attrs = {}) {
  svg.appendChild(svgNode("text", {
    x,
    y,
    fill: attrs.fill || "#405156",
    "font-size": attrs.size || 12,
    "font-weight": attrs.weight || 500,
    "text-anchor": attrs.anchor || "start",
    "dominant-baseline": attrs.baseline || "auto",
  }, text));
}

function tooltip() {
  let tip = document.querySelector(".tooltip");
  if (!tip) {
    tip = document.createElement("div");
    tip.className = "tooltip";
    tip.hidden = true;
    document.body.appendChild(tip);
  }
  return tip;
}

function showTip(event, html) {
  const tip = tooltip();
  tip.innerHTML = html;
  tip.hidden = false;
  const x = clamp(event.clientX + 14, 8, window.innerWidth - 280);
  const y = clamp(event.clientY + 14, 8, window.innerHeight - 120);
  tip.style.left = `${x}px`;
  tip.style.top = `${y}px`;
}

function hideTip() {
  const tip = tooltip();
  tip.hidden = true;
}

function bindTip(node, htmlFactory) {
  node.addEventListener("mouseenter", (event) => showTip(event, htmlFactory(event)));
  node.addEventListener("mousemove", (event) => showTip(event, htmlFactory(event)));
  node.addEventListener("mouseleave", hideTip);
}

function populateSelect(select, values, selected, labels = {}) {
  if (!select) return;
  select.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = labels[value] || value;
    if (value === selected) option.selected = true;
    select.appendChild(option);
  });
}

function setText(id, text) {
  const node = $(id);
  if (node) node.textContent = text;
}

function updateHeaderKpis() {
  const { kpi, decision, modelMetrics } = state.data;
  const best = [...modelMetrics].sort((a, b) => b.test_roc_auc - a.test_roc_auc)[0];
  setText("date-range", `${kpi.date_min} 至 ${kpi.date_max}`);
  setText("flight-count", fmt.int(kpi.flights));
  setText("airport-count", fmt.int(kpi.airport_count));
  setText("main-recommendation", STRATEGY_LABELS[decision.recommended_strategy] || decision.recommended_strategy);
  setText("kpi-delay-rate", fmt.pct(kpi.delay_rate));
  setText("kpi-avg-delay", `${fmt.num(kpi.avg_arr_delay, 1)} min`);
  setText("kpi-cancel-rate", fmt.pct(kpi.cancel_rate));
  setText("kpi-auc", fmt.num(best?.test_roc_auc, 3));
}

function updateControls() {
  const airports = state.data.predictionOptions.airports;
  const scenarios = [...new Set(state.data.strategyMetrics.map((row) => row.scenario))];
  const strategies = [...new Set(state.data.strategyMetrics.map((row) => row.strategy))];

  populateSelect($("airport-select"), airports, state.airport);
  populateSelect($("origin-input"), airports, state.airport);
  populateSelect($("dest-input"), airports, "DFW");
  populateSelect($("shock-airport-select"), airports, state.shockAirport);
  populateSelect($("scenario-select"), scenarios, state.scenario, SCENARIO_LABELS);
  populateSelect($("strategy-select"), strategies, state.strategy, STRATEGY_LABELS);
}

function drawDailyChart() {
  const data = state.data.dashboardDaily;
  if (!data?.length) return emptyState("daily-chart", "未找到每日运行数据");

  const svg = clearChart("daily-chart", 360);
  const plot = { x: 58, y: 34, w: 790, h: 258 };
  addGrid(svg, plot, 4);

  const x = (i) => plot.x + (plot.w * i) / Math.max(1, data.length - 1);
  const flightScale = makeScale(data.map((d) => d.flights), plot.y + plot.h, plot.y, 0.02);
  const delayScale = makeScale(data.map((d) => d.delay_rate), plot.y + plot.h, plot.y, 0.12);
  const barW = Math.max(2, plot.w / data.length - 1);

  data.forEach((d, i) => {
    const barH = plot.y + plot.h - flightScale.map(d.flights);
    const bar = svgNode("rect", {
      x: x(i) - barW / 2,
      y: flightScale.map(d.flights),
      width: barW,
      height: barH,
      fill: "rgba(50,109,146,0.18)",
      rx: 1,
    });
    bindTip(bar, () => `${String(d.FlightDate).slice(0, 10)}<br>航班量 ${fmt.int(d.flights)}<br>延误率 ${fmt.pct(d.delay_rate)}`);
    svg.appendChild(bar);
  });

  const path = data.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(2)} ${delayScale.map(d.delay_rate).toFixed(2)}`).join(" ");
  svg.appendChild(svgNode("path", {
    d: path,
    fill: "none",
    stroke: "#c96f2d",
    "stroke-width": 3,
    "stroke-linejoin": "round",
  }));

  data.filter((_, i) => i % 10 === 0).forEach((d, i) => {
    const realIndex = i * 10;
    addText(svg, String(d.FlightDate).slice(5, 10), x(realIndex), 320, { size: 11, anchor: "middle" });
  });
  addText(svg, "柱：航班量", plot.x, 22, { size: 12, fill: "#326d92", weight: 800 });
  addText(svg, "线：延误率", plot.x + 105, 22, { size: 12, fill: "#c96f2d", weight: 800 });
  addText(svg, `${fmt.pct(Math.max(...data.map((d) => d.delay_rate)))}`, 858, plot.y + 8, { size: 11, anchor: "end" });
  addText(svg, "0", 858, plot.y + plot.h + 4, { size: 11, anchor: "end" });
}

function drawHeatmap() {
  const rows = state.data.dashboardHeatmap;
  if (!rows?.length) return emptyState("heatmap-chart", "未找到热力图数据");

  const svg = clearChart("heatmap-chart", 360);
  const plot = { x: 72, y: 42, w: 760, h: 242 };
  const hours = [...new Set(rows.map((d) => Number(d.crs_dep_hour)))].sort((a, b) => a - b);
  const days = [1, 2, 3, 4, 5, 6, 7];
  const dayLabel = { 1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日" };
  const maxRate = Math.max(...rows.map((d) => d.delay_rate));
  const cellW = plot.w / hours.length;
  const cellH = plot.h / days.length;
  const lookup = new Map(rows.map((d) => [`${d.DayOfWeek}-${d.crs_dep_hour}`, d]));

  days.forEach((day, r) => {
    addText(svg, dayLabel[day], 48, plot.y + r * cellH + cellH / 2 + 4, { size: 12, anchor: "end" });
    hours.forEach((hour, c) => {
      const item = lookup.get(`${day}-${hour}`);
      const rate = item?.delay_rate ?? 0;
      const t = clamp(rate / maxRate, 0, 1);
      const fill = mixHex("#edf2ef", "#c96f2d", t);
      const rect = svgNode("rect", {
        x: plot.x + c * cellW + 1,
        y: plot.y + r * cellH + 1,
        width: Math.max(4, cellW - 2),
        height: Math.max(4, cellH - 2),
        fill,
        rx: 3,
      });
      bindTip(rect, () => `${dayLabel[day]} ${hour}:00<br>延误率 ${fmt.pct(rate)}<br>航班 ${fmt.int(item?.flights || 0)}`);
      svg.appendChild(rect);
    });
  });

  hours.forEach((hour, idx) => {
    if (idx % 3 === 0) addText(svg, `${hour}`, plot.x + idx * cellW + cellW / 2, 315, { size: 11, anchor: "middle" });
  });
  addText(svg, "计划起飞小时", plot.x + plot.w / 2, 342, { size: 12, anchor: "middle" });
  addText(svg, "浅色低风险，橙色高风险", plot.x, 24, { size: 12, fill: "#c96f2d", weight: 800 });
}

function drawAirportBars() {
  const rows = [...state.data.airportNodes].sort((a, b) => b.criticality - a.criticality);
  const svg = clearChart("airport-bars", 330);
  const plot = { x: 94, y: 28, w: 720, h: 248 };
  const max = Math.max(...rows.map((d) => d.criticality));
  const barH = plot.h / rows.length - 5;

  rows.forEach((row, i) => {
    const y = plot.y + i * (barH + 5);
    const w = (row.criticality / max) * plot.w;
    const active = row.airport === state.airport;
    const rect = svgNode("rect", {
      x: plot.x,
      y,
      width: w,
      height: barH,
      fill: active ? "#c96f2d" : "#147c7c",
      opacity: active ? 0.96 : 0.74,
      rx: 4,
      tabindex: 0,
      role: "button",
      "aria-label": `选择 ${row.airport}`,
    });
    rect.addEventListener("click", () => selectAirport(row.airport));
    rect.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectAirport(row.airport);
    });
    bindTip(rect, () => `${row.airport}<br>关键性 ${fmt.num(row.criticality, 3)}<br>延误率 ${fmt.pct(row.delay_rate)}<br>平均风险 ${fmt.pct(row.avg_risk)}`);
    svg.appendChild(rect);
    addText(svg, row.airport, plot.x - 12, y + barH / 2 + 4, { anchor: "end", weight: active ? 900 : 700, fill: active ? "#c96f2d" : "#405156" });
    addText(svg, fmt.num(row.criticality, 2), plot.x + w + 8, y + barH / 2 + 4, { size: 11 });
  });
  addText(svg, "点击条形可切换机场画像和网络高亮", plot.x, 314, { size: 12, fill: "#6c7b80" });
}

function drawModelBars() {
  const rows = [...state.data.modelMetrics].sort((a, b) => b.test_roc_auc - a.test_roc_auc);
  if (!rows.length) return emptyState("model-bars", "未找到模型指标");
  const svg = clearChart("model-bars", 270);
  const plot = { x: 96, y: 34, w: 720, h: 172 };
  const metrics = ["test_roc_auc", "test_pr_auc", "test_f1"];
  const labels = { test_roc_auc: "ROC-AUC", test_pr_auc: "PR-AUC", test_f1: "F1" };
  const colors = ["#147c7c", "#326d92", "#c96f2d"];
  addGrid(svg, plot, 4);
  rows.forEach((row, i) => {
    const groupY = plot.y + i * 54;
    addText(svg, row.model.replace("_", " "), 22, groupY + 26, { size: 12, weight: 800 });
    metrics.forEach((metric, j) => {
      const width = row[metric] * plot.w;
      const rect = svgNode("rect", {
        x: plot.x,
        y: groupY + j * 14,
        width,
        height: 10,
        fill: colors[j],
        rx: 2,
      });
      bindTip(rect, () => `${row.model}<br>${labels[metric]} ${fmt.num(row[metric], 3)}`);
      svg.appendChild(rect);
      addText(svg, fmt.num(row[metric], 3), plot.x + width + 7, groupY + j * 14 + 9, { size: 10 });
    });
  });
  metrics.forEach((metric, j) => addText(svg, labels[metric], 120 + j * 100, 246, { size: 11, fill: colors[j], weight: 800 }));
}

function drawShapBars() {
  const rows = [...state.data.shapSummary].slice(0, 8);
  if (!rows.length) return emptyState("shap-bars", "未找到 SHAP 数据");
  const svg = clearChart("shap-bars", 270);
  const plot = { x: 230, y: 28, w: 580, h: 198 };
  const max = Math.max(...rows.map((d) => d.mean_abs_shap));
  const barH = plot.h / rows.length - 6;
  rows.forEach((row, i) => {
    const y = plot.y + i * (barH + 6);
    const label = row.source_feature.replaceAll("_", " ");
    addText(svg, label, plot.x - 12, y + barH / 2 + 4, { size: 10.5, anchor: "end" });
    const w = (row.mean_abs_shap / max) * plot.w;
    svg.appendChild(svgNode("rect", { x: plot.x, y, width: w, height: barH, fill: "#326d92", rx: 3, opacity: 0.86 }));
    addText(svg, fmt.num(row.mean_abs_shap, 3), plot.x + w + 6, y + barH / 2 + 4, { size: 10 });
  });
  addText(svg, "mean |SHAP|，数值越大表示全局贡献越高", plot.x, 252, { size: 11, fill: "#6c7b80" });
}

function updateRiskEstimator() {
  const origin = byId($("origin-input")?.value) || byId(state.airport);
  const dest = byId($("dest-input")?.value) || byId("DFW");
  const hour = Number($("hour-input")?.value || 17);
  const distance = Number($("distance-input")?.value || state.data.predictionOptions.distance_median);
  const congestion = Number($("congestion-input")?.value || 42) / 100;
  const base = Number(state.data.kpi.delay_rate);
  const hourEffect = 0.05 * Math.sin(((hour - 14) / 24) * Math.PI * 2) + (hour >= 16 && hour <= 21 ? 0.065 : 0);
  const distanceEffect = clamp((distance - 800) / 2400, -0.12, 0.22) * 0.08;
  const airportEffect = ((origin?.avg_risk || base) + (dest?.avg_risk || base)) * 0.34;
  const congestionEffect = congestion * 0.22;
  const risk = clamp(base * 0.42 + airportEffect + hourEffect + distanceEffect + congestionEffect - 0.04, 0.03, 0.82);

  setText("hour-output", `${String(hour).padStart(2, "0")}:00`);
  setText("distance-output", `${fmt.int(distance)} mi`);
  setText("congestion-output", `${Math.round(congestion * 100)}%`);
  setText("risk-probability", fmt.pct(risk, 1));
  const meter = $("risk-meter");
  if (meter) meter.style.width = `${Math.round(risk * 100)}%`;
  const level = risk > 0.35 ? "高风险" : risk > 0.22 ? "中等风险" : "较低风险";
  setText(
    "risk-interpretation",
    `${level}：${origin?.airport || "--"} → ${dest?.airport || "--"}，${hour}:00，拥堵 ${Math.round(congestion * 100)}%。该结果用于解释计划阶段风险输入，不替代实时调度系统。`,
  );
}

function drawNetwork() {
  const canvas = $("network-canvas");
  if (!canvas || !state.data) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = canvas.clientWidth || 920;
  const cssHeight = Math.max(380, Math.round(cssWidth * 0.6));
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);
  canvas.style.height = `${cssHeight}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssWidth, cssHeight);

  const nodes = state.data.networkNodes;
  const edges = [...state.data.networkEdges].sort((a, b) => b.flights - a.flights).slice(0, 80);
  const center = { x: cssWidth / 2, y: cssHeight / 2 };
  const radius = Math.min(cssWidth, cssHeight) * 0.39;
  const maxFlights = Math.max(...edges.map((e) => e.flights));
  const maxCritical = Math.max(...nodes.map((n) => n.criticality));
  state.nodePositions = nodes.map((node, i) => {
    const angle = -Math.PI / 2 + (i / nodes.length) * Math.PI * 2;
    const radial = radius * (0.86 + (1 - node.criticality / maxCritical) * 0.18);
    return {
      ...node,
      x: center.x + Math.cos(angle) * radial,
      y: center.y + Math.sin(angle) * radial,
      r: 8 + (node.criticality / maxCritical) * 13,
    };
  });
  const pos = new Map(state.nodePositions.map((n) => [n.id, n]));

  ctx.fillStyle = "#fbfcfb";
  ctx.fillRect(0, 0, cssWidth, cssHeight);
  ctx.strokeStyle = "rgba(22,58,70,0.06)";
  ctx.lineWidth = 1;
  for (let x = 24; x < cssWidth; x += 36) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, cssHeight);
    ctx.stroke();
  }
  for (let y = 24; y < cssHeight; y += 36) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(cssWidth, y);
    ctx.stroke();
  }

  edges.forEach((edge) => {
    const a = pos.get(edge.source);
    const b = pos.get(edge.target);
    if (!a || !b) return;
    const active = edge.source === state.airport || edge.target === state.airport;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    const cx = center.x + (a.x + b.x - center.x * 2) * 0.08;
    const cy = center.y + (a.y + b.y - center.y * 2) * 0.08;
    ctx.quadraticCurveTo(cx, cy, b.x, b.y);
    ctx.strokeStyle = active ? "rgba(201,111,45,0.42)" : "rgba(50,109,146,0.16)";
    ctx.lineWidth = 0.7 + (edge.flights / maxFlights) * (active ? 3.6 : 2.2);
    ctx.stroke();
  });

  state.nodePositions.forEach((node) => {
    const active = node.id === state.airport;
    ctx.beginPath();
    ctx.arc(node.x, node.y, node.r + (active ? 4 : 0), 0, Math.PI * 2);
    ctx.fillStyle = active ? "rgba(201,111,45,0.18)" : "rgba(20,124,124,0.12)";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
    ctx.fillStyle = active ? "#c96f2d" : "#147c7c";
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = active ? "#172326" : "#405156";
    ctx.font = `${active ? 800 : 700} 12px Segoe UI, Microsoft YaHei, sans-serif`;
    ctx.textAlign = "center";
    ctx.fillText(node.id, node.x, node.y + node.r + 17);
  });
}

function updateAirportProfile() {
  const node = byId(state.airport);
  if (!node) return;
  setText("selected-airport-title", `${node.airport} 综合画像`);
  const profile = $("airport-profile");
  if (profile) {
    profile.innerHTML = [
      ["出港航班", fmt.int(node.departures)],
      ["到港航班", fmt.int(node.arrivals)],
      ["历史延误率", fmt.pct(node.delay_rate)],
      ["平均风险", fmt.pct(node.avg_risk)],
      ["介数中心性", fmt.num(node.betweenness, 4)],
      ["综合关键性", fmt.num(node.criticality, 3)],
    ].map(([label, value]) => `<div class="profile-stat"><span>${label}</span><strong>${value}</strong></div>`).join("");
  }
  drawCriticalityBars();
}

function drawCriticalityBars() {
  const rows = [...state.data.airportNodes].sort((a, b) => b.criticality - a.criticality).slice(0, 8);
  const svg = clearChart("criticality-bars", 270);
  const plot = { x: 78, y: 26, w: 730, h: 190 };
  const max = Math.max(...rows.map((d) => d.criticality));
  const barH = plot.h / rows.length - 6;
  rows.forEach((row, i) => {
    const y = plot.y + i * (barH + 6);
    const active = row.airport === state.airport;
    const w = (row.criticality / max) * plot.w;
    svg.appendChild(svgNode("rect", {
      x: plot.x,
      y,
      width: w,
      height: barH,
      fill: active ? "#c96f2d" : "#326d92",
      rx: 3,
    }));
    addText(svg, row.airport, plot.x - 10, y + barH / 2 + 4, { anchor: "end", weight: active ? 900 : 700 });
    addText(svg, fmt.num(row.criticality, 2), plot.x + w + 6, y + barH / 2 + 4, { size: 10 });
  });
  addText(svg, "关键性 = 流量 + 介数中心性 + 预测风险 + 历史延误率", plot.x, 248, { size: 11, fill: "#6c7b80" });
}

function selectAirport(airport) {
  state.airport = airport;
  const airportSelect = $("airport-select");
  if (airportSelect) airportSelect.value = airport;
  const origin = $("origin-input");
  if (origin) origin.value = airport;
  updateAirportProfile();
  drawAirportBars();
  drawNetwork();
  updateRiskEstimator();
}

function scenarioRows() {
  return state.data.scenarioResults.filter((row) => row.scenario === state.scenario && row.shock_airport === state.shockAirport);
}

function metricRows() {
  let rows = state.data.strategyMetrics.filter((row) => row.scenario === state.scenario && row.shock_airport === state.shockAirport);
  if (!rows.length) rows = state.data.strategyMetrics.filter((row) => row.scenario === state.scenario);
  return rows;
}

function drawRecoveryChart() {
  const rows = scenarioRows();
  if (!rows.length) return emptyState("recovery-chart", "当前情景没有仿真轨迹");
  const svg = clearChart("recovery-chart", 360);
  const plot = { x: 58, y: 34, w: 780, h: 250 };
  addGrid(svg, plot, 5);
  const strategies = [...new Set(rows.map((row) => row.strategy))];
  const hours = [...new Set(rows.map((row) => Number(row.hour)))].sort((a, b) => a - b);
  const xScale = makeScale(hours, plot.x, plot.x + plot.w, 0);
  const yScale = makeScale(rows.map((row) => row.total_delay), plot.y + plot.h, plot.y, 0.08);

  strategies.forEach((strategy) => {
    const series = rows.filter((row) => row.strategy === strategy).sort((a, b) => a.hour - b.hour);
    const path = series.map((d, i) => `${i === 0 ? "M" : "L"} ${xScale.map(d.hour).toFixed(2)} ${yScale.map(d.total_delay).toFixed(2)}`).join(" ");
    svg.appendChild(svgNode("path", {
      d: path,
      fill: "none",
      stroke: STRATEGY_COLORS[strategy] || "#405156",
      "stroke-width": strategy === state.strategy ? 4 : 2.2,
      opacity: strategy === state.strategy ? 1 : 0.52,
      "stroke-linejoin": "round",
      "stroke-linecap": "round",
    }));
    const last = series[series.length - 1];
    addText(svg, STRATEGY_LABELS[strategy] || strategy, xScale.map(last.hour) + 8, yScale.map(last.total_delay) + 4, {
      size: 11,
      fill: STRATEGY_COLORS[strategy] || "#405156",
      weight: strategy === state.strategy ? 900 : 700,
    });
  });
  hours.filter((h) => h % 4 === 0).forEach((hour) => addText(svg, `${hour}h`, xScale.map(hour), 318, { size: 11, anchor: "middle" }));
  addText(svg, "累计延误状态（分钟，越低越好）", plot.x, 22, { fill: "#c96f2d", weight: 800 });
  addText(svg, `情景：${SCENARIO_LABELS[state.scenario] || state.scenario}，冲击机场：${state.shockAirport}`, plot.x, 342, { size: 11, fill: "#6c7b80" });
}

function updateStrategySummary() {
  const rows = metricRows().sort((a, b) => a.strategy_cost - b.strategy_cost);
  setText("scenario-caption", `${SCENARIO_LABELS[state.scenario] || state.scenario} / ${state.shockAirport}`);
  const host = $("strategy-summary");
  if (!host) return;
  host.innerHTML = rows.map((row) => {
    const active = row.strategy === state.strategy;
    return `
      <div class="strategy-card${active ? " active" : ""}">
        <span>${STRATEGY_LABELS[row.strategy] || row.strategy}</span>
        <strong>${fmt.short(row.cumulative_delay)} min / ${fmt.num(row.recovery_time, 1)}h</strong>
        <small>最低性能 ${fmt.pct(row.min_performance)} · 成本 ${fmt.short(row.strategy_cost)}</small>
      </div>
    `;
  }).join("");
}

function drawScenarioBars() {
  const rows = metricRows();
  if (!rows.length) return emptyState("scenario-bars", "当前情景缺少策略指标");
  const svg = clearChart("scenario-bars", 270);
  const plot = { x: 126, y: 28, w: 680, h: 182 };
  const maxDelay = Math.max(...rows.map((d) => d.cumulative_delay));
  const maxCost = Math.max(...rows.map((d) => d.strategy_cost || 1));
  rows.forEach((row, i) => {
    const y = plot.y + i * 44;
    const active = row.strategy === state.strategy;
    addText(svg, STRATEGY_LABELS[row.strategy] || row.strategy, plot.x - 12, y + 17, { anchor: "end", weight: active ? 900 : 700, fill: active ? "#c96f2d" : "#405156" });
    svg.appendChild(svgNode("rect", {
      x: plot.x,
      y,
      width: (row.cumulative_delay / maxDelay) * plot.w,
      height: 13,
      fill: active ? "#c96f2d" : "#326d92",
      rx: 3,
    }));
    svg.appendChild(svgNode("rect", {
      x: plot.x,
      y: y + 18,
      width: ((row.strategy_cost || 0) / maxCost) * plot.w,
      height: 8,
      fill: "#147c7c",
      opacity: 0.72,
      rx: 2,
    }));
    addText(svg, `${fmt.short(row.cumulative_delay)} / cost ${fmt.short(row.strategy_cost)}`, plot.x + plot.w + 8, y + 13, { size: 10 });
  });
  addText(svg, "上：累计延误  下：相对成本", plot.x, 250, { size: 11, fill: "#6c7b80" });
}

function drawLambdaChart() {
  const rows = state.data.weightSensitivity;
  if (!rows?.length) return emptyState("lambda-chart", "缺少敏感性数据");
  const svg = clearChart("lambda-chart", 270);
  const plot = { x: 62, y: 32, w: 760, h: 164 };
  addGrid(svg, plot, 4);
  const xScale = makeScale(rows.map((d) => d.lambda_ahp), plot.x, plot.x + plot.w, 0.05);
  const yScale = makeScale(rows.map((d) => d.top_score), plot.y + plot.h, plot.y, 0.08);
  const path = rows.map((d, i) => `${i === 0 ? "M" : "L"} ${xScale.map(d.lambda_ahp)} ${yScale.map(d.top_score)}`).join(" ");
  svg.appendChild(svgNode("path", { d: path, fill: "none", stroke: "#147c7c", "stroke-width": 3, "stroke-linejoin": "round" }));
  rows.forEach((row) => {
    const active = Number(row.lambda_ahp).toFixed(1) === Number(state.lambda).toFixed(1);
    const dot = svgNode("circle", {
      cx: xScale.map(row.lambda_ahp),
      cy: yScale.map(row.top_score),
      r: active ? 7 : 4,
      fill: row.recommended_strategy === "dynamic_combo" ? "#c96f2d" : "#326d92",
      stroke: "#ffffff",
      "stroke-width": 2,
    });
    bindTip(dot, () => `λ=${row.lambda_ahp}<br>推荐：${STRATEGY_LABELS[row.recommended_strategy] || row.recommended_strategy}<br>top score ${fmt.num(row.top_score, 3)}<br>dynamic rank ${row.dynamic_combo_rank}`);
    svg.appendChild(dot);
  });
  rows.forEach((row) => addText(svg, String(row.lambda_ahp), xScale.map(row.lambda_ahp), 226, { size: 10, anchor: "middle" }));
  addText(svg, "λ：主观 AHP 恢复偏好占比", plot.x + plot.w / 2, 252, { size: 11, anchor: "middle" });
}

function updateLambda() {
  const output = $("lambda-output");
  if (output) output.textContent = Number(state.lambda).toFixed(2);
  const selected = state.data.weightSensitivity.find((row) => Number(row.lambda_ahp).toFixed(1) === Number(state.lambda).toFixed(1));
  const callout = $("lambda-callout");
  if (callout && selected) {
    const label = STRATEGY_LABELS[selected.recommended_strategy] || selected.recommended_strategy;
    const boundary = selected.recommended_strategy === "dynamic_combo"
      ? "恢复/韧性偏好足够高，动态组合成为第一。"
      : "成本和保守性占优，基准策略在该权重下反超。";
    callout.innerHTML = `<strong>${label}</strong> 在 λ=${Number(state.lambda).toFixed(1)} 时排名第一。${boundary}`;
  }
  drawLambdaChart();
}

function drawTopsisChart() {
  const rows = [...state.data.strategyRankings].sort((a, b) => b.topsis_score - a.topsis_score);
  const svg = clearChart("topsis-chart", 270);
  const plot = { x: 126, y: 36, w: 650, h: 166 };
  const max = Math.max(...rows.map((d) => d.topsis_score));
  rows.forEach((row, i) => {
    const y = plot.y + i * 42;
    const w = (row.topsis_score / max) * plot.w;
    const first = row.overall_rank === 1;
    svg.appendChild(svgNode("rect", {
      x: plot.x,
      y,
      width: w,
      height: 22,
      fill: first ? "#c96f2d" : "#147c7c",
      rx: 4,
    }));
    addText(svg, STRATEGY_LABELS[row.strategy] || row.strategy, plot.x - 12, y + 16, { anchor: "end", weight: first ? 900 : 700 });
    addText(svg, fmt.num(row.topsis_score, 3), plot.x + w + 8, y + 16, { size: 11 });
  });
  addText(svg, "主偏好 TOPSIS 接近度，越高越优", plot.x, 248, { size: 11, fill: "#6c7b80" });
}

function updateRiskTable() {
  const tbody = $("risk-table")?.querySelector("tbody");
  if (!tbody) return;
  const rows = [...state.data.riskDecision].sort((a, b) => {
    const ar = a.risk_rank ?? a.rank ?? a.expected_loss;
    const br = b.risk_rank ?? b.rank ?? b.expected_loss;
    return ar - br;
  });
  tbody.innerHTML = rows.map((row, i) => {
    const strategy = row.strategy || row.Strategy;
    const loss = row.expected_loss ?? row.ExpectedLoss ?? row.expected_regret ?? row.value;
    return `<tr><td>${STRATEGY_LABELS[strategy] || strategy}</td><td>${fmt.num(loss, 2)}</td><td>${row.risk_rank || row.rank || i + 1}</td></tr>`;
  }).join("");
}

function renderDecision() {
  drawTopsisChart();
  updateRiskTable();
  updateLambda();
}

function renderSimulation() {
  drawRecoveryChart();
  updateStrategySummary();
  drawScenarioBars();
}

function renderAll() {
  if (!state.data) return;
  drawDailyChart();
  drawHeatmap();
  drawAirportBars();
  drawModelBars();
  drawShapBars();
  updateRiskEstimator();
  drawNetwork();
  updateAirportProfile();
  renderSimulation();
  renderDecision();
}

function bindControls() {
  $("airport-select")?.addEventListener("change", (event) => selectAirport(event.target.value));
  $("origin-input")?.addEventListener("change", updateRiskEstimator);
  $("dest-input")?.addEventListener("change", updateRiskEstimator);
  ["hour-input", "distance-input", "congestion-input"].forEach((id) => $(id)?.addEventListener("input", updateRiskEstimator));
  $("scenario-select")?.addEventListener("change", (event) => {
    state.scenario = event.target.value;
    renderSimulation();
  });
  $("strategy-select")?.addEventListener("change", (event) => {
    state.strategy = event.target.value;
    renderSimulation();
  });
  $("shock-airport-select")?.addEventListener("change", (event) => {
    state.shockAirport = event.target.value;
    renderSimulation();
  });
  $("lambda-input")?.addEventListener("input", (event) => {
    state.lambda = Number(event.target.value);
    updateLambda();
  });
  $("network-canvas")?.addEventListener("click", (event) => {
    const canvas = event.currentTarget;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const nearest = state.nodePositions
      .map((node) => ({ node, distance: Math.hypot(node.x - x, node.y - y) }))
      .sort((a, b) => a.distance - b.distance)[0];
    if (nearest && nearest.distance < nearest.node.r + 18) selectAirport(nearest.node.id);
  });
  window.addEventListener("resize", debounce(renderAll, 180));
}

function debounce(fn, delay) {
  let timer = 0;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), delay);
  };
}

function bindNavigation() {
  const links = [...document.querySelectorAll(".nav-links a")];
  const sections = links.map((link) => document.querySelector(link.getAttribute("href"))).filter(Boolean);
  if (!("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver((entries) => {
    const active = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!active) return;
    links.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${active.target.id}`));
  }, { rootMargin: "-25% 0px -60% 0px", threshold: [0.2, 0.4, 0.6] });
  sections.forEach((section) => observer.observe(section));
}

function renderError(error) {
  console.error(error);
  [
    "daily-chart",
    "heatmap-chart",
    "airport-bars",
    "model-bars",
    "shap-bars",
    "criticality-bars",
    "recovery-chart",
    "scenario-bars",
    "lambda-chart",
    "topsis-chart",
  ].forEach((id) => emptyState(id, "静态数据加载失败。请通过本地静态服务器或 GitHub Pages 访问 web/ 目录。"));
  setText("date-range", "数据未加载");
  setText("flight-count", "--");
  setText("airport-count", "--");
  setText("main-recommendation", "--");
}

async function init() {
  bindNavigation();
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`Failed to load ${DATA_URL}: ${response.status}`);
    state.data = await response.json();
    state.airport = byId("DEN") ? "DEN" : state.data.predictionOptions.airports[0];
    state.shockAirport = state.airport;
    const scenarios = new Set(state.data.strategyMetrics.map((row) => row.scenario));
    if (!scenarios.has(state.scenario)) state.scenario = [...scenarios][0];
    updateControls();
    updateHeaderKpis();
    bindControls();
    renderAll();
  } catch (error) {
    renderError(error);
  }
}

init();
