"""Deep Verify integration hook for validate_story phase.

Story 26.16: Validate Story Integration Hook

This module provides the integration point for Deep Verify into the
validate_story phase, running DV verification in parallel with Multi-LLM
validators via asyncio.gather().

Example:
    >>> from bmad_assist.deep_verify.integration.validate_story_hook import (
    ...     run_deep_verify_validation,
    ... )
    >>> result = await run_deep_verify_validation(
    ...     artifact_text="def authenticate_user(token): ...",
    ...     config=config,
    ...     project_path=Path("."),
    ...     epic_num=26,
    ...     story_num=16,
    ... )
    >>> print(result.verdict)
    VerdictDecision.REJECT

"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from bmad_assist.core.exceptions import BmadAssistError, ProviderError, ProviderTimeoutError
from bmad_assist.deep_verify.core.engine import DeepVerifyEngine
from bmad_assist.deep_verify.core.types import (
    DeepVerifyValidationResult,
    VerdictDecision,
)

if TYPE_CHECKING:
    from bmad_assist.core.config import Config
    from bmad_assist.core.types import EpicId

logger = logging.getLogger(__name__)


async def run_deep_verify_validation(
    artifact_text: str,
    config: Config,
    project_path: Path,
    epic_num: EpicId,
    story_num: int | str,
    timeout: int | None = None,
) -> DeepVerifyValidationResult:
    """Run Deep Verify validation parallel to Multi-LLM validators.

    This function is designed to be added to the asyncio.gather() call
    in the validation orchestrator. It creates a DeepVerifyEngine instance
    and runs verification on the artifact text.

    If Deep Verify is disabled in config, or if the engine fails,
    returns an empty ACCEPT result (non-blocking behavior).

    Args:
        artifact_text: The compiled story/prompt text to analyze.
        config: Application configuration with deep_verify settings.
        project_path: Path to project root.
        epic_num: Epic number being validated (int or str like "testarch").
        story_num: Story number being validated (int or str).
        timeout: Optional timeout in seconds. If None, uses config default.

    Returns:
        DeepVerifyValidationResult with findings, domains, verdict, and score.
        Returns empty ACCEPT result if DV is disabled or fails.

    Example:
        >>> result = await run_deep_verify_validation(
        ...     artifact_text="def authenticate_user(token): ...",
        ...     config=config,
        ...     project_path=Path("."),
        ...     epic_num=26,
        ...     story_num=16,
        ...     timeout=60,
        ... )
        >>> print(f"DV Verdict: {result.verdict.value}")
        >>> print(f"Findings: {len(result.findings)}")

    """
    # Check if DV is enabled in config
    dv_config = getattr(config, "deep_verify", None)
    if dv_config is None:
        logger.debug("Deep Verify config not present, skipping")
        return DeepVerifyValidationResult(
            findings=[],
            domains_detected=[],
            methods_executed=[],
            verdict=VerdictDecision.ACCEPT,
            score=0.0,
            duration_ms=0,
            error=None,
        )

    if not dv_config.enabled:
        logger.debug("Deep Verify disabled in config")
        return DeepVerifyValidationResult(
            findings=[],
            domains_detected=[],
            methods_executed=[],
            verdict=VerdictDecision.ACCEPT,
            score=0.0,
            duration_ms=0,
            error=None,
        )

    try:
        logger.info("Starting Deep Verify validation for story %s.%s", epic_num, story_num)

        # Track duration
        start_time = time.perf_counter()

        # Get helper provider config for fallback (when deep_verify.provider not set)
        helper_provider_config = getattr(config.providers, "helper", None)

        # Create engine and run verification
        engine = DeepVerifyEngine(
            project_root=project_path,
            config=dv_config,
            helper_provider_config=helper_provider_config,
        )

        verdict = await engine.verify(
            artifact_text=artifact_text,
            timeout=timeout,
        )

        # Calculate duration
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Convert Verdict to DeepVerifyValidationResult
        result = DeepVerifyValidationResult(
            findings=verdict.findings,
            domains_detected=verdict.domains_detected,
            methods_executed=verdict.methods_executed,
            verdict=verdict.decision,
            score=verdict.score,
            duration_ms=duration_ms,
            error=None,
        )

        logger.info(
            "Deep Verify validation complete: verdict=%s, score=%.1f, findings=%d",
            result.verdict.value,
            result.score,
            len(result.findings),
        )

        return result

    except (ProviderError, ProviderTimeoutError, BmadAssistError) as e:
        # Expected provider/config errors - non-blocking
        logger.warning(
            "Deep Verify validation failed (non-blocking) for story %s.%s: %s",
            epic_num,
            story_num,
            type(e).__name__,
        )
        return DeepVerifyValidationResult(
            findings=[],
            domains_detected=[],
            methods_executed=[],
            verdict=VerdictDecision.ACCEPT,
            score=0.0,
            duration_ms=0,
            error=f"{type(e).__name__}: {e}",
        )
    except Exception as e:
        # Unexpected errors - log with exc_info for debugging but still non-blocking
        logger.warning(
            "Deep Verify unexpected error (non-blocking) for story %s.%s: %s",
            epic_num,
            story_num,
            type(e).__name__,
            exc_info=True,
        )
        return DeepVerifyValidationResult(
            findings=[],
            domains_detected=[],
            methods_executed=[],
            verdict=VerdictDecision.ACCEPT,
            score=0.0,
            duration_ms=0,
            error=f"{type(e).__name__}: {e}",
        )
