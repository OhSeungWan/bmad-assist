"""Knowledge base framework for Deep Verify Domain Expert Method.

This module provides the infrastructure for loading and managing domain-specific
knowledge bases used by the Domain Expert Method (#203). Knowledge bases contain
rules, standards, and best practices from various domains (SECURITY, STORAGE, etc.)

Public API:
    KnowledgeCategory: Enum for knowledge rule categories
    KnowledgeRule: Dataclass representing a single knowledge rule
    KnowledgeRuleYaml: Pydantic model for YAML validation
    KnowledgeLoader: Loads and manages knowledge base YAML files

Example:
    >>> from bmad_assist.deep_verify.knowledge import KnowledgeLoader, KnowledgeCategory
    >>>
    >>> # Load knowledge bases
    >>> loader = KnowledgeLoader()
    >>> rules = loader.load([ArtifactDomain.SECURITY])
    >>>
    >>> # Filter by category
    >>> standards = [r for r in rules if r.category == KnowledgeCategory.STANDARDS]

"""

from bmad_assist.deep_verify.knowledge.loader import (
    KnowledgeLoader,
    KnowledgeRule,
    KnowledgeRuleYaml,
)
from bmad_assist.deep_verify.knowledge.types import KnowledgeCategory

__all__ = [
    "KnowledgeCategory",
    "KnowledgeLoader",
    "KnowledgeRule",
    "KnowledgeRuleYaml",
]
