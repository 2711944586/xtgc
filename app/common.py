from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "data" / "demo"
FIGURES_DIR = ROOT / "reports" / "figures"
MODELS_DIR = ROOT / "models"


PALETTE = {
    "navy": "#163A5F",
    "blue": "#2F7EA8",
    "slate": "#7C93A6",
    "orange": "#E58B3A",
    "red": "#C94C4C",
    "green": "#4F8A6B",
    "gray": "#F4F6F8",
    "ink": "#1F2933",
}


def setup_page(title: str) -> None:
    st.set_page_config(page_title=f"FlightResilience - {title}", page_icon="FR", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        h1, h2, h3 { letter-spacing: 0; color: #163A5F; }
        [data-testid="stMetricValue"] { color: #163A5F; }
        .fr-note {
          border-left: 4px solid #2F7EA8;
          padding: .55rem .75rem;
          background: #F4F6F8;
          color: #1F2933;
          margin: .4rem 0 1rem 0;
        }
        .fr-chip {
          display: inline-block;
          padding: .22rem .5rem;
          border: 1px solid #D6DEE6;
          border-radius: 6px;
          margin-right: .35rem;
          font-size: .82rem;
          color: #425466;
          background: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def conclusion(text: str) -> None:
    st.markdown(f"<div class='fr-note'><strong>本页结论：</strong>{text}</div>", unsafe_allow_html=True)


@st.cache_data
def read_json(name: str):
    with (DEMO_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DEMO_DIR / name)


@st.cache_data
def read_parquet(name: str) -> pd.DataFrame:
    return pd.read_parquet(DEMO_DIR / name)


def image(name: str, caption: str | None = None) -> None:
    st.image(str(FIGURES_DIR / name), caption=caption, use_container_width=True)


def strategy_label(name: str) -> str:
    labels = {
        "baseline": "A 基准运行",
        "uniform_buffer": "B 统一缓冲",
        "hub_priority": "C 关键枢纽优先",
        "dynamic_combo": "D 动态组合",
    }
    return labels.get(name, name)

