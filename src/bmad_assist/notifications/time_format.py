"""Human-readable time formatting utilities for notifications.

This module re-exports format_duration from core.timing for backwards
compatibility. New code should import directly from core.timing.

Example:
    >>> from bmad_assist.notifications import format_duration
    >>> format_duration(2_820_000)  # 47 minutes
    '47m'
    >>> format_duration(8_220_000)  # 2h 17m
    '2h 17m'
    >>> format_duration(104_400_000)  # 1d 5h
    '1d 5h'

"""

from bmad_assist.core.timing import (
    MS_PER_DAY,
    MS_PER_HOUR,
    MS_PER_MINUTE,
    format_duration,
)

__all__ = ["format_duration", "MS_PER_MINUTE", "MS_PER_HOUR", "MS_PER_DAY"]
