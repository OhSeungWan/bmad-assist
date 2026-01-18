"""Fixture isolation engine for experiment framework.

This module provides fixture isolation for experiment runs, ensuring
reproducibility by creating deep copies of fixtures to isolated run directories.

Usage:
    from bmad_assist.experiments import FixtureIsolator, IsolationResult

    # Create isolator with runs directory
    isolator = FixtureIsolator(Path("experiments/runs"))

    # Isolate a fixture
    result = isolator.isolate(fixture_path, "run-2026-01-08-001")

    print(f"Isolated to: {result.snapshot_path}")
    print(f"Files: {result.file_count}, Size: {result.total_bytes / 1024 / 1024:.1f}MB")

"""

from __future__ import annotations

import logging
import os
import shutil
import stat
import time
from dataclasses import dataclass
from pathlib import Path

from bmad_assist.core.exceptions import ConfigError, IsolationError

logger = logging.getLogger(__name__)

# Patterns to skip during copy
SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "node_modules",
        ".pytest_cache",
    }
)

SKIP_EXTENSIONS: frozenset[str] = frozenset({".pyc", ".pyo"})

# Default timeout for isolation operation (5 minutes)
DEFAULT_TIMEOUT_SECONDS: int = 300

# Progress logging intervals
PROGRESS_FILES_INTERVAL: int = 100
PROGRESS_BYTES_INTERVAL: int = 10 * 1024 * 1024  # 10MB


@dataclass(frozen=True)
class IsolationResult:
    """Result of a fixture isolation operation.

    Attributes:
        source_path: Original fixture directory (absolute).
        snapshot_path: Destination snapshot directory (absolute).
        file_count: Number of files copied.
        total_bytes: Total size in bytes copied.
        duration_seconds: Time taken for copy operation.
        verified: Whether integrity verification passed.

    """

    source_path: Path
    snapshot_path: Path
    file_count: int
    total_bytes: int
    duration_seconds: float
    verified: bool

    def __repr__(self) -> str:
        """Human-readable summary."""
        size_mb = self.total_bytes / (1024 * 1024)
        return (
            f"IsolationResult(files={self.file_count}, "
            f"size={size_mb:.1f}MB, {self.duration_seconds:.1f}s, "
            f"verified={self.verified})"
        )


