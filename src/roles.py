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
    gates: tuple[tuple[str, float], ...] = ()
    boosts: tuple[tuple[str, float, float], ...] = ()


ROLE_DEFINITIONS = [
    RoleDefinition(
        "\u9ad8\u983b\u6838\u5fc3\u578b",
        "\u4e92\u52d5\u91cf\u548c\u6d3b\u8e8d\u5929\u6578\u90fd\u504f\u9ad8\uff0c\u662f\u7fa4\u7d44\u8a0e\u8ad6\u7684\u4e3b\u8981\u63a8\u9032\u8005\u3002",
        ("message_count", "active_days", "avg_messages_per_day"),
        (("message_count", 0.80),),
        (("message_count", 0.85, 1.0), ("active_days", 0.80, 0.4)),
    ),
    RoleDefinition(
        "\u8a71\u984c\u555f\u52d5\u578b",
        "\u5e38\u958b\u555f\u65b0\u8a71\u984c\u6216\u63d0\u51fa\u554f\u984c\uff0c\u6703\u628a\u5c0d\u8a71\u5f80\u4e0b\u4e00\u6bb5\u63a8\u9032\u3002",
        ("topic_start_count", "question_ratio"),
        (("topic_start_count", 0.65),),
        (("topic_start_count", 0.75, 0.8), ("question_ratio", 0.75, 0.7)),
    ),
    RoleDefinition(
        "\u8868\u60c5\u56de\u61c9\u578b",
        "\u5e38\u7528\u8cbc\u5716\u6216\u8868\u60c5\u5feb\u901f\u4e92\u52d5\uff0c\u8b93\u7fa4\u7d44\u6c23\u6c1b\u4fdd\u6301\u8f15\u9b06\u3002",
        ("sticker_ratio", "emoji_ratio", "reply_like_ratio"),
        (("sticker_ratio", 0.70),),
        (("sticker_ratio", 0.80, 0.8), ("emoji_ratio", 0.80, 0.5)),
    ),
    RoleDefinition(
        "\u5716\u50cf\u5206\u4eab\u578b",
        "\u504f\u597d\u7528\u5716\u7247\u6216\u5a92\u9ad4\u88dc\u5145\u8cc7\u8a0a\uff0c\u5716\u50cf\u578b\u4e92\u52d5\u8f03\u660e\u986f\u3002",
        ("image_ratio",),
        (("image_ratio", 0.85),),
        (("image_ratio", 0.90, 1.0),),
    ),
    RoleDefinition(
        "\u8cc7\u8a0a\u8f49\u8b6f\u578b",
        "\u5e38\u5206\u4eab\u9023\u7d50\u6216\u8cc7\u8a0a\uff0c\u8a5e\u5f59\u8b8a\u5316\u4e5f\u6bd4\u8f03\u9ad8\u3002",
        ("url_ratio", "unique_word_ratio", "avg_message_length"),
        (("url_ratio", 0.65),),
        (("url_ratio", 0.80, 0.9), ("unique_word_ratio", 0.80, 0.5)),
    ),
    RoleDefinition(
        "\u591c\u9593\u9577\u6587\u578b",
        "\u5e38\u5728\u591c\u9593\u51fa\u73fe\uff0c\u8a0a\u606f\u4e5f\u6bd4\u8f03\u5b8c\u6574\uff0c\u9069\u5408\u627f\u63a5\u9700\u8981\u8108\u7d61\u7684\u8a0e\u8ad6\u3002",
        ("night_ratio", "avg_message_length", "median_message_length"),
        (("avg_message_length", 0.75),),
        (("night_ratio", 0.75, 0.6), ("avg_message_length", 0.85, 0.8)),
    ),
    RoleDefinition(
        "\u601d\u8003\u56de\u8986\u578b",
        "\u56de\u8986\u6bd4\u4f8b\u9ad8\u4e14\u5167\u5bb9\u8f03\u5b8c\u6574\uff0c\u5e38\u626e\u6f14\u6574\u7406\u8207\u88dc\u5145\u7684\u89d2\u8272\u3002",
        ("reply_like_ratio", "avg_response_time_min", "avg_message_length"),
        (("reply_like_ratio", 0.75),),
        (("reply_like_ratio", 0.85, 0.8), ("avg_message_length", 0.70, 0.4)),
    ),
    RoleDefinition(
        "\u7a69\u5b9a\u53c3\u8207\u578b",
        "\u5404\u9805\u4e92\u52d5\u7279\u5fb5\u76f8\u5c0d\u5e73\u5747\uff0c\u662f\u7fa4\u7d44\u4e2d\u7684\u7a69\u5b9a\u53c3\u8207\u8005\u3002",
        ("text_ratio", "morning_ratio", "afternoon_ratio", "evening_ratio"),
    ),
]

FALLBACK_ROLE = ROLE_DEFINITIONS[-1]


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
    metric_scores = [float(z_frame.at[user, metric]) for metric in role.metrics if metric in z_frame.columns]
    if not metric_scores:
        return -999.0

    score = float(np.mean(metric_scores))
    unmet_gates = 0
    for metric, threshold in role.gates:
        if metric not in pct_frame.columns or float(pct_frame.at[user, metric]) < threshold:
            unmet_gates += 1
    score -= 1.25 * unmet_gates

    for metric, threshold, boost in role.boosts:
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
    """Attach role details to every user row using gated per-user scores."""

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
        if selected_role is FALLBACK_ROLE and len(ROLE_DEFINITIONS) > 1:
            non_fallback_score, non_fallback_role = max(scored_roles[:-1], key=lambda item: item[0])
            fallback_score = _role_score(user, FALLBACK_ROLE, z_frame, pct_frame)
            if non_fallback_score >= fallback_score - 0.2:
                selected_role = non_fallback_role
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

