from __future__ import annotations

import numpy as np
import pandas as pd


def test_propagation_matrix_is_stable_and_nonnegative():
    A = pd.read_csv("reports/tables/propagation_matrix_A.csv", index_col=0).to_numpy()
    assert (A >= -1e-12).all()
    radius = max(abs(np.linalg.eigvals(A)))
    assert radius < 1.0


def test_strategy_metrics_exist_for_four_by_four_grid():
    metrics = pd.read_csv("reports/tables/strategy_metrics_by_scenario.csv")
    assert metrics["scenario"].nunique() == 4
    assert metrics["strategy"].nunique() == 4
    assert len(metrics) == 16
    assert (metrics["recovery_time"] > 0).all()

