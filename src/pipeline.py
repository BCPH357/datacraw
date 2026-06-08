"""End-to-end analysis orchestration shared by the web server and Streamlit.

``analyze_text`` runs the full pipeline (parser → features → clustering → roles
→ report) on raw export text and returns the React ``APP_DATA`` payload plus the
JSON report artifacts, without writing anything to disk.
"""

from __future__ import annotations

from typing import Any

from . import cluster_interpreter, clustering, features, parser, report, roles, webreport

VALID_ANALYSIS_MODES = {"rule", "ai_cluster"}


def analyze_text(text: str, mode: str = "rule") -> dict[str, Any]:
    """Run the full pipeline on raw LINE export text.

    Returns a dict with ``app_data`` (for the React UI), ``personas``,
    ``group_health`` and ``summary``. Raises ``ValueError`` when the text has no
    analyzable user messages.
    """

    if mode not in VALID_ANALYSIS_MODES:
        raise ValueError(f"Unsupported analysis mode: {mode}")

    parsed = parser.parse_text(text)
    records = parser.to_dataframe(parsed)
    summary = parser.summarize(parsed)
    if records.empty or records[~records["is_system"]].empty:
        raise ValueError("找不到任何可分析的使用者訊息，請確認這是 LINE 匯出的 .txt 檔。")

    feature_frame = features.extract_features(records)
    clustered, metadata = clustering.cluster_users(feature_frame)
    if mode == "rule":
        role_table = roles.assign_roles(clustered)
        user_roles = roles.roles_by_user(clustered, role_table)
        cluster_interpretations: list[dict[str, Any]] = []
    else:
        cluster_summaries = cluster_interpreter.build_cluster_summaries(clustered, feature_frame)
        cluster_interpretations = cluster_interpreter.interpret_clusters_with_openai(cluster_summaries)
        user_roles = cluster_interpreter.apply_cluster_interpretations(clustered, cluster_interpretations)
    personas = report.build_personas(user_roles)
    group_health = report.build_group_health(user_roles, metadata)
    app_data = webreport.build_app_data(
        records,
        feature_frame,
        clustered,
        user_roles,
        group_health,
        metadata,
        summary,
        analysis_mode=mode,
        cluster_interpretations=cluster_interpretations,
    )
    return {
        "app_data": app_data,
        "personas": personas,
        "group_health": group_health,
        "summary": summary,
    }
