from __future__ import annotations

import plotly.express as px
import streamlit as st

from common import conclusion, read_csv, read_parquet, setup_page, strategy_label


setup_page("扰动仿真")
st.title("扰动仿真")
conclusion("在同一 DEN 冲击、相同仿真时长和统一预算口径下，动态组合策略通常能降低累计延误并提升最低系统性能。")

traj = read_parquet("scenario_results.parquet")
metrics = read_csv("strategy_metrics_by_scenario.csv")

scenario = st.selectbox("冲击情景", ["normal", "peak", "weather", "hub_failure"], index=2)
strategies = st.multiselect("对比策略", ["baseline", "uniform_buffer", "hub_priority", "dynamic_combo"], default=["baseline", "dynamic_combo", "hub_priority", "uniform_buffer"])
view = traj[(traj["scenario"] == scenario) & (traj["strategy"].isin(strategies))]
metric_view = metrics[(metrics["scenario"] == scenario) & (metrics["strategy"].isin(strategies))]

c1, c2, c3 = st.columns(3)
best_delay = metric_view.sort_values("cumulative_delay").iloc[0]
c1.metric("累计延误最小策略", strategy_label(best_delay["strategy"]))
c2.metric("累计延误", f"{best_delay['cumulative_delay']:.0f}")
c3.metric("恢复时间", f"{best_delay['recovery_time']:.0f} 小时")

fig = px.line(view, x="hour", y="performance", color="strategy", title="系统性能恢复曲线")
st.plotly_chart(fig, use_container_width=True)

fig2 = px.line(view, x="hour", y="total_delay", color="strategy", title="全网总延误随时间变化")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("策略指标表")
st.dataframe(metric_view, use_container_width=True, hide_index=True)

