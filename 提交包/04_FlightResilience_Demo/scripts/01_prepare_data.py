from __future__ import annotations

import bootstrap  # noqa: F401

from src.flightresilience.data import prepare_data


if __name__ == "__main__":
    df, audit = prepare_data(force_download=False)
    print(f"Prepared {len(df):,} scoped rows")
    print(f"Top airports: {', '.join(audit['top_airports'])}")
    print(f"Split counts: {audit['split_counts']}")
