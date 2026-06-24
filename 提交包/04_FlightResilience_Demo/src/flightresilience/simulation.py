from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .config import DEMO_DIR, PROCESSED_DIR, TABLES_DIR, ensure_dirs, load_yaml
from .utils import minmax, write_json


@dataclass(frozen=True)
class PropagationModel:
    airports: list[str]
    A: np.ndarray
    baseline: np.ndarray
    hourly: pd.DataFrame
    validation: dict[str, float]


def build_hourly_state() -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED_DIR / "flights_scored.parquet")
    completed = df[df["is_completed"] == 1].copy()
    completed["hour"] = completed["scheduled_datetime"].dt.floor("h")
    airports = sorted(pd.read_csv(TABLES_DIR / "airport_nodes.csv")["airport"].tolist())
    full_hours = pd.date_range(completed["hour"].min(), completed["hour"].max(), freq="h")
    idx = pd.MultiIndex.from_product([full_hours, airports], names=["hour", "airport"])
    hourly = (
        completed.groupby(["hour", "Origin"], as_index=True)
        .agg(
            avg_delay=("ArrDelayMinutes", "mean"),
            delay_rate=("ArrDel15", "mean"),
            flights=("ArrDel15", "size"),
            avg_risk=("delay_risk", "mean"),
        )
        .rename_axis(index={"Origin": "airport"})
        .reindex(idx)
        .reset_index()
    )
    hourly["avg_delay"] = hourly["avg_delay"].fillna(0)
    hourly["delay_rate"] = hourly["delay_rate"].fillna(0)
    hourly["flights"] = hourly["flights"].fillna(0).astype(int)
    hourly["avg_risk"] = hourly["avg_risk"].fillna(hourly["avg_risk"].mean())
    hourly.to_parquet(PROCESSED_DIR / "airport_hourly.parquet", index=False)
    return hourly


def estimate_propagation_matrix() -> PropagationModel:
    ensure_dirs()
    hourly = build_hourly_state()
    nodes = pd.read_csv(TABLES_DIR / "airport_nodes.csv").sort_values("airport")
    edges = pd.read_csv(TABLES_DIR / "airport_edges.csv")
    airports = nodes["airport"].tolist()
    pivot = hourly.pivot(index="hour", columns="airport", values="avg_delay").fillna(0)
    pivot = pivot[airports]
    X_all = pivot.iloc[:-1].to_numpy()
    Y_all = pivot.iloc[1:].to_numpy()

    edge_set = {(r.Origin, r.Dest) for r in edges.itertuples(index=False)}
    A = np.zeros((len(airports), len(airports)))
    preds = np.zeros_like(Y_all)
    for j, dest in enumerate(airports):
        allowed = [i for i, origin in enumerate(airports) if origin == dest or (origin, dest) in edge_set]
        model = Ridge(alpha=12.0, fit_intercept=True)
        model.fit(X_all[:, allowed], Y_all[:, j])
        coef = np.maximum(model.coef_, 0)
        A[j, allowed] = coef
        preds[:, j] = model.predict(X_all[:, allowed])

    # Scale to a stable system. This preserves relative propagation strengths.
    eig = np.linalg.eigvals(A)
    radius = float(np.max(np.abs(eig))) if len(eig) else 0.0
    scale_factor = 1.0
    if radius >= 0.92:
        scale_factor = 0.92 / radius
        A *= scale_factor
        preds = X_all @ A.T

    validation = {
        "mae": float(mean_absolute_error(Y_all.ravel(), preds.ravel())),
        "rmse": float(math.sqrt(mean_squared_error(Y_all.ravel(), preds.ravel()))),
        "spectral_radius_raw": radius,
        "stability_scale_factor": scale_factor,
        "spectral_radius_final": float(np.max(np.abs(np.linalg.eigvals(A)))) if A.size else 0.0,
        "baseline_hold_mae": float(mean_absolute_error(Y_all.ravel(), X_all.ravel())),
    }
    baseline = pivot.quantile(0.50).to_numpy()
    pd.DataFrame(A, index=airports, columns=airports).to_csv(TABLES_DIR / "propagation_matrix_A.csv", encoding="utf-8-sig")
    hourly.to_parquet(DEMO_DIR / "airport_hourly.parquet", index=False)
    write_json(TABLES_DIR / "propagation_validation.json", validation)
    write_json(DEMO_DIR / "propagation_validation.json", validation)
    return PropagationModel(airports=airports, A=A, baseline=baseline, hourly=hourly, validation=validation)


def _scenario_vector(model: PropagationModel, scenario_name: str, shock_airport: str) -> tuple[np.ndarray, dict]:
    scenarios = load_yaml("scenarios.yaml")["scenarios"]
    params = scenarios[scenario_name]
    nodes = pd.read_csv(TABLES_DIR / "airport_nodes.csv").set_index("airport")
    airport_idx = {a: i for i, a in enumerate(model.airports)}
    shock = np.zeros(len(model.airports))
    idx = airport_idx[shock_airport]
    base = max(18.0, float(nodes.loc[shock_airport, "avg_delay"]) * 1.4)
    shock[idx] = base * float(params["shock_multiplier"])
    if scenario_name == "weather":
        # Weather shocks are spatially clustered through high-volume neighbors.
        edges = pd.read_csv(TABLES_DIR / "airport_edges.csv")
        downstream = (
            edges[edges["Origin"] == shock_airport]
            .sort_values("flights", ascending=False)
            .head(3)["Dest"]
            .tolist()
        )
        for airport in downstream:
            if airport in airport_idx:
                shock[airport_idx[airport]] += base * 0.45
    return shock, params


