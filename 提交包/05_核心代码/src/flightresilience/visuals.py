from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import joblib
import plotly.graph_objects as go
import seaborn as sns
from sklearn.metrics import precision_recall_curve, roc_curve

from .config import DEMO_DIR, FIGURES_DIR, MODELS_DIR, PROCESSED_DIR, TABLES_DIR, ensure_dirs
from .modeling import CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET
from .utils import write_json


PALETTE = {
    "navy": "#163A5F",
    "blue": "#2F7EA8",
    "slate": "#7C93A6",
    "orange": "#E58B3A",
    "red": "#C94C4C",
    "green": "#4F8A6B",
    "gray": "#F4F6F8",
    "ink": "#1F2933",
}


def set_theme() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial"],
            "axes.unicode_minus": False,
            "figure.dpi": 140,
            "savefig.dpi": 220,
            "axes.edgecolor": "#D6DEE6",
            "axes.labelcolor": PALETTE["ink"],
            "xtick.color": "#425466",
            "ytick.color": "#425466",
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "axes.titlecolor": PALETTE["navy"],
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
        }
    )


def savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def eda_figures(df: pd.DataFrame) -> None:
    completed = df[df["is_completed"] == 1].copy()

    plt.figure(figsize=(8.5, 4.8))
    clipped = completed["ArrDelayMinutes"].clip(upper=180)
    sns.histplot(clipped, bins=45, color=PALETTE["blue"])
    plt.title("图 6  到达延误分钟数分布（180分钟截尾显示）")
    plt.xlabel("到达延误分钟数")
    plt.ylabel("航班数")
    savefig(FIGURES_DIR / "fig_06_delay_distribution.png")

    daily = completed.groupby("FlightDate").agg(flights=("ArrDel15", "size"), delay_rate=("ArrDel15", "mean")).reset_index()
    fig, ax1 = plt.subplots(figsize=(9.5, 4.8))
    ax1.plot(daily["FlightDate"], daily["flights"], color=PALETTE["slate"], linewidth=1.7, label="航班量")
    ax1.set_ylabel("航班量")
    ax2 = ax1.twinx()
    ax2.plot(daily["FlightDate"], daily["delay_rate"], color=PALETTE["orange"], linewidth=1.7, label="延误率")
    ax2.set_ylabel("延误率")
    ax1.set_title("图 7  每日航班量与延误率趋势")
    fig.autofmt_xdate()
    savefig(FIGURES_DIR / "fig_07_daily_volume_delay.png")

    heat = completed.pivot_table(index="DayOfWeek", columns="crs_dep_hour", values="ArrDel15", aggfunc="mean")
    plt.figure(figsize=(10, 4.6))
    sns.heatmap(heat, cmap="YlOrRd", linewidths=0.1, cbar_kws={"label": "延误率"})
    plt.title("图 8  星期 × 计划起飞小时延误率热力图")
    plt.xlabel("计划起飞小时")
    plt.ylabel("星期")
    savefig(FIGURES_DIR / "fig_08_week_hour_heatmap.png")

    airport = (
        completed.groupby("Origin")
        .agg(flights=("ArrDel15", "size"), delay_rate=("ArrDel15", "mean"), avg_delay=("ArrDelayMinutes", "mean"))
        .sort_values("delay_rate", ascending=False)
    )
    top_delay = airport.head(15).reset_index()
    plt.figure(figsize=(8.5, 5.2))
    sns.barplot(data=top_delay, y="Origin", x="delay_rate", color=PALETTE["orange"])
    plt.title("图 10  主要机场延误率排名")
    plt.xlabel("延误率")
    plt.ylabel("机场")
    savefig(FIGURES_DIR / "fig_10_airport_delay_rank.png")

    airline = (
        completed.groupby("Reporting_Airline", as_index=False)
        .agg(flights=("ArrDel15", "size"), delay_rate=("ArrDel15", "mean"), avg_delay=("ArrDelayMinutes", "mean"))
        .query("flights >= 1200")
        .sort_values("delay_rate", ascending=False)
        .head(15)
    )
    plt.figure(figsize=(8.4, 4.8))
    sns.barplot(data=airline, y="Reporting_Airline", x="delay_rate", color=PALETTE["green"])
    plt.title("图 11  航司计划阶段延误暴露差异")
    plt.xlabel("延误率")
    plt.ylabel("承运航司")
    for i, row in enumerate(airline.itertuples(index=False)):
        plt.text(row.delay_rate + 0.003, i, f"{int(row.flights):,}", va="center", fontsize=8, color=PALETTE["slate"])
    savefig(FIGURES_DIR / "fig_11_airline_delay_rank.png")

    route = (
        completed.groupby(["Origin", "Dest", "route"], as_index=False)
        .agg(flights=("ArrDel15", "size"), delay_rate=("ArrDel15", "mean"), avg_delay=("ArrDelayMinutes", "mean"))
        .query("flights >= 350")
    )
    route["risk_volume"] = route["flights"] * route["delay_rate"]
    top_route = route.sort_values("risk_volume", ascending=False).head(22).copy()
    plt.figure(figsize=(8.8, 5.8))
    ax = sns.scatterplot(
        data=top_route,
        x="flights",
        y="delay_rate",
        size="avg_delay",
        hue="risk_volume",
        palette="YlOrRd",
        sizes=(60, 520),
        edgecolor="white",
        linewidth=0.8,
    )
    for row in top_route.itertuples(index=False):
        plt.text(row.flights, row.delay_rate, row.route, fontsize=7.6, color=PALETTE["ink"])
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True, fontsize=7.5)
    plt.title("图 12  高暴露航线：流量、延误率与平均延误")
    plt.xlabel("样本航班量")
    plt.ylabel("延误率")
    savefig(FIGURES_DIR / "fig_12_route_risk_bubble.png")

    plt.figure(figsize=(7.5, 5.2))
    sns.scatterplot(data=airport.reset_index(), x="flights", y="delay_rate", size="avg_delay", sizes=(40, 280), color=PALETTE["blue"])
    for airport_code, row in airport.iterrows():
        if row["flights"] >= airport["flights"].quantile(0.80) or row["delay_rate"] >= airport["delay_rate"].quantile(0.80):
            plt.text(row["flights"], row["delay_rate"], airport_code, fontsize=8)
    plt.title("图 9  航班量与延误率并非简单等价")
    plt.xlabel("出港航班量")
    plt.ylabel("延误率")
    savefig(FIGURES_DIR / "fig_09_volume_delay_scatter.png")

    split = completed.groupby("split")["ArrDel15"].mean().reindex(["train", "valid", "test"]).reset_index()
    plt.figure(figsize=(6.8, 4.2))
    sns.barplot(data=split, x="split", y="ArrDel15", color=PALETTE["blue"])
    plt.title("图 13  训练/验证/测试目标比例")
    plt.xlabel("时间切分")
    plt.ylabel("ArrDel15 比例")
    savefig(FIGURES_DIR / "fig_13_split_delay_rate.png")


