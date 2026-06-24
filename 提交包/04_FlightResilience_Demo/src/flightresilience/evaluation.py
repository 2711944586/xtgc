from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DEMO_DIR, TABLES_DIR, ensure_dirs, load_yaml
from .utils import write_json


INDICATORS = [
    ("cumulative_delay", "运行效率", "累计总延误", "cost"),
    ("avg_delay", "运行效率", "平均延误", "cost"),
    ("recovery_time", "运行效率", "恢复时间", "cost"),
    ("min_performance", "网络韧性", "最低性能", "benefit"),
    ("loss_area", "网络韧性", "恢复损失面积", "cost"),
    ("spread_range", "网络韧性", "传播范围", "cost"),
    ("delay_flight_ratio", "航班影响", "延误航班比例", "cost"),
    ("cancel_proxy", "航班影响", "取消代理数量", "cost"),
    ("strategy_cost", "经济性", "相对策略成本", "cost"),
    ("complexity", "可实施性", "策略复杂度", "cost"),
]


def ahp_weights() -> tuple[pd.DataFrame, dict]:
    # Group decision judgment matrix. Order follows INDICATORS.
    # The values intentionally emphasize recovery and network resilience while
    # keeping cost and implementability visible.
    n = len(INDICATORS)
    priority = np.array([8, 6, 7, 7, 6, 5, 5, 3, 4, 3], dtype=float)
    matrix = priority[:, None] / priority[None, :]
    geom = np.prod(matrix, axis=1) ** (1 / n)
    w = geom / geom.sum()
    eig_max = float(np.mean((matrix @ w) / w))
    ci = (eig_max - n) / (n - 1)
    ri_table = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    cr = ci / ri_table[n]
    weights = pd.DataFrame(
        {
            "indicator": [i[0] for i in INDICATORS],
            "criterion": [i[1] for i in INDICATORS],
            "label": [i[2] for i in INDICATORS],
            "type": [i[3] for i in INDICATORS],
            "ahp_weight": w,
        }
    )
    matrix_df = pd.DataFrame(matrix, index=weights["indicator"], columns=weights["indicator"])
    matrix_df.to_csv(TABLES_DIR / "ahp_judgment_matrix.csv", encoding="utf-8-sig")
    return weights, {"lambda_max": eig_max, "ci": float(ci), "cr": float(cr)}


def entropy_weights(data: pd.DataFrame, indicators: list[str]) -> np.ndarray:
    X = data[indicators].astype(float).copy()
    for indicator, _, _, typ in INDICATORS:
        if indicator not in X.columns:
            continue
        col = X[indicator]
        if typ == "cost":
            X[indicator] = col.max() - col
        else:
            X[indicator] = col - col.min()
    X = X - X.min(axis=0) + 1e-9
    P = X / X.sum(axis=0)
    k = 1 / np.log(len(X))
    entropy = -k * (P * np.log(P)).sum(axis=0)
    d = 1 - entropy
    if np.isclose(d.sum(), 0):
        return np.ones(len(indicators)) / len(indicators)
    return (d / d.sum()).to_numpy()


def topsis(data: pd.DataFrame, weights: np.ndarray, indicators: list[str]) -> pd.Series:
    X = data[indicators].astype(float).copy()
    for indicator, _, _, typ in INDICATORS:
        if indicator not in X.columns:
            continue
        if typ == "cost":
            X[indicator] = X[indicator].max() - X[indicator]
    denom = np.sqrt((X**2).sum(axis=0)).replace(0, 1)
    Z = (X / denom) * weights
    ideal_pos = Z.max(axis=0)
    ideal_neg = Z.min(axis=0)
    d_pos = np.sqrt(((Z - ideal_pos) ** 2).sum(axis=1))
    d_neg = np.sqrt(((Z - ideal_neg) ** 2).sum(axis=1))
    return d_neg / (d_pos + d_neg + 1e-12)


def fuzzy_grade(score: float) -> dict[str, float]:
    centers = {"优秀": 0.90, "良好": 0.70, "一般": 0.50, "较差": 0.30}
    raw = {k: max(0.0, 1 - abs(score - c) / 0.22) for k, c in centers.items()}
    s = sum(raw.values()) or 1
    return {k: v / s for k, v in raw.items()}


def uncertain_decision(loss: pd.DataFrame) -> pd.DataFrame:
    rows = []
    strategies = loss.index.tolist()
    scenarios = loss.columns.tolist()
    regrets = loss - loss.min(axis=0)
    hurwicz_alpha = 0.6
    rows.append({"criterion": "乐观准则", "recommended_strategy": loss.min(axis=1).idxmin(), "value": float(loss.min(axis=1).min())})
    rows.append({"criterion": "悲观准则", "recommended_strategy": loss.max(axis=1).idxmin(), "value": float(loss.max(axis=1).min())})
    rows.append({"criterion": "Laplace 等概率准则", "recommended_strategy": loss.mean(axis=1).idxmin(), "value": float(loss.mean(axis=1).min())})
    rows.append({"criterion": "最小最大后悔值准则", "recommended_strategy": regrets.max(axis=1).idxmin(), "value": float(regrets.max(axis=1).min())})
    hurwicz = hurwicz_alpha * loss.min(axis=1) + (1 - hurwicz_alpha) * loss.max(axis=1)
    rows.append({"criterion": "Hurwicz 折中准则", "recommended_strategy": hurwicz.idxmin(), "value": float(hurwicz.min())})
    return pd.DataFrame(rows)


