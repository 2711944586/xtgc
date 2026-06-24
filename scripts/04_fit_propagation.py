from __future__ import annotations

import bootstrap  # noqa: F401

from src.flightresilience.simulation import estimate_propagation_matrix


if __name__ == "__main__":
    model = estimate_propagation_matrix()
    print(f"Airports: {len(model.airports)}")
    print(f"MAE: {model.validation['mae']:.2f}")
    print(f"Spectral radius: {model.validation['spectral_radius_final']:.3f}")

