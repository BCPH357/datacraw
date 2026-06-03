"""Visualization helpers for LINE persona analysis."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def configure_cjk_font() -> None:
    """Use an available CJK font for chart labels."""

    candidates = ["Noto Sans CJK TC", "Microsoft JhengHei", "PingFang TC", "Heiti TC", "WenQuanYi Zen Hei"]
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in candidates:
        if candidate in available:
            matplotlib.rcParams["font.family"] = candidate
            break
    matplotlib.rcParams["axes.unicode_minus"] = False


def _save(fig: plt.Figure, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path


def plot_message_count(features: pd.DataFrame, output_dir: str | Path) -> Path:
    configure_cjk_font()
    output_path = Path(output_dir) / "bar_message_count.png"
    fig, ax = plt.subplots(figsize=(9, 5))
    features["message_count"].sort_values(ascending=False).plot(kind="bar", ax=ax, color="#3a7d74")
    ax.set_title("Message Count by User")
    ax.set_xlabel("User")
    ax.set_ylabel("Messages")
    return _save(fig, output_path)


def plot_active_hours(records: pd.DataFrame, output_dir: str | Path) -> Path:
    configure_cjk_font()
    output_path = Path(output_dir) / "heatmap_active_hours.png"
    frame = records[~records["is_system"]].copy()
    frame["hour"] = pd.to_datetime(frame["datetime"]).dt.hour
    pivot = pd.crosstab(frame["user"], frame["hour"]).reindex(columns=range(24), fill_value=0)
    fig, ax = plt.subplots(figsize=(11, max(3, len(pivot) * 0.45)))
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlGnBu")
    ax.set_title("Active Hours")
    ax.set_xlabel("Hour")
    ax.set_ylabel("User")
    ax.set_xticks(range(24))
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    fig.colorbar(im, ax=ax, label="Messages")
    return _save(fig, output_path)


def plot_clusters(clustered_features: pd.DataFrame, output_dir: str | Path) -> Path:
    configure_cjk_font()
    output_path = Path(output_dir) / "scatter_clusters.png"
    numeric = clustered_features.select_dtypes("number").drop(columns=["cluster"], errors="ignore")
    fig, ax = plt.subplots(figsize=(7, 5))
    if len(clustered_features) >= 2 and numeric.shape[1] >= 1:
        scaled = StandardScaler().fit_transform(numeric.fillna(0))
        if numeric.shape[1] >= 2:
            points = PCA(n_components=2, random_state=42).fit_transform(scaled)
        else:
            points = pd.DataFrame({"x": scaled[:, 0], "y": [0] * len(scaled)}).values
        scatter = ax.scatter(points[:, 0], points[:, 1], c=clustered_features["cluster"], cmap="tab10", s=90)
        for (x, y), user in zip(points, clustered_features.index):
            ax.annotate(user, (x, y), xytext=(5, 5), textcoords="offset points", fontsize=9)
        fig.colorbar(scatter, ax=ax, label="Cluster")
    ax.set_title("User Clusters")
    ax.set_xlabel("Component 1")
    ax.set_ylabel("Component 2")
    return _save(fig, output_path)


def plot_role_distribution(user_roles: pd.DataFrame, output_dir: str | Path) -> Path:
    configure_cjk_font()
    output_path = Path(output_dir) / "pie_role_distribution.png"
    fig, ax = plt.subplots(figsize=(7, 5))
    counts = user_roles["role_name"].value_counts()
    ax.pie(counts.values, labels=counts.index, autopct="%1.0f%%", startangle=90)
    ax.set_title("Role Distribution")
    return _save(fig, output_path)


def generate_all(records: pd.DataFrame, features: pd.DataFrame, clustered_features: pd.DataFrame, user_roles: pd.DataFrame, output_dir: str | Path) -> list[Path]:
    """Generate all MVP charts."""

    return [
        plot_message_count(features, output_dir),
        plot_active_hours(records, output_dir),
        plot_clusters(clustered_features, output_dir),
        plot_role_distribution(user_roles, output_dir),
    ]

