from __future__ import annotations

import bootstrap  # noqa: F401

from src.flightresilience.evaluation import evaluate_strategies


if __name__ == "__main__":
    summary = evaluate_strategies()
    print(f"TOPSIS recommended strategy: {summary['recommended_strategy']}")
    print(f"Risk decision recommended strategy: {summary['risk_recommended_strategy']}")
    print(f"AHP CR: {summary['ahp_check']['cr']:.4f}")

