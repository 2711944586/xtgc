from __future__ import annotations

import bootstrap  # noqa: F401

from src.flightresilience.modeling import train_models


if __name__ == "__main__":
    summary = train_models()
    print(f"Best model: {summary['best_model']}")
    print(f"Threshold: {summary['threshold']:.2f}")
    print(f"Test PR-AUC: {summary['best_test_metrics']['pr_auc']:.3f}")
    print(f"Test ROC-AUC: {summary['best_test_metrics']['roc_auc']:.3f}")

