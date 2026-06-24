from __future__ import annotations

import bootstrap  # noqa: F401

from src.flightresilience.network_analysis import build_airport_network, build_ism


if __name__ == "__main__":
    network = build_airport_network()
    ism = build_ism()
    print(f"Network nodes: {network['summary']['node_count']}")
    print(f"Network edges: {network['summary']['edge_count']}")
    print(f"Top critical airports: {', '.join(network['summary']['top_critical_airports'])}")
    print(f"ISM levels: {ism['levels']['level'].nunique()}")

