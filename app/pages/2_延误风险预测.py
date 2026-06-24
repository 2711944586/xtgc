from __future__ import annotations

import joblib
import pandas as pd
import plotly.express as px
import streamlit as st

from common import DEMO_DIR, MODELS_DIR, conclusion, image, read_csv, read_json, read_parquet, setup_page


setup_page("延误风险预测")
st.title("延误风险预测")
conclusion("模型只使用计划阶段与历史统计特征，输出作为传播仿真和策略优先级的风险输入，而不是孤立的最终目标。")

options = read_json("prediction_options.json")
routes = read_parquet("route_options.parquet")
model = joblib.load(MODELS_DIR / "delay_model.joblib")
spec = joblib.load(MODELS_DIR / "feature_spec.joblib")
metrics = read_json("model_metrics.json")

left, right = st.columns([0.8, 1.2])
with left:
    origin = st.selectbox("Origin", options["airports"], index=options["airports"].index("DEN") if "DEN" in options["airports"] else 0)
    dest_options = sorted(routes[routes["Origin"] == origin]["Dest"].unique().tolist()) or options["airports"]
    dest = st.selectbox("Dest", dest_options)
    airline = st.selectbox("Airline", options["airlines"])
    day = st.slider("Day of week", 1, 7, 3)
    hour = st.slider("Planned departure hour", 0, 23, 16)
    route_row = routes[(routes["Origin"] == origin) & (routes["Dest"] == dest)].head(1)
    distance = float(route_row["distance"].iloc[0]) if len(route_row) else options["distance_median"]
    elapsed = float(route_row["crs_elapsed"].iloc[0]) if len(route_row) else options["elapsed_median"]
    congestion_default = round(float(options["hist_delay_rate"]), 2)
    congestion = st.slider("Origin rolling 3h delay rate", 0.0, 0.8, congestion_default, 0.01)

row = pd.DataFrame(
    [
        {
            "Month": 3,
            "DayOfWeek": day,
            "is_weekend": int(day in [6, 7]),
            "crs_dep_hour": hour,
            "Distance": distance,
            "CRSElapsedTime": elapsed,
            "origin_hist_delay_rate": options["hist_delay_rate"],
            "dest_hist_delay_rate": options["hist_delay_rate"],
            "route_hist_delay_rate": float(route_row["delay_rate"].iloc[0]) if len(route_row) else options["hist_delay_rate"],
            "airline_hist_delay_rate": options["hist_delay_rate"],
            "origin_hour_hist_delay_rate": options["hist_delay_rate"],
            "origin_rolling_3h_delay_rate": congestion,
            "origin_rolling_3h_volume": options["rolling_volume_median"],
            "hour_sin": __import__("math").sin(2 * __import__("math").pi * hour / 24),
            "hour_cos": __import__("math").cos(2 * __import__("math").pi * hour / 24),
            "month_sin": 1.0,
            "month_cos": 0.0,
            "Origin": origin,
            "Dest": dest,
            "Reporting_Airline": airline,
            "dep_time_block": "evening_peak" if 16 <= hour <= 19 else "midday",
        }
    ]
)
prob = float(model.predict_proba(row[spec["features"]])[:, 1][0])
threshold = float(spec["threshold"])
risk_level = "高风险" if prob >= threshold else ("中风险" if prob >= threshold * 0.65 else "低风险")

with left:
    st.metric("延误概率", f"{prob:.1%}")
    st.metric("风险等级", risk_level)
    st.caption(f"当前分类阈值：{threshold:.2f}")

with right:
    shap_df = read_csv("shap_summary.csv").head(10)
    fig = px.bar(shap_df.sort_values("mean_abs_shap"), x="mean_abs_shap", y="source_feature", orientation="h", title="全局解释：SHAP Top 10")
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"最佳模型：{metrics['best_model']}；测试 ROC-AUC {metrics['best_test_metrics']['roc_auc']:.3f}，PR-AUC {metrics['best_test_metrics']['pr_auc']:.3f}。")

image("fig_17_calibration_curve.png", "概率校准曲线")
