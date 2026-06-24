from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTERNAL_DIR = DATA_DIR / "external"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_DIR = DATA_DIR / "features"
DEMO_DIR = DATA_DIR / "demo"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
SLIDES_DIR = ROOT / "slides"
CONFIG_DIR = ROOT / "configs"


def ensure_dirs() -> None:
    for path in [
        DATA_DIR,
        RAW_DIR,
        EXTERNAL_DIR,
        INTERIM_DIR,
        PROCESSED_DIR,
        FEATURES_DIR,
        DEMO_DIR,
        MODELS_DIR,
        REPORTS_DIR,
        FIGURES_DIR,
        TABLES_DIR,
        SCREENSHOTS_DIR,
        SLIDES_DIR,
        ROOT / "notebooks",
        ROOT / "tests",
        ROOT / "app" / "pages",
        ROOT / "app" / "assets",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def load_yaml(name: str) -> dict[str, Any]:
    with (CONFIG_DIR / name).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_base_config() -> dict[str, Any]:
    return load_yaml("base.yaml")

