from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "提交包"

IGNORED_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".playwright-mcp",
    ".git",
    ".vscode",
    "outputs",
    "tmp",
}

IGNORED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
}


def ignore_names(_dir: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(name)
        if name in IGNORED_NAMES:
            ignored.add(name)
        elif path.suffix.lower() in IGNORED_SUFFIXES:
            ignored.add(name)
        elif name.startswith("github_pages") and name.endswith("_access.png"):
            ignored.add(name)
        elif name.startswith("screen_") and name.endswith("_raw.png"):
            ignored.add(name)
        elif name.endswith(".zip") and "On_Time_Reporting" in name:
            ignored.add(name)
    return ignored


def copytree(src: Path, dst: Path, patterns: tuple[str, ...] | None = None) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    if patterns is None:
        for item in src.iterdir():
            if item.is_file() and item.name not in ignore_names(str(src), [item.name]):
                shutil.copy2(item, dst / item.name)
        return
    for pattern in patterns:
        for item in src.glob(pattern):
            if item.is_file() and item.name not in ignore_names(str(src), [item.name]):
                shutil.copy2(item, dst / item.name)


def copy_dir(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=ignore_names)


def build_demo_backup_gif() -> Path:
    frames = []
    for path in sorted((ROOT / "reports" / "screenshots").glob("screen_*.png")):
        if path.name.endswith("_raw.png"):
            continue
        img = Image.open(path).convert("RGB")
        img.thumbnail((1280, 720))
        canvas = Image.new("RGB", (1280, 720), "white")
        x = (1280 - img.width) // 2
        y = (720 - img.height) // 2
        canvas.paste(img, (x, y))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 674, 1280, 720), fill=(22, 58, 70))
        draw.text((36, 690), path.stem, fill=(255, 255, 255))
        frames.append(canvas)
    out = ROOT / "slides" / "demo_backup.gif"
    if frames:
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=1700, loop=0)
    return out


def write_division(path: Path) -> None:
    path.write_text(
        """# 小组分工说明

成员 A：系统分析与文稿负责人，负责系统边界、霍尔与切克兰德、鱼骨图与 ISM、报告前半部分和 PPT 前 4 页。

成员 B：数据与模型负责人，负责 BTS 数据获取、清洗、特征工程、EDA、预测模型、SHAP、复杂网络和 PPT 第 5-8 页。

成员 C：仿真、评价与 Demo 负责人，负责传播模型、四策略仿真、AHP/熵权/TOPSIS、风险决策、静态 Web Demo 和 PPT 第 10-13 页。

交叉复核：A 复核模型解释，B 复核仿真输入，C 复核报告、Web 和 PPT 核心数字一致性。
""",
        encoding="utf-8",
    )


def write_manifest(path: Path) -> None:
    lines = [
        "# 提交包清单",
        "",
        "本提交包由 `scripts/10_build_submission_package.py` 重新生成，已过滤 `__pycache__`、`.pytest_cache`、临时输出和大型原始 ZIP 数据。",
        "",
        "## 主文件",
        "",
        "- `01_航空网络延误传播与恢复策略_报告.pdf`",
        "- `01_航空网络延误传播与恢复策略_报告.docx`",
        "- `02_航空网络延误传播与恢复策略_PPT.pptx`",
        "- `03_讲稿.md`",
        "- `08_Demo备份动图.gif`",
        "- `09_小组分工说明.md`",
        "- `10_最终自审.md`",
        "",
        "## 目录",
        "",
        "- `04_FlightResilience_Demo/`：Streamlit 原型与运行包。",
        "- `04_FlightResilience_Static_Web/`：可 GitHub Pages 静态部署版本。",
        "- `05_核心代码/`：核心 Python 包、脚本、配置和测试。",
        "- `06_补充图表与矩阵/`：报告图表、矩阵、长表、数据审计与字典。",
        "- `07_Web截图/`：新版静态 Web 演示截图。",
        "",
        "## 复现提示",
        "",
        "1. Python 流水线：`python scripts/00_run_all.py`。",
        "2. 静态站预览：`python -m http.server 4173 -d web`。",
        "3. GitHub Pages：推送到 `2711944586/xtgc` 后使用 `.github/workflows/pages.yml` 发布 `web/`。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if PACKAGE.exists():
        shutil.rmtree(PACKAGE)
    PACKAGE.mkdir(parents=True)

    shutil.copy2(ROOT / "reports" / "report.pdf", PACKAGE / "01_航空网络延误传播与恢复策略_报告.pdf")
    shutil.copy2(ROOT / "reports" / "report.docx", PACKAGE / "01_航空网络延误传播与恢复策略_报告.docx")
    shutil.copy2(ROOT / "slides" / "FlightResilience_presentation.pptx", PACKAGE / "02_航空网络延误传播与恢复策略_PPT.pptx")
    shutil.copy2(ROOT / "slides" / "script.md", PACKAGE / "03_讲稿.md")

    demo_dir = PACKAGE / "04_FlightResilience_Demo"
    for folder in ["app", "src", "configs", "scripts"]:
        copy_dir(ROOT / folder, demo_dir / folder)
    copy_dir(ROOT / "data" / "demo", demo_dir / "data" / "demo")
    copy_dir(ROOT / "models", demo_dir / "models")
    shutil.copy2(ROOT / "requirements.txt", demo_dir / "requirements.txt")
    shutil.copy2(ROOT / "README.md", demo_dir / "README.md")

    copy_dir(ROOT / "web", PACKAGE / "04_FlightResilience_Static_Web")

    core_code = PACKAGE / "05_核心代码"
    for folder in ["src", "scripts", "configs", "tests"]:
        copy_dir(ROOT / folder, core_code / folder)
    shutil.copy2(ROOT / "requirements.txt", core_code / "requirements.txt")
    shutil.copy2(ROOT / "pytest.ini", core_code / "pytest.ini")

    supplement = PACKAGE / "06_补充图表与矩阵"
    copytree(ROOT / "reports" / "figures", supplement / "figures")
    copytree(ROOT / "reports" / "tables", supplement / "tables")
    shutil.copy2(ROOT / "data" / "data_manifest.csv", supplement / "data_manifest.csv")
    shutil.copy2(ROOT / "data" / "data_dictionary.csv", supplement / "data_dictionary.csv")
    shutil.copy2(ROOT / "data" / "data_audit.json", supplement / "data_audit.json")

    screenshots = PACKAGE / "07_Web截图"
    copytree(ROOT / "reports" / "screenshots", screenshots)

    gif = build_demo_backup_gif()
    shutil.copy2(gif, PACKAGE / "08_Demo备份动图.gif")

    write_division(PACKAGE / "09_小组分工说明.md")
    audit = ROOT / "docs" / "FINAL_SELF_AUDIT.md"
    if audit.exists():
        shutil.copy2(audit, PACKAGE / "10_最终自审.md")
    write_manifest(PACKAGE / "提交包清单.md")
    write_manifest(ROOT / "提交包清单.md")
    print(PACKAGE)


if __name__ == "__main__":
    main()
