from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
DATA_DIR = WEB_DIR / "assets" / "data"
MEDIA_DIR = WEB_DIR / "assets" / "media"
DEMO_DIR = ROOT / "data" / "demo"
TABLE_DIR = ROOT / "reports" / "tables"
FIGURE_DIR = ROOT / "reports" / "figures"


def records_from_csv(path: Path) -> list[dict[str, Any]]:
    return clean_records(pd.read_csv(path))


def records_from_parquet(path: Path) -> list[dict[str, Any]]:
    return clean_records(pd.read_parquet(path))


def clean_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        elif out[col].dtype == "object":
            out[col] = out[col].map(lambda x: x.isoformat() if hasattr(x, "isoformat") else x)
    out = out.where(pd.notnull(out), None)
    return out.to_dict(orient="records")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def round_float(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {k: round_float(v) for k, v in value.items()}
    if isinstance(value, list):
        return [round_float(v) for v in value]
    return value


def copy_media() -> list[str]:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    selected = [
        "fig_12_route_risk_bubble.png",
        "fig_16_roc_pr_curves.png",
        "fig_20_airport_network.png",
        "fig_25_ism_hierarchy.png",
        "fig_26_airport_role_quadrant.png",
        "fig_28_recovery_heatmap.png",
        "fig_29_recovery_curves.png",
        "fig_33_strategy_radar.png",
        "fig_34_topsis_score.png",
        "fig_36_indicator_weights.png",
        "fig_37_weight_sensitivity.png",
        "fig_38_risk_vs_topsis.png",
    ]
    copied: list[str] = []
    for name in selected:
        src = FIGURE_DIR / name
        if src.exists():
            shutil.copy2(src, MEDIA_DIR / name)
            copied.append(f"assets/media/{name}")
    return copied


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    audit = read_json(ROOT / "data" / "data_audit.json")
    airport_count = len(audit.get("top_airports", []))

    payload: dict[str, Any] = {
        "meta": {
            "snapshot_time": datetime.now(timezone.utc).isoformat(),
            "source": "U.S. DOT BTS TranStats, 2024-01 to 2024-03",
            "scope": f"Top {airport_count} airports by traffic in the selected sample",
            "scope_note": "Values come from project tables and demo data files.",
        },
        "audit": audit,
        "kpi": read_json(DEMO_DIR / "kpi_summary.json"),
        "decision": read_json(DEMO_DIR / "decision_summary.json"),
        "modelSummary": read_json(DEMO_DIR / "model_metrics.json"),
        "predictionOptions": read_json(DEMO_DIR / "prediction_options.json"),
        "networkNodes": read_json(DEMO_DIR / "network_nodes.json"),
        "networkEdges": read_json(DEMO_DIR / "network_edges.json"),
        "ism": read_json(DEMO_DIR / "ism.json"),
        "propagationValidation": read_json(DEMO_DIR / "propagation_validation.json"),
        "dashboardDaily": records_from_parquet(DEMO_DIR / "dashboard_daily.parquet"),
        "dashboardHeatmap": records_from_parquet(DEMO_DIR / "dashboard_heatmap.parquet"),
        "dashboardAirports": records_from_parquet(DEMO_DIR / "dashboard_airports.parquet"),
        "routeOptions": records_from_parquet(DEMO_DIR / "route_options.parquet"),
        "scenarioResults": records_from_parquet(DEMO_DIR / "scenario_results.parquet"),
        "strategyMetrics": records_from_csv(DEMO_DIR / "strategy_metrics_by_scenario.csv"),
        "strategyRankings": records_from_csv(DEMO_DIR / "strategy_rankings.csv"),
        "weightSensitivity": records_from_csv(DEMO_DIR / "weight_sensitivity.csv"),
        "riskDecision": records_from_csv(DEMO_DIR / "risk_decision.csv"),
        "uncertaintyDecision": records_from_csv(DEMO_DIR / "uncertainty_decision.csv"),
        "indicatorWeights": records_from_csv(DEMO_DIR / "indicator_weights.csv"),
        "fuzzyEvaluation": records_from_csv(DEMO_DIR / "fuzzy_evaluation.csv"),
        "modelMetrics": records_from_csv(DEMO_DIR / "model_metrics.csv"),
        "shapSummary": records_from_csv(DEMO_DIR / "shap_summary.csv"),
        "airportNodes": records_from_csv(DEMO_DIR / "airport_nodes.csv"),
        "airportEdges": records_from_csv(DEMO_DIR / "airport_edges.csv"),
        "ahpJudgment": records_from_csv(TABLE_DIR / "ahp_judgment_matrix.csv"),
        "lossMatrix": records_from_csv(TABLE_DIR / "loss_matrix.csv"),
        "topsisByScenario": records_from_csv(TABLE_DIR / "topsis_by_scenario.csv"),
        "media": copy_media(),
    }

    out = DATA_DIR / "flightresilience-data.json"
    out.write_text(
        json.dumps(round_float(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
