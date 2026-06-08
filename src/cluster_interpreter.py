"""Interpret KMeans clusters as readable roles without exposing raw chat text."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

SUMMARY_FEATURE_LIMIT = 4


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
