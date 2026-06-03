"""Generate JSON reports from persona analysis outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _ranking(features: pd.DataFrame, user: str, column: str) -> dict[str, Any]:
    ordered = features[column].sort_values(ascending=False)
    return {
        "feature": column,
        "rank": int(list(ordered.index).index(user) + 1),
        "value": float(features.loc[user, column]),
    }


def build_personas(user_roles: pd.DataFrame, output_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Build per-user persona JSON payloads."""

    personas: list[dict[str, Any]] = []
    if user_roles.empty:
        return personas

    numeric_features = user_roles.select_dtypes(include=[np.number]).drop(columns=["cluster"], errors="ignore")
    for user, row in user_roles.iterrows():
        top_features = list(row["top_features"])
        personas.append(
            {
                "user": user,
                "role": row["role_name"],
                "description": row["description"],
                "top_features": top_features,
                "rankings": [_ranking(numeric_features, user, feature) for feature in top_features if feature in numeric_features],
            }
        )

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(personas, ensure_ascii=False, indent=2), encoding="utf-8")
    return personas


def build_group_health(
    user_roles: pd.DataFrame,
    metadata: dict[str, Any] | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build lightweight group health metrics."""

    if user_roles.empty:
        payload = {
            "group_health_score": 0,
            "summary": "No user messages were available for analysis.",
            "role_distribution": {},
            "warnings": ["No analyzable user messages."],
        }
    else:
        message_counts = user_roles["message_count"].astype(float)
        total_messages = float(message_counts.sum())
        dependency_score = float(message_counts.max() / total_messages) if total_messages else 0.0
        ghost_ratio = float((message_counts <= max(1, message_counts.median() * 0.25)).mean())
        role_distribution = user_roles["role_name"].value_counts().to_dict()
        diversity_score = len(role_distribution) / max(1, len(user_roles))
        balance_score = max(0.0, 1.0 - dependency_score)
        health_score = round(100 * (0.45 * balance_score + 0.35 * diversity_score + 0.20 * (1 - ghost_ratio)), 2)
        warnings = []
        if dependency_score > 0.55:
            warnings.append("A single participant carries more than half of the visible discussion.")
        if ghost_ratio > 0.35:
            warnings.append("Several participants are much less active than the group median.")
        payload = {
            "group_health_score": float(np.clip(health_score, 0, 100)),
            "summary": "The group shows a mix of participation styles with measurable role diversity.",
            "role_distribution": {str(k): int(v) for k, v in role_distribution.items()},
            "warnings": warnings,
            "metrics": {
                "ghost_ratio": ghost_ratio,
                "dependency_score": dependency_score,
                "diversity_score": diversity_score,
            },
            "clustering": metadata or {},
        }

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

