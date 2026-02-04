r"""Language detection for Deep Verify.

This module provides the LanguageDetector class that detects programming languages
from file paths and content using multiple detection methods:

1. File Extension Detection (primary) - Fast and reliable
2. Shebang Line Detection (fallback) - For scripts without extensions
3. Content Heuristics (last resort) - Pattern matching for ambiguous files

Usage:
    >>> from pathlib import Path
    >>> from bmad_assist.deep_verify.core.language_detector import LanguageDetector
    >>> detector = LanguageDetector()
    >>> info = detector.detect(Path("main.go"))
    >>> print(info)
    LanguageInfo(language='go', confidence=0.95, file_type='source', detection_method='extension')

    # With content for shebang/heuristic detection
    >>> info = detector.detect(Path("script"), "#!/usr/bin/env python3\nprint('hello')")
    >>> print(info.language)
    python

Supported Languages:
    - Go (.go)
    - Python (.py, .pyi)
    - TypeScript (.ts)
    - JavaScript (.js, .mjs)
    - Rust (.rs)
    - Java (.java)
    - Ruby (.rb)

Detection Methods:
    - Extension: Checks file suffix against known mappings
    - Shebang: Parses #! line for interpreter (e.g., python3, node)
    - Heuristics: Pattern matching on content (e.g., "package main" for Go)

Design Principles:
    - Fast: No LLM calls, pure deterministic detection
    - Reliable: Multiple methods with confidence scores
    - Extensible: Easy to add new languages and patterns
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# Language Info Dataclass
# =============================================================================


@dataclass(frozen=True, slots=True)
class LanguageInfo:
    """Information about a detected programming language.

    Attributes:
        language: Canonical language name (e.g., "go", "python", "typescript").
        confidence: Detection confidence score from 0.0 to 1.0.
        file_type: Type of file - "source", "test", "interface", "script", or "unknown".
        detection_method: How the language was detected - "extension", "shebang",
                         "heuristic", or "unknown".

    Example:
        >>> info = LanguageInfo(language="go", confidence=0.95,
        ...                     file_type="source", detection_method="extension")
        >>> info.language
        'go'
        >>> info.is_unknown
        False

    """

    language: str
    confidence: float
    file_type: str
    detection_method: str

    @classmethod
    def unknown(cls) -> LanguageInfo:
        """Return LanguageInfo for unknown/undetected language.

        Returns:
            LanguageInfo with all fields set to "unknown" and confidence 0.0.

        Example:
            >>> info = LanguageInfo.unknown()
            >>> info.language
            'unknown'
            >>> info.confidence
            0.0

        """
        return cls(
            language="unknown",
            confidence=0.0,
            file_type="unknown",
            detection_method="unknown",
        )

    @property
    def is_unknown(self) -> bool:
        """Check if language is unknown.

        Returns:
            True if language is "unknown", False otherwise.

        """
        return self.language == "unknown"

    def __repr__(self) -> str:
        """Return string representation with formatted confidence."""
        return (
            f"LanguageInfo(language={self.language!r}, "
            f"confidence={self.confidence:.2f}, "
            f"file_type={self.file_type!r}, "
            f"detection_method={self.detection_method!r})"
        )


# =============================================================================
# Detection Mappings
# =============================================================================

# Extension mapping: extension -> (language, file_type, confidence)
EXTENSION_MAP: dict[str, tuple[str, str, float]] = {
    ".go": ("go", "source", 0.95),
    ".py": ("python", "source", 0.95),
    ".pyi": ("python", "interface", 0.95),  # Python stub files
    ".ts": ("typescript", "source", 0.95),
    ".js": ("javascript", "source", 0.95),
    ".mjs": ("javascript", "source", 0.95),  # ES module
    ".rs": ("rust", "source", 0.95),
    ".java": ("java", "source", 0.95),
    ".rb": ("ruby", "source", 0.95),
}

# Test file patterns: (suffix, language, file_type, confidence)
# These are checked when extension alone doesn't indicate a test file
TEST_PATTERNS: list[tuple[str, str, str, float]] = [
    ("_test.go", "go", "test", 0.90),
    ("_test.py", "python", "test", 0.90),
    (".test.ts", "typescript", "test", 0.90),
    (".spec.ts", "typescript", "test", 0.90),
    (".test.js", "javascript", "test", 0.90),
    (".spec.js", "javascript", "test", 0.90),
    ("_test.rs", "rust", "test", 0.90),
]

# Shebang patterns: (regex pattern, language, confidence)
# Regex matches the interpreter name after #!
SHEBANG_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # Python variants: python, python3, python3.11, etc.
    (re.compile(r"^#!/usr/bin/env\s+(?:-\S+\s+)?python\d*\.?\d*"), "python", 0.90),
    (re.compile(r"^#!/usr/bin/python\d*\.?\d*"), "python", 0.85),
    (re.compile(r"^#!/bin/python\d*\.?\d*"), "python", 0.85),
    (re.compile(r"^#!/usr/local/bin/python\d*\.?\d*"), "python", 0.85),
]

# Heuristic patterns: (regex pattern, language, confidence)
# Checked in order, first match wins
HEURISTIC_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # Go patterns
    (re.compile(r"\bpackage\s+\w+"), "go", 0.75),
    (re.compile(r"\bfunc\s+\w+\s*\("), "go", 0.80),
    (re.compile(r"\bgo\s+func\s*\("), "go", 0.85),
    # Python patterns
    (re.compile(r"\bdef\s+\w+\s*\([^)]*\)\s*:"), "python", 0.80),
    (re.compile(r"\basync\s+def\s+"), "python", 0.85),
    (re.compile(r"\bif\s+__name__\s*==\s*['\"]__main__['\"]"), "python", 0.95),
    # JavaScript/TypeScript patterns
    (re.compile(r"\bconst\s+\w+\s*=\s*.*=>"), "javascript", 0.70),
    (re.compile(r"\basync\s+function\s+"), "javascript", 0.80),
    (re.compile(r"\bexport\s+(default\s+)?"), "javascript", 0.65),
    # Rust patterns
    (re.compile(r"\bfn\s+main\s*\(\s*\)"), "rust", 0.85),
    (re.compile(r"\buse\s+std::"), "rust", 0.90),
    (re.compile(r"\blet\s+mut\s+"), "rust", 0.85),
    # Java patterns
    (re.compile(r"\bpublic\s+(class|interface)\s+\w+"), "java", 0.85),
    (re.compile(r"\bimport\s+java\."), "java", 0.90),
]

# Maximum file size to read for content detection (1MB)
MAX_FILE_SIZE = 1024 * 1024

# Maximum content length to scan for heuristics (first 500 chars)
MAX_HEURISTIC_SCAN_LENGTH = 500

# Maximum bytes to check for binary detection
BINARY_CHECK_BYTES = 1024


# =============================================================================
# Language Detector Class
# =============================================================================


class LanguageDetector:
    r"""Detects programming language from file path and content.

    Uses a 3-tier detection strategy:
    1. File extension (most reliable, 0.95 confidence)
    2. Shebang line (for scripts, 0.85-0.90 confidence)
    3. Content heuristics (last resort, 0.65-0.95 confidence)

    The detector is stateless and thread-safe. Results are cached based on
    file path and modification time.

    Attributes:
        _cache_enabled: Whether to cache detection results.
        _cache_maxsize: Maximum number of cached results.

    Example:
        >>> detector = LanguageDetector()
        >>> info = detector.detect(Path("main.go"))
        >>> info.language
        'go'
        >>> info.confidence
        0.95

        >>> info = detector.detect(Path("script"), "#!/usr/bin/env python3\n...")
        >>> info.language
        'python'
        >>> info.detection_method
        'shebang'

    """

    def __init__(self, cache_enabled: bool = True, cache_maxsize: int = 100) -> None:
        """Initialize the language detector.

        Args:
            cache_enabled: Whether to enable LRU caching (default: True).
            cache_maxsize: Maximum cache entries (default: 100).

        """
        self._cache_enabled = cache_enabled
        self._cache_maxsize = cache_maxsize
        self._cached_detect: Callable[..., LanguageInfo] | None = None

        # Create cached detect method if caching enabled
        if cache_enabled:
            self._cached_detect = lru_cache(maxsize=cache_maxsize)(self._detect_impl)

    def __repr__(self) -> str:
        """Return string representation."""
        cache_status = "enabled" if self._cache_enabled else "disabled"
        return f"LanguageDetector(cache={cache_status}, maxsize={self._cache_maxsize})"

    # ========================================================================
    # Public API
    # ========================================================================

    def detect(self, file_path: Path, content: str | None = None) -> LanguageInfo:
        r"""Detect language from file path and optional content.

        Detection order:
        1. File extension (primary method)
        2. Shebang line (if no extension match and content provided)
        3. Content heuristics (if shebang fails and content provided)
        4. Unknown (if all methods fail)

        Args:
            file_path: Path to the file (used for extension detection).
            content: Optional file content for shebang/heuristic detection.
                    If None and file exists, content will be read from file.

        Returns:
            LanguageInfo with detected language and metadata.

        Example:
            >>> detector = LanguageDetector()
            >>> info = detector.detect(Path("main.py"))
            >>> info.language
            'python'

            >>> info = detector.detect(Path("script"), "#!/bin/bash\necho hi")
            >>> info.is_unknown
            True  # bash is not supported

        """
        # Convert to Path if string
        path = Path(file_path) if isinstance(file_path, str) else file_path

        # Use cache if enabled
        if self._cache_enabled and self._cached_detect is not None:
            # Create cache key from path string and mtime (if file exists)
            try:
                mtime = path.stat().st_mtime if path.exists() else 0
            except OSError:
                mtime = 0
            cache_key = f"{path}:{mtime}"
            return self._cached_detect(cache_key, path, content)

        return self._detect_impl("", path, content)

    # ========================================================================
    # Detection Implementation
    # ========================================================================

    def _detect_impl(self, _cache_key: str, file_path: Path, content: str | None) -> LanguageInfo:
        """Internal detection implementation.

        Args:
            _cache_key: Cache key (unused, part of signature for cache).
            file_path: Path to the file.
            content: Optional file content.

        Returns:
            LanguageInfo with detection result.

        """
        # 1. Try extension detection (most reliable)
        result = self._detect_by_extension(file_path)
        if result is not None:
            return result

        # 2. Try shebang detection (need content)
        if content is None and file_path.exists():
            content = self._read_file_content(file_path)

        if content:
            result = self._detect_by_shebang(content)
            if result is not None:
                return result

            # 3. Try heuristic detection
            result = self._detect_by_heuristics(content)
            if result is not None:
                return result

        # 4. All methods failed
        return LanguageInfo.unknown()

    def _detect_by_extension(self, file_path: Path) -> LanguageInfo | None:
        """Detect language by file extension.

        Also checks for test file suffixes after extension match.

        Args:
            file_path: Path to analyze.

        Returns:
            LanguageInfo if detected, None otherwise.

        """
        name = file_path.name.lower()

        # First check exact extension match
        suffix = file_path.suffix.lower()
        if suffix in EXTENSION_MAP:
            language, file_type, confidence = EXTENSION_MAP[suffix]

            # Check for test file patterns
            for test_suffix, test_lang, test_type, test_conf in TEST_PATTERNS:
                if name.endswith(test_suffix) and test_lang == language:
                    # Only override if language matches
                    return LanguageInfo(
                            language=test_lang,
                            confidence=test_conf,
                            file_type=test_type,
                            detection_method="extension",
                        )

            return LanguageInfo(
                language=language,
                confidence=confidence,
                file_type=file_type,
                detection_method="extension",
            )

        # Check test patterns for files that might not have standard extension
        for test_suffix, test_lang, test_type, test_conf in TEST_PATTERNS:
            if name.endswith(test_suffix):
                return LanguageInfo(
                    language=test_lang,
                    confidence=test_conf,
                    file_type=test_type,
                    detection_method="extension",
                )

        return None

    def _detect_by_shebang(self, content: str) -> LanguageInfo | None:
        """Detect language by shebang line.

        Args:
            content: File content to analyze.

        Returns:
            LanguageInfo if detected, None if no match or unsupported.

        """
        # Get first line
        lines = content.splitlines()
        if not lines:
            return None

        first_line = lines[0].strip()

        # Check shebang patterns
        for pattern, language, confidence in SHEBANG_PATTERNS:
            if pattern.match(first_line):
                return LanguageInfo(
                    language=language,
                    confidence=confidence,
                    file_type="script",
                    detection_method="shebang",
                )

        return None

    def _detect_by_heuristics(self, content: str) -> LanguageInfo | None:
        """Detect language by content heuristics.

        Only scans the first 500 characters for performance.

        Args:
            content: File content to analyze.

        Returns:
            LanguageInfo if detected, None if no patterns match.

        """
        # Limit scan length for performance
        scan_content = content[:MAX_HEURISTIC_SCAN_LENGTH]

        # Check heuristic patterns in order
        for pattern, language, confidence in HEURISTIC_PATTERNS:
            if pattern.search(scan_content):
                return LanguageInfo(
                    language=language,
                    confidence=confidence,
                    file_type="source",
                    detection_method="heuristic",
                )

        return None

    # ========================================================================
    # File Reading
    # ========================================================================

    def _read_file_content(self, file_path: Path) -> str | None:
        """Read file content with safety checks.

        Handles:
        - Binary file detection (null bytes in first 1KB)
        - Size limits (max 1MB)
        - Encoding errors (uses errors="replace")
        - Permission errors

        Args:
            file_path: Path to read.

        Returns:
            File content as string, or None if cannot/should not read.

        """
        try:
            # Check if file exists and is a file
            if not file_path.exists() or not file_path.is_file():
                return None

            # Get file size
            try:
                size = file_path.stat().st_size
            except OSError:
                return None

            # Skip if too large
            if size > MAX_FILE_SIZE:
                logger.debug("File too large for content detection: %s", file_path)
                return None

            # Read binary first to check for null bytes
            with open(file_path, "rb") as f:
                header = f.read(BINARY_CHECK_BYTES)
                if b"\x00" in header:
                    logger.debug("Binary file detected, skipping: %s", file_path)
                    return None

            # Read as text
            with open(file_path, encoding="utf-8", errors="replace") as f:
                return f.read()

        except PermissionError:
            logger.warning("Permission denied reading file: %s", file_path)
            return None
        except OSError as e:
            logger.warning("Error reading file %s: %s", file_path, e)
            return None
        except (ValueError, UnicodeDecodeError) as e:
            logger.warning("Encoding/validation error reading file %s: %s", file_path, e)
            return None
