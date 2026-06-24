from __future__ import annotations

import bootstrap  # noqa: F401

from src.flightresilience.simulation import run_all_simulations


if __name__ == "__main__":
    summary = run_all_simulations()
    print(f"Shock airport: {summary['shock_airport']}")
    print(f"Trajectory rows: {summary['trajectory_rows']}")
    print(f"Strategy-scenario rows: {summary['metric_rows']}")
    print(f"Propagation MAE: {summary['validation']['mae']:.2f}")

