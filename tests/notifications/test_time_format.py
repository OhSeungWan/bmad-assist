"""Tests for human-readable time formatting utilities.

Tests cover:
- AC1: Short durations (< 60 minutes)
- AC2: Medium durations (1-24 hours)
- AC3: Long durations (>= 24 hours)
- AC4: Zero duration edge case
- AC5: Large value edge case
- AC6: Negative input edge case
"""

import pytest

from bmad_assist.notifications.time_format import (
    MS_PER_DAY,
    MS_PER_HOUR,
    MS_PER_MINUTE,
    format_duration,
)


class TestFormatDurationConstants:
    """Test conversion constants are correct."""

    def test_ms_per_minute(self) -> None:
        """Test MS_PER_MINUTE is 60,000."""
        assert MS_PER_MINUTE == 60_000

    def test_ms_per_hour(self) -> None:
        """Test MS_PER_HOUR is 3,600,000."""
        assert MS_PER_HOUR == 3_600_000

    def test_ms_per_day(self) -> None:
        """Test MS_PER_DAY is 86,400,000."""
        assert MS_PER_DAY == 86_400_000


class TestFormatDurationShort:
    """Test AC1: Short durations (< 60 minutes).

    Story standalone-03 AC8: durations < 1 hour show "{m}m {s}s" format.
    Zero seconds are omitted (e.g., "2m" instead of "2m 0s").
    Sub-second values show as "0s".
    """

    def test_zero_milliseconds(self) -> None:
        """Test 0ms returns '0s' (AC4, updated for seconds support)."""
        assert format_duration(0) == "0s"

    def test_sub_second_durations_floor_to_zero_seconds(self) -> None:
        """Test durations < 1 second floor to '0s'."""
        assert format_duration(1) == "0s"
        assert format_duration(999) == "0s"

    def test_seconds_only_durations(self) -> None:
        """Test durations showing seconds only (< 1 minute)."""
        assert format_duration(1_000) == "1s"  # 1 second
        assert format_duration(14_000) == "14s"  # 14 seconds
        assert format_duration(30_000) == "30s"  # 30 seconds
        assert format_duration(59_000) == "59s"  # 59 seconds

    def test_exactly_one_minute(self) -> None:
        """Test exactly 60,000ms returns '1m' (zero seconds omitted)."""
        assert format_duration(60_000) == "1m"

    def test_minutes_and_seconds(self) -> None:
        """Test durations showing both minutes and seconds."""
        assert format_duration(2 * MS_PER_MINUTE + 14_000) == "2m 14s"  # story example
        assert format_duration(5 * MS_PER_MINUTE + 30_000) == "5m 30s"
        assert format_duration(47 * MS_PER_MINUTE + 1_000) == "47m 1s"

    def test_exact_minute_values_omit_seconds(self) -> None:
        """Test exact minutes omit zero seconds component."""
        assert format_duration(2 * MS_PER_MINUTE) == "2m"
        assert format_duration(5 * MS_PER_MINUTE) == "5m"
        assert format_duration(15 * MS_PER_MINUTE) == "15m"
        assert format_duration(47 * MS_PER_MINUTE) == "47m"

    def test_fifty_nine_minutes(self) -> None:
        """Test 59 minutes returns '59m'."""
        assert format_duration(59 * MS_PER_MINUTE) == "59m"

    def test_just_under_one_hour(self) -> None:
        """Test 59m59s shows full precision."""
        assert format_duration(MS_PER_HOUR - 1000) == "59m 59s"


