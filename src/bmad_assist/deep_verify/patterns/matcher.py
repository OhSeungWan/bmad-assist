"""Pattern matcher for Deep Verify.

This module provides the PatternMatcher class for matching patterns
against text with signal detection and confidence scoring.
"""

from __future__ import annotations

import logging
import re
import signal
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bmad_assist.deep_verify.core.types import Pattern, Signal
from bmad_assist.deep_verify.patterns.library import PatternLibrary
from bmad_assist.deep_verify.patterns.types import MatchedSignal, PatternMatchResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default regex timeout in seconds
DEFAULT_REGEX_TIMEOUT = 5.0

# Track if SIGALRM is available (Unix only)
_SIGALRM_AVAILABLE = hasattr(signal, "SIGALRM")


class TimeoutError(Exception):
    """Raised when regex pattern matching times out."""

    pass


def _timeout_handler(signum: int, frame: object) -> None:
    """Signal handler for regex timeout."""
    raise TimeoutError("Regex pattern matching timed out")


def match_with_timeout(pattern: re.Pattern[str], text: str, timeout_seconds: float) -> re.Match[str] | None:
    """Match regex pattern with timeout protection.

    Uses signal.SIGALRM on Unix systems for timeout. On non-Unix systems,
    falls back to direct matching without timeout (best effort).

    Args:
        pattern: Compiled regex pattern.
        text: Text to search in.
        timeout_seconds: Timeout in seconds.

    Returns:
        Match object if found, None otherwise.

    Raises:
        TimeoutError: If matching exceeds timeout.

    """
    if not _SIGALRM_AVAILABLE:
        # Fallback: no timeout protection on non-Unix systems
        return pattern.search(text)

    # Set up timeout handler
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    old_alarm = signal.alarm(int(timeout_seconds))

    try:
        return pattern.search(text)
    finally:
        # Restore previous handler and alarm
        signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(old_alarm)


@dataclass(frozen=True, slots=True)
class MatchContext:
    """Context for pattern matching.

    Attributes:
        text: The full text being matched against.
        lines: The text split into lines (for line number extraction).
        line_offsets: List of starting positions for each line.

    """

    text: str
    lines: list[str]
    line_offsets: list[int]

    @classmethod
    def from_text(cls, text: str) -> MatchContext:
        """Create a MatchContext from text.

        Args:
            text: The text to create context for.

        Returns:
            MatchContext with parsed lines and offsets.

        """
        lines = text.split("\n")
        line_offsets = []
        offset = 0
        for line in lines:
            line_offsets.append(offset)
            offset += len(line) + 1  # +1 for newline character
        return cls(text=text, lines=lines, line_offsets=line_offsets)

    def get_line_number(self, position: int) -> int:
        """Get the 1-based line number for a character position.

        Args:
            position: Character position in the text.

        Returns:
            1-based line number (clamped to valid range).

        """
        for i, offset in enumerate(reversed(self.line_offsets)):
            if position >= offset:
                return len(self.line_offsets) - i
        return 1

    def get_line_content(self, line_number: int) -> str:
        """Get the content of a specific line.

        Args:
            line_number: 1-based line number.

        Returns:
            The line content, or empty string if out of range.

        """
        idx = line_number - 1
        if 0 <= idx < len(self.lines):
            return self.lines[idx]
        return ""


