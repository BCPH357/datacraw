"""Bridge pipeline outputs into the React editorial UI (``window.APP_DATA``).

This module is the glue between the Python analysis pipeline (parser → features →
clustering → roles → report) and the React single-page report under
``claude_design/app/``. It is intentionally UI-agnostic: ``build_app_data``
returns a plain ``dict`` matching the schema the front-end's ``data.js`` used to
hard-code, and ``render_html`` assembles a self-contained HTML document that
loads React/Babel from a CDN and injects that data.

The static design metadata (role colours/titles, axis labels, feature labels)
is ported here from ``claude_design/app/data.js`` so the front-end carries no
hard-coded data and there is a single source of truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSETS_DIR = ROOT / "claude_design" / "app"

# Front-end script files, in load order. ``charts.jsx`` must run first because
# it declares ``const { useState, ... } = React`` that later files rely on.
ASSET_SCRIPTS = ("charts.jsx", "cards.jsx", "views.jsx", "views2.jsx", "app.jsx")

# ---------------------------------------------------------------------------
# Static design metadata (ported from claude_design/app/data.js)
# ---------------------------------------------------------------------------

ROLES: dict[str, dict[str, str]] = {
    "高頻核心型": {"glyph": "核", "title": "群組引擎", "cvar": "--r-core", "soft": "--r-core-soft",
                "desc": "互動量和活躍天數都偏高，是群組討論的主要推進者。"},
    "話題啟動型": {"glyph": "啟", "title": "開場王", "cvar": "--r-topic", "soft": "--r-topic-soft",
                "desc": "常開啟新話題或提出問題，會把對話往下一段推進。"},
    "表情回應型": {"glyph": "情", "title": "氣氛組組長", "cvar": "--r-emoji", "soft": "--r-emoji-soft",
                "desc": "常用貼圖或表情快速互動，讓群組氣氛保持輕鬆。"},
    "圖像分享型": {"glyph": "像", "title": "現場直擊者", "cvar": "--r-image", "soft": "--r-image-soft",
                "desc": "偏好用圖片或媒體補充資訊，圖像型互動較明顯。"},
    "資訊轉譯型": {"glyph": "訊", "title": "情報販子", "cvar": "--r-info", "soft": "--r-info-soft",
                "desc": "常分享連結或資訊，詞彙變化也比較高。"},
    "夜間長文型": {"glyph": "夜", "title": "深夜哲學家", "cvar": "--r-night", "soft": "--r-night-soft",
                "desc": "常在夜間出現，訊息也比較完整，適合承接需要脈絡的討論。"},
    "思考回覆型": {"glyph": "思", "title": "群組軍師", "cvar": "--r-think", "soft": "--r-think-soft",
                "desc": "回覆比例高且內容較完整，常扮演整理與補充的角色。"},
    "穩定參與型": {"glyph": "穩", "title": "定海神針", "cvar": "--r-stable", "soft": "--r-stable-soft",
                "desc": "各項互動特徵相對平均，是群組中的穩定參與者。"},
}

# Fallback styling for any role name not present above.
_DEFAULT_ROLE = {"glyph": "員", "title": "群組成員", "cvar": "--r-stable", "soft": "--r-stable-soft",
                 "desc": "群組中的參與者。"}

AXES = ["活躍", "開話題", "表情", "影像", "夜貓", "回應"]

FEATURES: dict[str, dict[str, str]] = {
    "message_count": {"label": "訊息總數", "fmt": "int"},
    "active_days": {"label": "活躍天數", "fmt": "int", "unit": "天"},
    "avg_messages_per_day": {"label": "每日平均訊息", "fmt": "f1"},
    "night_ratio": {"label": "夜間比例", "fmt": "pct"},
    "morning_ratio": {"label": "早晨比例", "fmt": "pct"},
    "afternoon_ratio": {"label": "午後比例", "fmt": "pct"},
    "evening_ratio": {"label": "傍晚比例", "fmt": "pct"},
    "avg_message_length": {"label": "平均訊息長度", "fmt": "f0", "unit": "字"},
    "median_message_length": {"label": "長度中位數", "fmt": "f0", "unit": "字"},
    "text_ratio": {"label": "純文字比例", "fmt": "pct"},
    "sticker_ratio": {"label": "貼圖比例", "fmt": "pct"},
    "image_ratio": {"label": "圖片比例", "fmt": "pct"},
    "url_ratio": {"label": "連結比例", "fmt": "pct"},
    "emoji_ratio": {"label": "emoji 比例", "fmt": "pct"},
    "reply_like_ratio": {"label": "回覆率", "fmt": "pct"},
    "topic_start_count": {"label": "開啟話題數", "fmt": "int", "unit": "次"},
    "avg_response_time_min": {"label": "平均回覆時間", "fmt": "f1", "unit": "分"},
    "question_ratio": {"label": "提問率", "fmt": "pct"},
    "unique_word_ratio": {"label": "詞彙多樣度", "fmt": "pct"},
}

FEATURE_KEYS = list(FEATURES.keys())

# Count-like features are emitted as ints; everything else stays float.
_INT_FEATURES = {"message_count", "active_days", "topic_start_count"}

# One tagline per role, applied deterministically when the backend has none.
TAGLINE_TEMPLATES: dict[str, str] = {
    "高頻核心型": "群組沒有他就安靜了。",
    "話題啟動型": "「欸欸我跟你們說」本人。",
    "表情回應型": "貼圖庫存量驚人。",
    "圖像分享型": "現場照永遠第一手。",
    "資訊轉譯型": "連結界的 RSS。",
    "夜間長文型": "凌晨兩點的小論文。",
    "思考回覆型": "總是那個收尾的人。",
    "穩定參與型": "永遠都在，剛剛好。",
}

# Radar axis (0–100, percentile based) → backing feature(s).
_AXIS_FEATURES: dict[str, tuple[str, ...]] = {
    "活躍": ("message_count",),
    "開話題": ("topic_start_count",),
    "表情": ("sticker_ratio", "emoji_ratio"),
    "影像": ("image_ratio",),
    "夜貓": ("night_ratio",),
    "回應": ("reply_like_ratio",),
}

# Hall-of-fame definitions: (label, feature, unit, formatter, note builder).
_SUPERLATIVES = [
    ("最活躍", "message_count", "則訊息", "int", "全群最高的發言量"),
    ("開場王", "topic_start_count", "次起頭", "int", "最常拋出新話題"),
    ("貼圖王", "sticker_ratio", "為貼圖", "pct", "純文字反而是少數"),
    ("深夜代表", "night_ratio", "在午夜後", "pct", "群裡最晚睡的那個"),
    ("群組軍師", "reply_like_ratio", "為回覆", "pct", "話題收尾交給他準沒錯"),
    ("情報量", "url_ratio", "帶連結", "pct", "最常分享連結與資訊"),
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _native(value: Any) -> Any:
    """Convert numpy scalars to plain Python types for JSON serialisation."""

    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def role_style(role: str) -> dict[str, str]:
    return ROLES.get(role, _DEFAULT_ROLE)


def _role_metadata_for(members: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    role_metadata = {role: dict(style) for role, style in ROLES.items()}
    palette = [(style["cvar"], style["soft"]) for style in ROLES.values()]

    unknown_roles: list[str] = []
    for member in members:
        role = str(member["role"])
        if role not in role_metadata and role not in unknown_roles:
            unknown_roles.append(role)

    for index, role in enumerate(unknown_roles):
        cvar, soft = palette[index % len(palette)]
        role_metadata[role] = {
            **_DEFAULT_ROLE,
            "cvar": cvar,
            "soft": soft,
            "title": role,
            "desc": "由分群統計摘要與 AI 命名產生的角色。",
        }
    return role_metadata


def _fmt_value(feature: str, value: float) -> str:
    fmt = FEATURES.get(feature, {}).get("fmt", "int")
    if fmt == "pct":
        return f"{round(float(value) * 100)}%"
    if fmt == "f1":
        return f"{float(value):.1f}"
    if fmt == "f0":
        return f"{round(float(value))}"
    return f"{int(round(float(value)))}"


def _percentile_100(series: pd.Series) -> pd.Series:
    """Percentile rank scaled to 0–100 (single value → 100)."""

    if len(series) <= 1:
        return pd.Series(100.0, index=series.index)
    return (series.rank(pct=True) * 100).round()


def _format_range(start: str | None, end: str | None) -> str:
    def dot(value: str | None) -> str:
        return value.replace("-", ".") if value else "—"

    return f"{dot(start)} — {dot(end)}"


def _day_span(start: str | None, end: str | None) -> int:
    if not start or not end:
        return 0
    try:
        delta = pd.Timestamp(end) - pd.Timestamp(start)
        return int(delta.days) + 1
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# APP_DATA assembly
# ---------------------------------------------------------------------------

def build_app_data(
    records: pd.DataFrame,
    features: pd.DataFrame,
    clustered: pd.DataFrame,
    user_roles: pd.DataFrame,
    group_health: dict[str, Any],
    metadata: dict[str, Any],
    summary: dict[str, Any],
    analysis_mode: str = "rule",
    cluster_selection: str = "auto",
    cluster_interpretations: list[dict[str, Any]] | None = None,
    excluded_members: list[dict[str, Any]] | None = None,
    token_usage: dict[str, int] | None = None,
    exclude_threshold_pct: float = 1.0,
) -> dict[str, Any]:
    """Map pipeline outputs into the React front-end's ``APP_DATA`` schema."""

    if user_roles is None or user_roles.empty:
        return _empty_app_data(summary)

    users = list(user_roles.index)
    id_by_user = {user: f"u{index}" for index, user in enumerate(users)}

    # Per-axis percentile tables, computed once across all users.
    axis_percentiles: dict[str, pd.Series] = {}
    for axis, axis_features in _AXIS_FEATURES.items():
        combined = sum(
            (features[col] if col in features else user_roles.get(col, 0))
            for col in axis_features
        )
        axis_percentiles[axis] = _percentile_100(pd.Series(combined, index=users))

    # Per-feature percentile ranks, used to fall back to a valid "top features"
    # list when the stored top_features aren't real feature keys (e.g. AI mode
    # stores natural-language evidence strings there instead).
    feature_columns = [key for key in FEATURE_KEYS if key in user_roles.columns]
    feature_percentiles = pd.DataFrame(
        {key: _percentile_100(user_roles[key]) for key in feature_columns},
        index=users,
    )

    members = []
    for user in users:
        row = user_roles.loc[user]
        role = str(row["role_name"])
        feature_values = {
            key: (int(round(float(row[key]))) if key in _INT_FEATURES else float(row[key]))
            for key in FEATURE_KEYS
            if key in user_roles.columns
        }
        stats = {axis: int(axis_percentiles[axis].loc[user]) for axis in AXES}
        top = [item for item in (str(value) for value in list(row.get("top_features", []))) if item in FEATURE_KEYS][:3]
        if len(top) < 3 and feature_columns:
            for key in feature_percentiles.loc[user].sort_values(ascending=False).index:
                if key not in top:
                    top.append(key)
                if len(top) == 3:
                    break
        ai_tagline = str(row.get("tagline") or "").strip()
        members.append(
            {
                "id": id_by_user[user],
                "name": str(user),
                "role": role,
                "cluster": int(row["cluster"]) if "cluster" in user_roles.columns else 0,
                "tagline": ai_tagline or TAGLINE_TEMPLATES.get(role, "群組裡的一份子。"),
                "stats": stats,
                "top": top,
                "f": feature_values,
            }
        )

    role_dist: dict[str, int] = {}
    for member in members:
        role_dist[member["role"]] = role_dist.get(member["role"], 0) + 1
    role_metadata = _role_metadata_for(members)

    total_messages = int(sum(member["f"].get("message_count", 0) for member in members))
    date_range = summary.get("date_range", {}) or {}
    start, end = date_range.get("start"), date_range.get("end")
    health_metrics = (group_health or {}).get("metrics", {}) or {}

    group = {
        "name": summary.get("group_name") or "LINE 群組",
        "emoji": "💬",
        "range": _format_range(start, end),
        "days": _day_span(start, end),
        "messageCount": total_messages,
        "userCount": int(summary.get("user_count") or len(members)),
        "health": _native(group_health.get("group_health_score", 0)) if group_health else 0,
        "dependency": float(health_metrics.get("dependency_score", 0.0)),
        "diversity": float(health_metrics.get("diversity_score", 0.0)),
        "ghost": float(health_metrics.get("ghost_ratio", 0.0)),
    }

    return {
        "group": group,
        "members": members,
        "ROLES": role_metadata,
        "AXES": AXES,
        "FEATURES": FEATURES,
        "roleDist": role_dist,
        "superlatives": _build_superlatives(members),
        "observations": _build_observations(group_health or {}, role_dist, len(members)),
        "heatmap": _build_heatmap(records, members, id_by_user),
        "scatter": _build_scatter(features, user_roles, id_by_user),
        "clusterMeta": _build_cluster_meta(user_roles, metadata),
        "analysisMode": analysis_mode,
        "clusterSelection": cluster_selection,
        "clusterInterpretations": cluster_interpretations or [],
        "excludedMembers": excluded_members or [],
        "excludeThresholdPct": float(exclude_threshold_pct),
        "tokenUsage": token_usage,
        "__embedded": True,
    }