def _score_with_lambda(metrics: pd.DataFrame, ahp_df: pd.DataFrame, entropy: np.ndarray, lam: float) -> pd.DataFrame:
    indicators = [i[0] for i in INDICATORS]
    combined = lam * ahp_df["ahp_weight"].to_numpy() + (1 - lam) * entropy
    scored = metrics.copy()
    scored["topsis_score"] = topsis(scored, combined, indicators)
    summary = scored.groupby("strategy", as_index=False).agg(
        topsis_score=("topsis_score", "mean"),
        cumulative_delay=("cumulative_delay", "mean"),
        recovery_time=("recovery_time", "mean"),
        min_performance=("min_performance", "mean"),
        spread_range=("spread_range", "mean"),
        strategy_cost=("strategy_cost", "mean"),
        complexity=("complexity", "mean"),
    )
    summary["overall_rank"] = summary["topsis_score"].rank(ascending=False, method="dense").astype(int)
    return summary.sort_values("overall_rank")


def evaluate_strategies() -> dict:
    ensure_dirs()
    metrics = pd.read_csv(TABLES_DIR / "strategy_metrics_by_scenario.csv")
    indicators = [i[0] for i in INDICATORS]
    ahp_df, ahp_check = ahp_weights()
    entropy = entropy_weights(metrics, indicators)
    weights = ahp_df.copy()
    weights["entropy_weight"] = entropy
    # Main classroom decision profile: recovery and resilience are prioritized,
    # while entropy/cost sensitivity is preserved as a robustness profile below.
    main_lambda = 0.90
    weights["combined_weight"] = main_lambda * weights["ahp_weight"] + (1 - main_lambda) * weights["entropy_weight"]
    weights.to_csv(TABLES_DIR / "indicator_weights.csv", index=False, encoding="utf-8-sig")

    metric_scores = metrics.copy()
    metric_scores["topsis_score"] = topsis(metric_scores, weights["combined_weight"].to_numpy(), indicators)
    metric_scores["rank_in_scenario"] = metric_scores.groupby("scenario")["topsis_score"].rank(ascending=False, method="dense")

    strategy_summary = _score_with_lambda(metrics, ahp_df, entropy, main_lambda)
    sensitivity_rows = []
    for lam in np.linspace(0.2, 1.0, 9):
        summary = _score_with_lambda(metrics, ahp_df, entropy, float(lam))
        sensitivity_rows.append(
            {
                "lambda_ahp": float(lam),
                "recommended_strategy": str(summary.iloc[0]["strategy"]),
                "top_score": float(summary.iloc[0]["topsis_score"]),
                "dynamic_combo_rank": int(summary.loc[summary["strategy"] == "dynamic_combo", "overall_rank"].iloc[0]),
                "baseline_rank": int(summary.loc[summary["strategy"] == "baseline", "overall_rank"].iloc[0]),
            }
        )
    sensitivity_df = pd.DataFrame(sensitivity_rows)
    fuzzy_rows = []
    for row in strategy_summary.itertuples(index=False):
        grade = fuzzy_grade(float(row.topsis_score))
        fuzzy_rows.append({"strategy": row.strategy, **grade, "dominant_grade": max(grade, key=grade.get)})
    fuzzy_df = pd.DataFrame(fuzzy_rows)

    scenarios = load_yaml("scenarios.yaml")["scenarios"]
    probs = {k: float(v["probability"]) for k, v in scenarios.items()}
    loss_source = metrics.copy()
    loss_source["loss"] = (
        0.35 * loss_source["cumulative_delay"]
        + 18.0 * loss_source["recovery_time"]
        + 45.0 * loss_source["spread_range"]
        + 2.0 * loss_source["strategy_cost"]
    )
    loss = loss_source.pivot(index="strategy", columns="scenario", values="loss")
    expected_loss = loss.mul(pd.Series(probs), axis=1).sum(axis=1).sort_values()
    risk_df = expected_loss.rename("expected_loss").reset_index()
    risk_df["risk_rank"] = range(1, len(risk_df) + 1)
    uncertainty_df = uncertain_decision(loss)

    metric_scores.to_csv(TABLES_DIR / "topsis_by_scenario.csv", index=False, encoding="utf-8-sig")
    strategy_summary.to_csv(TABLES_DIR / "strategy_rankings.csv", index=False, encoding="utf-8-sig")
    sensitivity_df.to_csv(TABLES_DIR / "weight_sensitivity.csv", index=False, encoding="utf-8-sig")
    fuzzy_df.to_csv(TABLES_DIR / "fuzzy_evaluation.csv", index=False, encoding="utf-8-sig")
    loss.to_csv(TABLES_DIR / "loss_matrix.csv", encoding="utf-8-sig")
    risk_df.to_csv(TABLES_DIR / "risk_decision.csv", index=False, encoding="utf-8-sig")
    uncertainty_df.to_csv(TABLES_DIR / "uncertainty_decision.csv", index=False, encoding="utf-8-sig")

    for name in [
        "strategy_rankings",
        "fuzzy_evaluation",
        "risk_decision",
        "uncertainty_decision",
        "indicator_weights",
        "weight_sensitivity",
    ]:
        pd.read_csv(TABLES_DIR / f"{name}.csv").to_csv(DEMO_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")

    best = str(strategy_summary.iloc[0]["strategy"])
    write_json(
        DEMO_DIR / "decision_summary.json",
        {
            "recommended_strategy": best,
            "main_lambda_ahp": main_lambda,
            "ahp_consistency": ahp_check,
            "risk_recommended_strategy": str(risk_df.iloc[0]["strategy"]),
            "uncertainty_recommendations": uncertainty_df.to_dict(orient="records"),
        },
    )
    return {
        "recommended_strategy": best,
        "ahp_check": ahp_check,
        "risk_recommended_strategy": str(risk_df.iloc[0]["strategy"]),
    }
