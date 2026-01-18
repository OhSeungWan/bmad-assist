"""Centralized time API for bmad-assist.

This module provides consistent datetime handling throughout the application:
- UTC-aware datetimes for API timestamps and external communication
- Naive UTC datetimes for internal state persistence (YAML serialization)
- Local time for human-readable filenames and logs
- Duration calculations in milliseconds
- Injectable clock for testing

Usage:
    from bmad_assist.core.timing import utc_now, utc_now_naive, local_now, duration_ms

    # For API timestamps, ISO strings, Discord embeds
    timestamp = utc_now()  # datetime with UTC timezone

    # For state persistence (State model, YAML files)
    state.updated_at = utc_now_naive()  # naive datetime in UTC

    # For filenames, logs (human-readable local time)
    filename = f"report-{format_local_date()}.yaml"

    # For duration calculations
    start = utc_now_naive()
    # ... work ...
    end = utc_now_naive()
    ms = duration_ms(start, end)
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime


# Injectable clock for testing - returns naive UTC datetime
def _default_clock() -> datetime:
    """Return current naive UTC time."""
    return datetime.now(UTC).replace(tzinfo=None)


_clock: Callable[[], datetime] = _default_clock


def set_clock(clock: Callable[[], datetime]) -> None:
    """Set custom clock for testing.

    Args:
        clock: Function returning naive UTC datetime

    """
    global _clock
    _clock = clock


def reset_clock() -> None:
    """Reset clock to default (real time)."""
    global _clock
    _clock = _default_clock


# -----------------------------------------------------------------------------
# Core datetime functions
# -----------------------------------------------------------------------------


def utc_now() -> datetime:
    """Get current UTC time with timezone info.

    Use for:
    - API timestamps
    - ISO 8601 strings
    - Discord embeds
    - External communication

    Returns:
        Timezone-aware datetime in UTC

    """
    return _clock().replace(tzinfo=UTC)


def utc_now_naive() -> datetime:
    """Get current UTC time without timezone info.

    Use for:
    - State persistence (State model)
    - YAML serialization
    - Internal timestamps

    Returns:
        Naive datetime representing UTC time

    """
    return _clock()


def local_now() -> datetime:
    """Get current local time.

    Use for:
    - Filenames
    - Log timestamps
    - Human-readable output

    Returns:
        Naive datetime in local timezone

    """
    # Get naive UTC, then convert to local
    utc_naive = _clock()
    # Create aware UTC datetime, convert to local, strip timezone
    utc_aware = utc_naive.replace(tzinfo=UTC)
    local_aware = utc_aware.astimezone()
    return local_aware.replace(tzinfo=None)


# -----------------------------------------------------------------------------
# Duration calculations
# -----------------------------------------------------------------------------


def duration_ms(start: datetime | None, end: datetime | None = None) -> int:
    """Calculate duration in milliseconds.

    Args:
        start: Start datetime (naive or aware)
        end: End datetime (naive or aware), defaults to now

    Returns:
        Duration in milliseconds, 0 if start is None

    """
    if start is None:
        return 0
    if end is None:
        # Use same timezone awareness as start
        end = utc_now() if start.tzinfo else utc_now_naive()
    delta = end - start
    return int(delta.total_seconds() * 1000)


def duration_seconds(start: datetime | None, end: datetime | None = None) -> float:
    """Calculate duration in seconds.

    Args:
        start: Start datetime (naive or aware)
        end: End datetime (naive or aware), defaults to now

    Returns:
        Duration in seconds, 0.0 if start is None

    """
    if start is None:
        return 0.0
    if end is None:
        end = utc_now() if start.tzinfo else utc_now_naive()
    delta = end - start
    return delta.total_seconds()


# -----------------------------------------------------------------------------
# Formatting functions
# -----------------------------------------------------------------------------


def format_iso(dt: datetime | None = None) -> str:
    """Format datetime as ISO 8601 string.

    Args:
        dt: Datetime to format, defaults to utc_now()

    Returns:
        ISO 8601 formatted string

    """
    if dt is None:
        dt = utc_now()
    return dt.isoformat()


def format_local_date(dt: datetime | None = None, fmt: str = "%Y-%m-%d") -> str:
    """Format datetime as local date string.

    Args:
        dt: Datetime to format, defaults to local_now()
        fmt: strftime format string

    Returns:
        Formatted date string

    """
    if dt is None:
        dt = local_now()
    return dt.strftime(fmt)


def format_local_datetime(dt: datetime | None = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime as local datetime string.

    Args:
        dt: Datetime to format, defaults to local_now()
        fmt: strftime format string

    Returns:
        Formatted datetime string

    """
    if dt is None:
        dt = local_now()
    return dt.strftime(fmt)


