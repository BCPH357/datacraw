"""Cluster users from extracted chat features."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def numeric_feature_matrix(features: pd.DataFrame) -> pd.DataFrame:
    """Return numeric columns suitable for clustering."""

    matrix = features.select_dtypes(include=[np.number]).copy()
    return matrix.replace([np.inf, -np.inf], 0).fillna(0)


def cluster_users(
    features: pd.DataFrame,
    output_path: str | Path | None = None,
    random_state: int = 42,
    cluster_count: int | str | None = "auto",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run KMeans and optionally let callers request a fixed cluster count."""

    if features.empty:
        return pd.DataFrame(), {"best_k": 0, "silhouette_scores": {}}

    matrix = numeric_feature_matrix(features)
    n_users = len(matrix)
    result = features.copy()
    requested_k = _requested_cluster_count(cluster_count)
    if n_users < 2:
        if requested_k is not None:
            raise ValueError("分群數至少需要 2 位以上成員。")
        result["cluster"] = 0
        metadata = {
            "best_k": 1,
            "cluster_selection": "auto",
            "silhouette_scores": {},
            "feature_columns": list(matrix.columns),
        }
    else:
        scaled = StandardScaler().fit_transform(matrix)
        max_k = min(5, n_users - 1)
        if requested_k is not None and requested_k > max_k:
            raise ValueError(f"分群數 {requested_k} 超過可用成員數，最多只能分 {max_k} 群。")
        silhouette_scores: dict[int, float] = {}
        labels_by_k: dict[int, np.ndarray] = {}
        candidates = [requested_k] if requested_k is not None else range(2, max_k + 1)
        for k in candidates:
            model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
            labels = model.fit_predict(scaled)
            labels_by_k[k] = labels
            silhouette_scores[k] = float(silhouette_score(scaled, labels)) if len(set(labels)) > 1 else -1.0

        best_k = requested_k or (max(silhouette_scores, key=silhouette_scores.get) if silhouette_scores else 1)
        result["cluster"] = labels_by_k[best_k] if best_k in labels_by_k else 0
        metadata = {
            "best_k": int(best_k),
            "cluster_selection": str(cluster_count or "auto"),
            "silhouette_scores": {str(k): v for k, v in silhouette_scores.items()},
            "feature_columns": list(matrix.columns),
        }

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_path, encoding="utf-8-sig")
    return result, metadata


def _requested_cluster_count(cluster_count: int | str | None) -> int | None:
    if cluster_count in (None, "", "auto"):
        return None
    try:
        requested = int(cluster_count)
    except (TypeError, ValueError) as error:
        raise ValueError("分群數必須是 auto、3、4 或 5。") from error
    if requested not in {3, 4, 5}:
        raise ValueError("分群數必須是 auto、3、4 或 5。")
    return requested

