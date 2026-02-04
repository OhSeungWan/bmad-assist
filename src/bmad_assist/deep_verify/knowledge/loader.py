"""Knowledge base loader for Deep Verify Domain Expert Method.

This module provides the KnowledgeLoader class for loading and managing
domain-specific knowledge bases from YAML files. It supports loading
base rules (universal) plus domain-specific rules with proper
deduplication and override handling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from bmad_assist.deep_verify.core.types import Severity
from bmad_assist.deep_verify.knowledge.types import KnowledgeCategory

logger = logging.getLogger(__name__)

__all__ = [
    "KnowledgeLoader",
    "KnowledgeRule",
    "KnowledgeRuleYaml",
]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass(frozen=True)
class KnowledgeRule:
    """Single knowledge base rule for domain expert review.

    Attributes:
        id: Unique rule identifier (e.g., "SEC-OWASP-A01", "SEC-CWE-089", "GEN-001")
        domain: Domain this rule applies to (e.g., "security", "storage", "general")
        category: Knowledge category (STANDARDS, COMPLIANCE, BEST_PRACTICES, HEURISTICS)
        title: Short rule title
        description: Detailed rule description
        severity: Severity if rule is violated (enum)
        references: List of reference URLs (OWASP, CWE, etc.)

    """

    id: str
    domain: str
    category: KnowledgeCategory
    title: str
    description: str
    severity: Severity
    references: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """Return a string representation of the knowledge rule."""
        return (
            f"KnowledgeRule("
            f"id={self.id!r}, "
            f"domain={self.domain!r}, "
            f"category={self.category.value!r}, "
            f"title={self.title!r}, "
            f"references={self.references!r}"
            f")"
        )


# =============================================================================
# Pydantic Models for YAML Validation
# =============================================================================


class KnowledgeRuleYaml(BaseModel):
    """Pydantic model for validating knowledge rule YAML.

    This model validates the YAML structure and converts severity strings
    to the Severity enum via to_knowledge_rule().
    """

    id: str = Field(..., min_length=1, description="Unique rule identifier")
    domain: str = Field(..., min_length=1, description="Domain this rule applies to")
    category: str = Field(..., min_length=1, description="Knowledge category")
    title: str = Field(..., min_length=1, description="Short rule title")
    description: str = Field(..., min_length=1, description="Detailed rule description")
    severity: str = Field(..., min_length=1, description="Severity if violated")
    references: list[str] = Field(default_factory=list, description="Reference URLs")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is one of allowed values."""
        valid = {"standards", "compliance", "best_practices", "heuristics"}
        # Normalize: convert BEST_PRACTICES -> best_practices
        v_normalized = v.lower().replace("-", "_")
        if v_normalized not in valid:
            raise ValueError(f"Invalid category: {v}. Must be one of: {valid}")
        return v_normalized

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity is one of allowed values."""
        valid = {s.value for s in Severity}
        if v.lower() not in valid:
            raise ValueError(f"Invalid severity: {v}. Must be one of: {valid}")
        return v.lower()

    def to_knowledge_rule(self) -> KnowledgeRule:
        """Convert YAML model to runtime dataclass.

        Returns:
            KnowledgeRule with proper enum types.

        """
        # Convert category string to enum (the string value matches the enum value)
        # self.category is already normalized to lowercase by validator
        category_enum = KnowledgeCategory(self.category)

        return KnowledgeRule(
            id=self.id,
            domain=self.domain,
            category=category_enum,
            title=self.title,
            description=self.description,
            severity=Severity(self.severity),  # Already normalized to lowercase by validator
            references=self.references,
        )


class KnowledgeBaseYaml(BaseModel):
    """Root model for knowledge base YAML files."""

    knowledge_base: dict[str, Any]

    @field_validator("knowledge_base")
    @classmethod
    def validate_knowledge_base(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate knowledge_base has required fields."""
        required = {"version", "domain", "description", "rules"}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Validate rules is a list
        if not isinstance(v.get("rules"), list):
            raise ValueError("'rules' must be a list")

        return v


# =============================================================================
# Knowledge Loader
# =============================================================================


