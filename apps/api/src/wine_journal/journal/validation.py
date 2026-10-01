from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def local_minute(value: time | None) -> time | None:
    if value and (value.tzinfo is not None or value.second or value.microsecond):
        raise ValueError("Use a local time with minute precision and no offset.")
    return value


def known_timezone(value: str | None) -> str | None:
    if value is not None:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use an IANA timezone name.") from None
    return value
