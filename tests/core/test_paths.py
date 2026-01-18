"""Tests for bmad_assist.core.paths module."""

import pytest
from pathlib import Path

from bmad_assist.core.paths import (
    ProjectPaths,
    get_paths,
    init_paths,
    _reset_paths,
)


@pytest.fixture(autouse=True)
def reset_paths_singleton():
    """Reset paths singleton before and after each test."""
    _reset_paths()
    yield
    _reset_paths()


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root directory."""
    return tmp_path / "my-project"


class TestProjectPaths:
    """Tests for ProjectPaths class."""

    def test_init_with_project_root(self, project_root: Path):
        """ProjectPaths initializes with project root."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.project_root == project_root.resolve()

    def test_init_resolves_project_root(self, tmp_path: Path):
        """ProjectPaths resolves relative paths to absolute."""
        # Create a relative-looking path
        project = tmp_path / "relative" / ".." / "actual"
        project.mkdir(parents=True)
        paths = ProjectPaths(project)
        # Should be resolved (no ..)
        assert ".." not in str(paths.project_root)

    def test_default_output_folder(self, project_root: Path):
        """Default output folder is {project-root}/_bmad-output."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.output_folder == project_root.resolve() / "_bmad-output"

    def test_default_planning_artifacts(self, project_root: Path):
        """Default planning artifacts path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        expected = project_root.resolve() / "_bmad-output" / "planning-artifacts"
        assert paths.planning_artifacts == expected

    def test_default_implementation_artifacts(self, project_root: Path):
        """Default implementation artifacts path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        expected = project_root.resolve() / "_bmad-output" / "implementation-artifacts"
        assert paths.implementation_artifacts == expected

    def test_default_project_knowledge(self, project_root: Path):
        """Default project knowledge path is docs/."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.project_knowledge == project_root.resolve() / "docs"

    def test_config_override_output_folder(self, project_root: Path):
        """Config can override output folder."""
        project_root.mkdir(parents=True)
        config = {"output_folder": "{project-root}/custom-output"}
        paths = ProjectPaths(project_root, config)
        assert paths.output_folder == project_root.resolve() / "custom-output"

    def test_config_override_planning_artifacts(self, project_root: Path):
        """Config can override planning artifacts path."""
        project_root.mkdir(parents=True)
        config = {"planning_artifacts": "{project-root}/planning"}
        paths = ProjectPaths(project_root, config)
        assert paths.planning_artifacts == project_root.resolve() / "planning"

    def test_config_override_implementation_artifacts(self, project_root: Path):
        """Config can override implementation artifacts path."""
        project_root.mkdir(parents=True)
        config = {"implementation_artifacts": "{project-root}/impl"}
        paths = ProjectPaths(project_root, config)
        assert paths.implementation_artifacts == project_root.resolve() / "impl"


class TestPlanningArtifactPaths:
    """Tests for planning artifact subdirectories."""

    def test_epics_dir(self, project_root: Path):
        """Epics directory under planning artifacts."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        expected = project_root.resolve() / "_bmad-output" / "planning-artifacts" / "epics"
        assert paths.epics_dir == expected

    def test_stories_dir_is_implementation_artifacts(self, project_root: Path):
        """Stories directory is implementation_artifacts (matching BMAD convention)."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        # Stories are stored directly in implementation-artifacts per BMAD workflows
        expected = project_root.resolve() / "_bmad-output" / "implementation-artifacts"
        assert paths.stories_dir == expected


class TestImplementationArtifactPaths:
    """Tests for implementation artifact subdirectories."""

    def test_sprint_status_file(self, project_root: Path):
        """Sprint status file under implementation artifacts."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        expected = (
            project_root.resolve()
            / "_bmad-output"
            / "implementation-artifacts"
            / "sprint-status.yaml"
        )
        assert paths.sprint_status_file == expected

    def test_validations_dir(self, project_root: Path):
        """Validations directory under implementation artifacts."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        expected = (
            project_root.resolve()
            / "_bmad-output"
            / "implementation-artifacts"
            / "story-validations"
        )
        assert paths.validations_dir == expected

    def test_code_reviews_dir(self, project_root: Path):
        """Code reviews directory under implementation artifacts."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        expected = (
            project_root.resolve() / "_bmad-output" / "implementation-artifacts" / "code-reviews"
        )
        assert paths.code_reviews_dir == expected

    def test_benchmarks_dir(self, project_root: Path):
        """Benchmarks directory under implementation artifacts."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        expected = (
            project_root.resolve() / "_bmad-output" / "implementation-artifacts" / "benchmarks"
        )
        assert paths.benchmarks_dir == expected

    def test_retrospectives_dir(self, project_root: Path):
        """Retrospectives directory under implementation artifacts."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        expected = (
            project_root.resolve() / "_bmad-output" / "implementation-artifacts" / "retrospectives"
        )
        assert paths.retrospectives_dir == expected


class TestProjectKnowledgePaths:
    """Tests for project knowledge paths."""

    def test_prd_file(self, project_root: Path):
        """PRD file path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.prd_file == project_root.resolve() / "docs" / "prd.md"

    def test_architecture_file(self, project_root: Path):
        """Architecture file path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.architecture_file == project_root.resolve() / "docs" / "architecture.md"

    def test_project_context_file(self, project_root: Path):
        """Project context file path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.project_context_file == project_root.resolve() / "docs" / "project_context.md"


