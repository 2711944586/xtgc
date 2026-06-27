# FlightResilience 静态研究控制台

本目录是可静态部署版本，不依赖 Python 后端或 Streamlit 服务。

## 本地预览

在仓库根目录运行：

```powershell
python -m http.server 4173 -d web
```

然后访问：

```text
http://127.0.0.1:4173/
```

不要直接双击 `index.html` 预览，因为浏览器可能拦截本地 JSON `fetch`。

## 核心文件

- `index.html`：页面结构与演示模块。
- `assets/css/styles.css`：航空运行控制台风格样式。
- `assets/js/app.js`：静态数据加载、SVG/Canvas 图表绘制和控件联动。
- `assets/data/flightresilience-data.json`：由仓库预计算结果导出的静态数据。
- `assets/media/`：报告图表备份和页面图标；页面主体图表由 JSON 即时绘制。

## 重新导出数据

在根目录运行：

```powershell
python scripts/11_export_static_web_assets.py
```

该脚本会读取预计算数据目录与 `reports/tables/`，重新生成
`web/assets/data/flightresilience-data.json` 并复制核心图表到 `web/assets/media/`。

## 部署到 GitHub Pages

目标仓库为：

```text
https://github.com/2711944586/xtgc
```

推荐方式：

1. 将本项目内容推送到 `2711944586/xtgc` 仓库。
2. 保留根目录 `.github/workflows/pages.yml`。
3. 在 GitHub 仓库 Settings -> Pages 中，将 Source 设为 `GitHub Actions`。
4. 推送到 `main` 分支后，工作流会把 `web/` 作为静态站点发布。

正式访问地址：

```text
https://2711944586.github.io/xtgc/
```

新版页面已取消单独现场入口模块，答辩现场直接使用正式访问地址或本地预览地址；“自动演示”会按讲稿真实触发选择、点击和滑杆交互。

也可以手动将 `web/` 目录内容复制到 Pages 分支或其他静态托管平台。

## 答辩演示建议

建议按以下路径演示：

1. 总览：确认样本范围、航班量、机场数和主推荐策略。
2. 数据：选择 MIA 或 DEN，展示时间热力图和机场风险排名。
3. 预测：调节小时、距离和拥堵水平，说明风险输入的变化。
4. 网络：点击机场节点，说明关键性不等同于单纯航班量。
5. 仿真：切换天气冲击和四类策略，比较恢复曲线与恢复热力图。
6. 决策：调节 λ 权重，展示 dynamic_combo 和 baseline 的排名反转边界。
