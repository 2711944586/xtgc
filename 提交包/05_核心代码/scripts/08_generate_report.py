from __future__ import annotations

import bootstrap  # noqa: F401

from src.flightresilience.reporting import generate_deliverables


if __name__ == "__main__":
    outputs = generate_deliverables()
    for key, path in outputs.items():
        print(f"{key}: {path}")