class TestInternalStatePaths:
    """Tests for internal tool state paths."""

    def test_bmad_assist_dir(self, project_root: Path):
        """Internal .bmad-assist directory."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.bmad_assist_dir == project_root.resolve() / ".bmad-assist"

    def test_state_file(self, project_root: Path):
        """State file path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.state_file == project_root.resolve() / ".bmad-assist" / "state.yaml"

    def test_patches_dir(self, project_root: Path):
        """Patches directory path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.patches_dir == project_root.resolve() / ".bmad-assist" / "patches"

    def test_cache_dir(self, project_root: Path):
        """Cache directory path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        assert paths.cache_dir == project_root.resolve() / ".bmad-assist" / "cache"


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_benchmark_month_dir(self, project_root: Path):
        """Benchmark month directory path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        result = paths.get_benchmark_month_dir(2025, 12)
        expected = paths.benchmarks_dir / "2025-12"
        assert result == expected

    def test_get_benchmark_month_dir_pads_month(self, project_root: Path):
        """Benchmark month is zero-padded."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        result = paths.get_benchmark_month_dir(2025, 1)
        assert result.name == "2025-01"

    def test_get_story_file(self, project_root: Path):
        """Story file path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        result = paths.get_story_file(14, 3)
        expected = paths.stories_dir / "14-3.md"
        assert result == expected

    def test_get_validation_file(self, project_root: Path):
        """Validation file path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        result = paths.get_validation_file(14, 3, "validator-a")
        expected = paths.validations_dir / "validation-14-3-validator-a.md"
        assert result == expected

    def test_get_code_review_file(self, project_root: Path):
        """Code review file path."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        result = paths.get_code_review_file(14, 3, "master")
        expected = paths.code_reviews_dir / "code-review-14-3-master.md"
        assert result == expected

    def test_ensure_directories_creates_all(self, project_root: Path):
        """ensure_directories creates all output directories."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        paths.ensure_directories()

        assert paths.output_folder.exists()
        assert paths.planning_artifacts.exists()
        assert paths.implementation_artifacts.exists()
        assert paths.epics_dir.exists()
        assert paths.stories_dir.exists()
        assert paths.validations_dir.exists()
        assert paths.code_reviews_dir.exists()
        assert paths.benchmarks_dir.exists()
        assert paths.retrospectives_dir.exists()
        assert paths.bmad_assist_dir.exists()
        assert paths.patches_dir.exists()
        assert paths.cache_dir.exists()

    def test_ensure_directories_idempotent(self, project_root: Path):
        """ensure_directories can be called multiple times."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        paths.ensure_directories()
        paths.ensure_directories()  # Should not raise
        assert paths.output_folder.exists()


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_paths_without_init_raises(self):
        """get_paths raises RuntimeError if not initialized."""
        with pytest.raises(RuntimeError, match="Paths not initialized"):
            get_paths()

    def test_init_paths_returns_instance(self, project_root: Path):
        """init_paths returns ProjectPaths instance."""
        project_root.mkdir(parents=True)
        paths = init_paths(project_root)
        assert isinstance(paths, ProjectPaths)

    def test_get_paths_after_init(self, project_root: Path):
        """get_paths returns initialized instance."""
        project_root.mkdir(parents=True)
        init_paths(project_root)
        paths = get_paths()
        assert isinstance(paths, ProjectPaths)
        assert paths.project_root == project_root.resolve()

    def test_init_paths_with_config(self, project_root: Path):
        """init_paths accepts config dictionary."""
        project_root.mkdir(parents=True)
        config = {"output_folder": "{project-root}/custom"}
        init_paths(project_root, config)
        paths = get_paths()
        assert paths.output_folder == project_root.resolve() / "custom"

    def test_init_paths_replaces_singleton(self, project_root: Path, tmp_path: Path):
        """Calling init_paths again replaces singleton."""
        project_root.mkdir(parents=True)
        other_root = tmp_path / "other"
        other_root.mkdir(parents=True)

        init_paths(project_root)
        init_paths(other_root)

        paths = get_paths()
        assert paths.project_root == other_root.resolve()

    def test_reset_paths_clears_singleton(self, project_root: Path):
        """_reset_paths clears the singleton."""
        project_root.mkdir(parents=True)
        init_paths(project_root)
        _reset_paths()
        with pytest.raises(RuntimeError, match="Paths not initialized"):
            get_paths()


class TestRepr:
    """Tests for __repr__."""

    def test_repr(self, project_root: Path):
        """__repr__ includes project_root."""
        project_root.mkdir(parents=True)
        paths = ProjectPaths(project_root)
        result = repr(paths)
        assert "ProjectPaths" in result
        assert str(project_root.resolve()) in result
