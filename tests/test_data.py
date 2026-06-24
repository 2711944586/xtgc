from __future__ import annotations

import pandas as pd


def test_time_splits_do_not_overlap():
    df = pd.read_parquet("data/processed/flights_features.parquet")
    ranges = df.groupby("split")["FlightDate"].agg(["min", "max"])
    assert ranges.loc["train", "max"] <= pd.Timestamp("2024-02-15")
    assert ranges.loc["valid", "min"] > pd.Timestamp("2024-02-15")
    assert ranges.loc["valid", "max"] <= pd.Timestamp("2024-02-29")
    assert ranges.loc["test", "min"] > pd.Timestamp("2024-02-29")


def test_arrdel15_consistency_is_recorded():
    df = pd.read_parquet("data/processed/flights_features.parquet")
    assert "arrdel15_consistent" in df.columns
    assert df["arrdel15_consistent"].mean() > 0.99

