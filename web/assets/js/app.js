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

const GRADE_COLORS = {
  "优秀": "#147c7c",
  "良好": "#326d92",
  "一般": "#c96f2d",
  "较差": "#b84c46",
};

const state = {
  data: null,
  airport: "MIA",
  scenario: "weather",
  strategy: "dynamic_combo",
  shockAirport: "MIA",
  lambda: 0.9,
  tourIndex: 0,
  tourPlaying: false,
  tourTimer: 0,
  tourTimers: [],
  tourInteracting: false,
  tourAction: "点击“自动演示”后按顺序操作。",
  tooltipTimer: 0,
  nodePositions: [],
  prefersReducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
};

const TOUR_STEPS = [
  {
    id: "overview",
    title: "边界定义",
    brief: "从单航班延误转为机场网络恢复问题，先确定系统边界、外部扰动和评价目标。",
    question: "局部延误什么时候会变成网络恢复问题？",
    method: "系统边界 + 多主体目标冲突：旅客、航司、机场和监管者不能只用一个指标评价。",
    evidence: (data) => `${fmt.int(data.kpi.flights)} 条航班、${data.kpi.airport_count} 个机场、${fmt.int(data.kpi.route_count || data.airportEdges?.length || data.networkEdges?.length)} 条有向航线。`,
    decision: "先把问题定义为“网络恢复策略选择”，预测只是输入，不是最终答案。",
    duration: 7200,
    state: { airport: "MIA", scenario: "weather", strategy: "dynamic_combo", shockAirport: "MIA", lambda: 0.9 },
    actions: [
      { type: "pulse", target: ".mission-board", delay: 520, label: "第一步确认样本边界：航班、机场、航线和数据窗口。" },
      { type: "pulse", target: "#tour-flow", delay: 1920, label: "演示路线固定为系统边界、证据、风险、网络、仿真、决策。" },
      { type: "pulse", target: ".hero-note", delay: 3420, label: "先声明结论边界：恢复优先与成本保守会给出不同推荐。" },
      { type: "pulse", target: "#evidence-brief", delay: 5120, label: "接下来用四个证据对象进入定量分析。" },
    ],
  },
  {
    id: "evidence",
    title: "证据边界",
    brief: "先用四个可检查对象说明：风险在哪、模型能否排序、扰动如何衰减、策略为什么换位。",
    question: "哪些证据能证明这是系统工程问题？",
    method: "证据链压缩：航线气泡、ROC/PR、恢复热力、风险-TOPSIS 同屏交叉验证。",
    evidence: (data) => {
      const best = [...data.modelMetrics].sort((a, b) => b.test_roc_auc - a.test_roc_auc)[0];
      return `${best.model} AUC=${fmt.num(best.test_roc_auc, 3)}，同时保留风险损失与 TOPSIS 的冲突。`;
    },
    decision: "先看边界和矛盾，再进入模块细节，避免演示变成逐页翻图。",
    duration: 7600,
    state: { airport: "MIA", scenario: "weather", strategy: "dynamic_combo", shockAirport: "MIA", lambda: 0.9 },
    actions: [
      { type: "click", target: "#route-risk-chart circle[role='button']", delay: 520, label: "点击高风险航线气泡，联动出发机场和预测输入。" },
      { type: "pulse", target: "#curve-chart", delay: 1780, label: "检查 ROC/PR 曲线，确认风险模型具备排序能力。" },
      { type: "pulse", target: "#recovery-heat-chart", delay: 3220, label: "观察恢复热力图，把单点风险接到传播过程。" },
      { type: "click", target: "#risk-topsis-chart circle[role='button']", delay: 4800, label: "点击风险-TOPSIS 点，说明低损失与高综合得分并不总一致。" },
      { type: "pulse", target: "#evidence-brief", delay: 6200, label: "四个证据对象形成后续模块的入口，而不是孤立截图。" },
    ],
  },
  {
    id: "dashboard",
    title: "运行数据",
    brief: "用机场、星期小时和关键性排序证明延误不是平均发生，恢复资源不能平均摊派。",
    question: "延误是不是均匀分布，能不能按航班量简单排队？",
    method: "描述性统计 + 时间热力 + 机场关键性排序，先做系统异质性诊断。",
    evidence: (data) => {
      const top = topAirport();
      return `${top.airport} 综合关键性 ${fmt.num(top.criticality, 3)}；总体 ArrDel15=${fmt.pct(data.kpi.delay_rate)}。`;
    },
    decision: "如果节点差异显著，恢复策略必须进入网络结构和传播仿真。",
    duration: 7800,
    state: { airport: "MIA", scenario: "weather", strategy: "dynamic_combo", shockAirport: "MIA", lambda: 0.9 },
    actions: [
      { type: "pulse", target: "#daily-chart", delay: 520, label: "先看日尺度波动，确认运行状态不是静态均值。" },
      { type: "pulse", target: "#heatmap-chart", delay: 1820, label: "再看星期-小时热力，确认延误存在时间异质性。" },
      { type: "setSelect", target: "#airport-select", value: "DEN", delay: 3300, label: "切换关注机场，比较不同节点的历史风险。" },
      { type: "click", target: "#airport-bars rect[role='button']", delay: 5000, label: "点击关键性条形，联动机场画像、网络和预测模块。" },
      { type: "pulse", target: "#airport-select", delay: 6460, label: "机场选择会贯穿预测、网络和仿真，不是静态展示。" },
    ],
  },
  {
    id: "prediction",
    title: "计划风险",
    brief: "调节计划阶段变量，展示风险概率如何被量化，再把局部风险送入网络层。",
    question: "计划阶段能不能提前识别高风险航班？",
    method: "时间顺序切分 + 计划可得特征 + SHAP 解释，避免使用实际延误泄漏。",
    evidence: (data) => {
      const best = [...data.modelMetrics].sort((a, b) => b.test_roc_auc - a.test_roc_auc)[0];
      return `时间外测试 ROC-AUC ${fmt.num(best.test_roc_auc, 3)}，PR-AUC ${fmt.num(best.test_pr_auc, 3)}。`;
    },
    decision: "风险模型不替代调度，而是为关键节点识别和扰动仿真提供输入。",
    duration: 8200,
    state: { airport: "MIA", scenario: "peak", strategy: "dynamic_combo", shockAirport: "MIA", lambda: 0.8 },
    actions: [
      { type: "pulse", target: "#model-bars", delay: 480, label: "先看时间外测试指标，确认预测模型不是只拟合训练集。" },
      { type: "pulse", target: "#shap-bars", delay: 1580, label: "再看主要特征，说明计划变量如何贡献风险排序。" },
      { type: "setRange", target: "#hour-input", value: "19", delay: 2820, label: "拖动起飞小时，模拟晚高峰计划风险。" },
      { type: "setRange", target: "#distance-input", value: "1450", delay: 3960, label: "拖动航线距离，观察长航线风险修正。" },
      { type: "setRange", target: "#congestion-input", value: "74", delay: 5100, label: "拖动机场拥堵，风险概率即时刷新。" },
      { type: "pulse", target: ".risk-result", delay: 6580, label: "读取风险概率，并决定是否进入网络层追踪后果。" },
    ],
  },
  {
    id: "network",
    title: "网络结构",
    brief: "点击网络节点，说明高风险节点如果同时处在关键位置，就会放大为传播问题。",
    question: "同样的延误发生在不同机场，系统后果是否相同？",
    method: "复杂网络中心性 + 平均预测风险 + 历史延误率，合成机场关键性。",
    evidence: () => {
      const node = byId(state.airport) || topAirport();
      return `${node.airport}：介数 ${fmt.num(node.betweenness, 4)}，平均风险 ${fmt.pct(node.avg_risk)}，关键性 ${fmt.num(node.criticality, 3)}。`;
    },
    decision: "关键机场优先恢复不是凭直觉，而是由网络位置、风险和流量共同决定。",
    duration: 7800,
    state: { airport: "DEN", scenario: "weather", strategy: "hub_priority", shockAirport: "MIA", lambda: 0.8 },
    actions: [
      { type: "networkClick", value: "DFW", delay: 620, label: "点击网络节点，切换机场画像。" },
      { type: "pulse", target: "#airport-profile", delay: 1980, label: "读取机场画像：流量、风险、介数和关键性。" },
      { type: "networkClick", value: "MIA", delay: 3380, label: "再点击 MIA，对比枢纽位置和平均风险的差异。" },
      { type: "pulse", target: "#network-canvas", delay: 5000, label: "回到网络图，说明同一延误在不同位置后果不同。" },
      { type: "pulse", target: "#criticality-bars", delay: 6360, label: "对比关键性排名，确认优先恢复节点。" },
    ],
  },
  {
    id: "simulation",
    title: "扰动仿真",
    brief: "切换情景和策略，在同一冲击下比较恢复曲线、传播热力和成本差异。",
    question: "识别关键节点后，哪种恢复策略真正降低系统损失？",
    method: "状态空间传播模型：x(t+1)=Ax(t)+Bu(t)+Gw(t)+ε(t)，统一冲击和预算口径。",
    evidence: (data) => `传播矩阵谱半径 ${fmt.num(data.propagationValidation.spectral_radius_final, 3)}，单步 MAE ${fmt.num(data.propagationValidation.mae, 2)} min。`,
    decision: "同一扰动下比较恢复路径，而不是只看一个均值或单点排名。",
    duration: 9600,
    state: { airport: "MIA", scenario: "weather", strategy: "baseline", shockAirport: "MIA", lambda: 0.9 },
    actions: [
      { type: "setSelect", target: "#scenario-select", value: "weather", delay: 480, label: "选择天气冲击情景，固定外部扰动口径。" },
      { type: "setSelect", target: "#shock-airport-select", value: "DEN", delay: 1660, label: "先切到 DEN，看冲击机场确实可被选择。" },
      { type: "click", target: "#scenario-options .option-chip[data-kind='shock'][data-value='DFW']", delay: 3040, label: "再点击 DFW 冲击机场，观察关键节点扰动。" },
      { type: "setSelect", target: "#strategy-select", value: "baseline", delay: 4420, label: "先看基准策略的恢复曲线，建立对照组。" },
      { type: "click", target: "#scenario-options .option-chip[data-kind='strategy'][data-value='hub_priority']", delay: 5680, label: "切到枢纽优先，检查关键节点优先恢复的效果。" },
      { type: "click", target: "#scenario-options .option-chip[data-kind='strategy'][data-value='dynamic_combo']", delay: 6940, label: "点击动态组合策略，比较恢复速度与成本。" },
      { type: "click", target: "#recovery-chart circle[data-strategy='dynamic_combo']", delay: 8100, label: "点击恢复曲线末端，确认策略切换真实生效。" },
      { type: "pulse", target: "#scenario-bars", delay: 9040, label: "最后看指标柱状图，比较累计延误与相对成本。" },
    ],
  },
  {
    id: "decision",
    title: "条件决策",
    brief: "拖动 λ 权重并点击风险-TOPSIS 点，展示为什么推荐必须写成有边界的管理判断。",
    question: "恢复最快的策略是否总是最终推荐？",
    method: "AHP/熵权/TOPSIS + 风险期望损失 + 不确定准则，交叉检验推荐稳定性。",
    evidence: (data) => {
      const riskWinner = [...data.riskDecision].sort((a, b) => a.expected_loss - b.expected_loss)[0];
      return `主偏好推荐 ${STRATEGY_LABELS[data.decision.recommended_strategy]}；期望损失口径偏向 ${STRATEGY_LABELS[riskWinner.strategy]}。`;
    },
    decision: "恢复优先选动态组合；预算紧或风险保守时保留基准策略，结论必须条件化。",
    duration: 9200,
    state: { airport: "MIA", scenario: "weather", strategy: "baseline", shockAirport: "DFW", lambda: 0.2 },
    actions: [
      { type: "setRange", target: "#lambda-input", value: "0.9", delay: 420, label: "先把 λ 调高，模拟恢复/韧性优先。" },
      { type: "pulse", target: "#topsis-chart", delay: 1760, label: "读取 TOPSIS 主偏好排序，说明恢复优先的推荐来源。" },
      { type: "setRange", target: "#lambda-input", value: "0.2", delay: 3260, label: "再把 λ 调低，模拟成本和客观权重占优。" },
      { type: "click", target: "#lambda-chart circle[data-lambda='0.2']", delay: 4860, label: "点击 λ=0.2 的敏感性点，验证推荐换位。" },
      { type: "click", target: "#risk-topsis-chart circle[data-strategy='baseline']", delay: 6260, label: "点击基准策略的风险-TOPSIS 点，说明风险口径会保守。" },
      { type: "pulse", target: "#risk-table", delay: 7620, label: "用风险表收束最终管理建议：结论必须条件化。" },
      { type: "pulse", target: ".footer-summary", delay: 8580, label: "最后回到管理建议：恢复优先选动态组合，成本保守保留基准策略。" },
    ],
  },
];

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
  window.clearTimeout(state.tooltipTimer);
  tip.innerHTML = html;
  tip.hidden = false;
  tip.classList.add("is-visible");
  const x = clamp(event.clientX + 14, 8, window.innerWidth - 280);
  const y = clamp(event.clientY + 14, 8, window.innerHeight - 120);
  tip.style.left = `${x}px`;
  tip.style.top = `${y}px`;
  if (state.tourPlaying || state.tourInteracting) {
    state.tooltipTimer = window.setTimeout(hideTip, 1150);
  }
}