def model_figures() -> None:
    metrics = pd.read_csv(TABLES_DIR / "model_metrics.csv")
    plot = metrics[["model", "test_roc_auc", "test_pr_auc", "test_f1", "test_recall"]].melt("model")
    plt.figure(figsize=(8.6, 4.8))
    sns.barplot(data=plot, x="model", y="value", hue="variable", palette=[PALETTE["blue"], PALETTE["orange"], PALETTE["green"], PALETTE["red"]])
    plt.title("图 14  时间外测试集模型指标对比")
    plt.xlabel("模型")
    plt.ylabel("指标值")
    plt.legend(title="")
    savefig(FIGURES_DIR / "fig_14_model_metrics.png")

    best = metrics.sort_values(["test_pr_auc", "test_roc_auc"], ascending=False).iloc[0]
    cm = np.array([[best["test_tn"], best["test_fp"]], [best["test_fn"], best["test_tp"]]], dtype=float)
    plt.figure(figsize=(4.8, 4.2))
    sns.heatmap(cm, annot=True, fmt=".0f", cmap="Blues", cbar=False, xticklabels=["预测准点", "预测延误"], yticklabels=["实际准点", "实际延误"])
    plt.title("图 15  最佳模型测试集混淆矩阵")
    savefig(FIGURES_DIR / "fig_15_confusion_matrix.png")

    cal = pd.read_csv(TABLES_DIR / "calibration_curve.csv")
    plt.figure(figsize=(5.4, 4.6))
    plt.plot([0, 1], [0, 1], "--", color=PALETTE["slate"], linewidth=1)
    plt.plot(cal["mean_predicted"], cal["fraction_positive"], marker="o", color=PALETTE["orange"])
    plt.title("图 17  概率校准曲线")
    plt.xlabel("平均预测概率")
    plt.ylabel("实际延误比例")
    savefig(FIGURES_DIR / "fig_17_calibration_curve.png")

    shap_df = pd.read_csv(TABLES_DIR / "shap_summary.csv").head(10)
    plt.figure(figsize=(7.6, 4.8))
    sns.barplot(data=shap_df, y="source_feature", x="mean_abs_shap", color=PALETTE["blue"])
    plt.title("图 18  SHAP 全局特征重要性")
    plt.xlabel("mean(|SHAP|)")
    plt.ylabel("特征")
    savefig(FIGURES_DIR / "fig_18_shap_summary.png")

    df = pd.read_parquet(PROCESSED_DIR / "flights_features.parquet")
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    test = df[(df["is_completed"] == 1) & (df["split"] == "test")].copy()
    if (MODELS_DIR / "delay_model.joblib").exists() and len(test):
        model = joblib.load(MODELS_DIR / "delay_model.joblib")
        sample = test.sample(n=min(50000, len(test)), random_state=42)
        y = sample[TARGET].astype(int)
        proba = model.predict_proba(sample[feature_cols])[:, 1]
        fpr, tpr, _ = roc_curve(y, proba)
        precision, recall, _ = precision_recall_curve(y, proba)
        curve_df = pd.DataFrame({"fpr": pd.Series(fpr), "tpr": pd.Series(tpr)})
        curve_df.to_csv(TABLES_DIR / "roc_curve.csv", index=False, encoding="utf-8-sig")
        pr_df = pd.DataFrame({"recall": pd.Series(recall), "precision": pd.Series(precision)})
        pr_df.to_csv(TABLES_DIR / "pr_curve.csv", index=False, encoding="utf-8-sig")

        fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.3))
        axes[0].plot(fpr, tpr, color=PALETTE["blue"], linewidth=2.2)
        axes[0].plot([0, 1], [0, 1], "--", color=PALETTE["slate"], linewidth=1)
        axes[0].set_title("ROC 曲线")
        axes[0].set_xlabel("FPR")
        axes[0].set_ylabel("TPR")
        axes[1].plot(recall, precision, color=PALETTE["orange"], linewidth=2.2)
        axes[1].set_title("PR 曲线")
        axes[1].set_xlabel("Recall")
        axes[1].set_ylabel("Precision")
        fig.suptitle("图 16  时间外测试集排序能力曲线", x=0.5, y=1.02, fontweight="bold", color=PALETTE["navy"])
        savefig(FIGURES_DIR / "fig_16_roc_pr_curves.png")


