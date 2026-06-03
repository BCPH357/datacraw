"""Streamlit UI for LINE chat persona analysis."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import clustering, features, parser, report, roles, viz


st.set_page_config(page_title="LINE Persona Analyzer", layout="wide")
st.title("LINE Persona Analyzer")

uploaded = st.file_uploader("Upload LINE chat export", type=["txt"])
if uploaded:
    text = uploaded.getvalue().decode("utf-8-sig", errors="replace")
    parsed = parser.parse_text(text)
    records = parser.to_dataframe(parsed)
    summary = parser.summarize(parsed)
    feature_frame = features.extract_features(records)
    clustered, metadata = clustering.cluster_users(feature_frame)
    role_table = roles.assign_roles(clustered)
    user_roles = roles.roles_by_user(clustered, role_table)
    personas = report.build_personas(user_roles)
    group_health = report.build_group_health(user_roles, metadata)

    cols = st.columns(4)
    cols[0].metric("Messages", summary["message_count"])
    cols[1].metric("Users", summary["user_count"])
    cols[2].metric("Health", group_health["group_health_score"])
    cols[3].metric("Best K", metadata.get("best_k", 0))

    st.subheader("Personas")
    st.dataframe(user_roles[["role_name", "description", "message_count", "text_ratio", "sticker_ratio"]])

    with tempfile.TemporaryDirectory() as temp_dir:
        chart_paths = viz.generate_all(records, feature_frame, clustered, user_roles, temp_dir)
        chart_cols = st.columns(2)
        for index, chart_path in enumerate(chart_paths):
            chart_cols[index % 2].image(str(chart_path))

    st.subheader("Downloads")
    st.download_button("personas.json", data=report.json.dumps(personas, ensure_ascii=False, indent=2), file_name="personas.json")
    st.download_button("group_health.json", data=report.json.dumps(group_health, ensure_ascii=False, indent=2), file_name="group_health.json")
else:
    st.info("Upload a LINE `.txt` export to start.")