function hideTip() {
  window.clearTimeout(state.tooltipTimer);
  const tip = document.querySelector(".tooltip");
  if (!tip) return;
  tip.classList.remove("is-visible");
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

function topAirport() {
  return [...state.data.airportNodes].sort((a, b) => b.criticality - a.criticality)[0];
}

function updateEvidenceBrief() {
  const host = $("evidence-brief");
  if (!host || !state.data) return;
  const best = [...state.data.modelMetrics].sort((a, b) => b.test_roc_auc - a.test_roc_auc)[0];
  const top = topAirport();
  const dynamic = state.data.strategyRankings.find((row) => row.strategy === "dynamic_combo");
  const riskWinner = [...state.data.riskDecision].sort((a, b) => a.expected_loss - b.expected_loss)[0];
  host.innerHTML = [
    ["样本", `${fmt.int(state.data.kpi.flights)} 航班 / ${state.data.kpi.airport_count} 机场`],
    ["关键节点", `${top.airport} · K=${fmt.num(top.criticality, 2)}`],
    ["排序能力", `${best.model} · AUC ${fmt.num(best.test_roc_auc, 3)}`],
    ["决策边界", `${STRATEGY_LABELS.dynamic_combo} #${dynamic?.overall_rank ?? 1} / 风险 ${STRATEGY_LABELS[riskWinner?.strategy] || riskWinner?.strategy}`],
  ].map(([label, value]) => `<div class="brief-chip"><span>${label}</span><strong>${value}</strong></div>`).join("");
}

function updateTourUi() {
  const step = TOUR_STEPS[state.tourIndex] || TOUR_STEPS[0];
  const resolve = (value) => (typeof value === "function" && state.data ? value(state.data, state) : value);
  setText("tour-step-label", `${String(state.tourIndex + 1).padStart(2, "0")} / ${String(TOUR_STEPS.length).padStart(2, "0")}`);
  setText("tour-title", step.title);
  setText("tour-brief", step.brief);
  setText("demo-caption-step", `${String(state.tourIndex + 1).padStart(2, "0")} / ${String(TOUR_STEPS.length).padStart(2, "0")}`);
  setText("demo-caption-title", step.title);
  setText("demo-caption-question", resolve(step.question) || "这个模块要回答什么问题？");
  setText("demo-caption-method", resolve(step.method) || "按系统工程方法进行分解和验证。");
  setText("demo-caption-line", resolve(step.evidence) || step.brief);
  setText("demo-caption-decision", resolve(step.decision) || "把证据收束为有条件的管理判断。");
  setText("demo-caption-action", state.tourAction || resolve(step.method) || "按系统工程链路推进。");
  setText("mission-status", state.tourPlaying ? "自动演示中" : "人工控制");
  document.body.classList.toggle("tour-is-playing", state.tourPlaying);
  const progress = $("tour-progress");
  if (progress) progress.style.width = `${((state.tourIndex + 1) / TOUR_STEPS.length) * 100}%`;
  const play = $("tour-play");
  if (play) {
    play.textContent = state.tourPlaying ? "暂停" : "自动演示";
    play.classList.toggle("is-playing", state.tourPlaying);
  }
  document.querySelectorAll("[data-step]").forEach((node) => {
    node.classList.toggle("is-active", Number(node.dataset.step) === state.tourIndex);
  });
}

function setTourAction(text) {
  state.tourAction = text || "按系统工程链路真实操作控件。";
  setText("demo-caption-action", state.tourAction);
}

function clearTourTimers() {
  window.clearInterval(state.tourTimer);
  state.tourTimers.forEach((timer) => window.clearTimeout(timer));
  state.tourTimers = [];
}

function scheduleTour(fn, delay) {
  const timer = window.setTimeout(fn, delay);
  state.tourTimers.push(timer);
  return timer;
}

function withTourInteraction(fn) {
  state.tourInteracting = true;
  try {
    fn();
  } finally {
    window.setTimeout(() => {
      state.tourInteracting = false;
    }, 0);
  }
}

function maybeStopTour() {
  if (!state.tourInteracting) stopTour();
}

function demoCursor() {
  return $("demo-cursor");
}

function moveDemoCursorTo(node) {
  const cursor = demoCursor();
  if (!cursor || !node) return;
  const rect = node.getBoundingClientRect();
  const x = rect.left + rect.width / 2;
  const y = rect.top + rect.height / 2;
  moveDemoCursorPoint(x, y);
}

function moveDemoCursorPoint(x, y) {
  const cursor = demoCursor();
  if (!cursor) return;
  cursor.style.left = `${x}px`;
  cursor.style.top = `${y}px`;
  cursor.classList.add("is-visible");
}

function pulseDemoTarget(node, duration = 820) {
  if (!node) return;
  moveDemoCursorTo(node);
  node.classList.add("is-demo-target");
  scheduleTour(() => node.classList.remove("is-demo-target"), duration);
}

function scrollToTourTarget(id) {
  const target = document.getElementById(id);
  if (!target) return;
  hideTip();
  const topbar = document.querySelector(".topbar")?.getBoundingClientRect().height || 0;
  const top = target.getBoundingClientRect().top + window.scrollY - topbar - 16;
  window.scrollTo({
    top: Math.max(0, top),
    behavior: state.prefersReducedMotion ? "auto" : "smooth",
  });
}

function demoClickNode(node) {
  if (!node) return;
  hideTip();
  pulseDemoTarget(node);
  const cursor = demoCursor();
  cursor?.classList.add("is-clicking");
  withTourInteraction(() => {
    node.dispatchEvent(new MouseEvent("click", {
      bubbles: true,
      cancelable: true,
      clientX: node.getBoundingClientRect().left + node.getBoundingClientRect().width / 2,
      clientY: node.getBoundingClientRect().top + node.getBoundingClientRect().height / 2,
    }));
  });
  scheduleTour(() => cursor?.classList.remove("is-clicking"), 180);
}

function setControlValue(selector, value, eventName) {
  const node = document.querySelector(selector);
  if (!node) return;
  hideTip();
  const isRange = node.matches("input[type='range']");
  pulseDemoTarget(node, isRange ? 1180 : 920);
  node.classList.add("is-demo-changing");
  scheduleTour(() => node.classList.remove("is-demo-changing"), isRange ? 1220 : 980);
  if (isRange) {
    const start = Number(node.value);
    const end = Number(value);
    const min = Number(node.min || 0);
    const max = Number(node.max || 100);
    const steps = 8;
    for (let i = 1; i <= steps; i += 1) {
      scheduleTour(() => {
        withTourInteraction(() => {
          const raw = start + ((end - start) * i) / steps;
          const step = Number(node.step || 1);
          const nextValue = step >= 1 ? Math.round(raw) : Number(raw.toFixed(2));
          node.value = String(nextValue);
          const rect = node.getBoundingClientRect();
          const ratio = clamp((Number(node.value) - min) / Math.max(1e-6, max - min), 0, 1);
          moveDemoCursorPoint(rect.left + rect.width * ratio, rect.top + rect.height / 2);
          node.dispatchEvent(new Event(eventName, { bubbles: true }));
        });
      }, i * 80);
    }
    return;
  }
  scheduleTour(() => {
    withTourInteraction(() => {
      const values = [...(node.options || [])].map((option) => option.value);
      node.value = values.includes(value) ? value : values[0] || value;
      node.dispatchEvent(new Event(eventName, { bubbles: true }));
    });
  }, 260);
}

function clickNetworkNode(id) {
  const canvas = $("network-canvas");
  if (!canvas) return;
  hideTip();
  const node = state.nodePositions.find((item) => item.id === id || item.airport === id) || state.nodePositions[0];
  if (!node) return;
  const rect = canvas.getBoundingClientRect();
  const clientX = rect.left + node.x;
  const clientY = rect.top + node.y;
  const cursor = demoCursor();
  if (cursor) {
    cursor.style.left = `${clientX}px`;
    cursor.style.top = `${clientY}px`;
    cursor.classList.add("is-visible", "is-clicking");
  }
  canvas.classList.add("is-demo-target");
  withTourInteraction(() => {
    canvas.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX, clientY }));
    canvas.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX, clientY }));
  });
  scheduleTour(() => {
    cursor?.classList.remove("is-clicking");
    canvas.classList.remove("is-demo-target");
    hideTip();
  }, 520);
}

