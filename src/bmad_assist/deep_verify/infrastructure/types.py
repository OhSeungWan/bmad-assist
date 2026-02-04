"""Type definitions for Deep Verify LLM infrastructure.

This module provides data types for cost tracking, call logging, and
LLM client configuration.

All dataclasses are frozen for immutability, following bmad-assist patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# =============================================================================
# Cost Tracking Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class ModelCost:
    """Cost tracking for a specific model.

    Attributes:
        calls: Number of calls made to this model.
        input_tokens: Total input tokens sent to this model.
        output_tokens: Total output tokens received from this model.
        estimated_cost_usd: Estimated cost in USD.

    """

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def __repr__(self) -> str:
        """Return a string representation of the model cost."""
        return (
            f"ModelCost(calls={self.calls}, "
            f"tokens={self.input_tokens}+{self.output_tokens}, "
            f"cost=${self.estimated_cost_usd:.6f})"
        )


@dataclass(frozen=True, slots=True)
class MethodCost:
    """Cost tracking for a specific verification method.

    Attributes:
        calls: Number of calls made by this method.
        input_tokens: Total input tokens used by this method.
        output_tokens: Total output tokens used by this method.
        estimated_cost_usd: Estimated cost in USD.

    """

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def __repr__(self) -> str:
        """Return a string representation of the method cost."""
        return (
            f"MethodCost(calls={self.calls}, "
            f"tokens={self.input_tokens}+{self.output_tokens}, "
            f"cost=${self.estimated_cost_usd:.6f})"
        )


@dataclass(frozen=True, slots=True)
class CostSummary:
    """Summary of LLM costs for a verification run.

    Attributes:
        total_calls: Total number of LLM calls.
        total_input_tokens: Total input tokens across all calls.
        total_output_tokens: Total output tokens across all calls.
        total_tokens: Total tokens (input + output).
        estimated_cost_usd: Total estimated cost in USD.
        by_model: Cost breakdown by model.
        by_method: Cost breakdown by verification method.

    """

    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    by_model: dict[str, ModelCost] = field(default_factory=dict)
    by_method: dict[str, MethodCost] = field(default_factory=dict)

    def __repr__(self) -> str:
        """Return a string representation of the cost summary."""
        return (
            f"CostSummary(calls={self.total_calls}, "
            f"tokens={self.total_tokens}, "
            f"cost=${self.estimated_cost_usd:.6f})"
        )


# =============================================================================
# Call Logging Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class LLMCallRecord:
    """Record of a single LLM call.

    Attributes:
        timestamp: When the call was made.
        method_id: Which verification method made the call (if any).
        model: Model identifier used.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        latency_ms: Call latency in milliseconds.
        success: Whether the call succeeded.
        error: Error message if failed, None otherwise.
        retry_count: Number of retries performed.

    """

    timestamp: datetime
    method_id: str | None
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    success: bool
    error: str | None = None
    retry_count: int = 0

    def __repr__(self) -> str:
        """Return a string representation of the LLM call record."""
        status = "OK" if self.success else "FAIL"
        method_str = f"method={self.method_id}, " if self.method_id else ""
        return (
            f"LLMCallRecord({method_str}model={self.model}, "
            f"latency={self.latency_ms}ms, status={status})"
        )


# =============================================================================
# Rate Limiting Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class RateLimitStatus:
    """Current status of the rate limiter.

    Attributes:
        tokens_available: Current tokens in bucket.
        tokens_capacity: Maximum bucket capacity.
        refill_rate_per_second: Tokens added per second.
        last_refill_timestamp: Unix timestamp of last refill.

    """

    tokens_available: float
    tokens_capacity: int
    refill_rate_per_second: float
    last_refill_timestamp: float

    def __repr__(self) -> str:
        """Return a string representation of the rate limit status."""
        pct = (
            (self.tokens_available / self.tokens_capacity * 100) if self.tokens_capacity > 0 else 0
        )
        return (
            f"RateLimitStatus(tokens={self.tokens_available:.1f}/{self.tokens_capacity}, "
            f"{pct:.1f}%)"
        )


# =============================================================================
# Serialization Utilities
# =============================================================================


def serialize_cost_summary(summary: CostSummary) -> dict[str, Any]:
    """Serialize CostSummary to a dictionary."""
    return {
        "total_calls": summary.total_calls,
        "total_input_tokens": summary.total_input_tokens,
        "total_output_tokens": summary.total_output_tokens,
        "total_tokens": summary.total_tokens,
        "estimated_cost_usd": summary.estimated_cost_usd,
        "by_model": {
            model: {
                "calls": cost.calls,
                "input_tokens": cost.input_tokens,
                "output_tokens": cost.output_tokens,
                "estimated_cost_usd": cost.estimated_cost_usd,
            }
            for model, cost in summary.by_model.items()
        },
        "by_method": {
            method: {
                "calls": cost.calls,
                "input_tokens": cost.input_tokens,
                "output_tokens": cost.output_tokens,
                "estimated_cost_usd": cost.estimated_cost_usd,
            }
            for method, cost in summary.by_method.items()
        },
    }


def deserialize_cost_summary(data: dict[str, Any]) -> CostSummary:
    """Deserialize a dictionary to CostSummary."""
    return CostSummary(
        total_calls=data.get("total_calls", 0),
        total_input_tokens=data.get("total_input_tokens", 0),
        total_output_tokens=data.get("total_output_tokens", 0),
        total_tokens=data.get("total_tokens", 0),
        estimated_cost_usd=data.get("estimated_cost_usd", 0.0),
        by_model={
            model: ModelCost(
                calls=cost_data.get("calls", 0),
                input_tokens=cost_data.get("input_tokens", 0),
                output_tokens=cost_data.get("output_tokens", 0),
                estimated_cost_usd=cost_data.get("estimated_cost_usd", 0.0),
            )
            for model, cost_data in data.get("by_model", {}).items()
        },
        by_method={
            method: MethodCost(
                calls=cost_data.get("calls", 0),
                input_tokens=cost_data.get("input_tokens", 0),
                output_tokens=cost_data.get("output_tokens", 0),
                estimated_cost_usd=cost_data.get("estimated_cost_usd", 0.0),
            )
            for method, cost_data in data.get("by_method", {}).items()
        },
    )


def serialize_llm_call_record(record: LLMCallRecord) -> dict[str, Any]:
    """Serialize LLMCallRecord to a dictionary."""
    return {
        "timestamp": record.timestamp.isoformat(),
        "method_id": record.method_id,
        "model": record.model,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "latency_ms": record.latency_ms,
        "success": record.success,
        "error": record.error,
        "retry_count": record.retry_count,
    }


def deserialize_llm_call_record(data: dict[str, Any]) -> LLMCallRecord:
    """Deserialize a dictionary to LLMCallRecord."""
    return LLMCallRecord(
        timestamp=datetime.fromisoformat(data["timestamp"]),
        method_id=data.get("method_id"),
        model=data["model"],
        input_tokens=data.get("input_tokens", 0),
        output_tokens=data.get("output_tokens", 0),
        latency_ms=data.get("latency_ms", 0),
        success=data.get("success", True),
        error=data.get("error"),
        retry_count=data.get("retry_count", 0),
    )
