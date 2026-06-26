from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

from common import conclusion, image, read_csv, setup_page


setup_page("机场网络")
st.title("机场网络")
conclusion("高航班量机场不必然是最高传播关键节点；综合流量、介数中心性、延误率和预测风险后，MIA、DEN、DFW 等节点位于关键性前列。")

nodes = read_csv("airport_nodes.csv")
edges = read_csv("airport_edges.csv")
top_n = st.slider("显示机场数量", 5, 30, 18)
metric = st.selectbox("节点颜色", ["criticality", "delay_rate", "avg_risk", "betweenness"])
selected_nodes = nodes.sort_values("criticality", ascending=False).head(top_n)["airport"].tolist()
edges_view = edges[edges["Origin"].isin(selected_nodes) & edges["Dest"].isin(selected_nodes)]

G = nx.DiGraph()
for airport in selected_nodes:
    G.add_node(airport)
for row in edges_view.itertuples(index=False):
    G.add_edge(row.Origin, row.Dest, weight=float(row.flights))
pos = nx.spring_layout(G, seed=42, weight="weight")
edge_x, edge_y = [], []
for u, v in G.edges():
    edge_x += [pos[u][0], pos[v][0], None]
    edge_y += [pos[u][1], pos[v][1], None]
node_view = nodes[nodes["airport"].isin(selected_nodes)].set_index("airport").loc[selected_nodes].reset_index()
fig = go.Figure()
fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color="#9AA9B7", width=0.7), hoverinfo="none"))
fig.add_trace(
    go.Scatter(
        x=[pos[a][0] for a in selected_nodes],
        y=[pos[a][1] for a in selected_nodes],
        mode="markers+text",
        text=selected_nodes,
        textposition="top center",
        marker=dict(size=14 + 30 * node_view["departures"] / node_view["departures"].max(), color=node_view[metric], colorscale="YlOrRd", showscale=True),
        hovertemplate="<b>%{text}</b><extra></extra>",
    )
)
fig.update_layout(height=560, margin=dict(l=10, r=10, t=20, b=10), plot_bgcolor="white", showlegend=False)
st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns([1, 1])
with c1:
    st.subheader("关键机场排名")
    st.dataframe(nodes.sort_values("criticality", ascending=False).head(10), use_container_width=True, hide_index=True)
with c2:
    image("fig_22_network_risk_scatter.png", "中心性-风险-航班量关系")
