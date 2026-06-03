"""Streamlit UI for LINE chat persona analysis.

Streamlit owns the upload and runs the analysis pipeline, then embeds the React
editorial report (``claude_design/app``) full-height via ``components.html`` with
the real ``APP_DATA`` injected.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import clustering, features, parser, report, roles, webreport

ASSETS_DIR = ROOT / "claude_design" / "app"


st.set_page_config(page_title="LINE 群組人物誌", layout="wide")


def run_pipeline(text: str) -> dict:
    """Run the full analysis pipeline on raw export text."""

    parsed = parser.parse_text(text)
    records = parser.to_dataframe(parsed)
    summary = parser.summarize(parsed)
    if records.empty or records[~records["is_system"]].empty:
        raise ValueError("找不到任何可分析的使用者訊息，請確認這是 LINE 匯出的 .txt 檔。")

    feature_frame = features.extract_features(records)
    clustered, metadata = clustering.cluster_users(feature_frame)
    role_table = roles.assign_roles(clustered)
    user_roles = roles.roles_by_user(clustered, role_table)
    personas = report.build_personas(user_roles)
    group_health = report.build_group_health(user_roles, metadata)
    app_data = webreport.build_app_data(
        records, feature_frame, clustered, user_roles, group_health, metadata, summary
    )
    return {
        "app_data": app_data,
        "personas": personas,
        "group_health": group_health,
        "summary": summary,
    }


uploaded = st.file_uploader("上傳 LINE 對話記錄 (.txt)", type=["txt"])

if not uploaded:
    st.title("LINE 群組人物誌")
    st.info("上傳一份 LINE 匯出的 `.txt` 對話記錄，即可產生互動式人物誌報告。檔案只在本機處理，不會被保存。")
else:
    text = uploaded.getvalue().decode("utf-8-sig", errors="replace")
    try:
        result = run_pipeline(text)
    except Exception as error:  # noqa: BLE001 - surface a friendly message
        st.error(f"分析失敗：{error}")
    else:
        report_html = webreport.render_html(result["app_data"], ASSETS_DIR, embedded=True)
        components.html(report_html, height=900, scrolling=True)

        with st.expander("下載報告", expanded=False):
            st.download_button(
                "完整 HTML 報告 (可離線開啟)",
                data=report_html,
                file_name="line_persona_report.html",
                mime="text/html",
            )
            st.download_button(
                "personas.json",
                data=json.dumps(result["personas"], ensure_ascii=False, indent=2),
                file_name="personas.json",
                mime="application/json",
            )
            st.download_button(
                "group_health.json",
                data=json.dumps(result["group_health"], ensure_ascii=False, indent=2),
                file_name="group_health.json",
                mime="application/json",
            )
