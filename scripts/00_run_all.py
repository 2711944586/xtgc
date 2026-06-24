from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


STEPS = [
    "01_prepare_data.py",
    "02_train_model.py",
    "03_build_network.py",
    "04_fit_propagation.py",
    "05_run_simulation.py",
    "06_rank_strategies.py",
    "07_export_demo_assets.py",
    "08_generate_report.py",
    "09_generate_slides.py",
]


def main() -> None:
    for step in STEPS:
        print(f"\n=== {step} ===")
        subprocess.run([sys.executable, str(ROOT / "scripts" / step)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()

