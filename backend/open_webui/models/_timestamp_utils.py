import logging
from datetime import datetime, date, timezone
from typing import Optional, Union

from sqlalchemy.types import DateTime, TypeDecorator

try:
    from dateutil import parser as dateutil_parser  # type: ignore
except ImportError:  # pragma: no cover
    dateutil_parser = None  # type: ignore

log = logging.getLogger(__name__)

TimestampInput = Union[int, float, str, datetime, date, None]


def normalize_timestamp(value: TimestampInput, *, allow_none: bool = True) -> Optional[int]:
    """
    Convert assorted timestamp representations to epoch seconds.

    Accepts int/float epoch, datetime/date, numeric string, ISO 8601 string.
    Returns Optional[int] rounded down to seconds. Raises ValueError when conversion fails.
    """
    if value is None:
        if allow_none:
            return None
        raise ValueError("Timestamp value is required")

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, datetime):
        return int(value.timestamp())

    if isinstance(value, date):
        return int(datetime(value.year, value.month, value.day).timestamp())

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            if allow_none:
                return None
            raise ValueError("Timestamp string is empty")
        if stripped.isdigit():
            return int(stripped)
        # Attempt ISO 8601 parsing
        try:
            if dateutil_parser:
                parsed = dateutil_parser.isoparse(stripped)
            else:
                parsed = datetime.fromisoformat(stripped)
            return int(parsed.timestamp())
        except Exception as exc:  # pragma: no cover
            log.debug("Failed to parse timestamp string %s: %s", stripped, exc)
            raise ValueError(f"Unsupported timestamp string: {value}") from exc

    raise ValueError(f"Unsupported timestamp type: {type(value)!r}")


def normalize_required_timestamp(value: TimestampInput) -> int:
    normalized = normalize_timestamp(value, allow_none=False)
    if normalized is None:
        raise ValueError("Timestamp normalization returned None")
    return normalized


def normalize_optional_timestamp(value: TimestampInput) -> Optional[int]:
    if value is None:
        return None
    return normalize_timestamp(value, allow_none=True)

class EpochTimestamp(TypeDecorator):
    """
    Transparently persist epoch seconds into a timezone-aware timestamp column.

    Accepts int/float/datetime/date/ISO strings on input and stores them as UTC timestamps.
    Returns epoch seconds (int) when reading from the database.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: TimestampInput, dialect):
        normalized = normalize_optional_timestamp(value)
        if normalized is None:
            return None
        return datetime.fromtimestamp(normalized, tz=timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return int(value.timestamp())
        if isinstance(value, (int, float)):
            return int(value)
        raise ValueError(f"Unsupported database timestamp type: {type(value)!r}")

