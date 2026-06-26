from __future__ import annotations

import plotly.express as px
import streamlit as st

from common import conclusion, image, read_json, read_parquet, setup_page


setup_page("数据驾驶舱")
st.title("数据驾驶舱")
conclusion("2024 年 1-3 月前 30 个机场样本显示，延误具有明显时段差异和节点差异，航班量并不等于最高延误风险。")

kpi = read_json("kpi_summary.json")
daily = read_parquet("dashboard_daily.parquet")
airport = read_parquet("dashboard_airports.parquet")
heat = read_parquet("dashboard_heatmap.parquet")

cols = st.columns(4)
cols[0].metric("完成航班", f"{kpi['completed_flights']:,}")
cols[1].metric("平均延误", f"{kpi['avg_arr_delay']:.1f} 分钟")
cols[2].metric("取消率", f"{kpi['cancel_rate']:.1%}")
cols[3].metric("日期范围", f"{kpi['date_min']} 至 {kpi['date_max']}")

airport_filter = st.multiselect("机场筛选", sorted(airport["Origin"].unique()), default=sorted(airport["Origin"].unique())[:8])
airport_view = airport[airport["Origin"].isin(airport_filter)] if airport_filter else airport

c1, c2 = st.columns([1.1, 1])
with c1:
    fig = px.line(daily, x="FlightDate", y=["flights", "delay_rate"], title="每日航班量与延误率")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig = px.bar(airport_view.sort_values("delay_rate", ascending=True), x="delay_rate", y="Origin", orientation="h", title="机场延误率")
    st.plotly_chart(fig, use_container_width=True)

heat_fig = px.density_heatmap(heat, x="crs_dep_hour", y="DayOfWeek", z="delay_rate", histfunc="avg", title="星期 × 起飞小时延误率")
st.plotly_chart(heat_fig, use_container_width=True)

with st.expander("报告图表预览"):
    c3, c4 = st.columns(2)
    with c3:
        image("fig_09_volume_delay_scatter.png")
    with c4:
        image("fig_13_split_delay_rate.png")
