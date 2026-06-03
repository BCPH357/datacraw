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
    r"^(?:(?P<period>\u4e0a\u5348|\u4e0b\u5348|AM|PM|am|pm)\s*)?(?P<hour>\d{1,2}):(?P<minute>\d{2})\t(?P<body>.*)$"
)
SPACE_TIME_RE = re.compile(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})\s+(?P<body>.*)$")
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
ENGLISH_ALIAS_RE = re.compile(r"^[A-Za-z][\w.-]*$")

SYSTEM_EVENT_PATTERNS = [
    re.compile(r".*\u5df2\u6536\u56de\u8a0a\u606f$"),
    re.compile(r".*\u6536\u56de\u8a0a\u606f$"),
    re.compile(r".*(?:\u52a0\u5165|\u9000\u51fa|\u96e2\u958b).*(?:\u7fa4\u7d44|\u804a\u5929|\u7fa4)$"),
    re.compile(r".*\b(?:join|joined|left|leave)\b.*", re.IGNORECASE),
    re.compile(r".*(?:invited|removed).*(?:group|chat).*", re.IGNORECASE),
]

MEDIA_TYPES = {
    "[\u8cbc\u5716]": "sticker",
    "[\u7167\u7247]": "image",
    "[\u5716\u7247]": "image",
    "[\u5f71\u7247]": "video",
    "[\u6a94\u6848]": "file",
    "[\u8a18\u4e8b\u672c]": "note",
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
    if period == "\u4e0a\u5348" or normalized_period == "am":
        if hour == 12:
            hour = 0
    elif period == "\u4e0b\u5348" or normalized_period == "pm":
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


def is_system_event(text: str) -> bool:
    """Return True for LINE system events that should be dropped."""

    normalized = clean_control_chars(text).strip()
    return any(pattern.match(normalized) for pattern in SYSTEM_EVENT_PATTERNS)


def split_space_message(body: str) -> tuple[str, str]:
    """Split the local space-delimited LINE export variant into user/message."""

    parts = body.split(maxsplit=2)
    if not parts:
        return "SYSTEM", ""
    if len(parts) == 1:
        return clean_control_chars(parts[0]), ""
    if len(parts) >= 3 and len(parts[0]) == 1 and ENGLISH_ALIAS_RE.match(parts[1]):
        return clean_control_chars(f"{parts[0]} {parts[1]}"), clean_control_chars(parts[2])
    return clean_control_chars(parts[0]), clean_control_chars(body[len(parts[0]) :].strip())


def _group_name_from_header(lines: Iterable[str]) -> str | None:
    for raw_line in lines:
        line = clean_control_chars(raw_line)
        if line.startswith("[LINE]"):
            title = line.removeprefix("[LINE]").strip()
            title = re.sub(r"(?:\u7684\u804a\u5929|\u804a\u5929\u8a18\u9304|Chat history).*$", "", title).strip()
            return title or None
    return None


def _append_record(
    records: list[dict],
    current_date: str,
    time_24h: str,
    user: str,
    message: str,
) -> None:
    if user == "SYSTEM" or is_system_event(message) or is_system_event(f"{user}{message}"):
        return
    message_type, has_url = detect_message_type(message)
    message_dt = datetime.fromisoformat(f"{current_date}T{time_24h}:00")
    records.append(
        {
            "date": current_date,
            "time": time_24h,
            "datetime": message_dt.isoformat(),
            "user": user,
            "message": message,
            "type": message_type,
            "is_system": False,
            "has_url": has_url,
        }
    )


def parse_text(text: str) -> ParsedChat:
    """Parse LINE export text into normalized message records."""

    lines = text.splitlines()
    current_date: str | None = None
    records: list[dict] = []
    group_name = _group_name_from_header(lines[:5])

    for raw_line in lines:
        line = clean_control_chars(raw_line.rstrip("\n"))
        if not line:
            continue
        if line.startswith("[LINE]") or "\u5132\u5b58\u65e5\u671f" in line or "Saved on" in line:
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
            fields = time_match.group("body").split("\t")
            time_24h = normalize_time(
                time_match.group("period"),
                int(time_match.group("hour")),
                int(time_match.group("minute")),
            )
            if len(fields) >= 2 and fields[0].strip():
                user = clean_control_chars(fields[0])
                message = clean_control_chars("\t".join(fields[1:]))
            else:
                user = "SYSTEM"
                message = clean_control_chars("\t".join(part for part in fields if part))
            _append_record(records, current_date, time_24h, user, message)
            continue

        space_time_match = SPACE_TIME_RE.match(line)
        if space_time_match and current_date:
            raw_body = clean_control_chars(space_time_match.group("body"))
            if is_system_event(raw_body):
                continue
            time_24h = normalize_time(
                None,
                int(space_time_match.group("hour")),
                int(space_time_match.group("minute")),
            )
            user, message = split_space_message(raw_body)
            _append_record(records, current_date, time_24h, user, message)
            continue

        if records:
            previous = records[-1]
            previous["message"] = f"{previous['message']}\n{line}".strip()
            previous["type"], previous["has_url"] = detect_message_type(previous["message"])

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

