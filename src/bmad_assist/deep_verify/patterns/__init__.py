"""Pattern library for Deep Verify.

This module provides pattern loading and matching capabilities for the
Deep Verify verification system.

Pattern Types:
    - **Spec patterns** (data/spec/): Language-agnostic patterns for requirements,
      stories, and specifications. Pattern IDs like "CC-001", "SEC-004".
    - **Code patterns** (data/code/{language}/): Language-specific patterns for
      source code analysis. Pattern IDs like "CC-001-CODE", "CC-001-CODE-GO".

Supported Languages for Code Patterns:
    - Go (go/, golang)
    - Python (python/, py)

Example:
    >>> from bmad_assist.deep_verify.patterns import PatternLibrary, PatternMatcher
    >>> from pathlib import Path
    >>>
    >>> # Load patterns from YAML files
    >>> library = PatternLibrary.load([Path("patterns/data/spec")])
    >>> print(f"Loaded {len(library)} patterns")
    >>>
    >>> # Get patterns for specific domains
    >>> from bmad_assist.deep_verify.core.types import ArtifactDomain
    >>> patterns = library.get_patterns([ArtifactDomain.CONCURRENCY])
    >>>
    >>> # Get patterns for a specific language (includes spec + code patterns)
    >>> go_patterns = library.get_patterns(
    ...     [ArtifactDomain.CONCURRENCY, ArtifactDomain.SECURITY],
    ...     language="go",
    ... )
    >>>
    >>> # Match patterns against text
    >>> matcher = PatternMatcher(patterns)
    >>> results = matcher.match("some code with race condition")
    >>> for result in results:
    ...     print(f"{result.pattern.id}: {result.confidence:.2%}")

See Also:
    - data/code/README.md: Guide for authoring code patterns
    - data/spec/: Language-agnostic spec patterns
    - data/code/: Language-specific code patterns

"""

from bmad_assist.deep_verify.patterns.library import (
    PatternLibrary,
    get_default_pattern_library,
)
from bmad_assist.deep_verify.patterns.matcher import PatternMatcher
from bmad_assist.deep_verify.patterns.types import (
    MatchedSignal,
    PatternMatchResult,
)

__all__ = [
    "PatternLibrary",
    "PatternMatcher",
    "PatternMatchResult",
    "MatchedSignal",
    "get_default_pattern_library",
]
