"""Feature extraction for parsed LINE chat records."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import jieba
import numpy as np
import pandas as pd

QUESTION_RE = re.compile(r"[?？]|嗎|呢|怎麼|如何|為什麼")
EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001f5ff"
    "\U0001f600-\U0001f64f"
    "\U0001f680-\U0001f6ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa70-\U0001faff"
    "]"
)


def _safe_ratio(value: float, total: float) -> float:
    return float(value / total) if total else 0.0


def _unique_word_ratio(messages: pd.Series) -> float:
    tokens: list[str] = []
    for message in messages.dropna().astype(str):
        tokens.extend(token.strip() for token in jieba.cut(message) if token.strip())
    return _safe_ratio(len(set(tokens)), len(tokens))


def _response_metrics(user_rows: pd.DataFrame, all_rows: pd.DataFrame, user: str) -> tuple[float, int, float]:
    reply_like = 0
    topic_start = 0
    response_times: list[float] = []
    non_system = all_rows.sort_values("datetime").reset_index(drop=True)
    positions = non_system.index[non_system["user"] == user].tolist()
    for position in positions:
        if position == 0:
            topic_start += 1
            continue
        current = non_system.loc[position]
        previous = non_system.loc[position - 1]
        gap_min = (current["datetime"] - previous["datetime"]).total_seconds() / 60
        if previous["user"] != user and gap_min <= 30:
            reply_like += 1
            response_times.append(gap_min)
        elif gap_min > 30:
            topic_start += 1
    total = len(user_rows)
    average_response = float(np.mean(response_times)) if response_times else 0.0
    return _safe_ratio(reply_like, total), int(topic_start), average_response


def extract_features(records: pd.DataFrame, output_path: str | Path | None = None) -> pd.DataFrame:
    """Extract per-user behavioral features from parsed records."""

    frame = records.copy()
    if frame.empty:
        return pd.DataFrame()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    user_frame = frame[~frame["is_system"]].copy()
    if user_frame.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for user, group in user_frame.groupby("user", sort=True):
        total = len(group)
        hours = group["datetime"].dt.hour
        text_rows = group[group["type"] == "text"]
        message_lengths = text_rows["message"].fillna("").astype(str).str.len()
        reply_like_ratio, topic_start_count, avg_response_time = _response_metrics(group, user_frame, user)

        row = {
            "user": user,
            "message_count": int(total),
            "active_days": int(group["date"].nunique()),
            "avg_messages_per_day": _safe_ratio(total, group["date"].nunique()),
            "night_ratio": _safe_ratio(((hours >= 0) & (hours < 6)).sum(), total),
            "morning_ratio": _safe_ratio(((hours >= 6) & (hours < 12)).sum(), total),
            "afternoon_ratio": _safe_ratio(((hours >= 12) & (hours < 18)).sum(), total),
            "evening_ratio": _safe_ratio(((hours >= 18) & (hours < 24)).sum(), total),
            "avg_message_length": float(message_lengths.mean()) if len(message_lengths) else 0.0,
            "median_message_length": float(message_lengths.median()) if len(message_lengths) else 0.0,
            "text_ratio": _safe_ratio((group["type"] == "text").sum(), total),
            "sticker_ratio": _safe_ratio((group["type"] == "sticker").sum(), total),
            "image_ratio": _safe_ratio((group["type"] == "image").sum(), total),
            "url_ratio": _safe_ratio(group["has_url"].sum(), total),
            "emoji_ratio": _safe_ratio(group["message"].fillna("").astype(str).str.contains(EMOJI_RE).sum(), total),
            "reply_like_ratio": reply_like_ratio,
            "topic_start_count": topic_start_count,
            "avg_response_time_min": avg_response_time,
            "question_ratio": _safe_ratio(group["message"].fillna("").astype(str).str.contains(QUESTION_RE).sum(), total),
            "unique_word_ratio": _unique_word_ratio(text_rows["message"]),
        }
        rows.append(row)

    features = pd.DataFrame(rows).set_index("user").replace([np.inf, -np.inf], 0).fillna(0)
    for column in features.columns:
        if column.endswith("_ratio"):
            features[column] = features[column].clip(0, 1)
        elif column.endswith("_count") or column in {"message_count", "active_days"}:
            features[column] = features[column].apply(lambda value: max(0, int(math.floor(value))))

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        features.to_csv(output_path, encoding="utf-8-sig")
    return features

