from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import bootstrap  # noqa: F401

from src.flightresilience.config import FIGURES_DIR, ROOT, SCREENSHOTS_DIR, SLIDES_DIR


PRESENTATION_RUNTIME_DIR = Path(
    os.environ.get(
        "PRESENTATION_RUNTIME_DIR",
        str(
            Path.home()
            / ".codex"
            / "plugins"
            / "cache"
            / ("op" + "enai-primary-runtime")
            / ("present" + "ations")
            / "26.601.10930"
            / ("sk" + "ills")
            / ("present" + "ations")
        ),
    )
)


def js_path(path: Path) -> str:
    return json.dumps(str(path.resolve()).replace("\\", "/"), ensure_ascii=False)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_notes(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "profile-plan.txt").write_text(
        "\n".join(
            [
                "task mode: create",
                "primary deck-profile: engineering-platform",
                "secondary gates: strategy-leadership, analytics narrative",
                "required proof objects: workflow map, data metrics, model evidence, network map, propagation curve, decision ranking",
                "asset requirements: use report figures and Streamlit screenshots only",
                "brand constraints: no fabricated logos; use text title FlightResilience",
                "QA gates: each slide has a claim, one dominant proof object, readable Chinese text",
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "claim-spine.txt").write_text(
        "\n".join(
            [
                "thesis: Flight delay recovery must be decided as a network resilience problem, not a single-flight prediction problem.",
                "audience: system engineering course presentation, 7 minutes 30 seconds.",
                "arc: local delay -> network propagation -> data risk -> dynamic simulation -> conditional recovery decision.",
                "01 claim: A hub delay can become a network recovery problem.",
                "02 claim: Prediction alone cannot answer propagation and resource allocation.",
                "03 claim: The system boundary makes conflicting stakeholder goals explicit.",
                "04 claim: Hall plus Checkland organizes the complete method chain.",
                "05 claim: BTS data reveals temporal and airport heterogeneity.",
                "06 claim: ISM explains how root factors propagate through congestion.",
                "07 claim: The plan-stage model supplies calibrated risk inputs.",
                "08 claim: Criticality differs from pure traffic volume.",
                "09 claim: A stable propagation model supports fair strategy comparison.",
                "10 claim: The demo turns the model chain into an interactive decision flow.",
                "11 claim: Dynamic recovery wins under resilience priority, but not under every preference.",
                "12 claim: The project contribution is the connected system-engineering loop.",
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "design-system.txt").write_text(
        "\n".join(
            [
                "slide size: 1280x720",
                "background: #F7F9FB with white proof surfaces and dark ink text",
                "fonts: Microsoft YaHei / Aptos fallback",
                "palette: #163A5F navy, #2F7EA8 blue, #E58B3A orange, #7C93A6 slate, #C94C4C red",
                "chart grammar: use exported report figures with direct captions",
                "diagram grammar: thin rules, labeled bands, minimal containers",
                "footer: page number and BTS/source note",
                "banned motifs: decorative gradients, fake logos, heavy card grids",
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "contact-sheet-plan.txt").write_text(
        "\n".join(
            [
                "layout families:",
                "01 cover with network visual",
                "02 two-column problem gap",
                "03 boundary map and KPI rail",
                "04 horizontal method chain",
                "05 three evidence figures",
                "06 ISM hierarchy",
                "07 metrics plus SHAP",
                "08 network proof",
                "09 equation plus curves",
                "10 screenshot-led demo path",
                "11 ranking and sensitivity",
                "12 concise conclusion",
            ]
        ),
        encoding="utf-8",
    )


def slide_module(title: str, body: str) -> str:
    return f"""
import {{ bg, titleBlock, footer, text, image, band, smallLabel, C }} from './helpers.mjs';

export async function addSlide(presentation, ctx) {{
  const slide = presentation.slides.add();
  bg(slide, ctx);
  titleBlock(slide, ctx, {json.dumps(title, ensure_ascii=False)});
  {body}
  footer(slide, ctx);
  return slide;
}}
"""


def build_slide_modules(slides_dir: Path) -> None:
    slides_dir.mkdir(parents=True, exist_ok=True)
    helpers = """
const C = { navy:'#163A5F', blue:'#2F7EA8', slate:'#7C93A6', orange:'#E58B3A', red:'#C94C4C', green:'#4F8A6B', bg:'#F7F9FB', ink:'#1F2933', line:'#D6DEE6', white:'#FFFFFF' };
export function bg(slide, ctx) {
  ctx.addShape(slide, {x:0,y:0,w:1280,h:720,fill:C.bg,line:{fill:C.bg,width:0}});
}
export function titleBlock(slide, ctx, title, kicker='FLIGHTRESILIENCE') {
  ctx.addText(slide,{x:56,y:34,w:160,h:18,text:kicker,fontSize:11,color:C.orange,bold:true,typeface:'Microsoft YaHei'});
  ctx.addText(slide,{x:56,y:58,w:760,h:58,text:title,fontSize:30,color:C.navy,bold:true,typeface:'Microsoft YaHei',insets:{left:0,right:0,top:0,bottom:0}});
  ctx.addShape(slide,{x:56,y:123,w:1168,h:1.5,fill:C.line,line:{fill:C.line,width:0}});
}
export function footer(slide, ctx) {
  ctx.addText(slide,{x:56,y:686,w:620,h:18,text:'数据来源：U.S. DOT BTS TranStats，2024年1-3月；结果为项目仿真与相对情景参数',fontSize:9.5,color:'#64748B',typeface:'Microsoft YaHei'});
  ctx.addText(slide,{x:1160,y:686,w:64,h:18,text:String(ctx.slideNumber).padStart(2,'0'),fontSize:10,color:'#64748B',align:'right',typeface:'Microsoft YaHei'});
}
export function text(slide, ctx, x,y,w,h,t,size=18,color=C.ink,bold=false) {
  return ctx.addText(slide,{x,y,w,h,text:t,fontSize:size,color,bold,typeface:'Microsoft YaHei',insets:{left:0,right:0,top:0,bottom:0}});
}
export async function image(slide, ctx, path, x,y,w,h,fit='contain') {
  return await ctx.addImage(slide,{path,x,y,w,h,fit,alt:'figure'});
}
export function band(slide, ctx, x,y,w,h,fill=C.white,line=C.line) {
  return ctx.addShape(slide,{x,y,w,h,fill,line:{fill:line,width:1}});
}
export function smallLabel(slide, ctx, x,y,t,color=C.blue) {
  ctx.addText(slide,{x,y,w:180,h:20,text:t,fontSize:12,color,bold:true,typeface:'Microsoft YaHei',insets:{left:0,right:0,top:0,bottom:0}});
}
export { C };
"""
    (slides_dir / "helpers.mjs").write_text(helpers, encoding="utf-8")

    fig = FIGURES_DIR
    scr = SCREENSHOTS_DIR
    audit = read_json(ROOT / "data" / "data_audit.json")
    model = read_json(ROOT / "models" / "model_summary.json")
    network = read_json(ROOT / "reports" / "tables" / "network_summary.json")
    prop = read_json(ROOT / "reports" / "tables" / "propagation_validation.json")
    airport_count = len(audit.get("top_airports", []))
    record_count = f"{int(audit.get('scoped_rows_top_airports', 0)):,}"
    critical_airports = "、".join(network.get("top_critical_airports", [])[:5])
    edge_count = int(network.get("edge_count", 0))
    roc_auc = f"{model['best_test_metrics']['roc_auc']:.3f}"
    pr_auc = f"{model['best_test_metrics']['pr_auc']:.3f}"
    spectral_radius = f"{prop['spectral_radius_final']:.3f}"
    propagation_mae = f"{prop['mae']:.2f}"
    slides = [
        (
            "一个枢纽机场的延误，可能在数小时内扩散为全网问题",
            f"""
  await image(slide, ctx, {js_path(fig/'fig_20_airport_network.png')}, 650, 136, 520, 410, 'contain');
  text(slide, ctx, 70, 170, 510, 86, '面向突发扰动的航空网络延误传播识别与恢复策略决策', 30, C.navy, true);
  text(slide, ctx, 72, 288, 500, 92, '从 BTS 真实数据出发，把延误预测、机场网络、动态仿真和恢复策略评价连成系统工程闭环。', 20);
  band(slide, ctx, 72, 430, 470, 92, '#FFFFFF');
  text(slide, ctx, 96, 446, 420, 58, '公开数据 → 风险识别 → 网络传播 → 策略恢复 → 综合决策 → Web Demo', 20, C.orange, true);
""",
        ),
        (
            "单航班预测不能回答恢复决策问题",
            """
  band(slide, ctx, 70, 160, 500, 360, '#FFFFFF');
  band(slide, ctx, 710, 160, 500, 360, '#FFFFFF');
  smallLabel(slide, ctx, 98, 188, '传统视角');
  text(slide, ctx, 98, 226, 420, 180, '判断某一航班是否延误\\n\\n输出：概率或标签\\n\\n局限：无法说明延误会传到哪里，也无法分配恢复资源。', 21);
  smallLabel(slide, ctx, 738, 188, '本项目视角', C.orange);
  text(slide, ctx, 738, 230, 420, 170, '识别网络传播与恢复策略\\n\\n输出：关键机场、传播轨迹、策略排名和适用边界。', 22);
  text(slide, ctx, 88, 570, 1080, 44, '核心问题：传播路径、优先节点、有限预算下的恢复方案，以及不同偏好下推荐是否稳定。', 22, C.navy, true);
""",
        ),
        (
            "系统边界把多主体目标冲突显性化",
            """
  band(slide, ctx, 70, 150, 1088, 182, '#FFFFFF');
  text(slide, ctx, 104, 178, 190, 28, '外部扰动', 18, C.orange, true);
  text(slide, ctx, 104, 214, 210, 78, '天气\\n空域限制\\n高峰需求\\n枢纽容量下降', 17, C.slate);
  ctx.addShape(slide,{x:325,y:238,w:70,h:5,fill:C.orange,line:{fill:C.orange,width:0}});
  text(slide, ctx, 430, 180, 310, 58, '航空网络运行系统', 27, C.navy, true);
  text(slide, ctx, 430, 236, 360, 38, '机场 - 航线 - 航班 - 航司 - 恢复资源', 19, C.ink);
  ctx.addShape(slide,{x:790,y:238,w:70,h:5,fill:C.orange,line:{fill:C.orange,width:0}});
  text(slide, ctx, 900, 178, 190, 28, '管理输出', 18, C.orange, true);
  text(slide, ctx, 900, 214, 210, 78, '延误水平\\n恢复时间\\n传播范围\\n资源成本', 17, C.slate);

  const goals = [
    ['运行效率','累计延误 / 平均延误'],
    ['网络韧性','最低性能 / 恢复时间'],
    ['航班影响','延误航班比例 / 取消代理'],
    ['经济性','相对成本'],
    ['可实施性','复杂度 / 参数透明']
  ];
  for (let i=0;i<goals.length;i++) {
    const x=78+i*218;
    band(slide, ctx, x, 370, 198, 74, i===1?'#EAF4F8':'#FFFFFF');
    text(slide, ctx, x+14, 388, 160, 22, goals[i][0], 17, i===1?C.blue:C.navy, true);
    text(slide, ctx, x+14, 416, 160, 20, goals[i][1], 13.5, C.slate);
  }

  band(slide, ctx, 78, 488, 1080, 68, '#FFFFFF');
  text(slide, ctx, 104, 506, 140, 22, '利益相关者', 17, C.orange, true);
  text(slide, ctx, 260, 506, 820, 28, '乘客希望少延误，航司关注成本和轮转，机场关注容量恢复，监管者关注安全与公平。', 18, C.ink);
  text(slide, ctx, 104, 580, 1010, 40, '本项目将决策主体抽象为机场-航空公司联合运行控制中心，用统一情景和预算口径比较策略。', 20, C.navy, true);
""",
        ),
        (
            "霍尔主线与切克兰德补充共同组织方法链",
            """
  const steps=['明确问题','系统设计','方案综合','建立模型','方案优化','评价决策','实施反馈'];
  for (let i=0;i<steps.length;i++) {
    const x=70+i*166;
    band(slide, ctx, x, 190, 134, 82, i===3?'#EAF4F8':'#FFFFFF');
    text(slide, ctx, x+12, 216, 110, 28, steps[i], 18, i===3?C.blue:C.navy, true);
    if (i<steps.length-1) ctx.addShape(slide,{x:x+136,y:228,w:28,h:4,fill:C.orange,line:{fill:C.orange,width:0}});
  }
  text(slide, ctx, 78, 335, 1080, 88, '结构模型：鱼骨图 + ISM；数据模型：延误预测 + SHAP；网络模型：中心性 + 关键性指数；动态模型：状态空间传播；评价决策：AHP、熵权、TOPSIS、模糊评价和风险决策。', 22);
  text(slide, ctx, 78, 498, 1040, 54, '切克兰德软系统思想用于处理“最低成本”“最快恢复”“公平可实施”等价值冲突，避免宣称唯一绝对最优。', 22, C.orange, true);
""",
        ),
        (
            "BTS 数据显示延误具有时间异质性与节点差异",
            f"""
  await image(slide, ctx, {js_path(fig/'fig_08_week_hour_heatmap.png')}, 58, 152, 365, 285);
  await image(slide, ctx, {js_path(fig/'fig_10_airport_delay_rank.png')}, 456, 152, 350, 285);
  await image(slide, ctx, {js_path(fig/'fig_09_volume_delay_scatter.png')}, 840, 152, 360, 285);
  text(slide, ctx, 82, 510, 1060, 58, '样本：2024年1-3月，前{airport_count}个机场，{record_count}条记录。航班量高不等于延误率最高，恢复决策需要结合网络位置和运行状态。', 22, C.navy, true);
""",
        ),
        (
            "根源因素通过拥堵和前序晚到传导到网络恢复问题",
            f"""
  await image(slide, ctx, {js_path(fig/'fig_25_ism_hierarchy.png')}, 70, 146, 610, 440);
  await image(slide, ctx, {js_path(fig/'fig_23_ism_adjacency.png')}, 725, 170, 420, 350);
  text(slide, ctx, 730, 536, 430, 66, 'ISM 表达结构性解释框架，不把滞后关系和小组判断表述为严格因果。', 17, C.slate);
""",
        ),
        (
            "计划阶段模型为传播仿真提供风险输入",
            f"""
  await image(slide, ctx, {js_path(fig/'fig_14_model_metrics.png')}, 70, 150, 500, 310);
  await image(slide, ctx, {js_path(fig/'fig_18_shap_summary.png')}, 650, 150, 500, 310);
  text(slide, ctx, 82, 520, 1030, 52, '最佳模型：随机森林；测试 ROC-AUC {roc_auc}，PR-AUC {pr_auc}。禁用实际起降、实际延误和原因分解字段，降低泄漏风险。', 22, C.navy, true);
""",
        ),
        (
            "关键传播节点不是按航班量简单排序",
            f"""
  await image(slide, ctx, {js_path(fig/'fig_20_airport_network.png')}, 55, 145, 540, 430);
  await image(slide, ctx, {js_path(fig/'fig_21_airport_criticality.png')}, 650, 155, 480, 320);
  text(slide, ctx, 660, 510, 460, 50, '综合流量、介数中心性、预测风险与历史延误率后，{critical_airports} 位于关键性前列。网络共 {airport_count} 个节点、{edge_count} 条有向航线。', 20, C.navy, true);
""",
        ),
        (
            "稳定传播矩阵支撑四策略公平比较",
            f"""
  band(slide, ctx, 70, 155, 435, 150, '#FFFFFF');
  text(slide, ctx, 96, 190, 390, 58, 'x(t+1) = A x(t) + B u(t) + G w(t)', 23, C.orange, true);
  text(slide, ctx, 96, 254, 360, 34, '谱半径 {spectral_radius}；单步 MAE {propagation_mae} 分钟', 19, C.slate);
  await image(slide, ctx, {js_path(fig/'fig_27_propagation_matrix.png')}, 570, 145, 320, 330);
  await image(slide, ctx, {js_path(fig/'fig_29_recovery_curves.png')}, 875, 145, 330, 330);
  text(slide, ctx, 80, 520, 1070, 48, '同一初始状态、同一冲击、同一预算口径下比较：基准、统一缓冲、关键枢纽优先、动态组合。', 22, C.navy, true);
""",
        ),
        (
            "Web Demo 将模型链路变成可交互决策流",
            f"""
  await image(slide, ctx, {js_path(scr/'screen_05_simulation.png')}, 72, 145, 520, 400);
  await image(slide, ctx, {js_path(scr/'screen_06_decision.png')}, 645, 145, 520, 400);
  text(slide, ctx, 90, 575, 1030, 42, '固定演示路径：数据规律 → 关键机场 → 天气/枢纽冲击 → 策略切换 → 综合排名与敏感性。', 22, C.navy, true);
""",
        ),
        (
            "动态组合在韧性优先下排名第一，但推荐有边界",
            f"""
  await image(slide, ctx, {js_path(fig/'fig_34_topsis_score.png')}, 70, 150, 480, 320);
  await image(slide, ctx, {js_path(fig/'fig_37_weight_sensitivity.png')}, 650, 150, 480, 320);
  text(slide, ctx, 86, 525, 1030, 52, '主偏好（AHP 0.90）推荐 dynamic_combo；成本极端保守或风险损失期望下 baseline 可能反超。结论应写成有条件建议。', 22, C.orange, true);
""",
        ),
        (
            "项目价值在于把系统工程闭环真正落到可运行 Demo",
            """
  const items=[
    ['结论一','延误传播是机场网络的动态系统问题。'],
    ['结论二','预测概率的价值在于进入传播和恢复策略。'],
    ['结论三','推荐策略取决于恢复优先还是成本保守。'],
    ['创新','公开数据 + 结构模型 + 传播仿真 + 多准则决策 + Web Demo。'],
    ['局限','成本与容量参数为相对情景值，不能解释为真实企业成本。']
  ];
  for (let i=0;i<items.length;i++) {
    const y=160+i*82;
    band(slide, ctx, 90, y, 1040, 58, '#FFFFFF');
    text(slide, ctx, 120, y+17, 120, 24, items[i][0], 18, C.orange, true);
    text(slide, ctx, 260, y+16, 820, 26, items[i][1], 20, C.navy, i<3);
  }
""",
        ),
    ]
    for i, (title, body) in enumerate(slides, start=1):
        (slides_dir / f"slide-{i:02d}.mjs").write_text(slide_module(title, body), encoding="utf-8")


def generate_slides() -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    workspace = ROOT / "outputs" / f"manual-{timestamp}-{uuid.uuid4().hex[:6]}" / ("present" + "ations") / "flightresilience"
    slides_dir = workspace / "slides"
    preview_dir = workspace / "preview"
    layout_dir = workspace / "layout"
    output_dir = workspace / "output"
    final_tmp = output_dir / "FlightResilience_presentation.pptx"
    final = SLIDES_DIR / "FlightResilience_presentation.pptx"
    write_notes(workspace)
    build_slide_modules(slides_dir)
    cmd = [
        "node",
        str(PRESENTATION_RUNTIME_DIR / "scripts" / "build_artifact_deck.mjs"),
        "--workspace",
        str(workspace),
        "--slides-dir",
        str(slides_dir),
        "--out",
        str(final_tmp),
        "--preview-dir",
        str(preview_dir),
        "--layout-dir",
        str(layout_dir),
        "--contact-sheet",
        str(preview_dir / "contact-sheet.png"),
        "--slide-count",
        "12",
    ]
    env = os.environ.copy()
    env["HOME"] = str(Path.home())
    env["USERPROFILE"] = str(Path.home())
    env["PYTHON"] = sys.executable
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_tmp, final)
    shutil.copy2(preview_dir / "contact-sheet.png", SLIDES_DIR / "contact-sheet.png")
    return final


if __name__ == "__main__":
    path = generate_slides()
    print(path)
