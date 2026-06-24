from __future__ import annotations

import pandas as pd
import streamlit as st

from common import conclusion, read_json, setup_page


setup_page("方法与说明")
st.title("方法与说明")
conclusion("Demo 展示的是预计算或轻量实时计算结果；完整训练、传播估计和评价均由 scripts/ 下的可复现流水线生成。")

st.subheader("固定演示路径")
st.markdown(
    """
    1. 首页说明闭环和主推荐。
    2. 数据驾驶舱查看延误时段差异。
    3. 机场网络点击关键机场 DEN。
    4. 扰动仿真选择 weather 或 hub_failure，对比 baseline 与 dynamic_combo。
    5. 策略决策查看 TOPSIS、风险决策和敏感性反转条件。
    """
)

validation = read_json("propagation_validation.json")
metrics = read_json("model_metrics.json")
st.subheader("模型验证摘要")
st.write(
    pd.DataFrame(
        [
            {"模块": "预测模型", "指标": "测试 ROC-AUC", "数值": f"{metrics['best_test_metrics']['roc_auc']:.3f}"},
            {"模块": "预测模型", "指标": "测试 PR-AUC", "数值": f"{metrics['best_test_metrics']['pr_auc']:.3f}"},
            {"模块": "传播模型", "指标": "单步 MAE", "数值": f"{validation['mae']:.2f}"},
            {"模块": "传播模型", "指标": "谱半径", "数值": f"{validation['spectral_radius_final']:.3f}"},
        ]
    )
)

st.subheader("免责声明")
st.markdown(
    """
    - 数据源为 U.S. DOT BTS TranStats 月度准点文件。
    - 成本、容量下降和恢复资源为透明的相对情景参数，不代表航空公司真实美元成本。
    - SHAP、滞后关系和 ISM 表达结构性解释与关联，不宣称严格因果识别。
    - Demo 默认使用预计算资产，避免课堂现场重新训练导致不稳定。
    """
)

