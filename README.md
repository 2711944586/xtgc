# FlightResilience

FlightResilience 是一个系统工程课程项目，研究航空网络中局部延误如何传播，以及在有限恢复资源下如何选择恢复策略。项目使用 U.S. DOT BTS 航班准点公开数据，把延误预测、复杂网络、ISM 结构分析、状态空间仿真和多准则评价连接为一条可复现、可汇报、可静态部署的证据链。

## 研究范围

- 数据来源：U.S. DOT BTS Airline On-Time Performance 月度公开文件。
- 样本范围：2024-01 至 2024-03。
- 空间范围：样本内总流量前 30 个机场，形成 610,640 条航班记录与 824 条有向航线。
- 预测目标：`ArrDel15`，即到达延误是否达到 15 分钟。
- 策略比较：`baseline`、`uniform_buffer`、`hub_priority`、`dynamic_combo`。
- 主结论：恢复/韧性优先偏好下推荐 `dynamic_combo`；成本或风险极端保守条件下 `baseline` 可能反超。

## 方法链路

```text
BTS 真实数据
  -> 数据审计与防泄漏时间切分
  -> 计划阶段延误风险预测
  -> 机场有向加权网络与关键节点识别
  -> 鱼骨图与 ISM 结构解释
  -> 状态空间延误传播仿真
  -> AHP/熵权/TOPSIS/模糊评价/风险决策
  -> 静态 Web Demo 与答辩材料
```

## 目录结构

```text
app/                         Streamlit 原型 Demo
configs/                     情景与策略参数
data/demo/                   Demo 和静态站使用的轻量数据
data/processed/              处理后的中间数据
models/                      训练后的模型和特征规格
reports/                     报告、图表、矩阵、截图
scripts/                     全流程脚本
slides/                      PPT、讲稿、contact sheet
src/flightresilience/        核心 Python 包
tests/                       单元测试
web/                         可静态部署 Web Demo
提交包/                      课程提交包
```

## 环境安装

```powershell
python -m pip install -r requirements.txt
```

可选 Conda 环境：

```powershell
conda env create -f environment.yml
conda activate flightresilience
```

## 一键流水线

```powershell
python scripts/00_run_all.py
```

单步运行：

```powershell
python scripts/01_prepare_data.py
python scripts/02_train_model.py
python scripts/03_build_network.py
python scripts/04_fit_propagation.py
python scripts/05_run_simulation.py
python scripts/06_rank_strategies.py
python scripts/07_export_demo_assets.py
python scripts/08_generate_report.py
python scripts/09_generate_slides.py
python scripts/11_export_static_web_assets.py
```

## 主要输出

- 报告：`reports/report.docx`、`reports/report.pdf`
- PPT：`slides/FlightResilience_presentation.pptx`
- 讲稿：`slides/script.md`
- 静态 Web：`web/index.html`
- 静态数据：`web/assets/data/flightresilience-data.json`
- 图表：`reports/figures/`
- 矩阵与表：`reports/tables/`
- 提交包：`提交包/`

## Web Demo

本地预览静态站：

```powershell
python -m http.server 4173 -d web
```

访问：

```text
http://127.0.0.1:4173/
```

静态站包含总览、交互证据图板、数据驾驶舱、风险预测、机场网络、扰动仿真、综合决策和方法说明。页面只读取本地 JSON，不依赖后端；核心图表由 SVG/Canvas 即时绘制，支持悬停查看和点击联动。
正式发布地址为：

```text
https://2711944586.github.io/xtgc/
```

页面内已加入现场扫码入口，二维码文件为 `web/assets/media/github-pages-qr.svg`。

## GitHub Pages 部署

目标仓库：

```text
https://github.com/2711944586/xtgc
```

部署配置：

1. 本仓库推送到 `2711944586/xtgc` 的 `main` 分支。
2. `.github/workflows/pages.yml` 会把 `web/` 目录打包为 Pages artifact。
3. GitHub 仓库 Settings -> Pages 的 Source 使用 `GitHub Actions`。
4. 发布完成后访问 `https://2711944586.github.io/xtgc/`，或扫描页面内二维码。

## Streamlit 原型

```powershell
streamlit run app/Home.py
```

Streamlit 版本用于本地探索；正式静态部署请使用 `web/`。

## 测试与验证

```powershell
python -m pytest -q
python -m compileall src app scripts tests
node --check web/assets/js/app.js
```

静态站截图验证可使用：

```powershell
npx playwright screenshot --viewport-size=1440,1100 http://127.0.0.1:4173/ reports/screenshots/static_web_desktop.png
```

## 结论边界

- 所有预测特征遵循计划阶段可获得原则，禁止使用实际延误和延误原因字段。
- SHAP、ISM、传播矩阵和仿真结果用于结构解释与关联推断，不表述为严格因果。
- 成本、容量下降和恢复资源属于透明的相对情景设定，不代表真实企业成本。
- `dynamic_combo` 是恢复/韧性优先偏好下的推荐，不是无条件最优。

## 提交包生成

```powershell
python scripts/10_build_submission_package.py
```

生成后检查 `提交包清单.md`，确认报告、PPT、讲稿、静态 Web、核心代码、补充图表矩阵和截图均已包含。
