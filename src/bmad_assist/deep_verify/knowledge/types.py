"""Types for the knowledge base framework.

This module defines the KnowledgeCategory enum used to classify knowledge rules
by their type (standards, compliance, best practices, heuristics).
"""

from __future__ import annotations

from enum import Enum


class KnowledgeCategory(str, Enum):
    """Categories for knowledge base rules.

    Each category represents a different type of domain expertise:
    - STANDARDS: Industry standards (OWASP Top 10, PCI-DSS, HIPAA, etc.)
    - COMPLIANCE: Regulatory and compliance requirements
    - BEST_PRACTICES: Domain best practices and conventions
    - HEURISTICS: Expert heuristics and rules of thumb

    The category affects how findings are prioritized:
    - STANDARDS/COMPLIANCE violations are typically high severity
    - BEST_PRACTICES violations are typically warnings
    - HEURISTICS violations are typically informational
    """

    STANDARDS = "standards"
    COMPLIANCE = "compliance"
    BEST_PRACTICES = "best_practices"
    HEURISTICS = "heuristics"