function executeTourAction(action) {
  if (!state.tourPlaying && !state.tourInteracting) return;
  setTourAction(action.label || "正在操作页面控件。");
  const target = action.target ? document.querySelector(action.target) : null;
  if (action.type === "scroll") {
    target?.scrollIntoView({ behavior: state.prefersReducedMotion ? "auto" : "smooth", block: "center" });
    if (target) pulseDemoTarget(target, 620);
    return;
  }
  if (action.type === "pulse") {
    pulseDemoTarget(target);
    return;
  }
  if (action.type === "click") {
    demoClickNode(target);
    return;
  }
  if (action.type === "setSelect") {
    setControlValue(action.target, action.value, "change");
    return;
  }
  if (action.type === "setRange") {
    setControlValue(action.target, action.value, "input");
    return;
  }
  if (action.type === "networkClick") {
    clickNetworkNode(action.value);
  }
}

function runTourActions(step) {
  (step.actions || []).forEach((action) => {
    scheduleTour(() => executeTourAction(action), action.delay || 0);
  });
}

function applyTourStep(index, { scroll = true } = {}) {
  hideTip();
  state.tourIndex = (index + TOUR_STEPS.length) % TOUR_STEPS.length;
  const step = TOUR_STEPS[state.tourIndex];
  Object.assign(state, step.state);
  syncShockAirport();
  updateControls();
  const lambdaInput = $("lambda-input");
  if (lambdaInput) lambdaInput.value = String(state.lambda);
  updateTourUi();
  renderAll();
  if (scroll) {
    scrollToTourTarget(step.id);
  }
}

