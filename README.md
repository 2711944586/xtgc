# FlightResilience 航空网络延误传播与恢复策略

FlightResilience 是一个系统工程课程项目，用 U.S. DOT BTS 航班准点公开数据研究“局部延误如何在航空网络中传播，以及有限恢复资源下应如何选择恢复策略”。项目不是单独做延误分类模型，而是把数据审计、计划阶段风险预测、机场复杂网络、ISM 结构解释、状态空间传播仿真、多准则评价和静态 Web Demo 组织成一条可复现的证据链。

正式静态演示地址：

```text
https://2711944586.github.io/xtgc/
```

## 一句话结论

在恢复效率和网络韧性优先的偏好下，`dynamic_combo`（动态组合）综合表现最好；但在成本极端保守、风险规避或概率未知的决策口径下，`baseline`（基准策略）可能反超。因此最终建议采用“条件式推荐”，而不是宣称某个策略无条件最优。

## 最终交付物

所有正式提交材料集中在 `提交包/`，这是课程提交时优先查看的目录。

| 路径 | 用途 |
|---|---|
| `提交包/01_航空网络延误传播与恢复策略_报告.docx` | 正式 Word 报告，包含系统工程方法链、图文解释、公式、表格、Web 截图和结论边界。 |
| `提交包/01_航空网络延误传播与恢复策略_报告.pdf` | 与 Word 同步导出的 PDF 版报告，用于稳定阅读和提交。 |
| `提交包/02_航空网络延误传播与恢复策略_PPT.pptx` | 13 页答辩 PPT，包含封面、目录、问题界定、方法链、数据、预测、网络、仿真、Web Demo、决策和总结。 |
| `提交包/03_讲稿.md` | 逐页讲稿，主稿约 7 分 35 秒，含过渡句和可删减句。 |
| `提交包/04_FlightResilience_Static_Web/` | 可直接静态部署的 Web Demo，和线上 GitHub Pages 内容一致。 |
| `提交包/04_FlightResilience_Demo/` | Streamlit 本地原型运行包，适合继续探索和开发。 |
| `提交包/05_核心代码/` | 复现数据处理、模型、网络、仿真、评价和导出的核心代码。 |
| `提交包/06_补充图表与矩阵/` | 所有补充图表、ISM/AHP/传播矩阵、策略表、数据字典和审计文件。 |
| `提交包/07_Web截图/` | 最新静态 Web 的桌面、移动和模块截图，供报告/PPT/复核使用。 |
| `提交包/08_Demo备份动图.gif` | Web Demo 备用动图，按 7 个模块快速轮播。 |
| `提交包/09_小组分工说明.md` | 小组成员职责划分。 |
| `提交包/10_最终自审.md` | 最终验收记录、测试结果和限制说明。 |

根目录的 `提交包清单.md` 是提交包的简版索引；本 README 是完整项目地图。

## 项目结构

```text
app/                         Streamlit 原型页面，不作为线上部署入口
configs/                     情景、策略和基础参数配置
data/                        数据审计文件、数据字典和轻量 Demo 数据
docs/                        项目记忆、自审记录、系统工程课程 PDF 文本摘录
models/                      模型摘要；joblib 模型文件本地保留，不强制提交
reports/                     报告中间产物、图表、矩阵、Web 截图、LaTeX 草稿
scripts/                     从数据到提交包的全部流水线脚本
slides/                      PPT、讲稿、contact sheet、Demo GIF
src/flightresilience/        核心 Python 包
tests/                       单元测试
web/                         GitHub Pages 静态站源码
提交包/                      最终课程提交包
```

### 目录使用原则

- `web/` 是线上静态部署的唯一来源；不要手工改 `提交包/04_FlightResilience_Static_Web/`，应先改 `web/` 再重新生成提交包。
- `reports/figures/` 与 `reports/tables/` 是报告、PPT、Web 共用的证据资产。
- `reports/screenshots/` 是由 `scripts/13_capture_web_screenshots.py` 生成的最新版 Web 截图，报告、PPT 和 GIF 会同步使用。
- `slides/script.md` 是正式讲稿源文件，提交包中的 `03_讲稿.md` 从这里复制。
- `output/`、`outputs/`、`tmp/`、`.pytest_cache/` 是临时渲染和调试目录，已加入忽略规则，清理后不应出现在提交状态中。

## 方法链路

```text
BTS 公开航班数据
  -> 数据审计与时间切分
  -> 计划阶段延误风险预测
  -> 机场有向加权网络与关键节点识别
  -> 鱼骨图与 ISM 结构解释
  -> 状态空间延误传播仿真
  -> AHP / 熵权 / TOPSIS / 模糊评价 / 风险与不确定决策
  -> Word 报告 / PPT / 讲稿 / Web Demo / 提交包
```

课程 PDF 中使用到的系统工程方法包括：霍尔三维结构、切克兰德软系统方法、解释结构模型化技术（ISM）、状态空间模型、AHP（层次分析法）、模糊综合评价、风险型决策和不确定型决策。文本摘录位于 `docs/system_engineering_reference/chapter*.txt`，正式报告中已将这些方法映射到项目环节。课程 PDF 原件如需本地保留，放在 `docs/system_engineering_reference/source_pdfs/`；该目录为本地参考材料，不提交远程。