def network_figures() -> None:
    nodes = pd.read_csv(TABLES_DIR / "airport_nodes.csv")
    edges = pd.read_csv(TABLES_DIR / "airport_edges.csv")
    G = nx.DiGraph()
    for row in nodes.itertuples(index=False):
        G.add_node(row.airport, criticality=float(row.criticality), delay_rate=float(row.delay_rate), departures=int(row.departures))
    for row in edges.itertuples(index=False):
        G.add_edge(row.Origin, row.Dest, weight=float(row.flights))
    pos = nx.spring_layout(G, seed=42, weight="weight", k=1.15, iterations=220)
    plt.figure(figsize=(8, 6))
    widths = [0.4 + 2.5 * (G[u][v]["weight"] / edges["flights"].max()) for u, v in G.edges()]
    sizes = [120 + 760 * G.nodes[n]["departures"] / nodes["departures"].max() for n in G.nodes()]
    colors = [G.nodes[n]["criticality"] for n in G.nodes()]
    nx.draw_networkx_edges(G, pos, alpha=0.25, width=widths, edge_color=PALETTE["slate"], arrows=False)
    nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=colors, cmap="YlOrRd", edgecolors="white", linewidths=1.2)
    label_nodes = set(nodes.sort_values("criticality", ascending=False).head(14)["airport"])
    nx.draw_networkx_labels(G, pos, labels={n: n for n in G.nodes() if n in label_nodes}, font_size=8, font_family="Microsoft YaHei")
    plt.title("图 20  主要机场有向航线网络")
    plt.axis("off")
    savefig(FIGURES_DIR / "fig_20_airport_network.png")

    top = nodes.sort_values("criticality", ascending=False).head(10)
    plt.figure(figsize=(7.6, 4.8))
    sns.barplot(data=top, y="airport", x="criticality", color=PALETTE["orange"])
    plt.title("图 21  关键机场综合风险指数排名")
    plt.xlabel("关键性指数")
    plt.ylabel("机场")
    savefig(FIGURES_DIR / "fig_21_airport_criticality.png")

    plt.figure(figsize=(8.8, 5.2))
    ax = sns.scatterplot(
        data=nodes,
        x="pagerank",
        y="avg_risk",
        size="weighted_degree",
        hue="criticality",
        palette="YlOrRd",
        sizes=(70, 380),
        edgecolor="white",
        linewidth=0.8,
    )
    for row in nodes.itertuples(index=False):
        if row.criticality >= nodes["criticality"].quantile(0.70):
            plt.text(row.pagerank, row.avg_risk, row.airport, fontsize=8, fontweight="bold")
    plt.title("图 22  中心性、风险与航班量的三维关系")
    plt.xlabel("PageRank 中心性")
    plt.ylabel("平均预测风险")
    ax.legend(
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        borderaxespad=0,
        frameon=True,
        fontsize=7.5,
        title_fontsize=8.5,
    )
    savefig(FIGURES_DIR / "fig_22_network_risk_scatter.png")

    role = nodes.copy()
    role["departures_norm"] = role["departures"] / role["departures"].max()
    role["role"] = np.where(
        (role["pagerank"] >= role["pagerank"].median()) & (role["avg_risk"] >= role["avg_risk"].median()),
        "高中心-高风险",
        np.where(role["pagerank"] >= role["pagerank"].median(), "高中心", np.where(role["avg_risk"] >= role["avg_risk"].median(), "高风险", "低暴露")),
    )
    plt.figure(figsize=(8.6, 5.2))
    ax = sns.scatterplot(
        data=role,
        x="pagerank",
        y="avg_risk",
        hue="role",
        size="departures",
        sizes=(60, 430),
        palette=[PALETTE["red"], PALETTE["blue"], PALETTE["orange"], PALETTE["slate"]],
        edgecolor="white",
        linewidth=0.8,
    )
    for row in role.sort_values("criticality", ascending=False).head(12).itertuples(index=False):
        plt.text(row.pagerank, row.avg_risk, row.airport, fontsize=8, fontweight="bold")
    ax.axvline(role["pagerank"].median(), color=PALETTE["slate"], linestyle="--", linewidth=1)
    ax.axhline(role["avg_risk"].median(), color=PALETTE["slate"], linestyle="--", linewidth=1)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True, fontsize=7.4)
    plt.title("图 26  机场角色象限：中心性与风险暴露")
    plt.xlabel("PageRank 中心性")
    plt.ylabel("平均预测风险")
    savefig(FIGURES_DIR / "fig_26_airport_role_quadrant.png")


