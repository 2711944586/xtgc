from __future__ import annotations

from common import conclusion, image, read_csv, read_json, setup_page

import streamlit as st


setup_page("首页")

st.title("FlightResilience：航空网络延误传播与恢复决策支持系统")
conclusion("本系统把 BTS 真实航班数据、延误预测、机场网络、动态传播仿真和多准则决策连接成一个闭环。")

kpi = read_json("kpi_summary.json")
decision = read_json("decision_summary.json")

cols = st.columns(4)
cols[0].metric("样本航班", f"{kpi['flights']:,}")
cols[1].metric("机场数量", f"{kpi['airport_count']}")
cols[2].metric("到达延误率", f"{kpi['delay_rate']:.1%}")
cols[3].metric("主推荐策略", decision["recommended_strategy"])

st.markdown(
    "<span class='fr-chip'>系统分析</span><span class='fr-chip'>复杂网络</span><span class='fr-chip'>状态空间</span>"
    "<span class='fr-chip'>AHP + 熵权 + TOPSIS</span><span class='fr-chip'>风险决策</span>",
    unsafe_allow_html=True,
)

left, right = st.columns([1.05, 1])
with left:
    st.subheader("研究闭环")
    st.markdown(
        """
        1. BTS 公开数据形成可追溯样本。
        2. 计划阶段模型预测单航班延误风险。
        3. 机场有向网络识别关键传播节点。
        4. 机场小时状态方程模拟扰动传播。
        5. 四种恢复策略在同一预算与情景下比较。
        6. 系统评价和风险决策给出有条件建议。
        """
    )
with right:
    image("fig_29_recovery_curves.png", "天气冲击下的策略恢复曲线")

ranking = read_csv("strategy_rankings.csv")
st.subheader("主决策偏好下的策略排名")
st.dataframe(ranking, use_container_width=True, hide_index=True)