class TestFormatDurationMedium:
    """Test AC2: Medium durations (1-24 hours)."""

    def test_exactly_one_hour(self) -> None:
        """Test exactly 1 hour returns '1h' (no zero minutes)."""
        assert format_duration(MS_PER_HOUR) == "1h"

    def test_one_hour_five_minutes(self) -> None:
        """Test 1h 5m format."""
        assert format_duration(MS_PER_HOUR + 5 * MS_PER_MINUTE) == "1h 5m"

    def test_two_hours_seventeen_minutes(self) -> None:
        """Test 2h 17m format (story example)."""
        assert format_duration(2 * MS_PER_HOUR + 17 * MS_PER_MINUTE) == "2h 17m"

    def test_various_hour_minute_combinations(self) -> None:
        """Test various hour+minute combinations."""
        assert format_duration(3 * MS_PER_HOUR + 30 * MS_PER_MINUTE) == "3h 30m"
        assert format_duration(6 * MS_PER_HOUR + 45 * MS_PER_MINUTE) == "6h 45m"
        assert format_duration(12 * MS_PER_HOUR + 1 * MS_PER_MINUTE) == "12h 1m"

    def test_exact_hour_values_omit_minutes(self) -> None:
        """Test exact hours omit the zero minutes component."""
        assert format_duration(2 * MS_PER_HOUR) == "2h"
        assert format_duration(6 * MS_PER_HOUR) == "6h"
        assert format_duration(12 * MS_PER_HOUR) == "12h"
        assert format_duration(23 * MS_PER_HOUR) == "23h"

    def test_twenty_three_hours_fifty_nine_minutes(self) -> None:
        """Test 23h 59m is just under 24 hours."""
        assert format_duration(23 * MS_PER_HOUR + 59 * MS_PER_MINUTE) == "23h 59m"

    def test_just_under_twenty_four_hours(self) -> None:
        """Test just under 24h floors to 23h 59m."""
        assert format_duration(MS_PER_DAY - 1) == "23h 59m"


class TestFormatDurationLong:
    """Test AC3: Long durations (>= 24 hours)."""

    def test_exactly_one_day(self) -> None:
        """Test exactly 24 hours returns '1d' (no zero hours)."""
        assert format_duration(MS_PER_DAY) == "1d"

    def test_one_day_five_hours(self) -> None:
        """Test 1d 5h format (story example)."""
        assert format_duration(MS_PER_DAY + 5 * MS_PER_HOUR) == "1d 5h"

    def test_various_day_hour_combinations(self) -> None:
        """Test various day+hour combinations."""
        assert format_duration(2 * MS_PER_DAY + 12 * MS_PER_HOUR) == "2d 12h"
        assert format_duration(7 * MS_PER_DAY + 1 * MS_PER_HOUR) == "7d 1h"
        assert format_duration(14 * MS_PER_DAY + 3 * MS_PER_HOUR) == "14d 3h"

    def test_exact_day_values_omit_hours(self) -> None:
        """Test exact days omit the zero hours component."""
        assert format_duration(2 * MS_PER_DAY) == "2d"
        assert format_duration(3 * MS_PER_DAY) == "3d"
        assert format_duration(7 * MS_PER_DAY) == "7d"
        assert format_duration(30 * MS_PER_DAY) == "30d"

    def test_minutes_ignored_in_day_format(self) -> None:
        """Test that minutes are ignored in day format (only d+h shown)."""
        # 1 day, 5 hours, 30 minutes -> should show 1d 5h (not 1d 5h 30m)
        assert format_duration(MS_PER_DAY + 5 * MS_PER_HOUR + 30 * MS_PER_MINUTE) == "1d 5h"


class TestFormatDurationLargeValues:
    """Test AC5: Large value edge cases."""

    def test_two_weeks(self) -> None:
        """Test 14 days formatting."""
        assert format_duration(14 * MS_PER_DAY) == "14d"
        assert format_duration(14 * MS_PER_DAY + 3 * MS_PER_HOUR) == "14d 3h"

    def test_thirty_days(self) -> None:
        """Test 30 days formatting."""
        assert format_duration(30 * MS_PER_DAY) == "30d"

    def test_one_hundred_days(self) -> None:
        """Test 100 days formatting."""
        assert format_duration(100 * MS_PER_DAY) == "100d"
        assert format_duration(100 * MS_PER_DAY + 23 * MS_PER_HOUR) == "100d 23h"

    def test_one_year_approximately(self) -> None:
        """Test ~365 days formatting."""
        assert format_duration(365 * MS_PER_DAY) == "365d"

    def test_very_large_value(self) -> None:
        """Test very large value (1000 days)."""
        assert format_duration(1000 * MS_PER_DAY) == "1000d"
        assert format_duration(1000 * MS_PER_DAY + 12 * MS_PER_HOUR) == "1000d 12h"


