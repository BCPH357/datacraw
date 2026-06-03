"""Assign readable persona roles from user-level feature patterns."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    description: str
    metrics: tuple[str, ...]
    raw_boosts: tuple[tuple[str, float, float], ...] = ()


ROLE_DEFINITIONS = [
    RoleDefinition(
        "高頻核心型",
        "互動量和活躍天數都偏高，是群組討論的主要推進者。",
        ("message_count", "active_days", "avg_messages_per_day"),
        (("message_count", 0.70, 0.9),),
    ),
    RoleDefinition(
        "話題啟動型",
        "常開啟新話題或提出問題，會把對話往下一段推進。",
        ("topic_start_count", "question_ratio"),
        (("topic_start_count", 0.70, 0.8), ("question_ratio", 0.70, 0.6)),
    ),
    RoleDefinition(
        "表情回應型",
        "常用貼圖或表情快速互動，讓群組氣氛保持輕鬆。",
        ("sticker_ratio", "emoji_ratio"),
        (("sticker_ratio", 0.65, 1.0), ("emoji_ratio", 0.65, 0.8)),
    ),
    RoleDefinition(
        "圖像分享型",
        "偏好用圖片或媒體補充資訊，圖像型互動較明顯。",
        ("image_ratio",),
        (("image_ratio", 0.65, 1.0),),
    ),
    RoleDefinition(
        "資訊轉譯型",
        "常分享連結或資訊，詞彙變化也比較高。",
        ("url_ratio", "unique_word_ratio"),
        (("url_ratio", 0.60, 1.0), ("unique_word_ratio", 0.75, 0.5)),
    ),
    RoleDefinition(
        "夜間長文型",
        "常在夜間出現，訊息也比較完整，適合承接需要脈絡的討論。",
        ("night_ratio", "avg_message_length", "median_message_length"),
        (("night_ratio", 0.65, 0.9), ("avg_message_length", 0.70, 0.5)),
    ),
    RoleDefinition(
        "思考回覆型",
        "回覆比例高且內容較完整，常扮演整理與補充的角色。",
        ("reply_like_ratio", "avg_response_time_min", "avg_message_length"),
        (("reply_like_ratio", 0.70, 0.8),),
    ),
    RoleDefinition(
        "穩定參與型",
        "各項互動特徵相對平均，是群組中的穩定參與者。",
        ("text_ratio", "morning_ratio", "afternoon_ratio", "evening_ratio"),
    ),
]


def _numeric_features(features: pd.DataFrame) -> pd.DataFrame:
    return features.select_dtypes(include=[np.number]).drop(columns=["cluster"], errors="ignore").fillna(0)


def _z_scores(features: pd.DataFrame) -> pd.DataFrame:
    numeric = _numeric_features(features)
    std = numeric.std(ddof=0).replace(0, 1)
    return (numeric - numeric.mean()) / std


def _percentile_scores(features: pd.DataFrame) -> pd.DataFrame:
    numeric = _numeric_features(features)
    if numeric.empty:
        return numeric
    return numeric.rank(pct=True, method="average")


def _role_score(user: str, role: RoleDefinition, z_frame: pd.DataFrame, pct_frame: pd.DataFrame) -> float:
    scores = [float(z_frame.at[user, metric]) for metric in role.metrics if metric in z_frame.columns]
    score = max(scores) if scores else -999.0
    for metric, threshold, boost in role.raw_boosts:
        if metric in pct_frame.columns and float(pct_frame.at[user, metric]) >= threshold:
            score += boost
    return score


def _top_features(user: str, z_frame: pd.DataFrame, role: RoleDefinition) -> list[str]:
    preferred = [metric for metric in role.metrics if metric in z_frame.columns]
    ranked = z_frame.loc[user].sort_values(ascending=False)
    output: list[str] = []
    for metric in preferred:
        if metric in ranked.index and len(output) < 3:
            output.append(metric)
    for metric in ranked.index:
        if metric not in output and len(output) < 3:
            output.append(str(metric))
    return output


def assign_user_roles(clustered_features: pd.DataFrame) -> pd.DataFrame:
    """Attach role details to every user row using per-user feature scores."""

    if clustered_features.empty:
        return pd.DataFrame()

    features = clustered_features.copy()
    z_frame = _z_scores(features)
    pct_frame = _percentile_scores(features)
    rows = []
    for user, row in features.iterrows():
        scored_roles = [
            (_role_score(user, role, z_frame, pct_frame), role)
            for role in ROLE_DEFINITIONS
        ]
        _, selected_role = max(scored_roles, key=lambda item: item[0])
        payload = row.to_dict()
        payload.update(
            {
                "user": user,
                "role_name": selected_role.name,
                "top_features": _top_features(user, z_frame, selected_role),
                "description": selected_role.description,
            }
        )
        rows.append(payload)
    return pd.DataFrame(rows).set_index("user")


def assign_roles(clustered_features: pd.DataFrame) -> pd.DataFrame:
    """Summarize dominant user-level roles per cluster."""

    if clustered_features.empty:
        return pd.DataFrame(columns=["cluster", "role_name", "top_features", "description"])

    user_roles = assign_user_roles(clustered_features)
    rows = []
    for cluster, cluster_rows in user_roles.groupby("cluster", sort=True):
        dominant_role = cluster_rows["role_name"].mode().iloc[0]
        example = cluster_rows[cluster_rows["role_name"] == dominant_role].iloc[0]
        rows.append(
            {
                "cluster": int(cluster),
                "role_name": dominant_role,
                "top_features": example["top_features"],
                "description": example["description"],
            }
        )
    return pd.DataFrame(rows)


def roles_by_user(clustered_features: pd.DataFrame, role_table: pd.DataFrame | None = None) -> pd.DataFrame:
    """Backward-compatible wrapper for per-user role assignment."""

    return assign_user_roles(clustered_features)