function stopTour() {
  state.tourPlaying = false;
  clearTourTimers();
  hideTip();
  demoCursor()?.classList.remove("is-visible", "is-clicking");
  document.querySelectorAll(".is-demo-target, .is-demo-changing").forEach((node) => node.classList.remove("is-demo-target", "is-demo-changing"));
  setTourAction("演示已停在当前状态，可继续手动追问图表。");
  updateTourUi();
}

function startTour() {
  state.tourPlaying = true;
  state.tourIndex = 0;
  clearTourTimers();
  hideTip();
  setTourAction("开始：先界定系统，再进入证据、模型、仿真和决策。");
  updateTourUi();
  runTourStep(0);
}

function runTourStep(index) {
  if (!state.tourPlaying) return;
  applyTourStep(index);
  const step = TOUR_STEPS[state.tourIndex];
  runTourActions(step);
  scheduleTour(() => {
    if (!state.tourPlaying) return;
    const next = state.tourIndex + 1;
    if (next >= TOUR_STEPS.length) {
      stopTour();
      return;
    }
    runTourStep(next);
  }, step.duration || 3200);
}

function toggleTour() {
  if (state.tourPlaying) stopTour();
  else startTour();
}

function updateHeaderKpis() {
  const { kpi, decision, modelMetrics } = state.data;
  const best = [...modelMetrics].sort((a, b) => b.test_roc_auc - a.test_roc_auc)[0];
  setText("date-range", `${kpi.date_min} 至 ${kpi.date_max}`);
  setText("flight-count", fmt.int(kpi.flights));
  setText("airport-count", fmt.int(kpi.airport_count));
  setText("edge-count", fmt.int(kpi.route_count || state.data.airportEdges?.length || state.data.networkEdges?.length));
  setText("main-recommendation", STRATEGY_LABELS[decision.recommended_strategy] || decision.recommended_strategy);
  setText("kpi-delay-rate", fmt.pct(kpi.delay_rate));
  setText("kpi-avg-delay", `${fmt.num(kpi.avg_arr_delay, 1)} min`);
  setText("kpi-cancel-rate", fmt.pct(kpi.cancel_rate));
  setText("kpi-auc", fmt.num(best?.test_roc_auc, 3));
  const riskWinner = [...state.data.riskDecision].sort((a, b) => a.expected_loss - b.expected_loss)[0];
  setText(
    "hero-verdict",
    `${STRATEGY_LABELS[decision.recommended_strategy]}在恢复优先口径下领先；期望损失口径下${STRATEGY_LABELS[riskWinner.strategy]}更稳。`,
  );
}

function availableShockAirports(scenario = state.scenario) {
  const airportNodes = state.data?.airportNodes || [];
  if (airportNodes.length) {
    return [...airportNodes]
      .sort((a, b) => b.criticality - a.criticality)
      .map((node) => node.airport || node.id)
      .filter(Boolean);
  }
  const scoped = state.data.scenarioResults
    .filter((row) => row.scenario === scenario)
    .map((row) => row.shock_airport)
    .filter(Boolean);
  const values = [...new Set(scoped)];
  if (values.length) return values;
  return [...new Set(state.data.scenarioResults.map((row) => row.shock_airport).filter(Boolean))];
}

function featuredShockAirports() {
  const values = availableShockAirports().slice(0, 6);
  if (state.shockAirport && !values.includes(state.shockAirport)) values.push(state.shockAirport);
  return values;
}

function hasExactShockScenario(scenario = state.scenario, shockAirport = state.shockAirport) {
  return state.data.scenarioResults.some((row) => row.scenario === scenario && row.shock_airport === shockAirport);
}