def ism_figures() -> None:
    adj = pd.read_csv(TABLES_DIR / "ism_adjacency_matrix.csv", index_col=0)
    reach = pd.read_csv(TABLES_DIR / "ism_reachability_matrix.csv", index_col=0)
    for name, mat, title in [
        ("fig_23_ism_adjacency.png", adj, "图 23  ISM 邻接矩阵"),
        ("fig_24_ism_reachability.png", reach, "图 24  ISM 可达矩阵"),
    ]:
        plt.figure(figsize=(6.8, 5.8))
        sns.heatmap(mat, cmap="Blues", cbar=False, square=True, linewidths=0.4)
        plt.title(title)
        savefig(FIGURES_DIR / name)

    levels = pd.read_csv(TABLES_DIR / "ism_levels.csv")
    plt.figure(figsize=(8.4, 5.2))
    ax = plt.gca()
    ax.axis("off")
    for level, group in levels.groupby("level"):
        y = 1 - (level - 1) / max(1, levels["level"].max() - 1)
        xs = np.linspace(0.12, 0.88, len(group))
        for x, row in zip(xs, group.itertuples(index=False)):
            ax.text(
                x,
                y,
                f"{row.code}\n{row.factor}",
                ha="center",
                va="center",
                fontsize=8.5,
                bbox=dict(boxstyle="round,pad=0.35", fc="#F4F6F8", ec="#7C93A6"),
            )
        ax.text(0.02, y, f"L{level}", ha="left", va="center", color=PALETTE["navy"], fontweight="bold")
    plt.title("图 25  延误因素多级递阶结构")
    savefig(FIGURES_DIR / "fig_25_ism_hierarchy.png")


