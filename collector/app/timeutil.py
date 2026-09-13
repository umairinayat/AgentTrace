"""UTC normalization helpers.

The SDK emits timezone-aware UTC datetimes, but SQLite has no native timestamp
type and hands back naive datetimes regardless of ``DateTime(timezone=True)``.
Mixing the two raises ``TypeError: can't subtract offset-naive and offset-aware
datetimes`` -- which is exactly what happens when a trace is created by one
request (aware, still in the session) and closed out by a later one (naive, read
back from the database).

Everything is stored as UTC, so a naive value read from the database is safely
interpreted as UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(value: datetime) -> datetime:
    """Return ``value`` as a timezone-aware UTC datetime.

    Naive datetimes are assumed to already be UTC; aware ones are converted.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def duration_ms(start: datetime, end: datetime) -> float:
    """Milliseconds between two datetimes, tolerating mixed tz-awareness."""
    return (ensure_utc(end) - ensure_utc(start)).total_seconds() * 1000