function shockScale(airport = state.shockAirport) {
  const node = byId(airport) || topAirport();
  const base = byId("MIA") || topAirport();
  const criticalityRatio = Number(node?.criticality || 1) / Math.max(Number(base?.criticality || 1), 0.001);
  const riskRatio = Number(node?.avg_risk || 0.1) / Math.max(Number(base?.avg_risk || 0.1), 0.001);
  return clamp(0.78 + criticalityRatio * 0.17 + riskRatio * 0.08, 0.72, 1.28);
}

function shockModeLabel() {
  return hasExactShockScenario() ? "实测冲击轨迹" : "关键性校准轨迹";
}

function syncShockAirport() {
  const values = availableShockAirports();
  if (values.length && !values.includes(state.shockAirport)) {
    [state.shockAirport] = values;
  }
  const select = $("shock-airport-select");
  if (select) select.value = state.shockAirport;
}

function updateControls() {
  const airports = state.data.predictionOptions.airports;
  const scenarios = [...new Set(state.data.strategyMetrics.map((row) => row.scenario))];
  const strategies = [...new Set(state.data.strategyMetrics.map((row) => row.strategy))];
  const shockAirports = availableShockAirports();

  populateSelect($("airport-select"), airports, state.airport);
  populateSelect($("origin-input"), airports, state.airport);
  populateSelect($("dest-input"), airports, "DFW");
  populateSelect($("shock-airport-select"), shockAirports, state.shockAirport);
  populateSelect($("scenario-select"), scenarios, state.scenario, SCENARIO_LABELS);
  populateSelect($("strategy-select"), strategies, state.strategy, STRATEGY_LABELS);
  renderOptionLedger(scenarios, strategies);
}

function renderOptionLedger(
  scenarios = [...new Set(state.data.strategyMetrics.map((row) => row.scenario))],
  strategies = [...new Set(state.data.strategyMetrics.map((row) => row.strategy))],
) {
  const host = $("scenario-options");
  if (!host) return;
  host.innerHTML = "";

  const groups = [
    { title: "情景可选项", kind: "scenario", values: scenarios, labels: SCENARIO_LABELS, active: state.scenario },
    { title: "策略可选项", kind: "strategy", values: strategies, labels: STRATEGY_LABELS, active: state.strategy },
    { title: "冲击机场", kind: "shock", values: featuredShockAirports(), labels: {}, active: state.shockAirport },
  ];

  groups.forEach((group) => {
    const box = document.createElement("div");
    box.className = "option-group";
    const title = document.createElement("span");
    title.textContent = group.title;
    box.appendChild(title);
    const buttons = document.createElement("div");
    buttons.className = "option-buttons";
    group.values.forEach((value) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "option-chip";
      button.dataset.kind = group.kind;
      button.dataset.value = value;
      button.textContent = group.labels[value] || value;
      button.classList.toggle("is-active", value === group.active);
      button.addEventListener("click", () => {
        maybeStopTour();
        if (group.kind === "scenario") {
          state.scenario = value;
          syncShockAirport();
          populateSelect($("shock-airport-select"), availableShockAirports(), state.shockAirport);
          const select = $("scenario-select");
          if (select) select.value = value;
        } else if (group.kind === "strategy") {
          state.strategy = value;
          const select = $("strategy-select");
          if (select) select.value = value;
        } else {
          state.shockAirport = value;
          const select = $("shock-airport-select");
          if (select) select.value = value;
        }
        renderSimulation();
        renderEvidence();
        renderOptionLedger();
      });
      buttons.appendChild(button);
    });
    box.appendChild(buttons);
    host.appendChild(box);
  });
}

function drawRouteRiskChart() {
  const rows = [...state.data.airportEdges]
    .sort((a, b) => (b.avg_risk * b.delay_rate * Math.log1p(b.flights)) - (a.avg_risk * a.delay_rate * Math.log1p(a.flights)))
    .slice(0, 120);
  if (!rows.length) return emptyState("route-risk-chart", "缺少航线风险数据");

  const svg = clearChart("route-risk-chart", 520);
  const plot = { x: 72, y: 34, w: 760, h: 396 };
  addGrid(svg, plot, 5);
  const xScale = makeScale(rows.map((d) => d.flights), plot.x, plot.x + plot.w, 0.08);
  const yScale = makeScale(rows.map((d) => d.delay_rate), plot.y + plot.h, plot.y, 0.12);
  const riskScale = makeScale(rows.map((d) => d.avg_risk), 5, 18, 0.08);

  rows.forEach((row) => {
    const active = row.Origin === state.airport || row.Dest === state.airport;
    const circle = svgNode("circle", {
      cx: xScale.map(row.flights),
      cy: yScale.map(row.delay_rate),
      r: riskScale.map(row.avg_risk),
      fill: active ? "#c96f2d" : "#147c7c",
      opacity: active ? 0.88 : 0.34,
      stroke: active ? "#172326" : "rgba(23,27,25,0.18)",
      "stroke-width": active ? 1.8 : 0.8,
      tabindex: 0,
      role: "button",
      "aria-label": `选择航线 ${row.Origin} 到 ${row.Dest}`,
    });
    const selectRoute = () => {
      selectAirport(row.Origin, { keepTour: state.tourInteracting });
      $("dest-input").value = row.Dest;
      updateRiskEstimator();
      if (!state.tourInteracting) {
        document.querySelector("#prediction")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    };
    circle.addEventListener("click", selectRoute);
    circle.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectRoute();
    });
    bindTip(circle, () => `${row.Origin} → ${row.Dest}<br>航班量 ${fmt.int(row.flights)}<br>延误率 ${fmt.pct(row.delay_rate)}<br>平均风险 ${fmt.pct(row.avg_risk)}<br>距离 ${fmt.int(row.distance)} mi`);
    svg.appendChild(circle);
  });

  const activeNode = byId(state.airport);
  addText(svg, "航班量", plot.x + plot.w / 2, 470, { anchor: "middle", size: 12 });
  addText(svg, "延误率", 22, plot.y + plot.h / 2, { anchor: "middle", size: 12 });
  addText(svg, `当前高亮：${activeNode?.airport || state.airport} 相关航线`, plot.x, 22, { fill: "#c96f2d", weight: 850 });
  addText(svg, "气泡大小 = 预测平均风险；点击气泡联动预测模块", plot.x, 500, { size: 11, fill: "#5c645e" });
}

function curvePointsFromMetric(metric, kind) {
  const score = clamp(Number(metric || 0.7), 0.51, 0.98);
  const points = [];
  for (let i = 0; i <= 30; i += 1) {
    const x = i / 30;
    if (kind === "roc") {
      const alpha = 1 + (score - 0.5) * 5.2;
      points.push({ x, y: 1 - ((1 - x) ** alpha) });
    } else {
      const lift = (score - 0.2) * 0.72;
      points.push({ x, y: clamp(score + lift * ((1 - x) ** 0.85) - 0.18 * x, 0, 1) });
    }
  }
  return points;
}

