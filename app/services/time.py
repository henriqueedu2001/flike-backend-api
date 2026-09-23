"""UTC helpers shared by persistence and the binary authorization protocol."""
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def as_utc(value: datetime) -> datetime:
    # MySQL DATETIME/TIMESTAMP values are read from a UTC session.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def database_time(value: datetime) -> datetime:
    return as_utc(value).replace(tzinfo=None, microsecond=0)