## 环境准备

Python 依赖：

```powershell
python -m pip install -r requirements.txt
```

可选 Conda 环境：

```powershell
conda env create -f environment.yml
conda activate flightresilience
```

PPT 和 Web 截图需要 Node.js / npx：

```powershell
node --version
npx --version
```

Word/PDF 报告的目录刷新和 PDF 导出在 Windows 上使用 Word COM。如果没有 Word，仍可生成 DOCX，但 PDF 导出和目录页码刷新需要在有 Word 的机器上执行。

## 一键复现

完整流水线：

```powershell
python scripts/00_run_all.py
```

这会依次完成数据、模型、图表、静态 Web 数据、Web 截图、升级版 Word/PDF、PPT、讲稿和提交包生成。最终检查 `提交包/` 即可。

## 单步脚本说明

| 脚本 | 作用 |
|---|---|
| `scripts/01_prepare_data.py` | 读取并清洗 BTS 数据，输出审计、字典、训练/验证/测试切分和 Demo 数据。 |
| `scripts/02_train_model.py` | 训练计划阶段延误预测模型，输出模型指标、SHAP 相关表和模型摘要。 |
| `scripts/03_build_network.py` | 构建机场有向加权网络，计算关键性、中心性和网络摘要。 |
| `scripts/04_fit_propagation.py` | 估计带网络掩码的状态空间传播矩阵。 |
| `scripts/05_run_simulation.py` | 运行正常、高峰、天气、枢纽容量下降等情景仿真。 |
| `scripts/06_rank_strategies.py` | 计算 AHP/熵权/TOPSIS、模糊评价、风险型与不确定型决策结果。 |
| `scripts/07_export_demo_assets.py` | 生成报告图表并同步 Streamlit Demo 所需表格。 |
| `scripts/11_export_static_web_assets.py` | 将预计算数据打包为 `web/assets/data/flightresilience-data.json`。 |
| `scripts/13_capture_web_screenshots.py` | 临时启动本地静态站，用 Playwright 截取最新版 Web 截图。 |
| `scripts/12_upgrade_word_report.py` | 生成升级版 Word 报告，并同步导出 PDF。 |
| `scripts/09_generate_slides.py` | 使用 artifact-tool 生成 13 页 PPT 和 contact sheet。 |
| `scripts/14_update_presentation_script.py` | 生成约 7 分 30 秒的逐页讲稿。 |
| `scripts/10_build_submission_package.py` | 重建 `提交包/`，复制最终交付物、Web、核心代码、图表矩阵、截图和 GIF。 |

`scripts/08_generate_report.py` 保留为早期基础报告生成入口；最终提交以 `scripts/12_upgrade_word_report.py` 的升级版 Word/PDF 为准。

## Web Demo

本地预览：

```powershell
python -m http.server 4173 -d web
```

访问：

```text
http://127.0.0.1:4173/
```

Web Demo 不依赖后端，只读取 `web/assets/data/flightresilience-data.json`。自动演示会按讲稿真实触发控件：点击航线气泡、切换机场、拖动风险滑杆、点击网络节点、切换情景/策略/冲击机场、拖动 lambda 权重并点击风险-TOPSIS 点。

## GitHub Pages 部署

目标仓库：

```text
https://github.com/2711944586/xtgc
```

部署方式：

1. 推送 `main` 分支。
2. `.github/workflows/pages.yml` 会将 `web/` 作为 Pages artifact 发布。
3. GitHub 仓库 Settings -> Pages 的 Source 使用 `GitHub Actions`。
4. 发布后访问 `https://2711944586.github.io/xtgc/`。

## 测试与验收

建议提交前运行：

```powershell
python -m pytest -q
python -m compileall src app scripts tests
node --check web/assets/js/app.js
python scripts/13_capture_web_screenshots.py
python scripts/12_upgrade_word_report.py
python scripts/09_generate_slides.py
python scripts/14_update_presentation_script.py
python scripts/10_build_submission_package.py
```

交付前检查：

- `提交包/01_...docx` 与 `提交包/01_...pdf` 时间一致。
- `提交包/02_...pptx` 为 13 页，`slides/contact-sheet.png` 能快速看出完整叙事。
- `提交包/03_讲稿.md` 顶部写明约 7 分 30 秒。
- `提交包/04_FlightResilience_Static_Web/index.html` 能本地打开并加载 JSON。
- `提交包/07_Web截图/` 包含 `screen_01_home.png` 到 `screen_07_method.png` 以及桌面、移动、全页截图。
- `git status --short` 中不应出现 `tmp/`、`output/`、`outputs/`、`.pytest_cache/` 等临时目录。

## 结论边界

- 预测特征遵循计划阶段可获得原则，不使用实际延误分钟数、实际起降时间和延误原因字段。
- ISM、SHAP、传播矩阵和仿真结果用于结构解释与策略比较，不宣称为严格因果证明。
- 成本、容量下降和恢复资源是透明的相对情景参数，不代表真实航空公司成本。
- `dynamic_combo` 是恢复/韧性优先偏好下的推荐；成本极端保守或风险规避时，`baseline` 可能更稳妥。
