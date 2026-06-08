"""End-to-end analysis orchestration shared by the web server and Streamlit.

``analyze_text`` runs the full pipeline (parser → features → clustering → roles
→ report) on raw export text and returns the React ``APP_DATA`` payload plus the
JSON report artifacts, without writing anything to disk.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from . import cluster_interpreter, clustering, features, parser, report, roles, webreport

VALID_ANALYSIS_MODES = {"rule", "ai_cluster"}


def analyze_text(
    text: str,
    mode: str = "rule",
    cluster_count: int | str | None = "auto",
    min_share_pct: float = 1.0,
) -> dict[str, Any]:
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
    included_features, excluded_members = _split_by_participation(feature_frame, min_share_pct)
    if excluded_members and len(included_features) < 2:
        raise ValueError("排除門檻過高，剩餘可分析成員不足，請調低門檻。")

    clustered, metadata = clustering.cluster_users(included_features, cluster_count=cluster_count)
    token_usage: dict[str, int] | None = None
    if mode == "rule":
        role_table = roles.assign_roles(clustered)
        user_roles = roles.roles_by_user(clustered, role_table)
        cluster_interpretations: list[dict[str, Any]] = []
    else:
        cluster_summaries = cluster_interpreter.build_cluster_summaries(clustered, included_features)
        cluster_interpretations, token_usage = cluster_interpreter.interpret_clusters_with_openai(cluster_summaries)
        cluster_interpretations = cluster_interpreter.attach_members_to_interpretations(
            clustered,
            cluster_interpretations,
        )
        user_roles = cluster_interpreter.apply_cluster_interpretations(clustered, cluster_interpretations)
    personas = report.build_personas(user_roles)
    group_health = report.build_group_health(user_roles, metadata)
    app_data = webreport.build_app_data(
        records,
        included_features,
        clustered,
        user_roles,
        group_health,
        metadata,
        summary,
        analysis_mode=mode,
        cluster_selection=str(cluster_count or "auto"),
        cluster_interpretations=cluster_interpretations,
        excluded_members=excluded_members,
        token_usage=token_usage,
        exclude_threshold_pct=min_share_pct,
    )
    return {
        "app_data": app_data,
        "personas": personas,
        "group_health": group_health,
        "summary": summary,
    }


def _split_by_participation(
    feature_frame: pd.DataFrame,
    min_share_pct: float,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Split users by their share of the group's total messages.

    Users whose ``message_count`` makes up at most ``min_share_pct`` percent of
    the group total are treated as transient members (joined and left quickly)
    and excluded from clustering. They are still reported back as a separate
    list — name, message count, share — so the UI can show who was left out and
    why, instead of silently dropping them.
    """

    if feature_frame.empty or min_share_pct <= 0:
        return feature_frame, []

    total_messages = feature_frame["message_count"].sum()
    if total_messages <= 0:
        return feature_frame, []

    threshold = min_share_pct / 100.0
    share = feature_frame["message_count"] / total_messages
    excluded_mask = share <= threshold

    excluded = [
        {
            "name": str(user),
            "messageCount": int(feature_frame.loc[user, "message_count"]),
            "sharePct": round(float(share.loc[user]) * 100, 2),
        }
        for user in feature_frame.index[excluded_mask]
    ]
    return feature_frame.loc[~excluded_mask], excluded
