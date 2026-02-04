"""Core module for Deep Verify types, scoring, and engine."""

from bmad_assist.deep_verify.core.domain_detector import (
    DomainDetector,
    deserialize_domain_detection_result,
    detect_domains,
    serialize_domain_detection_result,
)
from bmad_assist.deep_verify.core.exceptions import (
    CategorizedError,
    DeepVerifyError,
    DomainDetectionError,
    ErrorCategorizer,
    ErrorCategory,
    InputValidationError,
    ResourceLimitError,
)
from bmad_assist.deep_verify.core.input_validator import (
    InputValidator,
    ValidationResult,
)
from bmad_assist.deep_verify.core.language_detector import (
    LanguageDetector,
    LanguageInfo,
)
from bmad_assist.deep_verify.core.method_selector import MethodSelector
from bmad_assist.deep_verify.core.scoring import (
    EvidenceScorer,
    calculate_score,
    determine_verdict,
)
from bmad_assist.deep_verify.core.types import (
    ArtifactDomain,
    DeepVerifyValidationResult,
    DomainAmbiguity,
    DomainConfidence,
    DomainDetectionResult,
    Evidence,
    Finding,
    MethodId,
    MethodResult,
    Pattern,
    PatternId,
    Severity,
    Verdict,
    VerdictDecision,
    VerdictError,
    deserialize_finding,
    deserialize_verdict,
    serialize_finding,
    serialize_verdict,
)

__all__ = [
    # Exceptions and Error Handling
    "DeepVerifyError",
    "InputValidationError",
    "ResourceLimitError",
    "DomainDetectionError",
    "ErrorCategory",
    "CategorizedError",
    "ErrorCategorizer",
    # Input Validation
    "InputValidator",
    "ValidationResult",
    # Domain detection
    "DomainDetector",
    "detect_domains",
    "serialize_domain_detection_result",
    "deserialize_domain_detection_result",
    # Language detection
    "LanguageDetector",
    "LanguageInfo",
    # Core types
    "ArtifactDomain",
    "DomainConfidence",
    "DomainDetectionResult",
    "Evidence",
    "Finding",
    "Verdict",
    "DeepVerifyValidationResult",
    "Pattern",
    "Severity",
    "VerdictDecision",
    "DomainAmbiguity",
    "MethodId",
    "PatternId",
    "VerdictError",
    "MethodResult",
    # Scoring
    "EvidenceScorer",
    "calculate_score",
    "determine_verdict",
    # Method Selector
    "MethodSelector",
    # Serialization
    "serialize_finding",
    "deserialize_finding",
    "serialize_verdict",
    "deserialize_verdict",
    # Engine - users should import directly from core.engine
    # "DeepVerifyEngine",
    # "VerificationContext",
]