class TestFormatDurationNegativeInput:
    """Test AC6: Negative input edge cases."""

    def test_small_negative_returns_zero_seconds(self) -> None:
        """Test small negative value returns '0s'."""
        assert format_duration(-1) == "0s"
        assert format_duration(-1000) == "0s"

    def test_large_negative_returns_zero_seconds(self) -> None:
        """Test large negative value returns '0s'."""
        assert format_duration(-MS_PER_MINUTE) == "0s"
        assert format_duration(-MS_PER_HOUR) == "0s"
        assert format_duration(-MS_PER_DAY) == "0s"

    def test_very_large_negative_returns_zero_seconds(self) -> None:
        """Test very large negative value returns '0s'."""
        assert format_duration(-1_000_000_000_000) == "0s"


class TestFormatDurationParametrized:
    """Parametrized tests covering all acceptance criteria."""

    @pytest.mark.parametrize(
        "milliseconds,expected",
        [
            # AC4: Zero duration (updated for seconds support)
            (0, "0s"),
            # AC1/AC8: Short durations (< 60 minutes) now include seconds
            (14_000, "14s"),  # 14 seconds only
            (30_000, "30s"),  # 30 seconds
            (59_999, "59s"),  # sub-minute shows seconds
            (60_000, "1m"),  # 1 minute exactly (0s omitted)
            (134_000, "2m 14s"),  # 2m 14s (story example)
            (2_820_000, "47m"),  # 47 minutes (0s omitted)
            (3_540_000, "59m"),  # 59 minutes (0s omitted)
            (3_599_000, "59m 59s"),  # 59m 59s
            # AC2: Medium durations (1-24 hours) - unchanged
            (3_600_000, "1h"),  # 1 hour exactly
            (3_900_000, "1h 5m"),  # 1h 5m
            (8_220_000, "2h 17m"),  # 2h 17m (story example)
            (43_200_000, "12h"),  # 12 hours exactly
            (86_340_000, "23h 59m"),  # 23h 59m
            # AC3: Long durations (>= 24 hours) - unchanged
            (86_400_000, "1d"),  # 1 day exactly
            (104_400_000, "1d 5h"),  # 1d 5h (story example)
            (259_200_000, "3d"),  # 3 days exactly
            (1_220_400_000, "14d 3h"),  # 14d 3h (story example)
            (2_592_000_000, "30d"),  # 30 days (story example)
            # AC6: Negative input (updated for seconds)
            (-1_000, "0s"),
            (-86_400_000, "0s"),  # negative day
        ],
    )
    def test_format_duration(self, milliseconds: int, expected: str) -> None:
        """Test duration formatting across all ranges."""
        assert format_duration(milliseconds) == expected


class TestFormatDurationBoundaries:
    """Test boundary conditions between format ranges."""

    def test_boundary_59s_to_1m(self) -> None:
        """Test transition from seconds-only to minutes format."""
        assert format_duration(59_000) == "59s"
        assert format_duration(60_000) == "1m"  # 0s omitted

    def test_boundary_59m_to_1h(self) -> None:
        """Test transition from minutes to hours format."""
        assert format_duration(59 * MS_PER_MINUTE) == "59m"
        assert format_duration(60 * MS_PER_MINUTE) == "1h"

    def test_boundary_23h59m_to_1d(self) -> None:
        """Test transition from hours to days format."""
        assert format_duration(23 * MS_PER_HOUR + 59 * MS_PER_MINUTE) == "23h 59m"
        assert format_duration(24 * MS_PER_HOUR) == "1d"

    def test_floor_division_behavior(self) -> None:
        """Test that floor division is used (fractional seconds truncated)."""
        # 1 minute + 59 seconds + 999ms should be 1m 59s, not 2m
        assert format_duration(MS_PER_MINUTE + 59_999) == "1m 59s"
        # 1 hour + 59 minutes + 59 seconds should be 1h 59m, not 2h
        assert format_duration(MS_PER_HOUR + 59 * MS_PER_MINUTE + 59_000) == "1h 59m"