def _empty_app_data(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": {
            "name": (summary or {}).get("group_name") or "LINE 群組",
            "emoji": "💬", "range": "—", "days": 0, "messageCount": 0,
            "userCount": 0, "health": 0, "dependency": 0.0, "diversity": 0.0, "ghost": 0.0,
        },
        "members": [], "ROLES": ROLES, "AXES": AXES, "FEATURES": FEATURES,
        "roleDist": {}, "superlatives": [], "observations": [],
        "heatmap": [], "scatter": [],
        "clusterMeta": {"best_k": 0, "silhouette": 0.0, "clusters": []},
        "analysisMode": "rule",
        "clusterSelection": "auto",
        "clusterInterpretations": [],
        "excludedMembers": [],
        "excludeThresholdPct": 1.0,
        "tokenUsage": None,
        "__embedded": True,
    }


def _build_superlatives(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    superlatives = []
    for key, feature, unit, fmt, note in _SUPERLATIVES:
        leader = max(members, key=lambda m: m["f"].get(feature, 0))
        value = leader["f"].get(feature, 0)
        if not value:  # skip meaningless "0%" / "0" highlights
            continue
        superlatives.append(
            {
                "key": key,
                "who": leader["name"],
                "role": leader["role"],
                "val": _fmt_value(feature, value),
                "unit": unit,
                "note": note,
            }
        )
    return superlatives


def _build_observations(
    group_health: dict[str, Any], role_dist: dict[str, int], user_count: int
) -> list[dict[str, Any]]:
    metrics = group_health.get("metrics", {}) or {}
    dependency = float(metrics.get("dependency_score", 0.0))
    diversity = float(metrics.get("diversity_score", 0.0))
    ghost = float(metrics.get("ghost_ratio", 0.0))

    observations: list[dict[str, Any]] = []
    if dependency > 0.55:
        observations.append({"tone": "watch", "text": "有單一成員扛起超過一半的對話，發言偏向集中。"})
    else:
        observations.append({"tone": "good", "text": "沒有人扛超過一半的對話，發言分布相對平均。"})

    if diversity >= 0.6:
        observations.append({"tone": "good", "text": f"{len(role_dist)} 種角色都齊了，群組互補性高。"})
    else:
        observations.append({"tone": "watch", "text": "角色種類偏少，互動模式較為集中。"})

    if ghost > 0.35:
        observations.append({"tone": "watch", "text": "有些成員的活躍度明顯低於群組中位數。"})
    elif ghost == 0:
        observations.append({"tone": "good", "text": "沒有人接近幽靈狀態，大家都還有在參與。"})

    if user_count <= 7:
        observations.append({"tone": "watch", "text": "群組樣本數較小，分群與健康度僅供參考。"})
    return observations


def _build_heatmap(
    records: pd.DataFrame, members: list[dict[str, Any]], id_by_user: dict[str, str]
) -> list[dict[str, Any]]:
    role_by_user = {member["name"]: member["role"] for member in members}
    heatmap = []
    if records is None or records.empty:
        return heatmap
    frame = records.copy()
    frame = frame[~frame["is_system"]] if "is_system" in frame else frame
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    hours = frame["datetime"].dt.hour
    for member in members:
        user = member["name"]
        user_hours = hours[frame["user"] == user]
        counts = np.zeros(24, dtype=float)
        for hour, count in user_hours.value_counts().items():
            counts[int(hour)] = float(count)
        peak = counts.max()
        normalized = (counts / peak).tolist() if peak else counts.tolist()
        heatmap.append(
            {
                "id": id_by_user[user],
                "name": user,
                "role": role_by_user.get(user, "穩定參與型"),
                "hours": [round(value, 4) for value in normalized],
            }
        )
    return heatmap


def _build_scatter(
    features: pd.DataFrame, user_roles: pd.DataFrame, id_by_user: dict[str, str]
) -> list[dict[str, Any]]:
    users = list(user_roles.index)
    matrix = features.loc[users].select_dtypes(include=[np.number])
    matrix = matrix.replace([np.inf, -np.inf], 0).fillna(0)
    cluster_by_user = {
        user: int(user_roles.loc[user, "cluster"]) if "cluster" in user_roles.columns else 0
        for user in users
    }

    if len(users) >= 2 and matrix.shape[1] >= 2:
        scaled = StandardScaler().fit_transform(matrix)
        coords = PCA(n_components=2, random_state=42).fit_transform(scaled)
    else:
        coords = np.tile([0.5, 0.5], (len(users), 1))

    def normalize(column: np.ndarray) -> np.ndarray:
        low, high = column.min(), column.max()
        if high - low < 1e-9:
            return np.full_like(column, 0.5)
        return (column - low) / (high - low)

    xs = normalize(coords[:, 0])
    ys = normalize(coords[:, 1])
    scatter = []
    for index, user in enumerate(users):
        scatter.append(
            {
                "id": id_by_user[user],
                "x": round(float(xs[index]), 4),
                "y": round(float(ys[index]), 4),
                "c": cluster_by_user[user],
            }
        )
    return scatter


def _build_cluster_meta(user_roles: pd.DataFrame, metadata: dict[str, Any]) -> dict[str, Any]:
    best_k = int((metadata or {}).get("best_k", 1) or 1)
    silhouette_scores = (metadata or {}).get("silhouette_scores", {}) or {}
    silhouette = float(silhouette_scores.get(str(best_k), 0.0) or 0.0)

    clusters_dict: dict[int, dict[str, Any]] = {}
    if "cluster" in user_roles.columns:
        for cluster_id, rows in user_roles.groupby("cluster", sort=True):
            dominant_role = str(rows["role_name"].mode().iloc[0])
            cluster_name = dominant_role.replace("型", "") + "群"
            clusters_dict[int(cluster_id)] = {
                "id": int(cluster_id),
                "name": cluster_name,
                "role": dominant_role,
                "cvar": role_style(dominant_role)["cvar"],
            }

    if clusters_dict:
        max_id = max(clusters_dict)
        clusters = []
        for cluster_id in range(max_id + 1):
            clusters.append(
                clusters_dict.get(
                    cluster_id,
                    {"id": cluster_id, "name": f"分群 {cluster_id}", "role": "穩定參與型",
                     "cvar": "--r-stable"},
                )
            )
    else:
        clusters = []

    return {"best_k": best_k, "silhouette": round(silhouette, 4), "clusters": clusters}


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def render_html(
    app_data: dict[str, Any],
    assets_dir: str | Path | None = None,
    embedded: bool = True,
) -> str:
    """Assemble a self-contained HTML document around ``app_data``.

    Uses ``claude_design/index.html`` as the canonical harness (single source of
    truth for the CDN React/Babel setup) and inlines the stylesheet + JSX so the
    result works from ``file://`` or inside a Streamlit iframe, with the fake
    ``data.js`` replaced by the real injected ``window.APP_DATA``.
    """

    assets = Path(assets_dir) if assets_dir else DEFAULT_ASSETS_DIR
    template_path = assets.parent / "index.html"
    payload = dict(app_data)
    payload["__embedded"] = embedded

    html = template_path.read_text(encoding="utf-8")

    # Inline the stylesheet (relative href won't resolve when self-contained).
    styles = (assets / "styles.css").read_text(encoding="utf-8")
    html = html.replace(
        '<link rel="stylesheet" href="app/styles.css" />',
        f"<style>\n{styles}\n</style>",
    )

    # Swap the demo data.js for the real, injected APP_DATA.
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace(
        '<script src="app/data.js"></script>',
        f"<script>window.APP_DATA = {data_json};</script>",
    )

    # Inline each JSX component (Babel can't XHR external src from file://).
    for name in ASSET_SCRIPTS:
        source = (assets / name).read_text(encoding="utf-8")
        html = html.replace(
            f'<script type="text/babel" src="app/{name}"></script>',
            f'<script type="text/babel" data-presets="react" data-file="{name}">\n{source}\n</script>',
        )

    return html


def render_upload_page(assets_dir: str | Path | None = None) -> str:
    """Return the React harness booting into the upload screen (no data yet).

    Used by the live web server: ``app/styles.css`` and the ``.jsx`` files stay
    as relative refs (served same-origin), and the demo ``data.js`` is removed so
    ``window.APP_DATA`` is undefined and the app starts at the upload view. Real
    data arrives from the server after the user uploads a file.
    """

    assets = Path(assets_dir) if assets_dir else DEFAULT_ASSETS_DIR
    html = (assets.parent / "index.html").read_text(encoding="utf-8")
    return html.replace('<script src="app/data.js"></script>', "")