class KnowledgeLoader:
    """Loads and manages knowledge base rules from YAML files.

    The loader supports:
    - Loading base rules (universal rules that apply to all domains)
    - Loading domain-specific rules based on detected domains
    - Deduplication by rule ID (later rules override earlier ones)
    - Caching to avoid reloading the same files

    File structure:
        knowledge/data/
        ├── base.yaml          # Universal rules (always loaded)
        ├── security.yaml      # SECURITY domain rules
        ├── storage.yaml       # STORAGE domain rules
        ├── messaging.yaml     # MESSAGING domain rules
        ├── api.yaml           # API domain rules
        └── concurrency.yaml   # CONCURRENCY domain rules

    Example:
        >>> loader = KnowledgeLoader()
        >>> rules = loader.load([ArtifactDomain.SECURITY])
        >>> # Base rules + security rules are loaded
        >>> # Domain-specific rules override base rules with same ID

    """

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        """Initialize the knowledge loader.

        Args:
            knowledge_dir: Directory containing knowledge base YAML files.
                          If None, uses default location.

        """
        if knowledge_dir is None:
            knowledge_dir = Path(__file__).parent / "data"
        self._knowledge_dir = knowledge_dir
        self._cache: dict[str, list[KnowledgeRule]] = {}

    def __repr__(self) -> str:
        """Return a string representation of the knowledge loader."""
        return f"KnowledgeLoader(dir={self._knowledge_dir!r})"

    def load(
        self,
        domains: list[Any] | None = None,
        use_base: bool = True,
    ) -> list[KnowledgeRule]:
        """Load knowledge base rules for specified domains.

        Load order:
        1. Base rules (if use_base=True) - loaded first
        2. Domain-specific rules - loaded in order of domains list

        Deduplication:
        - Rules with the same ID are deduplicated
        - Later rules override earlier rules
        - Domain-specific rules override base rules with same ID

        Args:
            domains: Optional list of ArtifactDomain to load domain-specific rules.
                     If None, only base rules are loaded (if use_base=True).
            use_base: Whether to load base.yaml rules first. Default True.

        Returns:
            List of KnowledgeRule objects with deduplication applied.

        """
        all_rules: list[KnowledgeRule] = []

        # Always load base rules first
        if use_base:
            base_rules = self._load_knowledge_file("base")
            all_rules.extend(base_rules)

        # Load domain-specific checklists
        if domains:
            domain_file_map = {
                "security": "security",
                "storage": "storage",
                "messaging": "messaging",
                "api": "api",
                "concurrency": "concurrency",
                "transform": "transform",
            }

            loaded_files: set[str] = set()
            for domain in domains:
                # Handle both enum and string domains
                domain_value = domain.value if hasattr(domain, "value") else str(domain).lower()
                file_name = domain_file_map.get(domain_value)
                if file_name and file_name not in loaded_files:
                    domain_rules = self._load_knowledge_file(file_name)
                    all_rules.extend(domain_rules)
                    loaded_files.add(file_name)

        # Deduplicate by ID with logging for overrides
        seen: dict[str, KnowledgeRule] = {}
        override_count = 0
        for rule in all_rules:
            if rule.id in seen:
                logger.warning(
                    "Knowledge rule override: '%s' from domain '%s' overriding previous definition",
                    rule.id,
                    rule.domain,
                )
                override_count += 1
            seen[rule.id] = rule

        if override_count > 0:
            logger.debug("Total knowledge rule overrides: %d", override_count)

        return list(seen.values())

    def _load_knowledge_file(self, name: str) -> list[KnowledgeRule]:
        """Load knowledge rules from a YAML file.

        Args:
            name: Base name of the knowledge file (e.g., "base", "security").

        Returns:
            List of KnowledgeRule objects from the file.

        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]

        file_path = self._knowledge_dir / f"{name}.yaml"

        if not file_path.exists():
            logger.debug("Knowledge file not found: %s", file_path)
            return []

        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                logger.debug("Empty knowledge file: %s", file_path)
                return []

            # Validate with Pydantic
            kb_yaml = KnowledgeBaseYaml(**data)
            kb_data = kb_yaml.knowledge_base

            # Convert rules
            rules: list[KnowledgeRule] = []
            for rule_data in kb_data.get("rules", []):
                try:
                    rule_yaml = KnowledgeRuleYaml(**rule_data)
                    rules.append(rule_yaml.to_knowledge_rule())
                except (ValidationError, ValueError, TypeError) as e:
                    logger.warning(
                        "Failed to parse rule in %s: %s - %s",
                        file_path,
                        rule_data.get("id", "unknown"),
                        e,
                    )

            logger.debug("Loaded %d rules from %s", len(rules), file_path)

            # Cache the result
            self._cache[name] = rules

            return rules

        except yaml.YAMLError as e:
            logger.error("Failed to parse knowledge YAML %s: %s", file_path, e)
            return []
        except Exception as e:
            logger.error("Failed to load knowledge %s: %s", file_path, e)
            return []

    def clear_cache(self) -> None:
        """Clear the internal cache.

        Useful for testing or when knowledge files have been updated.
        """
        self._cache.clear()