def simulation_figures() -> None:
    A = pd.read_csv(TABLES_DIR / "propagation_matrix_A.csv", index_col=0)
    plt.figure(figsize=(7.4, 6.2))
    sns.heatmap(A, cmap="YlGnBu", linewidths=0.2)
    plt.title("图 27  机场间传播矩阵 A")
    savefig(FIGURES_DIR / "fig_27_propagation_matrix.png")

    traj = pd.read_parquet(PROCESSED_DIR / "scenario_trajectories.parquet")
    weather = traj[traj["scenario"] == "weather"]
    plt.figure(figsize=(8.4, 4.8))
    for strategy, group in weather.groupby("strategy"):
        plt.plot(group["hour"], group["performance"], linewidth=2, label=strategy)
    plt.title("图 29  天气冲击下四策略性能恢复曲线")
    plt.xlabel("冲击后小时")
    plt.ylabel("系统性能")
    plt.legend()
    savefig(FIGURES_DIR / "fig_29_recovery_curves.png")

    heat = weather.pivot_table(index="strategy", columns="hour", values="total_delay", aggfunc="mean")
    plt.figure(figsize=(9.2, 3.8))
    sns.heatmap(heat, cmap="YlOrRd", linewidths=0.2, cbar_kws={"label": "总延误分钟"})
    plt.title("图 28  天气冲击下恢复过程热力图")
    plt.xlabel("冲击后小时")
    plt.ylabel("策略")
    savefig(FIGURES_DIR / "fig_28_recovery_heatmap.png")

    focus = weather[weather["hour"].isin([1, 3, 6, 12, 24])].copy()
    plt.figure(figsize=(9.2, 4.8))
    sns.lineplot(data=weather, x="hour", y="spread_range", hue="strategy", marker="o")
    plt.title("图 31  传播范围随时间收敛过程")
    plt.xlabel("冲击后小时")
    plt.ylabel("延误超过阈值的机场数")
    plt.legend(title="")
    savefig(FIGURES_DIR / "fig_31_spread_range_curves.png")

    metrics = pd.read_csv(TABLES_DIR / "strategy_metrics_by_scenario.csv")
    plt.figure(figsize=(8.4, 4.8))
    sns.barplot(data=metrics, x="scenario", y="cumulative_delay", hue="strategy")
    plt.title("图 30  不同情景下累计延误对比")
    plt.xlabel("情景")
    plt.ylabel("累计总延误")
    plt.legend(title="")
    savefig(FIGURES_DIR / "fig_30_scenario_delay_compare.png")

    plt.figure(figsize=(7.8, 4.8))
    sns.scatterplot(data=metrics, x="strategy_cost", y="cumulative_delay", hue="strategy", style="scenario", s=95)
    plt.title("图 32  成本-延误 Pareto 关系")
    plt.xlabel("相对策略成本")
    plt.ylabel("累计总延误")
    savefig(FIGURES_DIR / "fig_32_cost_delay_pareto.png")

    radar_cols = ["cumulative_delay", "recovery_time", "spread_range", "strategy_cost"]
    radar = metrics.groupby("strategy", as_index=False)[radar_cols].mean()
    radar_norm = radar.copy()
    for col in radar_cols:
        series = radar[col]
        radar_norm[col] = 1 - (series - series.min()) / (series.max() - series.min() + 1e-9)
    angles = np.linspace(0, 2 * np.pi, len(radar_cols), endpoint=False).tolist()
    angles += angles[:1]
    fig = plt.figure(figsize=(6.8, 6.2))
    ax = plt.subplot(111, polar=True)
    for row in radar_norm.itertuples(index=False):
        values = [getattr(row, col) for col in radar_cols]
        values += values[:1]
        ax.plot(angles, values, linewidth=2, label=row.strategy)
        ax.fill(angles, values, alpha=0.08)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(["低累计延误", "快恢复", "小传播", "低成本"], fontsize=9)
    ax.set_yticklabels([])
    ax.set_title("图 33  策略韧性画像雷达图", color=PALETTE["navy"], fontweight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.32, 1.1), fontsize=8)
    savefig(FIGURES_DIR / "fig_33_strategy_radar.png")


