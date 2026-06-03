"""Assign readable persona roles from clustered feature patterns."""

from __future__ import annotations

import numpy as np
import pandas as pd

ROLE_RULES = [
    ("night_ratio", "avg_message_length", "夜間長文型", "常在深夜出現，訊息也比較完整，適合承接需要脈絡的討論。"),
    ("sticker_ratio", "emoji_ratio", "表情回應型", "常用貼圖或表情互動，讓群組氣氛維持輕鬆。"),
    ("image_ratio", "text_ratio", "圖像分享型", "偏好用圖片或媒體補充資訊，文字比例相對低。"),
    ("message_count", "avg_messages_per_day", "高頻核心型", "互動量明顯較高，是群組討論的主要推進者。"),
    ("topic_start_count", "question_ratio", "話題啟動型", "常開啟新話題或提出問題，帶動對話方向。"),
    ("avg_message_length", "reply_like_ratio", "思考回覆型", "回覆比例高且內容較完整，常扮演整理與補充的角色。"),
    ("url_ratio", "unique_word_ratio", "資訊轉譯型", "常分享連結或資訊，詞彙變化也較高。"),
]


def _z_scores(features: pd.DataFrame) -> pd.DataFrame:
    numeric = features.select_dtypes(include=[np.number]).drop(columns=["cluster"], errors="ignore")
    std = numeric.std(ddof=0).replace(0, 1)
    return (numeric - numeric.mean()) / std


def _top_features(z_frame: pd.DataFrame, members: list[str]) -> list[str]:
    centroid = z_frame.loc[members].mean().sort_values(ascending=False)
    return [str(name) for name in centroid.head(3).index]


def assign_roles(clustered_features: pd.DataFrame) -> pd.DataFrame:
    """Assign a role name and description to each cluster."""

    if clustered_features.empty:
        return pd.DataFrame(columns=["cluster", "role_name", "top_features", "description"])

    features = clustered_features.copy()
    z_frame = _z_scores(features)
    rows: list[dict] = []
    used_names: set[str] = set()

    for cluster, cluster_rows in features.groupby("cluster", sort=True):
        members = list(cluster_rows.index)
        top_features = _top_features(z_frame, members)
        selected_name = "平衡參與型"
        selected_description = "各項互動特徵相對平均，是群組中的穩定參與者。"

        for first, second, name, description in ROLE_RULES:
            if first in top_features or second in top_features:
                if name not in used_names:
                    selected_name = name
                    selected_description = description
                    break

        if selected_name in used_names:
            selected_name = f"{selected_name}-{int(cluster)}"
        used_names.add(selected_name)
        rows.append(
            {
                "cluster": int(cluster),
                "role_name": selected_name,
                "top_features": top_features,
                "description": selected_description,
            }
        )

    return pd.DataFrame(rows)


def roles_by_user(clustered_features: pd.DataFrame, role_table: pd.DataFrame) -> pd.DataFrame:
    """Attach role details to every user row."""

    if clustered_features.empty:
        return pd.DataFrame()
    role_lookup = role_table.set_index("cluster")
    rows = []
    for user, row in clustered_features.iterrows():
        role = role_lookup.loc[row["cluster"]]
        payload = row.to_dict()
        payload.update(
            {
                "user": user,
                "role_name": role["role_name"],
                "top_features": role["top_features"],
                "description": role["description"],
            }
        )
        rows.append(payload)
    return pd.DataFrame(rows).set_index("user")

