"""Verification methods for Deep Verify.

This module provides the verification method implementations for the
Deep Verify system. Each method implements a specific verification technique.

Example:
    >>> from bmad_assist.deep_verify.methods import PatternMatchMethod
    >>> from bmad_assist.deep_verify.patterns import get_default_pattern_library
    >>>
    >>> # Load default patterns
    >>> library = get_default_pattern_library()
    >>> method = PatternMatchMethod(patterns=library.get_all_patterns())
    >>>
    >>> # Analyze artifact
    >>> findings = await method.analyze("some code with race condition")
    >>> for finding in findings:
    ...     print(f"{finding.id}: {finding.title}")

"""

from bmad_assist.deep_verify.methods.adversarial_review import (
    ADVERSARIAL_REVIEW_SYSTEM_PROMPT,
    AdversarialCategory,
    AdversarialDefinition,
    AdversarialReviewMethod,
    AdversarialReviewResponse,
    AdversarialVulnerabilityData,
    ThreatLevel,
    threat_to_confidence,
    threat_to_severity,
)
from bmad_assist.deep_verify.methods.adversarial_review import (
    get_category_definitions as get_adversarial_category_definitions,
)
from bmad_assist.deep_verify.methods.assumption_surfacing import (
    AssumptionCategory,
    AssumptionDefinition,
    AssumptionFindingData,
    AssumptionSurfacingMethod,
)
from bmad_assist.deep_verify.methods.base import BaseVerificationMethod
from bmad_assist.deep_verify.methods.boundary_analysis import (
    BoundaryAnalysisMethod,
    ChecklistItem,
    ChecklistLoader,
)
from bmad_assist.deep_verify.methods.domain_expert import (
    DOMAIN_EXPERT_SYSTEM_PROMPT,
    DomainExpertAnalysisResponse,
    DomainExpertMethod,
    DomainExpertViolationData,
    resolve_finding_severity,
)
from bmad_assist.deep_verify.methods.integration_analysis import (
    INTEGRATION_ANALYSIS_SYSTEM_PROMPT,
    IntegrationAnalysisMethod,
    IntegrationAnalysisResponse,
    IntegrationCategory,
    IntegrationDefinition,
    IntegrationIssueData,
    IntegrationRiskLevel,
    get_integration_category_definitions,
)
from bmad_assist.deep_verify.methods.integration_analysis import (
    risk_to_confidence as integration_risk_to_confidence,
)
from bmad_assist.deep_verify.methods.integration_analysis import (
    risk_to_severity as integration_risk_to_severity,
)
from bmad_assist.deep_verify.methods.pattern_match import PatternMatchMethod
from bmad_assist.deep_verify.methods.temporal_consistency import (
    TemporalCategory,
    TemporalConsistencyMethod,
)
from bmad_assist.deep_verify.methods.worst_case import (
    WORST_CASE_CONSTRUCTION_SYSTEM_PROMPT,
    ScenarioSeverity,
    WorstCaseAnalysisResponse,
    WorstCaseCategory,
    WorstCaseDefinition,
    WorstCaseMethod,
    WorstCaseScenarioData,
    severity_to_confidence,
    severity_to_finding_severity,
)
from bmad_assist.deep_verify.methods.worst_case import (
    get_category_definitions as get_worst_case_category_definitions,
)

__all__ = [
    # Domain Expert Method (#203)
    "DOMAIN_EXPERT_SYSTEM_PROMPT",
    "DomainExpertAnalysisResponse",
    "DomainExpertMethod",
    "DomainExpertViolationData",
    "resolve_finding_severity",
    # Integration Analysis Method (#204)
    "INTEGRATION_ANALYSIS_SYSTEM_PROMPT",
    "IntegrationAnalysisMethod",
    "IntegrationAnalysisResponse",
    "IntegrationCategory",
    "IntegrationDefinition",
    "IntegrationIssueData",
    "IntegrationRiskLevel",
    # Adversarial Review Method (#201)
    "AdversarialCategory",
    "AdversarialDefinition",
    "AdversarialReviewMethod",
    "AdversarialReviewResponse",
    "AdversarialVulnerabilityData",
    "ADVERSARIAL_REVIEW_SYSTEM_PROMPT",
    "ThreatLevel",
    # Assumption Surfacing Method (#155)
    "AssumptionCategory",
    "AssumptionDefinition",
    "AssumptionFindingData",
    "AssumptionSurfacingMethod",
    # Base
    "BaseVerificationMethod",
    # Boundary Analysis Method (#154)
    "BoundaryAnalysisMethod",
    "ChecklistItem",
    "ChecklistLoader",
    # Pattern Match Method (#153)
    "PatternMatchMethod",
    # Temporal Consistency Method (#157)
    "TemporalCategory",
    "TemporalConsistencyMethod",
    # Worst Case Method (#205)
    "WorstCaseCategory",
    "WorstCaseDefinition",
    "WorstCaseMethod",
    "WorstCaseAnalysisResponse",
    "WorstCaseScenarioData",
    "WORST_CASE_CONSTRUCTION_SYSTEM_PROMPT",
    "ScenarioSeverity",
    # Utility functions
    "get_adversarial_category_definitions",
    "get_integration_category_definitions",
    "get_worst_case_category_definitions",
    "integration_risk_to_confidence",
    "integration_risk_to_severity",
    "severity_to_confidence",
    "severity_to_finding_severity",
    "threat_to_confidence",
    "threat_to_severity",
]