def decision_figures() -> None:
    ranking = pd.read_csv(TABLES_DIR / "strategy_rankings.csv")
    plt.figure(figsize=(7.2, 4.4))
    sns.barplot(data=ranking.sort_values("topsis_score", ascending=False), y="strategy", x="topsis_score", color=PALETTE["blue"])
    plt.title("图 34  主决策偏好下 TOPSIS 接近度")
    plt.xlabel("TOPSIS 接近度")
    plt.ylabel("策略")
    savefig(FIGURES_DIR / "fig_34_topsis_score.png")

    fuzzy = pd.read_csv(TABLES_DIR / "fuzzy_evaluation.csv").set_index("strategy")[["优秀", "良好", "一般", "较差"]]
    fuzzy.plot(kind="barh", stacked=True, figsize=(7.6, 4.4), color=[PALETTE["green"], PALETTE["blue"], PALETTE["orange"], PALETTE["red"]])
    plt.title("图 35  模糊综合评价等级分布")
    plt.xlabel("隶属度")
    plt.ylabel("策略")
    savefig(FIGURES_DIR / "fig_35_fuzzy_grades.png")

    weights = pd.read_csv(TABLES_DIR / "indicator_weights.csv")
    plot_weights = weights.sort_values("combined_weight", ascending=False)
    plt.figure(figsize=(8.8, 5.0))
    sns.barplot(data=plot_weights, y="label", x="combined_weight", hue="criterion", dodge=False, palette=[PALETTE["blue"], PALETTE["green"], PALETTE["orange"], PALETTE["red"], PALETTE["slate"]])
    plt.title("图 36  组合权重结构")
    plt.xlabel("组合权重")
    plt.ylabel("评价指标")
    plt.legend(title="", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    savefig(FIGURES_DIR / "fig_36_indicator_weights.png")

    sens = pd.read_csv(TABLES_DIR / "weight_sensitivity.csv")
    plt.figure(figsize=(7.4, 4.4))
    plt.plot(sens["lambda_ahp"], sens["dynamic_combo_rank"], marker="o", label="dynamic_combo")
    plt.plot(sens["lambda_ahp"], sens["baseline_rank"], marker="o", label="baseline")
    plt.gca().invert_yaxis()
    plt.yticks([1, 2, 3, 4])
    plt.title("图 37  权重敏感性：排名反转条件")
    plt.xlabel("AHP 主观权重占比 λ")
    plt.ylabel("排名")
    plt.legend()
    savefig(FIGURES_DIR / "fig_37_weight_sensitivity.png")

    risk = pd.read_csv(TABLES_DIR / "risk_decision.csv")
    rank = pd.read_csv(TABLES_DIR / "strategy_rankings.csv")[["strategy", "overall_rank"]]
    merged = risk.merge(rank, on="strategy", how="left")
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2), sharey=False)
    sns.barplot(data=merged.sort_values("expected_loss"), y="strategy", x="expected_loss", ax=axes[0], color=PALETTE["red"])
    axes[0].set_title("风险型期望损失")
    axes[0].set_xlabel("期望损失")
    axes[0].set_ylabel("策略")
    sns.barplot(data=merged.sort_values("overall_rank"), y="strategy", x="overall_rank", ax=axes[1], color=PALETTE["blue"])
    axes[1].invert_xaxis()
    axes[1].set_title("主偏好 TOPSIS 排名")
    axes[1].set_xlabel("排名（越靠左越优）")
    axes[1].set_ylabel("")
    fig.suptitle("图 38  风险决策与主偏好排名并不完全一致", y=1.03, color=PALETTE["navy"], fontweight="bold")
    savefig(FIGURES_DIR / "fig_38_risk_vs_topsis.png")


