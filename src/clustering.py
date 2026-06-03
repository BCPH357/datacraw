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
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run KMeans for K=2..min(4, n_users-1) and select the best silhouette."""

    if features.empty:
        return pd.DataFrame(), {"best_k": 0, "silhouette_scores": {}}

    matrix = numeric_feature_matrix(features)
    n_users = len(matrix)
    result = features.copy()
    if n_users < 2:
        result["cluster"] = 0
        metadata = {"best_k": 1, "silhouette_scores": {}, "feature_columns": list(matrix.columns)}
    else:
        scaled = StandardScaler().fit_transform(matrix)
        max_k = min(4, n_users - 1)
        silhouette_scores: dict[int, float] = {}
        labels_by_k: dict[int, np.ndarray] = {}
        for k in range(2, max_k + 1):
            model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
            labels = model.fit_predict(scaled)
            labels_by_k[k] = labels
            silhouette_scores[k] = float(silhouette_score(scaled, labels)) if len(set(labels)) > 1 else -1.0

        best_k = max(silhouette_scores, key=silhouette_scores.get) if silhouette_scores else 1
        result["cluster"] = labels_by_k[best_k] if best_k in labels_by_k else 0
        metadata = {
            "best_k": int(best_k),
            "silhouette_scores": {str(k): v for k, v in silhouette_scores.items()},
            "feature_columns": list(matrix.columns),
        }

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_path, encoding="utf-8-sig")
    return result, metadata