def format_timestamp(dt: datetime | None = None) -> str:
    """Format datetime as compact timestamp for filenames.

    Args:
        dt: Datetime to format, defaults to local_now()

    Returns:
        Compact timestamp string (YYYYMMDD-HHMMSS)

    """
    if dt is None:
        dt = local_now()
    return dt.strftime("%Y%m%d-%H%M%S")


def format_year_month(dt: datetime | None = None) -> str:
    """Format datetime as YYYY-MM for directory names.

    Args:
        dt: Datetime to format, defaults to local_now()

    Returns:
        Year-month string (YYYY-MM)

    """
    if dt is None:
        dt = local_now()
    return dt.strftime("%Y-%m")


# Conversion constants for duration formatting
MS_PER_SECOND = 1_000
MS_PER_MINUTE = 60_000
MS_PER_HOUR = 60 * MS_PER_MINUTE
MS_PER_DAY = 24 * MS_PER_HOUR
_MINUTES_PER_DAY = 24 * 60
_SECONDS_PER_MINUTE = 60


def format_duration(milliseconds: int) -> str:
    """Format milliseconds as human-readable duration.

    Formats duration using compact notation with spaces between units:
    - < 1h: "{m}m {s}s" (e.g., "2m 14s", "47m", "30s"), omits zero components
    - 1-24h: "{h}h {m}m" (e.g., "2h 17m"), omits zero minutes
    - >= 24h: "{d}d {h}h" (e.g., "1d 5h"), omits zero hours

    Story standalone-03 AC8: Short durations (< 1 hour) now include seconds
    for better precision in phase timing notifications.

    Args:
        milliseconds: Duration in milliseconds. Negative values are
            treated as 0.

    Returns:
        Human-readable duration string.

    Examples:
        >>> format_duration(0)
        '0s'
        >>> format_duration(14_000)  # 14 seconds
        '14s'
        >>> format_duration(134_000)  # 2m 14s
        '2m 14s'
        >>> format_duration(2_820_000)  # 47 minutes
        '47m'
        >>> format_duration(8_220_000)  # 2h 17m
        '2h 17m'
        >>> format_duration(7_200_000)  # exactly 2h
        '2h'
        >>> format_duration(104_400_000)  # 1d 5h
        '1d 5h'
        >>> format_duration(259_200_000)  # exactly 3d
        '3d'
        >>> format_duration(-1000)  # negative input
        '0s'

    """
    # Clamp negative values to 0
    if milliseconds < 0:
        milliseconds = 0

    # Convert to total seconds (floor division)
    total_seconds = milliseconds // MS_PER_SECOND

    # Extract components using divmod
    total_minutes, seconds = divmod(total_seconds, _SECONDS_PER_MINUTE)
    days, remaining_minutes = divmod(total_minutes, _MINUTES_PER_DAY)
    hours, minutes = divmod(remaining_minutes, 60)

    # Format based on magnitude
    if days > 0:
        # Days format: "{d}d {h}h", omit zero hours
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days}d"
    elif hours > 0:
        # Hours format: "{h}h {m}m", omit zero minutes
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    elif minutes > 0:
        # Minutes format: "{m}m {s}s", omit zero seconds
        if seconds > 0:
            return f"{minutes}m {seconds}s"
        return f"{minutes}m"
    else:
        # Seconds only
        return f"{seconds}s"


# -----------------------------------------------------------------------------
# Parsing functions
# -----------------------------------------------------------------------------


def parse_iso(s: str) -> datetime:
    """Parse ISO 8601 string to datetime.

    Args:
        s: ISO 8601 formatted string

    Returns:
        Parsed datetime (timezone-aware if input has timezone)

    """
    return datetime.fromisoformat(s)


def parse_date(s: str, fmt: str = "%Y-%m-%d") -> datetime:
    """Parse date string to datetime.

    Args:
        s: Date string
        fmt: strftime format string

    Returns:
        Parsed datetime (naive)

    """
    return datetime.strptime(s, fmt)
