"""Deep Verify LLM Infrastructure module.

This module provides robust LLM calling infrastructure with:
- Retry logic with exponential backoff
- Token bucket rate limiting
- Cost tracking per model and method
- Timeout handling with graceful degradation
- Comprehensive call logging

Example:
    >>> from bmad_assist.deep_verify.infrastructure import LLMClient
    >>> from bmad_assist.deep_verify.config import DeepVerifyConfig
    >>> from bmad_assist.providers import ClaudeSDKProvider
    >>>
    >>> config = DeepVerifyConfig()
    >>> client = LLMClient(config, ClaudeSDKProvider())
    >>>
    >>> # Async invocation with all features
    >>> result = await client.invoke(
    ...     prompt="Analyze this code",
    ...     model="haiku",
    ...     timeout=30,
    ...     method_id="#153",
    ... )
    >>>
    >>> # Get cost summary
    >>> summary = client.get_cost_summary()
    >>> print(f"Total cost: ${summary.estimated_cost_usd:.4f}")

"""

from bmad_assist.deep_verify.infrastructure.cost_tracker import (
    MODEL_PRICING,
    CostTracker,
    calculate_cost,
    create_cost_tracker,
    estimate_tokens,
    get_model_pricing,
)
from bmad_assist.deep_verify.infrastructure.llm_client import (
    LLMClient,
    create_llm_client,
)
from bmad_assist.deep_verify.infrastructure.rate_limiter import (
    NoOpRateLimiter,
    TokenBucketRateLimiter,
    create_rate_limiter,
)
from bmad_assist.deep_verify.infrastructure.retry_handler import (
    RetryConfig,
    RetryHandler,
    calculate_retry_delay,
    is_retriable_error,
)
from bmad_assist.deep_verify.infrastructure.types import (
    CostSummary,
    LLMCallRecord,
    MethodCost,
    ModelCost,
    RateLimitStatus,
    serialize_cost_summary,
    serialize_llm_call_record,
)

__all__ = [
    # Main client
    "LLMClient",
    "create_llm_client",
    # Cost tracking
    "CostTracker",
    "create_cost_tracker",
    "calculate_cost",
    "estimate_tokens",
    "get_model_pricing",
    "MODEL_PRICING",
    # Retry handling
    "RetryConfig",
    "RetryHandler",
    "is_retriable_error",
    "calculate_retry_delay",
    # Rate limiting
    "TokenBucketRateLimiter",
    "NoOpRateLimiter",
    "create_rate_limiter",
    # Types
    "CostSummary",
    "ModelCost",
    "MethodCost",
    "LLMCallRecord",
    "RateLimitStatus",
    "serialize_cost_summary",
    "serialize_llm_call_record",
]
