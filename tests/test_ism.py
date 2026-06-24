from __future__ import annotations

import numpy as np
import pandas as pd


def test_reachability_has_identity_diagonal():
    reach = pd.read_csv("reports/tables/ism_reachability_matrix.csv", index_col=0).to_numpy()
    assert np.all(np.diag(reach) == 1)


def test_ism_levels_cover_all_factors():
    levels = pd.read_csv("reports/tables/ism_levels.csv")
    assert levels["code"].nunique() == 12
    assert not levels["code"].duplicated().any()