def interactive_network_html() -> None:
    nodes = pd.read_csv(TABLES_DIR / "airport_nodes.csv")
    edges = pd.read_csv(TABLES_DIR / "airport_edges.csv")
    G = nx.DiGraph()
    for row in nodes.itertuples(index=False):
        G.add_node(row.airport)
    for row in edges.itertuples(index=False):
        G.add_edge(row.Origin, row.Dest, weight=float(row.flights))
    pos = nx.spring_layout(G, seed=42, weight="weight")
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.6, color="#9AA9B7"), hoverinfo="none", mode="lines")
    node_trace = go.Scatter(
        x=[pos[a][0] for a in nodes["airport"]],
        y=[pos[a][1] for a in nodes["airport"]],
        mode="markers+text",
        text=nodes["airport"],
        textposition="top center",
        marker=dict(
            size=12 + 28 * nodes["departures"] / nodes["departures"].max(),
            color=nodes["criticality"],
            colorscale="YlOrRd",
            showscale=True,
            colorbar=dict(title="关键性"),
        ),
        customdata=np.stack([nodes["delay_rate"], nodes["avg_risk"], nodes["betweenness"]], axis=1),
        hovertemplate="<b>%{text}</b><br>延误率=%{customdata[0]:.1%}<br>预测风险=%{customdata[1]:.1%}<br>介数=%{customdata[2]:.3f}<extra></extra>",
    )
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(title="主要机场网络交互图", showlegend=False, margin=dict(l=10, r=10, t=45, b=10), plot_bgcolor="white")
    fig.write_html(FIGURES_DIR / "fig_20_airport_network.html", include_plotlyjs="cdn")


def export_demo_tables(df: pd.DataFrame) -> None:
    completed = df[df["is_completed"] == 1].copy()
    kpi = {
        "flights": int(len(df)),
        "completed_flights": int(len(completed)),
        "date_min": str(df["FlightDate"].min().date()),
        "date_max": str(df["FlightDate"].max().date()),
        "airport_count": int(pd.concat([df["Origin"], df["Dest"]]).nunique()),
        "delay_rate": float(completed["ArrDel15"].mean()),
        "avg_arr_delay": float(completed["ArrDelayMinutes"].mean()),
        "cancel_rate": float(df["Cancelled"].mean()),
        "data_source": "U.S. DOT BTS TranStats, 2024-01 to 2024-03",
    }
    write_json(DEMO_DIR / "kpi_summary.json", kpi)

    daily = completed.groupby("FlightDate", as_index=False).agg(
        flights=("ArrDel15", "size"),
        delay_rate=("ArrDel15", "mean"),
        avg_delay=("ArrDelayMinutes", "mean"),
    )
    daily.to_parquet(DEMO_DIR / "dashboard_daily.parquet", index=False)

    airport = completed.groupby("Origin", as_index=False).agg(
        flights=("ArrDel15", "size"),
        delay_rate=("ArrDel15", "mean"),
        avg_delay=("ArrDelayMinutes", "mean"),
        avg_risk=("origin_hist_delay_rate", "mean"),
    )
    airport.to_parquet(DEMO_DIR / "dashboard_airports.parquet", index=False)

    heat = completed.groupby(["DayOfWeek", "crs_dep_hour"], as_index=False).agg(delay_rate=("ArrDel15", "mean"), flights=("ArrDel15", "size"))
    heat.to_parquet(DEMO_DIR / "dashboard_heatmap.parquet", index=False)

    route = completed.groupby(["Origin", "Dest", "route"], as_index=False).agg(
        flights=("ArrDel15", "size"),
        delay_rate=("ArrDel15", "mean"),
        distance=("Distance", "mean"),
        crs_elapsed=("CRSElapsedTime", "mean"),
    )
    route.sort_values("flights", ascending=False).head(300).to_parquet(DEMO_DIR / "route_options.parquet", index=False)

    options = {
        "airports": sorted(pd.concat([df["Origin"], df["Dest"]]).dropna().unique().tolist()),
        "airlines": sorted(df["Reporting_Airline"].dropna().unique().tolist()),
        "distance_median": float(completed["Distance"].median()),
        "elapsed_median": float(completed["CRSElapsedTime"].median()),
        "hist_delay_rate": float(completed["ArrDel15"].mean()),
        "rolling_volume_median": float(completed["origin_rolling_3h_volume"].median()),
    }
    write_json(DEMO_DIR / "prediction_options.json", options)


def generate_figures() -> dict:
    ensure_dirs()
    set_theme()
    df = pd.read_parquet(PROCESSED_DIR / "flights_features.parquet")
    export_demo_tables(df)
    eda_figures(df)
    model_figures()
    network_figures()
    ism_figures()
    simulation_figures()
    decision_figures()
    interactive_network_html()
    figures = sorted(str(p.name) for p in FIGURES_DIR.glob("*"))
    with (DEMO_DIR / "figures_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(figures, f, ensure_ascii=False, indent=2)
    return {"figure_count": len(figures), "figures": figures}