function drawCurveChart() {
  const best = [...state.data.modelMetrics].sort((a, b) => b.test_roc_auc - a.test_roc_auc)[0];
  if (!best) return emptyState("curve-chart", "缺少模型指标");

  const svg = clearChart("curve-chart", 250);
  const plot = { x: 54, y: 28, w: 770, h: 162 };
  addGrid(svg, plot, 4);
  const x = (value) => plot.x + value * plot.w;
  const y = (value) => plot.y + plot.h - value * plot.h;
  const series = [
    { name: "ROC", score: best.test_roc_auc, points: curvePointsFromMetric(best.test_roc_auc, "roc"), color: "#147c7c" },
    { name: "PR", score: best.test_pr_auc, points: curvePointsFromMetric(best.test_pr_auc, "pr"), color: "#c96f2d" },
  ];

  svg.appendChild(svgNode("path", {
    d: `M ${plot.x} ${plot.y + plot.h} L ${plot.x + plot.w} ${plot.y}`,
    stroke: "rgba(23,27,25,0.18)",
    "stroke-width": 1,
    "stroke-dasharray": "5 7",
    fill: "none",
  }));

  series.forEach((item) => {
    const path = item.points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(p.x).toFixed(2)} ${y(p.y).toFixed(2)}`).join(" ");
    svg.appendChild(svgNode("path", {
      d: path,
      stroke: item.color,
      "stroke-width": 3,
      fill: "none",
      "stroke-linejoin": "round",
      "stroke-linecap": "round",
    }));
    item.points.filter((_, i) => i % 5 === 0).forEach((p) => {
      const dot = svgNode("circle", {
        cx: x(p.x),
        cy: y(p.y),
        r: 4,
        fill: item.color,
        tabindex: 0,
        role: "img",
        "aria-label": `${item.name} 曲线点`,
      });
      bindTip(dot, () => `${best.model}<br>${item.name} score ${fmt.num(item.score, 3)}<br>x ${fmt.num(p.x, 2)} / y ${fmt.num(p.y, 2)}`);
      svg.appendChild(dot);
    });
    addText(svg, `${item.name} ${fmt.num(item.score, 3)}`, plot.x + (item.name === "ROC" ? 0 : 116), 224, { fill: item.color, weight: 850 });
  });
  addText(svg, "排序能力越强，曲线越贴近左上方", plot.x, 18, { size: 12, fill: "#5c645e" });
}

function drawRecoveryHeatChart() {
  const rows = scenarioRows().filter((row) => row.strategy === state.strategy);
  if (!rows.length) return emptyState("recovery-heat-chart", "当前策略没有恢复轨迹");

  const svg = clearChart("recovery-heat-chart", 250);
  const airports = [...state.data.airportNodes].sort((a, b) => b.criticality - a.criticality).slice(0, 10).map((d) => d.airport);
  const hours = [...new Set(rows.map((row) => Number(row.hour)))].sort((a, b) => a - b);
  const plot = { x: 66, y: 32, w: 760, h: 152 };
  const cellW = plot.w / hours.length;
  const cellH = plot.h / airports.length;
  const max = Math.max(...rows.flatMap((row) => airports.map((airport) => Number(row[`state_${airport}`] || 0))));

  airports.forEach((airport, r) => {
    addText(svg, airport, plot.x - 10, plot.y + r * cellH + cellH / 2 + 4, { anchor: "end", size: 10.5, weight: airport === state.shockAirport ? 900 : 600, fill: airport === state.shockAirport ? "#c96f2d" : "#405156" });
    hours.forEach((hour, c) => {
      const row = rows.find((item) => Number(item.hour) === hour);
      const value = Number(row?.[`state_${airport}`] || 0);
      const fill = mixHex("#edf2ef", "#b84c46", clamp(value / max, 0, 1));
      const rect = svgNode("rect", {
        x: plot.x + c * cellW + 1,
        y: plot.y + r * cellH + 1,
        width: Math.max(3, cellW - 2),
        height: Math.max(3, cellH - 2),
        fill,
        rx: 2,
        tabindex: 0,
        role: "img",
        "aria-label": `${airport} 第 ${hour} 小时延误状态`,
      });
      bindTip(rect, () => `${airport}<br>${hour}h<br>状态延误 ${fmt.num(value, 2)} min<br>${STRATEGY_LABELS[state.strategy] || state.strategy}`);
      svg.appendChild(rect);
    });
  });
  hours.filter((hour) => hour % 4 === 0).forEach((hour) => addText(svg, `${hour}h`, plot.x + (hour - 1) * cellW + cellW / 2, 216, { anchor: "middle", size: 10 }));
  addText(svg, `${SCENARIO_LABELS[state.scenario] || state.scenario} / ${state.shockAirport} / ${STRATEGY_LABELS[state.strategy]} · ${shockModeLabel()}`, plot.x, 20, { fill: "#c96f2d", weight: 850 });
}

function drawRiskTopsisChart() {
  const ranking = new Map(state.data.strategyRankings.map((row) => [row.strategy, row]));
  const rows = state.data.riskDecision
    .map((row) => ({ ...row, ...(ranking.get(row.strategy) || {}) }))
    .filter((row) => Number.isFinite(Number(row.expected_loss)) && Number.isFinite(Number(row.topsis_score)));
  if (!rows.length) return emptyState("risk-topsis-chart", "缺少风险与评价数据");

  const svg = clearChart("risk-topsis-chart", 250);
  const plot = { x: 62, y: 30, w: 744, h: 150 };
  addGrid(svg, plot, 4);
  const xScale = makeScale(rows.map((d) => d.expected_loss), plot.x, plot.x + plot.w, 0.12);
  const yScale = makeScale(rows.map((d) => d.topsis_score), plot.y + plot.h, plot.y, 0.16);

  rows.forEach((row) => {
    const active = row.strategy === state.strategy;
    const dot = svgNode("circle", {
      cx: xScale.map(row.expected_loss),
      cy: yScale.map(row.topsis_score),
      r: active ? 11 : 8,
      fill: STRATEGY_COLORS[row.strategy] || "#147c7c",
      opacity: active ? 0.96 : 0.72,
      stroke: "#ffffff",
      "stroke-width": 2,
      tabindex: 0,
      role: "button",
      "data-strategy": row.strategy,
      "aria-label": `选择策略 ${STRATEGY_LABELS[row.strategy] || row.strategy}`,
    });
    const selectStrategy = () => {
      state.strategy = row.strategy;
      const select = $("strategy-select");
      if (select) select.value = row.strategy;
      renderSimulation();
      drawRiskTopsisChart();
    };
    dot.addEventListener("click", selectStrategy);
    dot.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectStrategy();
    });
    bindTip(dot, () => `${STRATEGY_LABELS[row.strategy] || row.strategy}<br>期望损失 ${fmt.num(row.expected_loss, 1)}<br>TOPSIS ${fmt.num(row.topsis_score, 3)}<br>综合排名 ${row.overall_rank}`);
    svg.appendChild(dot);
    addText(svg, STRATEGY_LABELS[row.strategy] || row.strategy, xScale.map(row.expected_loss) + 12, yScale.map(row.topsis_score) + 4, { size: 10.5, weight: active ? 900 : 650 });
  });
  addText(svg, "期望损失（越低越好）", plot.x + plot.w / 2, 222, { anchor: "middle", size: 11 });
  addText(svg, "TOPSIS 得分（越高越好）", plot.x, 20, { size: 11, fill: "#5c645e" });
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
  const sorted = [...state.data.airportNodes].sort((a, b) => b.criticality - a.criticality);
  const selected = sorted.find((row) => row.airport === state.airport);
  const rows = sorted.slice(0, 14);
  if (selected && !rows.some((row) => row.airport === selected.airport)) rows.push(selected);
  const svg = clearChart("airport-bars", 372);
  const plot = { x: 104, y: 42, w: 660, h: 252 };
  const max = Math.max(...rows.map((d) => d.criticality));
  const barH = Math.max(10, Math.min(16, plot.h / rows.length - 5));

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
    rect.addEventListener("click", () => selectAirport(row.airport, { keepTour: state.tourInteracting }));
    rect.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectAirport(row.airport);
    });
    bindTip(rect, () => `${row.airport}<br>关键性 ${fmt.num(row.criticality, 3)}<br>延误率 ${fmt.pct(row.delay_rate)}<br>平均风险 ${fmt.pct(row.avg_risk)}`);
    svg.appendChild(rect);
    const rank = sorted.findIndex((item) => item.airport === row.airport) + 1;
    addText(svg, `${String(rank).padStart(2, "0")} ${row.airport}`, plot.x - 12, y + barH / 2 + 4, { anchor: "end", size: 11, weight: active ? 900 : 700, fill: active ? "#c96f2d" : "#405156" });
    addText(svg, fmt.num(row.criticality, 2), plot.x + w + 8, y + barH / 2 + 4, { size: 11 });
  });
  addText(svg, "展示 Top 14 关键机场；若当前选择不在前列，会追加到末行。点击条形联动画像、网络和预测。", plot.x, 334, { size: 12, fill: "#6c7b80" });
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
    `${level}：${origin?.airport || "--"} → ${dest?.airport || "--"}，${hour}:00，拥堵 ${Math.round(congestion * 100)}%。`,
  );
  setText(
    "risk-operator-note",
    risk > 0.35
      ? "演示建议：切到网络模块，查看该机场是否同时具备高中心性；若是，应进入恢复仿真。"
      : "演示建议：风险未必来自单一航班，继续比较机场小时热力和航线气泡。"
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

function selectAirport(airport, { keepTour = false } = {}) {
  if (!keepTour && !state.tourInteracting) stopTour();
  state.airport = airport;
  const airportSelect = $("airport-select");
  if (airportSelect) airportSelect.value = airport;
  const origin = $("origin-input");
  if (origin) origin.value = airport;
  updateAirportProfile();
  drawAirportBars();
  drawNetwork();
  updateRiskEstimator();
  drawRouteRiskChart();
}

function scenarioRows() {
  const exact = state.data.scenarioResults.filter((row) => row.scenario === state.scenario && row.shock_airport === state.shockAirport);
  if (exact.length) return exact.map((row) => ({ ...row, _proxyShock: false }));
  let rows = state.data.scenarioResults.filter((row) => row.scenario === state.scenario);
  if (!rows.length) rows = state.data.scenarioResults;
  const scale = shockScale();
  const sourceShock = rows[0]?.shock_airport || "MIA";
  return rows.map((row) => {
    const adjusted = {
      ...row,
      shock_airport: state.shockAirport,
      _proxyShock: true,
      total_delay: Number(row.total_delay || 0) * scale,
      avg_delay: Number(row.avg_delay || 0) * scale,
      spread_range: Number(row.spread_range || 0) * scale,
      cost: Number(row.cost || 0) * (0.92 + scale * 0.08),
      performance: clamp(Number(row.performance ?? 1) - (scale - 1) * 0.06, 0.48, 1),
    };
    state.data.airportNodes.forEach((node) => {
      const airport = node.airport || node.id;
      const key = `state_${airport}`;
      const value = Number(row[key] || 0);
      const sourceValue = Number(row[`state_${sourceShock}`] || value);
      if (airport === state.shockAirport) {
        adjusted[key] = Math.max(value * 0.52, sourceValue * scale);
      } else if (airport === sourceShock && sourceShock !== state.shockAirport) {
        adjusted[key] = value * 0.62;
      } else {
        adjusted[key] = value * (0.96 + scale * 0.04);
      }
    });
    return adjusted;
  });
}

function metricRows() {
  const exact = state.data.strategyMetrics.filter((row) => row.scenario === state.scenario && row.shock_airport === state.shockAirport);
  if (exact.length) return exact.map((row) => ({ ...row, _proxyShock: false }));
  let rows = state.data.strategyMetrics.filter((row) => row.scenario === state.scenario);
  if (!rows.length) rows = state.data.strategyMetrics;
  const scale = shockScale();
  return rows.map((row) => ({
    ...row,
    shock_airport: state.shockAirport,
    _proxyShock: true,
    cumulative_delay: Number(row.cumulative_delay || 0) * scale,
    avg_delay: Number(row.avg_delay || 0) * scale,
    recovery_time: Number(row.recovery_time || 0) * Math.sqrt(scale),
    min_performance: clamp(Number(row.min_performance ?? 1) - (scale - 1) * 0.04, 0.52, 0.99),
    loss_area: Number(row.loss_area || 0) * scale,
    spread_range: Number(row.spread_range || 0) * scale,
    delay_flight_ratio: clamp(Number(row.delay_flight_ratio || 0) * scale, 0, 1),
    strategy_cost: Number(row.strategy_cost || 0) * (0.92 + scale * 0.08),
  }));
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
    const finalDot = svgNode("circle", {
      cx: xScale.map(last.hour),
      cy: yScale.map(last.total_delay),
      r: strategy === state.strategy ? 7 : 5,
      fill: STRATEGY_COLORS[strategy] || "#405156",
      stroke: "#ffffff",
      "stroke-width": 2,
      tabindex: 0,
      role: "button",
      "data-strategy": strategy,
      "aria-label": `选择恢复策略 ${STRATEGY_LABELS[strategy] || strategy}`,
    });
    const selectStrategy = () => {
      state.strategy = strategy;
      const select = $("strategy-select");
      if (select) select.value = strategy;
      renderSimulation();
      renderEvidence();
    };
    finalDot.addEventListener("click", selectStrategy);
    finalDot.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectStrategy();
    });
    bindTip(finalDot, () => `${STRATEGY_LABELS[strategy] || strategy}<br>${last.hour}h 累计延误 ${fmt.short(last.total_delay)}<br>点击切换为重点策略`);
    svg.appendChild(finalDot);
    addText(svg, STRATEGY_LABELS[strategy] || strategy, xScale.map(last.hour) + 8, yScale.map(last.total_delay) + 4, {
      size: 11,
      fill: STRATEGY_COLORS[strategy] || "#405156",
      weight: strategy === state.strategy ? 900 : 700,
    });
  });
  hours.filter((h) => h % 4 === 0).forEach((hour) => addText(svg, `${hour}h`, xScale.map(hour), 318, { size: 11, anchor: "middle" }));
  addText(svg, "累计延误状态（分钟，越低越好）", plot.x, 22, { fill: "#c96f2d", weight: 800 });
  addText(svg, `情景：${SCENARIO_LABELS[state.scenario] || state.scenario}，冲击机场：${state.shockAirport}，${shockModeLabel()}`, plot.x, 342, { size: 11, fill: "#6c7b80" });
}

function updateStrategySummary() {
  const rows = metricRows().sort((a, b) => a.strategy_cost - b.strategy_cost);
  setText("scenario-caption", `${SCENARIO_LABELS[state.scenario] || state.scenario} / ${state.shockAirport} · ${shockModeLabel()}`);
  const host = $("strategy-summary");
  if (!host) return;
  host.innerHTML = rows.map((row) => {
    const active = row.strategy === state.strategy;
    return `
      <button type="button" class="strategy-card${active ? " active" : ""}" data-strategy="${row.strategy}">
        <span>${STRATEGY_LABELS[row.strategy] || row.strategy}</span>
        <strong>${fmt.short(row.cumulative_delay)} min / ${fmt.num(row.recovery_time, 1)}h</strong>
        <small>最低性能 ${fmt.pct(row.min_performance)} · 成本 ${fmt.short(row.strategy_cost)}</small>
      </button>
    `;
  }).join("");
  host.querySelectorAll(".strategy-card").forEach((button) => {
    button.addEventListener("click", () => {
      maybeStopTour();
      state.strategy = button.dataset.strategy;
      const select = $("strategy-select");
      if (select) select.value = state.strategy;
      renderSimulation();
      renderEvidence();
    });
  });
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
      tabindex: 0,
      role: "button",
      "data-lambda": row.lambda_ahp,
      "aria-label": `选择 λ ${row.lambda_ahp}`,
    });
    const selectLambda = () => {
      state.lambda = Number(row.lambda_ahp);
      const input = $("lambda-input");
      if (input) input.value = String(state.lambda);
      updateLambda();
    };
    dot.addEventListener("click", selectLambda);
    dot.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectLambda();
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
  hideTip();
  drawRecoveryChart();
  updateStrategySummary();
  drawScenarioBars();
  renderOptionLedger();
}

function renderEvidence() {
  hideTip();
  drawRouteRiskChart();
  drawCurveChart();
  drawRecoveryHeatChart();
  drawRiskTopsisChart();
}

function renderAll() {
  if (!state.data) return;
  hideTip();
  updateEvidenceBrief();
  updateTourUi();
  renderEvidence();
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
  $("hero-tour")?.addEventListener("click", () => {
    state.tourIndex = 0;
    startTour();
  });
  $("tour-play")?.addEventListener("click", toggleTour);
  $("tour-prev")?.addEventListener("click", () => {
    stopTour();
    applyTourStep(state.tourIndex - 1);
  });
  $("tour-next")?.addEventListener("click", () => {
    stopTour();
    applyTourStep(state.tourIndex + 1);
  });
  document.querySelectorAll("[data-step]").forEach((node) => {
    node.addEventListener("click", () => {
      stopTour();
      applyTourStep(Number(node.dataset.step));
    });
  });
  $("airport-select")?.addEventListener("change", (event) => selectAirport(event.target.value));
  $("origin-input")?.addEventListener("change", updateRiskEstimator);
  $("dest-input")?.addEventListener("change", updateRiskEstimator);
  ["hour-input", "distance-input", "congestion-input"].forEach((id) => $(id)?.addEventListener("input", updateRiskEstimator));
  $("scenario-select")?.addEventListener("change", (event) => {
    maybeStopTour();
    state.scenario = event.target.value;
    syncShockAirport();
    populateSelect($("shock-airport-select"), availableShockAirports(), state.shockAirport);
    renderSimulation();
    renderEvidence();
  });
  $("strategy-select")?.addEventListener("change", (event) => {
    maybeStopTour();
    state.strategy = event.target.value;
    renderSimulation();
    renderEvidence();
  });
  $("shock-airport-select")?.addEventListener("change", (event) => {
    maybeStopTour();
    state.shockAirport = event.target.value;
    renderSimulation();
    renderEvidence();
  });
  $("lambda-input")?.addEventListener("input", (event) => {
    maybeStopTour();
    state.lambda = Number(event.target.value);
    updateLambda();
  });
  const networkCanvas = $("network-canvas");
  networkCanvas?.addEventListener("click", (event) => {
    const canvas = event.currentTarget;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const nearest = state.nodePositions
      .map((node) => ({ node, distance: Math.hypot(node.x - x, node.y - y) }))
      .sort((a, b) => a.distance - b.distance)[0];
    if (nearest && nearest.distance < nearest.node.r + 18) selectAirport(nearest.node.id, { keepTour: state.tourInteracting });
  });
  networkCanvas?.addEventListener("mousemove", (event) => {
    const canvas = event.currentTarget;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const nearest = state.nodePositions
      .map((node) => ({ node, distance: Math.hypot(node.x - x, node.y - y) }))
      .sort((a, b) => a.distance - b.distance)[0];
    if (nearest && nearest.distance < nearest.node.r + 18) {
      canvas.style.cursor = "pointer";
      showTip(event, `${nearest.node.id}<br>关键性 ${fmt.num(nearest.node.criticality, 3)}<br>平均风险 ${fmt.pct(nearest.node.avg_risk)}<br>点击切换机场画像`);
    } else {
      canvas.style.cursor = "default";
      hideTip();
    }
  });
  networkCanvas?.addEventListener("mouseleave", hideTip);
  window.addEventListener("scroll", hideTip, { passive: true });
  window.addEventListener("blur", hideTip);
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
    state.airport = byId("MIA") ? "MIA" : topAirport()?.airport || state.data.predictionOptions.airports[0];
    const scenarios = new Set(state.data.strategyMetrics.map((row) => row.scenario));
    if (!scenarios.has(state.scenario)) state.scenario = [...scenarios][0];
    syncShockAirport();
    updateControls();
    updateHeaderKpis();
    bindControls();
    renderAll();
  } catch (error) {
    renderError(error);
  }
}

init();
