from __future__ import annotations

import itertools

import networkx as nx
import numpy as np
import pandas as pd

from .config import DEMO_DIR, PROCESSED_DIR, TABLES_DIR, ensure_dirs
from .utils import minmax, write_json


def build_airport_network() -> dict:
    ensure_dirs()
    df = pd.read_parquet(PROCESSED_DIR / "flights_scored.parquet")
    completed = df[df["is_completed"] == 1].copy()

    route = (
        completed.groupby(["Origin", "Dest"], as_index=False)
        .agg(
            flights=("ArrDel15", "size"),
            delay_rate=("ArrDel15", "mean"),
            avg_arr_delay=("ArrDelayMinutes", "mean"),
            avg_risk=("delay_risk", "mean"),
            distance=("Distance", "mean"),
        )
        .query("Origin != Dest")
    )

    G = nx.DiGraph()
    airports = sorted(set(route["Origin"]).union(route["Dest"]))
    node_metrics = (
        completed.groupby("Origin", as_index=False)
        .agg(
            departures=("ArrDel15", "size"),
            delay_rate=("ArrDel15", "mean"),
            avg_delay=("ArrDelayMinutes", "mean"),
            avg_risk=("delay_risk", "mean"),
        )
        .rename(columns={"Origin": "airport"})
    )
    arrivals = completed.groupby("Dest").size().rename("arrivals")
    node_metrics["arrivals"] = node_metrics["airport"].map(arrivals).fillna(0).astype(int)
    for airport in airports:
        G.add_node(airport)
    for row in route.itertuples(index=False):
        G.add_edge(row.Origin, row.Dest, weight=float(row.flights), delay_rate=float(row.delay_rate))

    degree = dict(G.degree(weight="weight"))
    indegree = dict(G.in_degree(weight="weight"))
    outdegree = dict(G.out_degree(weight="weight"))
    betweenness = nx.betweenness_centrality(G, weight=None, normalized=True)
    pagerank = nx.pagerank(G, weight="weight")
    closeness = nx.closeness_centrality(G)
    density = nx.density(G)
    strong_components = list(nx.strongly_connected_components(G))

    node_metrics["weighted_degree"] = node_metrics["airport"].map(degree).fillna(0)
    node_metrics["in_weighted_degree"] = node_metrics["airport"].map(indegree).fillna(0)
    node_metrics["out_weighted_degree"] = node_metrics["airport"].map(outdegree).fillna(0)
    node_metrics["betweenness"] = node_metrics["airport"].map(betweenness).fillna(0)
    node_metrics["pagerank"] = node_metrics["airport"].map(pagerank).fillna(0)
    node_metrics["closeness"] = node_metrics["airport"].map(closeness).fillna(0)
    node_metrics["criticality"] = (
        0.25 * minmax(node_metrics["departures"])
        + 0.25 * minmax(node_metrics["betweenness"])
        + 0.25 * minmax(node_metrics["avg_risk"])
        + 0.25 * minmax(node_metrics["delay_rate"])
    )
    node_metrics = node_metrics.sort_values("criticality", ascending=False).reset_index(drop=True)

    route["route_share_to_dest"] = route["flights"] / route.groupby("Dest")["flights"].transform("sum")
    route["route_share_from_origin"] = route["flights"] / route.groupby("Origin")["flights"].transform("sum")

    node_metrics.to_csv(TABLES_DIR / "airport_nodes.csv", index=False, encoding="utf-8-sig")
    route.to_csv(TABLES_DIR / "airport_edges.csv", index=False, encoding="utf-8-sig")
    write_json(
        TABLES_DIR / "network_summary.json",
        {
            "node_count": int(G.number_of_nodes()),
            "edge_count": int(G.number_of_edges()),
            "density": float(density),
            "strong_component_count": len(strong_components),
            "largest_strong_component_size": max(len(c) for c in strong_components) if strong_components else 0,
            "top_critical_airports": node_metrics.head(5)["airport"].tolist(),
        },
    )

    nodes_json = []
    for row in node_metrics.itertuples(index=False):
        nodes_json.append(
            {
                "id": row.airport,
                "label": row.airport,
                "departures": int(row.departures),
                "arrivals": int(row.arrivals),
                "delay_rate": float(row.delay_rate),
                "avg_delay": float(row.avg_delay),
                "avg_risk": float(row.avg_risk),
                "betweenness": float(row.betweenness),
                "pagerank": float(row.pagerank),
                "criticality": float(row.criticality),
            }
        )
    edges_json = []
    for row in route.itertuples(index=False):
        edges_json.append(
            {
                "source": row.Origin,
                "target": row.Dest,
                "flights": int(row.flights),
                "delay_rate": float(row.delay_rate),
                "avg_arr_delay": float(row.avg_arr_delay),
                "avg_risk": float(row.avg_risk),
            }
        )
    write_json(DEMO_DIR / "network_nodes.json", nodes_json)
    write_json(DEMO_DIR / "network_edges.json", edges_json)
    return {
        "nodes": node_metrics,
        "edges": route,
        "summary": {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "density": density,
            "top_critical_airports": node_metrics.head(5)["airport"].tolist(),
        },
    }


