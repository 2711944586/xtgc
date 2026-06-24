from __future__ import annotations

import shutil

import bootstrap  # noqa: F401

from src.flightresilience.config import DEMO_DIR, FIGURES_DIR, TABLES_DIR
from src.flightresilience.visuals import generate_figures


if __name__ == "__main__":
    summary = generate_figures()
    # Copy compact tables that the Streamlit app reads directly.
    for name in [
        "airport_nodes.csv",
        "airport_edges.csv",
        "model_metrics.csv",
        "shap_summary.csv",
        "strategy_rankings.csv",
        "strategy_metrics_by_scenario.csv",
        "weight_sensitivity.csv",
    ]:
        src = TABLES_DIR / name
        if src.exists():
            shutil.copy2(src, DEMO_DIR / name)
    print(f"Exported {summary['figure_count']} figures and demo tables")

