"""Deep Verify module for bmad-assist.

This module implements the Deep Verify methodology for catching bugs, race conditions,
and edge cases that Multi-LLM validation misses. It provides 8 verification methods
with domain-aware conditional execution.

Public API:
    DomainDetector: LLM-based artifact domain detector
    detect_domains: Convenience function for domain detection
    ArtifactDomain: Enum for artifact classification domains
    DomainConfidence: Dataclass for domain detection confidence
    DomainDetectionResult: Dataclass for domain detection output
    Evidence: Dataclass for individual evidence items
    Finding: Dataclass for verification findings
    Verdict: Dataclass for verification verdicts
    DeepVerifyValidationResult: Dataclass for integration hook results
    Pattern: Dataclass for verification patterns
    Signal: Dataclass for pattern signals
    Severity: Enum for finding severity levels
    VerdictDecision: Enum for verdict decisions
    DomainAmbiguity: Type alias for ambiguity levels
    MethodId: Type alias for method identifiers
    PatternId: Type alias for pattern identifiers
    EvidenceScorer: Class for scoring findings
    calculate_score: Standalone function to calculate score
    determine_verdict: Standalone function to determine verdict
    serialize_finding: Serialize Finding to dict
    deserialize_finding: Deserialize dict to Finding
    serialize_verdict: Serialize Verdict to dict
    deserialize_verdict: Deserialize dict to Verdict
    PatternLibrary: Class for loading patterns from YAML
    PatternMatcher: Class for matching patterns against text
    PatternMatchResult: Dataclass for match results
    MatchedSignal: Dataclass for matched signals
    get_default_pattern_library: Cached function to load default patterns

Example:
    from bmad_assist.deep_verify import (
        DomainDetector,
        ArtifactDomain,
        EvidenceScorer,
        calculate_score,
        determine_verdict,
    )

    # Detect domains
    detector = DomainDetector(project_root=Path("."))
    result = detector.detect("Verify JWT tokens")

    # Score findings
    scorer = EvidenceScorer()
    score = scorer.calculate_score(findings, clean_passes=2)
    verdict = determine_verdict(score)

"""

from bmad_assist.deep_verify.config import DeepVerifyConfig
from bmad_assist.deep_verify.core.domain_detector import (
    DomainDetector,
    detect_domains,
)
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
    Pattern,
    PatternId,
    Severity,
    Signal,
    Verdict,
    VerdictDecision,
    deserialize_finding,
    deserialize_verdict,
    serialize_finding,
    serialize_verdict,
)
from bmad_assist.deep_verify.knowledge import (
    KnowledgeCategory,
    KnowledgeLoader,
    KnowledgeRule,
    KnowledgeRuleYaml,
)
from bmad_assist.deep_verify.methods import (
    AdversarialCategory,
    AdversarialReviewMethod,
    AssumptionCategory,
    AssumptionSurfacingMethod,
    BaseVerificationMethod,
    BoundaryAnalysisMethod,
    ChecklistItem,
    ChecklistLoader,
    DomainExpertMethod,
    PatternMatchMethod,
    ScenarioSeverity,
    TemporalCategory,
    TemporalConsistencyMethod,
    WorstCaseCategory,
    WorstCaseMethod,
)
from bmad_assist.deep_verify.patterns import (
    MatchedSignal,
    PatternLibrary,
    PatternMatcher,
    PatternMatchResult,
)
from bmad_assist.deep_verify.patterns.library import get_default_pattern_library

__all__ = [
    # Domain detection
    "DomainDetector",
    "detect_domains",
    # Core types
    "ArtifactDomain",
    "DomainConfidence",
    "DomainDetectionResult",
    "Evidence",
    "Finding",
    "Verdict",
    "DeepVerifyValidationResult",
    "Pattern",
    "Signal",
    # Type aliases and enums
    "Severity",
    "VerdictDecision",
    "DomainAmbiguity",
    "MethodId",
    "PatternId",
    # Scoring
    "EvidenceScorer",
    "calculate_score",
    "determine_verdict",
    # Serialization
    "serialize_finding",
    "deserialize_finding",
    "serialize_verdict",
    "deserialize_verdict",
    # Pattern library
    "PatternLibrary",
    "PatternMatcher",
    "PatternMatchResult",
    "MatchedSignal",
    "get_default_pattern_library",
    # Knowledge base
    "KnowledgeCategory",
    "KnowledgeLoader",
    "KnowledgeRule",
    "KnowledgeRuleYaml",
    # Verification methods
    "AdversarialCategory",
    "AdversarialReviewMethod",
    "AssumptionCategory",
    "AssumptionSurfacingMethod",
    "BaseVerificationMethod",
    "BoundaryAnalysisMethod",
    "ChecklistItem",
    "ChecklistLoader",
    "DomainExpertMethod",
    "PatternMatchMethod",
    "TemporalCategory",
    "TemporalConsistencyMethod",
    "WorstCaseCategory",
    "WorstCaseMethod",
    "ScenarioSeverity",
    # Config
    "DeepVerifyConfig",
]
