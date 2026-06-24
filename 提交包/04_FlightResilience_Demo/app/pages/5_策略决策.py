from __future__ import annotations

import plotly.express as px
import streamlit as st

from common import conclusion, image, read_csv, read_json, setup_page, strategy_label


setup_page("策略决策")
st.title("策略决策")
conclusion("恢复/韧性优先时推荐动态组合策略；当决策者极端重视零成本或状态概率按保守损失估计时，基准策略可能反超。")

decision = read_json("decision_summary.json")
ranking = read_csv("strategy_rankings.csv")
weights = read_csv("indicator_weights.csv")
fuzzy = read_csv("fuzzy_evaluation.csv")
risk = read_csv("risk_decision.csv")
uncertain = read_csv("uncertainty_decision.csv")
sensitivity = read_csv("weight_sensitivity.csv")

c1, c2, c3 = st.columns(3)
c1.metric("主推荐", strategy_label(decision["recommended_strategy"]))
c2.metric("风险型推荐", strategy_label(decision["risk_recommended_strategy"]))
c3.metric("AHP CR", f"{decision['ahp_consistency']['cr']:.3f}")

left, right = st.columns([1, 1])
with left:
    fig = px.bar(ranking.sort_values("topsis_score"), x="topsis_score", y="strategy", orientation="h", title="TOPSIS 接近度")
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = px.line(sensitivity, x="lambda_ahp", y=["dynamic_combo_rank", "baseline_rank"], title="权重敏感性")
    fig.update_yaxes(autorange="reversed", dtick=1)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("组合权重")
st.dataframe(weights, use_container_width=True, hide_index=True)

st.subheader("模糊评价与风险决策")
c4, c5 = st.columns([1, 1])
with c4:
    st.dataframe(fuzzy, use_container_width=True, hide_index=True)
with c5:
    st.dataframe(risk, use_container_width=True, hide_index=True)

st.subheader("不确定型准则")
st.dataframe(uncertain, use_container_width=True, hide_index=True)

with st.expander("报告图表"):
    image("fig_34_topsis_score.png")
    image("fig_37_weight_sensitivity.png")