def simulate_strategy(
    model: PropagationModel,
    scenario_name: str,
    strategy_name: str,
    shock_airport: str,
    horizon: int = 24,
) -> tuple[pd.DataFrame, dict]:
    strategies = load_yaml("strategies.yaml")["strategies"]
    strategy = strategies[strategy_name]
    shock, scenario = _scenario_vector(model, scenario_name, shock_airport)
    nodes = pd.read_csv(TABLES_DIR / "airport_nodes.csv").sort_values("airport").set_index("airport")
    centrality = minmax(nodes.loc[model.airports, "criticality"]).to_numpy()
    risk = minmax(nodes.loc[model.airports, "avg_risk"]).to_numpy()

    x = model.baseline.copy()
    rows = []
    total_resource = float(strategy.get("resource_budget", 0.0)) * 36.0
    buffer_minutes = float(strategy.get("buffer_minutes", 0.0))
    for t in range(horizon):
        w = shock if t < int(scenario["duration_hours"]) else np.zeros_like(shock)
        raw_next = model.A @ x + w
        control = np.zeros_like(x)
        cost = 0.0

        if strategy_name == "uniform_buffer":
            # Buffer is spread across the whole network. It is robust and easy
            # to explain, but resource is diluted when many airports are active.
            control += min(buffer_minutes * 0.16, total_resource / len(x))
            cost += total_resource * 1.10 + buffer_minutes * len(x) * 0.18
        elif strategy_name == "hub_priority":
            k = int(strategy.get("priority_airports", 3))
            selected = np.argsort(-centrality)[:k]
            if len(selected):
                control[selected] += total_resource / len(selected)
                cost += total_resource * 1.15
        elif strategy_name == "dynamic_combo":
            downstream = minmax(pd.Series(model.A.sum(axis=0))).to_numpy()
            state = minmax(pd.Series(x)).to_numpy()
            priority = (
                float(strategy.get("risk_weight", 0.30)) * risk
                + float(strategy.get("centrality_weight", 0.30)) * centrality
                + float(strategy.get("state_weight", 0.30)) * state
                + float(strategy.get("downstream_weight", 0.10)) * downstream
            )
            weights = priority / priority.sum() if priority.sum() > 0 else np.ones_like(priority) / len(priority)
            control += total_resource * weights
            # Dynamic dispatch needs more coordination, but uses the same
            # recovery budget with less dilution than a uniform buffer.
            cost += total_resource * 1.28 + float(strategy.get("complexity", 4)) * 0.7

        x = np.maximum(0, raw_next - control)
        total_delay = float(x.sum())
        performance = max(0.0, 1.0 - total_delay / 850.0)
        rows.append(
            {
                "hour": t + 1,
                "scenario": scenario_name,
                "strategy": strategy_name,
                "shock_airport": shock_airport,
                "total_delay": total_delay,
                "avg_delay": float(x.mean()),
                "performance": performance,
                "spread_range": int((x > 15).sum()),
                "cost": cost,
                **{f"state_{a}": float(x[i]) for i, a in enumerate(model.airports)},
            }
        )

    traj = pd.DataFrame(rows)
    baseline_performance = 0.95
    recovered = traj[traj["performance"] >= baseline_performance]
    recovery_time = int(recovered["hour"].iloc[0]) if len(recovered) else horizon + 1
    peak_total_delay = float(traj["total_delay"].max())
    cumulative_delay = float(traj["total_delay"].sum())
    affected = int(traj["spread_range"].max())
    loss_area = float((1 - traj["performance"]).sum())
    cancel_proxy = max(0.0, (peak_total_delay - 220.0) / 65.0)
    metrics = {
        "scenario": scenario_name,
        "strategy": strategy_name,
        "shock_airport": shock_airport,
        "cumulative_delay": cumulative_delay,
        "avg_delay": float(traj["avg_delay"].mean()),
        "recovery_time": recovery_time,
        "min_performance": float(traj["performance"].min()),
        "loss_area": loss_area,
        "spread_range": affected,
        "delay_flight_ratio": float(min(1.0, cumulative_delay / (horizon * len(model.airports) * 35.0))),
        "cancel_proxy": float(cancel_proxy),
        "strategy_cost": float(traj["cost"].sum()),
        "complexity": float(strategy.get("complexity", 1)),
    }
    return traj, metrics


def run_all_simulations() -> dict:
    model = estimate_propagation_matrix()
    nodes = pd.read_csv(TABLES_DIR / "airport_nodes.csv")
    shock_airport = str(nodes.sort_values("criticality", ascending=False).iloc[0]["airport"])
    scenarios = list(load_yaml("scenarios.yaml")["scenarios"].keys())
    strategies = list(load_yaml("strategies.yaml")["strategies"].keys())
    trajectories = []
    metrics = []
    for scenario, strategy in [(s, t) for s in scenarios for t in strategies]:
        traj, met = simulate_strategy(model, scenario, strategy, shock_airport)
        trajectories.append(traj)
        metrics.append(met)
    trajectory_df = pd.concat(trajectories, ignore_index=True)
    metrics_df = pd.DataFrame(metrics)
    trajectory_df.to_parquet(PROCESSED_DIR / "scenario_trajectories.parquet", index=False)
    metrics_df.to_csv(TABLES_DIR / "strategy_metrics_by_scenario.csv", index=False, encoding="utf-8-sig")
    trajectory_df.to_parquet(DEMO_DIR / "scenario_results.parquet", index=False)
    metrics_df.to_csv(DEMO_DIR / "strategy_metrics_by_scenario.csv", index=False, encoding="utf-8-sig")
    return {
        "shock_airport": shock_airport,
        "validation": model.validation,
        "trajectory_rows": len(trajectory_df),
        "metric_rows": len(metrics_df),
    }
