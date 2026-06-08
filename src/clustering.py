"""Cluster users from extracted chat features."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
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
            "explained_variance_2d": 1.0,
            "pca_components": 0,
        }
    else:
        # Reduce to the same low-dimensional PCA space the scatter plot shows,
        # then cluster there. With far more features than users (p > n), raw
        # high-dimensional distances suffer from the curse of dimensionality;
        # projecting first denoises the data and makes the clustering decision
        # visually verifiable against the scatter plot. webreport rebuilds the
        # identical PCA coordinates (same matrix, StandardScaler, n_components,
        # random_state) so point positions and cluster labels stay consistent.
        scaled = StandardScaler().fit_transform(matrix)
        n_components = min(2, scaled.shape[1], n_users - 1)
        pca = PCA(n_components=n_components, random_state=random_state)
        coords = pca.fit_transform(scaled)
        explained_variance = float(pca.explained_variance_ratio_[:n_components].sum())

        max_k = min(5, n_users - 1)
        if requested_k is not None and requested_k > max_k:
            raise ValueError(f"分群數 {requested_k} 超過可用成員數，最多只能分 {max_k} 群。")
        candidates = [requested_k] if requested_k is not None else list(range(2, max_k + 1))

        best_k, labels_by_k, scores = _select_cluster_count(
            coords, candidates, random_state, requested_k
        )
        result["cluster"] = labels_by_k[best_k]
        metadata = {
            "best_k": int(best_k),
            "cluster_selection": str(cluster_count or "auto"),
            "silhouette_scores": {str(k): v for k, v in scores["silhouette"].items()},
            "calinski_harabasz_scores": {str(k): v for k, v in scores["calinski_harabasz"].items()},
            "davies_bouldin_scores": {str(k): v for k, v in scores["davies_bouldin"].items()},
            "k_votes": {str(k): v for k, v in scores["votes"].items()},
            "feature_columns": list(matrix.columns),
            "explained_variance_2d": round(explained_variance, 4),
            "pca_components": int(n_components),
        }

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_path, encoding="utf-8-sig")
    return result, metadata


def _select_cluster_count(
    coords: np.ndarray,
    candidates: list[int],
    random_state: int,
    requested_k: int | None,
) -> tuple[int, dict[int, np.ndarray], dict[str, dict[int, float]]]:
    """Pick the cluster count by majority vote of three internal indices.

    silhouette and Calinski-Harabasz favour higher scores; Davies-Bouldin
    favours lower. Each index votes for its own optimal k; the count with the
    most votes wins, ties broken towards fewer clusters (parsimony). When the
    caller fixes ``requested_k`` we still score it for display but skip voting.
    """

    silhouette: dict[int, float] = {}
    calinski: dict[int, float] = {}
    davies: dict[int, float] = {}
    labels_by_k: dict[int, np.ndarray] = {}

    for k in candidates:
        labels = KMeans(n_clusters=k, random_state=random_state, n_init=10).fit_predict(coords)
        labels_by_k[k] = labels
        if len(set(labels)) > 1:
            silhouette[k] = float(silhouette_score(coords, labels))
            calinski[k] = float(calinski_harabasz_score(coords, labels))
            davies[k] = float(davies_bouldin_score(coords, labels))
        else:
            silhouette[k] = -1.0
            calinski[k] = 0.0
            davies[k] = float("inf")

    votes = {k: 0 for k in candidates}
    if requested_k is not None:
        best_k = requested_k
        votes[best_k] = 3
    else:
        votes[max(silhouette, key=silhouette.get)] += 1
        votes[max(calinski, key=calinski.get)] += 1
        votes[min(davies, key=davies.get)] += 1
        best_k = min(candidates, key=lambda k: (-votes[k], k))

    scores = {
        "silhouette": silhouette,
        "calinski_harabasz": calinski,
        "davies_bouldin": davies,
        "votes": votes,
    }
    return best_k, labels_by_k, scores


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

