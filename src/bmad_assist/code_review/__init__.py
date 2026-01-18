"""Code review orchestration module.

Story 13.10: Code Review Benchmarking Integration

This module provides Multi-LLM code review orchestration with benchmarking
integration. It follows the same pattern as validation/orchestrator.py
but uses workflow.id = "code-review" for evaluation records.

Public API:
    CodeReviewError: Base exception for code review errors
    InsufficientReviewsError: Raised when fewer than minimum reviews completed
    CodeReviewPhaseResult: Result dataclass for code review phase
    run_code_review_phase: Main orchestration function
    CODE_REVIEW_WORKFLOW_ID: Constant for workflow identification
    CODE_REVIEW_SYNTHESIS_WORKFLOW_ID: Constant for synthesis workflow
"""

from bmad_assist.code_review.orchestrator import (
    CODE_REVIEW_SYNTHESIS_WORKFLOW_ID,
    CODE_REVIEW_WORKFLOW_ID,
    CodeReviewError,
    CodeReviewPhaseResult,
    InsufficientReviewsError,
    load_reviews_for_synthesis,
    run_code_review_phase,
    save_reviews_for_synthesis,
)

__all__ = [
    "CodeReviewError",
    "InsufficientReviewsError",
    "CodeReviewPhaseResult",
    "run_code_review_phase",
    "save_reviews_for_synthesis",
    "load_reviews_for_synthesis",
    "CODE_REVIEW_WORKFLOW_ID",
    "CODE_REVIEW_SYNTHESIS_WORKFLOW_ID",
]
