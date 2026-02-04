"""Pattern-specific types for Deep Verify pattern library.

This module provides types specific to the pattern matching functionality,
including match results and matched signal representations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bmad_assist.deep_verify.core.types import Pattern, Signal


@dataclass(frozen=True, slots=True)
class MatchedSignal:
    """A signal that was matched with location information.

    Attributes:
        signal: The Signal that was matched.
        line_number: 1-based line number where the match occurred.
        matched_text: The actual text that matched.

    """

    signal: Signal
    line_number: int
    matched_text: str

    def __repr__(self) -> str:
        """Return a string representation of the matched signal."""
        matched_preview = (
            self.matched_text[:40] + "..." if len(self.matched_text) > 40 else self.matched_text
        )
        return f"MatchedSignal(signal={self.signal!r}, line={self.line_number}, text={matched_preview!r})"


@dataclass(frozen=True, slots=True)
class PatternMatchResult:
    """Result of matching a pattern against text.

    Attributes:
        pattern: The Pattern that was matched.
        confidence: Match confidence 0.0-1.0 (weighted signal coverage).
        matched_signals: List of signals that matched with location info.
        unmatched_signals: List of signals that did not match.

    """

    pattern: Pattern
    confidence: float
    matched_signals: list[MatchedSignal]
    unmatched_signals: list[Signal]

    def __repr__(self) -> str:
        """Return a string representation of the pattern match result."""
        return (
            f"PatternMatchResult(pattern={self.pattern.id!r}, "
            f"confidence={self.confidence:.2f}, "
            f"matched={len(self.matched_signals)}, "
            f"unmatched={len(self.unmatched_signals)})"
        )


def serialize_matched_signal(ms: MatchedSignal) -> dict[str, Any]:
    """Serialize MatchedSignal to a dictionary."""
    from bmad_assist.deep_verify.core.types import serialize_signal

    return {
        "signal": serialize_signal(ms.signal),
        "line_number": ms.line_number,
        "matched_text": ms.matched_text,
    }


def deserialize_matched_signal(data: dict[str, Any]) -> MatchedSignal:
    """Deserialize a dictionary to MatchedSignal."""
    from bmad_assist.deep_verify.core.types import deserialize_signal

    return MatchedSignal(
        signal=deserialize_signal(data["signal"]),
        line_number=data["line_number"],
        matched_text=data["matched_text"],
    )


def serialize_match_result(result: PatternMatchResult) -> dict[str, Any]:
    """Serialize PatternMatchResult to a dictionary."""
    from bmad_assist.deep_verify.core.types import serialize_pattern

    return {
        "pattern": serialize_pattern(result.pattern),
        "confidence": result.confidence,
        "matched_signals": [serialize_matched_signal(ms) for ms in result.matched_signals],
        "unmatched_signals": [
            {"type": s.type, "pattern": s.pattern, "weight": s.weight}
            for s in result.unmatched_signals
        ],
    }


def deserialize_match_result(data: dict[str, Any]) -> PatternMatchResult:
    """Deserialize a dictionary to PatternMatchResult."""
    from bmad_assist.deep_verify.core.types import (
        deserialize_pattern,
    )

    pattern_data = data["pattern"]
    # Deserialize the pattern first
    pattern = deserialize_pattern(pattern_data)

    # Deserialize matched signals
    matched_signals = [deserialize_matched_signal(ms) for ms in data.get("matched_signals", [])]

    # Deserialize unmatched signals (simplified - just basic Signal data)
    unmatched_signals = [
        Signal(type=s["type"], pattern=s["pattern"], weight=s.get("weight", 1.0))
        for s in data.get("unmatched_signals", [])
    ]

    return PatternMatchResult(
        pattern=pattern,
        confidence=data["confidence"],
        matched_signals=matched_signals,
        unmatched_signals=unmatched_signals,
    )