ISM_FACTORS = [
    ("S1", "恶劣天气或空域限制"),
    ("S2", "机场有效容量下降"),
    ("S3", "高峰航班密度"),
    ("S4", "航班计划紧凑"),
    ("S5", "时间缓冲不足"),
    ("S6", "上游/前序航班晚到"),
    ("S7", "出发延误"),
    ("S8", "地面滑行与排队增加"),
    ("S9", "局部机场拥堵"),
    ("S10", "跨机场延误传播"),
    ("S11", "航班取消或严重延误"),
    ("S12", "网络恢复时间增加"),
]


def boolean_transitive_closure(adj: np.ndarray) -> np.ndarray:
    reach = (adj.astype(bool) | np.eye(adj.shape[0], dtype=bool)).astype(int)
    changed = True
    while changed:
        new_reach = ((reach @ reach) > 0).astype(int)
        changed = not np.array_equal(reach, new_reach)
        reach = new_reach
    return reach


def ism_levels(reach: np.ndarray) -> list[list[int]]:
    remaining = set(range(reach.shape[0]))
    levels: list[list[int]] = []
    while remaining:
        level = []
        for i in sorted(remaining):
            reachable = {j for j in remaining if reach[i, j] == 1}
            antecedent = {j for j in remaining if reach[j, i] == 1}
            if reachable & antecedent == reachable:
                level.append(i)
        if not level:
            level = [min(remaining)]
        levels.append(level)
        remaining -= set(level)
    return levels


def build_ism() -> dict:
    # Mechanism-constrained structural relation matrix, row affects column.
    code_to_idx = {code: i for i, (code, _) in enumerate(ISM_FACTORS)}
    edges = [
        ("S1", "S2"),
        ("S1", "S8"),
        ("S1", "S9"),
        ("S2", "S8"),
        ("S2", "S9"),
        ("S3", "S9"),
        ("S3", "S7"),
        ("S4", "S5"),
        ("S4", "S6"),
        ("S5", "S7"),
        ("S6", "S7"),
        ("S6", "S10"),
        ("S7", "S8"),
        ("S7", "S10"),
        ("S8", "S9"),
        ("S9", "S10"),
        ("S9", "S11"),
        ("S10", "S11"),
        ("S10", "S12"),
        ("S11", "S12"),
    ]
    n = len(ISM_FACTORS)
    adj = np.zeros((n, n), dtype=int)
    for a, b in edges:
        adj[code_to_idx[a], code_to_idx[b]] = 1
    reach = boolean_transitive_closure(adj)
    levels = ism_levels(reach)
    level_rows = []
    for level_no, indices in enumerate(levels, start=1):
        for idx in indices:
            level_rows.append(
                {
                    "level": level_no,
                    "code": ISM_FACTORS[idx][0],
                    "factor": ISM_FACTORS[idx][1],
                    "interpretation": ["结果层", "直接层", "传导层", "根源层"][min(level_no - 1, 3)],
                }
            )
    factors = pd.DataFrame(ISM_FACTORS, columns=["code", "factor"])
    adj_df = pd.DataFrame(adj, index=factors["code"], columns=factors["code"])
    reach_df = pd.DataFrame(reach, index=factors["code"], columns=factors["code"])
    levels_df = pd.DataFrame(level_rows)
    adj_df.to_csv(TABLES_DIR / "ism_adjacency_matrix.csv", encoding="utf-8-sig")
    reach_df.to_csv(TABLES_DIR / "ism_reachability_matrix.csv", encoding="utf-8-sig")
    levels_df.to_csv(TABLES_DIR / "ism_levels.csv", index=False, encoding="utf-8-sig")
    write_json(
        DEMO_DIR / "ism.json",
        {
            "factors": factors.to_dict(orient="records"),
            "edges": [{"source": a, "target": b} for a, b in edges],
            "levels": levels_df.to_dict(orient="records"),
        },
    )
    return {"adjacency": adj_df, "reachability": reach_df, "levels": levels_df}