class FixtureIsolator:
    """Handles fixture isolation for experiment runs.

    Creates deep copies of fixture directories to ensure experiments
    are reproducible and source fixtures remain pristine.

    Usage:
        isolator = FixtureIsolator(Path("experiments/runs"))
        result = isolator.isolate(fixture_path, "run-2026-01-08-001")

    """

    def __init__(self, runs_dir: Path) -> None:
        """Initialize the isolator.

        Args:
            runs_dir: Base directory for experiment runs.

        """
        self._runs_dir = runs_dir

    def isolate(
        self,
        fixture_path: Path,
        run_id: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> IsolationResult:
        """Isolate a fixture by creating a deep copy.

        Args:
            fixture_path: Path to source fixture directory.
            run_id: Unique identifier for this experiment run.
            timeout_seconds: Maximum time allowed for copy operation.

        Returns:
            IsolationResult with copy details.

        Raises:
            ConfigError: If source doesn't exist, target already exists,
                or run_id contains invalid characters.
            IsolationError: If copy fails or verification fails.

        """
        # Validate run_id for path traversal attempts
        if "/" in run_id or "\\" in run_id or ".." in run_id:
            raise ConfigError(f"Invalid run_id '{run_id}': must not contain '/', '\\', or '..'")

        # Validate source
        source = fixture_path.resolve()
        if not source.exists():
            raise ConfigError(f"Fixture source does not exist: {source}")
        if not source.is_dir():
            raise ConfigError(f"Fixture source is not a directory: {source}")

        # Create target path
        snapshot = (self._runs_dir / run_id / "fixture-snapshot").resolve()
        if snapshot.exists():
            raise ConfigError(f"Snapshot directory already exists: {snapshot}")

        # Ensure parent exists
        snapshot.parent.mkdir(parents=True, exist_ok=True)

        start_time = time.monotonic()
        file_count = 0
        total_bytes = 0

        try:
            file_count, total_bytes = self._copy_directory(
                source, snapshot, timeout_seconds, start_time
            )

            duration = time.monotonic() - start_time

            # Verify copy
            verified, reason = self._verify_copy(source, snapshot)
            if not verified:
                raise IsolationError(
                    f"Verification failed: {reason}",
                    source_path=source,
                    snapshot_path=snapshot,
                )

            logger.info(
                "Isolated fixture %s to %s (%d files, %.1f MB, %.1fs)",
                source.name,
                snapshot,
                file_count,
                total_bytes / (1024 * 1024),
                duration,
            )

            return IsolationResult(
                source_path=source,
                snapshot_path=snapshot,
                file_count=file_count,
                total_bytes=total_bytes,
                duration_seconds=duration,
                verified=True,
            )

        except IsolationError:
            # Clean up and re-raise
            self._cleanup(snapshot)
            raise
        except Exception as e:
            # Clean up and wrap in IsolationError
            self._cleanup(snapshot)
            raise IsolationError(
                f"Copy failed: {e}",
                source_path=source,
                snapshot_path=snapshot,
            ) from e

    def _copy_directory(
        self,
        src: Path,
        dst: Path,
        timeout_seconds: int,
        start_time: float,
    ) -> tuple[int, int]:
        """Copy directory recursively with skip patterns.

        Returns:
            Tuple of (file_count, total_bytes).

        """
        file_count = 0
        total_bytes = 0
        last_progress_files = 0
        last_progress_bytes = 0

        # Create destination root
        os.makedirs(dst, exist_ok=False)

        # Walk source directory
        for root, dirs, files in os.walk(src, topdown=True):
            root_path = Path(root)
            rel_root = root_path.relative_to(src)

            # Prune skipped directories
            # Modify dirs in-place to prevent traversal
            dirs[:] = [
                d
                for d in dirs
                if d not in SKIP_DIRS
                and not any(part in SKIP_DIRS for part in (rel_root / d).parts)
            ]

            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed > timeout_seconds:
                raise IsolationError(
                    f"Timeout after {elapsed:.0f}s (limit: {timeout_seconds}s)",
                    source_path=src,
                    snapshot_path=dst,
                )

            # Process directories (to preserve empty ones)
            for d in dirs:
                src_path = root_path / d
                dst_path = dst / rel_root / d

                # Handle directory symlinks
                if src_path.is_symlink():
                    try:
                        target = src_path.resolve()
                        # Check if symlink points within source fixture
                        target.relative_to(src)
                        # Internal directory symlink - dereference by copying contents
                        # Use copytree to recursively copy the target directory contents
                        shutil.copytree(
                            target,
                            dst_path,
                            symlinks=False,  # Dereference any nested symlinks
                            ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc", "*.pyo"),
                            dirs_exist_ok=True,
                        )
                        # Count files in the dereferenced directory
                        for dereferenced_file in dst_path.rglob("*"):
                            if dereferenced_file.is_file():
                                file_count += 1
                                total_bytes += dereferenced_file.stat().st_size
                        logger.debug(
                            "Dereferenced internal directory symlink %s -> %s",
                            src_path,
                            target,
                        )
                    except (ValueError, OSError) as e:
                        logger.warning(
                            "Skipping directory symlink %s: %s",
                            src_path,
                            e,
                        )
                    continue

                dst_path.mkdir(parents=True, exist_ok=True)

            # Process files
            for f in files:
                src_path = root_path / f

                # Skip extensions
                if src_path.suffix in SKIP_EXTENSIONS:
                    logger.debug("Skipping (extension pattern): %s", src_path)
                    continue

                dst_path = dst / rel_root / f

                # Handle file symlinks
                if src_path.is_symlink():
                    try:
                        target = src_path.resolve()
                        target.relative_to(src)
                        # Internal file symlink - dereference
                        if target.is_file():
                            dst_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(target, dst_path)
                            file_count += 1
                            total_bytes += target.stat().st_size
                            logger.debug(
                                "Dereferenced internal symlink %s -> %s",
                                src_path,
                                target,
                            )
                    except ValueError:
                        # Symlink points outside fixture
                        logger.warning("Skipping symlink pointing outside fixture: %s", src_path)
                    except OSError as e:
                        # Broken symlink or other OS error
                        logger.warning("Skipping symlink %s: %s", src_path, e)
                    continue

                # Regular file
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)

                # Try to preserve permissions
                try:
                    src_stat = src_path.stat()
                    os.chmod(dst_path, stat.S_IMODE(src_stat.st_mode))
                except OSError as e:
                    logger.debug("Could not preserve permissions for %s: %s", dst_path, e)

                file_count += 1
                total_bytes += src_path.stat().st_size

                # Progress logging
                if (
                    file_count - last_progress_files >= PROGRESS_FILES_INTERVAL
                    or total_bytes - last_progress_bytes >= PROGRESS_BYTES_INTERVAL
                ):
                    logger.debug(
                        "Copy progress: %d files, %.1f MB",
                        file_count,
                        total_bytes / (1024 * 1024),
                    )
                    last_progress_files = file_count
                    last_progress_bytes = total_bytes

        # Check for empty fixture (only skipped patterns)
        if file_count == 0:
            raise IsolationError(
                "Fixture contains no copyable files after applying skip patterns",
                source_path=src,
                snapshot_path=dst,
            )

        return file_count, total_bytes

    def _verify_copy(self, src: Path, dst: Path) -> tuple[bool, str]:
        """Verify copy integrity.

        Returns:
            Tuple of (verified, reason).

        """
        # Count source files (excluding skipped patterns)
        # For source, count internal symlinks since they get dereferenced and copied
        src_files = self._count_files(src, is_source=True)
        dst_files = self._count_files(dst, is_source=False)

        if src_files != dst_files:
            return (
                False,
                f"File count mismatch: source={src_files}, snapshot={dst_files}",
            )

        # Calculate sizes
        # For source, include internal symlink target sizes since they get dereferenced
        src_size = self._calculate_size(src, is_source=True)
        dst_size = self._calculate_size(dst, is_source=False)

        if src_size != dst_size:
            return (
                False,
                f"Size mismatch: source={src_size}, snapshot={dst_size}",
            )

        # Check for symlinks in snapshot (should not exist)
        for f in dst.rglob("*"):
            if f.is_symlink():
                return (
                    False,
                    f"Symlink found in snapshot (should be dereferenced): {f}",
                )

        # Check critical paths
        docs_dst = dst / "docs"
        if not docs_dst.exists():
            logger.warning("Snapshot has no docs/ directory: %s", dst)
            # Not a failure, just a warning

        # Check for at least one .md or .yaml file
        has_content = any(
            f.suffix in {".md", ".yaml", ".yml"} for f in dst.rglob("*") if f.is_file()
        )
        if not has_content:
            return False, "No .md or .yaml files found in snapshot"

        return True, "OK"

    def _count_files(self, path: Path, is_source: bool = False) -> int:
        """Count files excluding skipped patterns.

        Args:
            path: Directory to count files in.
            is_source: If True, count internal symlinks as files (they get dereferenced).
                       If False, symlinks should not exist in snapshot.

        """
        count = 0
        for f in path.rglob("*"):
            # Handle symlinks differently for source vs snapshot
            if f.is_symlink():
                if is_source:
                    try:
                        target = f.resolve()
                        target.relative_to(path)  # Check if internal
                        if target.is_file():
                            # Internal file symlink - count it
                            count += 1
                        elif target.is_dir():
                            # Internal directory symlink - count files in dereferenced dir
                            for df in target.rglob("*"):
                                if df.is_file():
                                    rel_path = df.relative_to(target)
                                    parts = rel_path.parts
                                    if any(part in SKIP_DIRS for part in parts):
                                        continue
                                    if df.suffix in SKIP_EXTENSIONS:
                                        continue
                                    count += 1
                    except (ValueError, OSError):
                        # External or broken symlink - not counted
                        pass
                continue  # Don't count as regular file

            if f.is_file():
                rel_path = f.relative_to(path)
                parts = rel_path.parts
                if any(part in SKIP_DIRS for part in parts):
                    continue
                if f.suffix in SKIP_EXTENSIONS:
                    continue
                count += 1
        return count

    def _calculate_size(self, path: Path, is_source: bool = False) -> int:
        """Calculate total size excluding skipped patterns.

        Args:
            path: Directory to calculate size for.
            is_source: If True, include size of internal symlink targets.
                       If False, symlinks should not exist in snapshot.

        """
        total = 0
        for f in path.rglob("*"):
            # Handle symlinks differently for source vs snapshot
            if f.is_symlink():
                if is_source:
                    try:
                        target = f.resolve()
                        target.relative_to(path)  # Check if internal
                        if target.is_file():
                            # Internal file symlink - include target size
                            total += target.stat().st_size
                        elif target.is_dir():
                            # Internal directory symlink - include sizes of files in target
                            for df in target.rglob("*"):
                                if df.is_file():
                                    rel_path = df.relative_to(target)
                                    parts = rel_path.parts
                                    if any(part in SKIP_DIRS for part in parts):
                                        continue
                                    if df.suffix in SKIP_EXTENSIONS:
                                        continue
                                    total += df.stat().st_size
                    except (ValueError, OSError):
                        # External or broken symlink - not counted
                        pass
                continue  # Don't count as regular file

            if f.is_file():
                rel_path = f.relative_to(path)
                parts = rel_path.parts
                if any(part in SKIP_DIRS for part in parts):
                    continue
                if f.suffix in SKIP_EXTENSIONS:
                    continue
                total += f.stat().st_size
        return total

    def _cleanup(self, path: Path) -> None:
        """Clean up partial copy on failure."""
        if path.exists():
            logger.warning("Cleaning up partial snapshot: %s", path)
            try:
                shutil.rmtree(path)
            except OSError as e:
                logger.error("Failed to cleanup partial snapshot %s: %s", path, e)
