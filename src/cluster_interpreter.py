"""Interpret KMeans clusters as readable roles without exposing raw chat text."""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import pandas as pd

SUMMARY_FEATURE_LIMIT = 4
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class ClusterInterpretationError(RuntimeError):
    """Raised when AI cluster interpretation cannot complete safely."""


def _numeric(frame: pd.DataFrame) -> pd.DataFrame:
    """Return numeric behavior features, excluding the cluster label."""

    return (
        frame.select_dtypes(include=[np.number])
        .drop(columns=["cluster"], errors="ignore")
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
    )


def build_cluster_summaries(
    clustered_features: pd.DataFrame,
    feature_frame: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    """Create privacy-preserving statistical summaries for each cluster."""

    if clustered_features.empty or "cluster" not in clustered_features.columns:
        return []

    numeric = _numeric(clustered_features)
    if numeric.empty:
        return [
            {
                "cluster": int(cluster_id),
                "member_count": int(len(rows)),
                "feature_means": {},
                "top_high_features": [],
                "top_low_features": [],
            }
            for cluster_id, rows in clustered_features.groupby("cluster", sort=True)
        ]

    global_mean = numeric.mean()
    global_std = numeric.std(ddof=0).replace(0, 1)
    summaries: list[dict[str, Any]] = []

    for cluster_id, rows in clustered_features.groupby("cluster", sort=True):
        cluster_numeric = numeric.loc[rows.index]
        means = cluster_numeric.mean()
        z_scores = ((means - global_mean) / global_std).replace([np.inf, -np.inf], 0).fillna(0)
        summaries.append(
            {
                "cluster": int(cluster_id),
                "member_count": int(len(rows)),
                "feature_means": {str(key): float(value) for key, value in means.round(4).items()},
                "top_high_features": [
                    str(key) for key in z_scores.sort_values(ascending=False).head(SUMMARY_FEATURE_LIMIT).index
                ],
                "top_low_features": [
                    str(key) for key in z_scores.sort_values(ascending=True).head(SUMMARY_FEATURE_LIMIT).index
                ],
            }
        )
    return summaries


def apply_cluster_interpretations(
    clustered_features: pd.DataFrame,
    interpretations: list[dict[str, Any]],
) -> pd.DataFrame:
    """Attach cluster-level AI interpretations to each user row."""

    by_cluster = {int(item["cluster"]): item for item in interpretations}
    rows = []
    for user, row in clustered_features.iterrows():
        cluster_id = int(row["cluster"])
        interpretation = by_cluster[cluster_id]
        payload = row.to_dict()
        payload.update(
            {
                "user": user,
                "role_name": str(interpretation["roleName"]),
                "top_features": [str(item) for item in interpretation.get("evidence", [])][:3],
                "description": str(interpretation.get("description") or interpretation.get("tagline") or ""),
                "tagline": str(interpretation.get("tagline") or ""),
            }
        )
        rows.append(payload)
    return pd.DataFrame(rows).set_index("user")


def attach_members_to_interpretations(
    clustered_features: pd.DataFrame,
    interpretations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add display-only member names after AI interpretation returns."""

    members_by_cluster: dict[int, list[str]] = {}
    if "cluster" in clustered_features.columns:
        for cluster_id, rows in clustered_features.groupby("cluster", sort=True):
            members_by_cluster[int(cluster_id)] = [str(user) for user in rows.index]

    enriched = []
    for item in interpretations:
        cluster_id = int(item["cluster"])
        payload = dict(item)
        payload["members"] = members_by_cluster.get(cluster_id, [])
        enriched.append(payload)
    return enriched


def normalize_interpretations(
    payload: dict[str, Any],
    summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate and normalize structured AI output."""

    expected = {int(summary["cluster"]) for summary in summaries}
    clusters = payload.get("clusters")
    if not isinstance(clusters, list):
        raise ClusterInterpretationError("AI 回傳格式缺少 clusters。")

    normalized: list[dict[str, Any]] = []
    seen: set[int] = set()
    for item in clusters:
        try:
            cluster_id = int(item["cluster"])
            role_name = str(item["roleName"])
            tagline = str(item["tagline"])
            description = str(item["description"])
        except (KeyError, TypeError, ValueError) as error:
            raise ClusterInterpretationError(f"AI 回傳 cluster 欄位不完整：{error}") from error

        evidence = item.get("evidence") or []
        if not isinstance(evidence, list):
            raise ClusterInterpretationError("AI 回傳 evidence 必須是陣列。")

        seen.add(cluster_id)
        normalized.append(
            {
                "cluster": cluster_id,
                "roleName": role_name,
                "tagline": tagline,
                "description": description,
                "evidence": [str(value) for value in evidence][:5],
            }
        )

    missing = expected - seen
    if missing:
        raise ClusterInterpretationError(f"AI 回傳缺少 cluster: {sorted(missing)}")
    return sorted(normalized, key=lambda item: item["cluster"])


def _response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "clusters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "cluster": {"type": "integer"},
                        "roleName": {"type": "string"},
                        "tagline": {"type": "string"},
                        "description": {"type": "string"},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["cluster", "roleName", "tagline", "description", "evidence"],
                },
            }
        },
        "required": ["clusters"],
    }


def interpret_clusters_with_openai(
    summaries: list[dict[str, Any]],
    model: str | None = None,
) -> list[dict[str, Any]]:
    """Use OpenAI to name and explain clusters from statistics only."""

    if not os.getenv("OPENAI_API_KEY"):
        raise ClusterInterpretationError("AI 分析需要後端設定 OPENAI_API_KEY。")

    try:
        from openai import OpenAI
    except ImportError as error:
        raise ClusterInterpretationError("AI 分析需要安裝 openai 套件。") from error

    client = OpenAI()
    selected_model = model or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    prompt = {
        "instruction": "根據分群統計摘要，為每個 cluster 產生繁體中文角色名稱與解釋。不要要求或推測原始聊天內容。",
        "clusters": summaries,
    }

    try:
        response = client.responses.create(
            model=selected_model,
            input=[
                {
                    "role": "system",
                    "content": "你是資料探勘報告助教，只根據統計摘要解釋分群。請輸出 JSON。",
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "cluster_interpretations",
                    "strict": True,
                    "schema": _response_schema(),
                }
            },
        )
    except Exception as error:  # noqa: BLE001 - normalize provider errors for UI
        raise ClusterInterpretationError(f"OpenAI 分析失敗：{error}") from error

    try:
        return normalize_interpretations(json.loads(response.output_text), summaries)
    except (AttributeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise ClusterInterpretationError(f"AI 回傳格式無法解析：{error}") from error
