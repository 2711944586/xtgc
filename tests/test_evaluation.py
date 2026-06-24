from __future__ import annotations

import pandas as pd


def test_topsis_scores_are_bounded():
    rankings = pd.read_csv("reports/tables/strategy_rankings.csv")
    assert rankings["topsis_score"].between(0, 1).all()


def test_weights_sum_to_one():
    weights = pd.read_csv("reports/tables/indicator_weights.csv")
    assert abs(weights["combined_weight"].sum() - 1.0) < 1e-9