class PatternMatcher:
    """Matcher for detecting patterns in text.

    The matcher analyzes text against a set of patterns and returns
    match results with confidence scores and location information.

    Attributes:
        _patterns: List of patterns to match against.
        _threshold: Minimum confidence threshold for matches.
        _regex_timeout: Timeout for regex matching in seconds.

    """

    DEFAULT_THRESHOLD = 0.6  # 60% signal match required

    def __init__(
        self,
        patterns: list[Pattern],
        threshold: float = DEFAULT_THRESHOLD,
        library: PatternLibrary | None = None,
        regex_timeout: float = DEFAULT_REGEX_TIMEOUT,
    ) -> None:
        """Initialize the matcher with patterns.

        Args:
            patterns: List of patterns to match against.
            threshold: Minimum confidence threshold (0.0-1.0).
            library: Optional PatternLibrary for pre-compiled regexes.
            regex_timeout: Timeout for regex pattern matching in seconds.

        """
        self._patterns = patterns
        self._threshold = threshold
        self._library = library
        self._regex_timeout = regex_timeout

    def __repr__(self) -> str:
        """Return a string representation of the matcher."""
        return f"PatternMatcher(patterns={len(self._patterns)}, threshold={self._threshold:.2f})"

    def match(self, text: str) -> list[PatternMatchResult]:
        """Match all patterns against the text.

        Args:
            text: The text to analyze.

        Returns:
            List of PatternMatchResult objects with confidence >= threshold,
            sorted by confidence descending.

        """
        if not text or not self._patterns:
            return []

        context = MatchContext.from_text(text)
        results: list[PatternMatchResult] = []

        for pattern in self._patterns:
            result = self._match_single(pattern, context)
            if result and result.confidence >= self._threshold:
                results.append(result)

        # Sort by confidence descending
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def match_single(self, text: str, pattern: Pattern) -> PatternMatchResult | None:
        """Match a single pattern against text.

        Args:
            text: The text to analyze.
            pattern: The pattern to match.

        Returns:
            PatternMatchResult if the pattern matches (confidence >= threshold),
            None otherwise.

        """
        if not text:
            return None

        context = MatchContext.from_text(text)
        result = self._match_single(pattern, context)

        # Apply threshold filter for consistency with match() behavior
        if result and result.confidence < self._threshold:
            return None
        return result

    def _match_single(self, pattern: Pattern, context: MatchContext) -> PatternMatchResult | None:
        """Match a single pattern against the context.

        Args:
            pattern: The pattern to match.
            context: The match context.

        Returns:
            PatternMatchResult if the pattern matches, None otherwise.

        """
        matched_signals: list[MatchedSignal] = []
        unmatched_signals: list[Signal] = []

        for sig in pattern.signals:
            matched, line_number, matched_text = self._match_signal(sig, context, pattern)
            if matched:
                matched_signals.append(
                    MatchedSignal(
                        signal=sig,
                        line_number=line_number,
                        matched_text=matched_text,
                    )
                )
            else:
                unmatched_signals.append(sig)

        confidence = self._calculate_confidence(pattern, matched_signals)

        return PatternMatchResult(
            pattern=pattern,
            confidence=confidence,
            matched_signals=matched_signals,
            unmatched_signals=unmatched_signals,
        )

    def _match_signal(
        self,
        signal: Signal,
        context: MatchContext,
        pattern: Pattern,
    ) -> tuple[bool, int, str]:
        """Match a single signal against the context.

        Args:
            signal: The signal to match.
            context: The match context.
            pattern: The parent pattern (for library lookup).

        Returns:
            Tuple of (matched, line_number, matched_text).

        """
        if signal.type == "regex":
            return self._match_regex_signal(signal, context, pattern)
        else:
            return self._match_exact_signal(signal, context)

    def _match_exact_signal(self, signal: Signal, context: MatchContext) -> tuple[bool, int, str]:
        """Match an exact string signal.

        Args:
            signal: The exact signal to match.
            context: The match context.

        Returns:
            Tuple of (matched, line_number, matched_text).

        """
        pattern_lower = signal.pattern.lower()
        text_lower = context.text.lower()

        idx = text_lower.find(pattern_lower)
        if idx == -1:
            return False, 0, ""

        line_number = context.get_line_number(idx)
        # Capture ACTUAL text from input to preserve case and context
        matched_text = context.text[idx : idx + len(signal.pattern)]
        return True, line_number, matched_text

    def _match_regex_signal(
        self,
        signal: Signal,
        context: MatchContext,
        pattern: Pattern,
    ) -> tuple[bool, int, str]:
        """Match a regex signal with timeout protection.

        Args:
            signal: The regex signal to match.
            context: The match context.
            pattern: The parent pattern.

        Returns:
            Tuple of (matched, line_number, matched_text).

        """
        # Try to get pre-compiled regex from library
        compiled_regex = None
        if self._library:
            # Find the signal index in the pattern
            try:
                signal_idx = pattern.signals.index(signal)
                compiled_regex = self._library.get_compiled_regex(pattern.id, signal_idx)
            except ValueError:
                pass

        # Compile on the fly if not found in library
        if compiled_regex is None:
            try:
                # Use DOTALL so . matches newlines for multiline code matching
                compiled_regex = re.compile(signal.pattern, re.IGNORECASE | re.DOTALL)
            except re.error as e:
                logger.warning(
                    "Invalid regex pattern '%s' in pattern '%s': %s",
                    signal.pattern,
                    pattern.id,
                    e,
                )
                return False, 0, ""

        try:
            # Use timeout-protected matching
            match = match_with_timeout(compiled_regex, context.text, self._regex_timeout)
        except TimeoutError:
            logger.error(
                "Regex timeout for pattern '%s' signal '%s' after %.1fs",
                pattern.id,
                signal.pattern[:50],
                self._regex_timeout,
            )
            return False, 0, ""

        if not match:
            return False, 0, ""

        line_number = context.get_line_number(match.start())
        matched_text = match.group(0)
        return True, line_number, matched_text

    def _calculate_confidence(
        self, pattern: Pattern, matched_signals: list[MatchedSignal]
    ) -> float:
        """Calculate match confidence based on weighted signal coverage.

        Formula: sum(matched_signal_weights) / sum(all_signal_weights)

        Args:
            pattern: The pattern being matched.
            matched_signals: List of signals that matched.

        Returns:
            Float 0.0-1.0 representing confidence percentage.

        """
        total_weight = sum(s.weight for s in pattern.signals)
        if total_weight == 0:
            return 0.0

        matched_weight = sum(ms.signal.weight for ms in matched_signals)
        confidence = matched_weight / total_weight

        return min(confidence, 1.0)
