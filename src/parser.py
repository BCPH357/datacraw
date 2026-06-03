"""Parse LINE chat exports into normalized records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

BIDI_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
DATE_RE = re.compile(r"^(?P<year>\d{4})[/.](?P<month>\d{1,2})[/.](?P<day>\d{1,2})")
TIME_RE = re.compile(
    r"^(?:(?P<period>上午|下午|AM|PM|am|pm)\s*)?(?P<hour>\d{1,2}):(?P<minute>\d{2})\t(?P<body>.*)$"
)
SPACE_TIME_RE = re.compile(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})\s+(?P<body>.*)$")
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

MEDIA_TYPES = {
    "[貼圖]": "sticker",
    "[照片]": "image",
    "[圖片]": "image",
    "[影片]": "video",
    "[檔案]": "file",
    "[記事本]": "note",
}


@dataclass(frozen=True)
class ParsedChat:
    """Parsed LINE chat data and lightweight metadata."""

    records: list[dict]
    group_name: str | None = None


def clean_control_chars(text: str) -> str:
    """Remove bidi and direction markers that LINE may include around names."""

    return BIDI_RE.sub("", text).strip()


def normalize_time(period: str | None, hour: int, minute: int) -> str:
    """Convert LINE AM/PM time strings to 24-hour HH:MM."""

    normalized_period = (period or "").lower()
    if period == "上午" or normalized_period == "am":
        if hour == 12:
            hour = 0
    elif period == "下午" or normalized_period == "pm":
        if hour != 12:
            hour += 12
    return f"{hour:02d}:{minute:02d}"


def detect_message_type(message: str) -> tuple[str, bool]:
    """Return normalized message type and URL flag."""

    stripped = message.strip()
    has_url = bool(URL_RE.search(stripped))
    if stripped in MEDIA_TYPES:
        return MEDIA_TYPES[stripped], has_url
    if stripped.startswith("[") and stripped.endswith("]"):
        return "media", has_url
    return "text", has_url


def split_space_message(body: str) -> tuple[str, str]:
    """Split the space-delimited LINE export variant into user and message.

    Some LINE exports use tabs, while the local dataset uses
    ``HH:MM name message``. A Chinese surname followed by an English alias,
    such as ``段 Duan``, is treated as a two-token display name.
    """

    parts = body.split(maxsplit=2)
    if not parts:
        return "SYSTEM", ""
    if len(parts) == 1:
        return clean_control_chars(parts[0]), ""
    if len(parts) >= 3 and len(parts[0]) == 1 and re.match(r"^[A-Za-z][\w.-]*$", parts[1]):
        return clean_control_chars(f"{parts[0]} {parts[1]}"), clean_control_chars(parts[2])
    return clean_control_chars(parts[0]), clean_control_chars(body[len(parts[0]) :].strip())


def _group_name_from_header(lines: Iterable[str]) -> str | None:
    for raw_line in lines:
        line = clean_control_chars(raw_line)
        if line.startswith("[LINE]"):
            title = line.removeprefix("[LINE]").strip()
            title = re.sub(r"(的聊天|聊天記錄|Chat history).*$", "", title).strip()
            return title or None
    return None


def parse_text(text: str) -> ParsedChat:
    """Parse LINE export text.

    The parser accepts common Traditional Chinese LINE exports:
    date rows, message rows separated by tabs, system rows with an empty user
    field, and continuation lines appended to the previous message.
    """

    lines = text.splitlines()
    current_date: str | None = None
    records: list[dict] = []
    group_name = _group_name_from_header(lines[:5])

    for raw_line in lines:
        line = clean_control_chars(raw_line.rstrip("\n"))
        if not line:
            continue
        if line.startswith("[LINE]") or "儲存日期" in line or "Saved on" in line:
            continue

        date_match = DATE_RE.match(line)
        if date_match:
            year = int(date_match.group("year"))
            month = int(date_match.group("month"))
            day = int(date_match.group("day"))
            current_date = f"{year:04d}-{month:02d}-{day:02d}"
            continue

        time_match = TIME_RE.match(line)
        if time_match and current_date:
            body = time_match.group("body")
            fields = body.split("\t")
            time_24h = normalize_time(
                time_match.group("period"),
                int(time_match.group("hour")),
                int(time_match.group("minute")),
            )
            message_dt = datetime.fromisoformat(f"{current_date}T{time_24h}:00")

            if len(fields) >= 2 and fields[0].strip():
                user = clean_control_chars(fields[0])
                message = clean_control_chars("\t".join(fields[1:]))
                is_system = False
            else:
                user = "SYSTEM"
                message = clean_control_chars("\t".join(part for part in fields if part))
                is_system = True

            message_type, has_url = detect_message_type(message)
            if is_system:
                message_type = "system"

            records.append(
                {
                    "date": current_date,
                    "time": time_24h,
                    "datetime": message_dt.isoformat(),
                    "user": user,
                    "message": message,
                    "type": message_type,
                    "is_system": is_system,
                    "has_url": has_url,
                }
            )
            continue

        space_time_match = SPACE_TIME_RE.match(line)
        if space_time_match and current_date:
            time_24h = normalize_time(
                None,
                int(space_time_match.group("hour")),
                int(space_time_match.group("minute")),
            )
            user, message = split_space_message(space_time_match.group("body"))
            message_dt = datetime.fromisoformat(f"{current_date}T{time_24h}:00")
            is_system = user == "SYSTEM"
            message_type, has_url = detect_message_type(message)
            if is_system:
                message_type = "system"
            records.append(
                {
                    "date": current_date,
                    "time": time_24h,
                    "datetime": message_dt.isoformat(),
                    "user": user,
                    "message": message,
                    "type": message_type,
                    "is_system": is_system,
                    "has_url": has_url,
                }
            )
            continue

        if records:
            previous = records[-1]
            previous["message"] = f"{previous['message']}\n{line}".strip()
            previous["type"], previous["has_url"] = detect_message_type(previous["message"])
            if previous["is_system"]:
                previous["type"] = "system"

    return ParsedChat(records=records, group_name=group_name)


def parse_file(path: str | Path, encoding: str = "utf-8") -> ParsedChat:
    """Read and parse a LINE export file."""

    file_path = Path(path)
    try:
        text = file_path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        text = file_path.read_text(encoding="utf-8-sig")
    return parse_text(text)


def to_dataframe(parsed: ParsedChat | list[dict]) -> pd.DataFrame:
    """Convert parsed records into a typed DataFrame."""

    records = parsed.records if isinstance(parsed, ParsedChat) else parsed
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return pd.DataFrame(
            columns=["date", "time", "datetime", "user", "message", "type", "is_system", "has_url"]
        )
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["date"] = pd.to_datetime(frame["date"]).dt.date.astype(str)
    frame["is_system"] = frame["is_system"].astype(bool)
    frame["has_url"] = frame["has_url"].astype(bool)
    return frame


def summarize(parsed: ParsedChat | list[dict]) -> dict:
    """Summarize parsed chat records."""

    group_name = parsed.group_name if isinstance(parsed, ParsedChat) else None
    frame = to_dataframe(parsed)
    if frame.empty:
        return {
            "group_name": group_name,
            "message_count": 0,
            "user_count": 0,
            "date_range": {"start": None, "end": None},
        }
    user_frame = frame[~frame["is_system"]]
    return {
        "group_name": group_name,
        "message_count": int(len(frame)),
        "user_count": int(user_frame["user"].nunique()),
        "date_range": {
            "start": str(frame["date"].min()),
            "end": str(frame["date"].max()),
        },
    }
