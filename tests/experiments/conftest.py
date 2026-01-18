"""Pytest fixtures for experiments module tests.

Provides fixtures for creating temporary config/loop template files and directories.
"""

from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def configs_dir(tmp_path: Path) -> Path:
    """Create temp directory for config templates."""
    configs = tmp_path / "configs"
    configs.mkdir()
    return configs


@pytest.fixture
def loops_dir(tmp_path: Path) -> Path:
    """Create temp directory for loop templates."""
    loops = tmp_path / "loops"
    loops.mkdir()
    return loops


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create temp directory as project root."""
    project = tmp_path / "project"
    project.mkdir()
    return project


@pytest.fixture
def write_config(configs_dir: Path) -> Callable[[str, str], Path]:
    """Factory to write config template files.

    Args:
        configs_dir: Directory for config files.

    Returns:
        Function that writes content to a named file and returns the path.

    """

    def _write(content: str, filename: str = "test-config.yaml") -> Path:
        path = configs_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def write_loop(loops_dir: Path) -> Callable[[str, str], Path]:
    """Factory to write loop template files.

    Args:
        loops_dir: Directory for loop files.

    Returns:
        Function that writes content to a named file and returns the path.

    """

    def _write(content: str, filename: str = "test-loop.yaml") -> Path:
        path = loops_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def valid_minimal_config() -> str:
    """Minimal valid config template YAML."""
    return """\
name: test-config
description: "Test configuration"

providers:
  master:
    provider: claude
    model: opus
  multi: []
"""


@pytest.fixture
def valid_full_config() -> str:
    """Full config template with all fields."""
    return """\
name: full-config
description: "Full configuration with multi validators"

providers:
  master:
    provider: claude
    model: opus
  multi:
    - provider: claude
      model: sonnet
    - provider: gemini
      model: gemini-2.5-flash
"""


@pytest.fixture
def config_with_project_var() -> str:
    """Config template using ${project} variable."""
    return """\
name: project-var-config
description: "Config using project variable"

providers:
  master:
    provider: claude
    model: opus
    settings: ${project}/.bmad-assist/settings.json
  multi: []
"""


@pytest.fixture
def config_with_home_var() -> str:
    """Config template using ${home} variable."""
    return """\
name: home-var-config
description: "Config using home variable"

providers:
  master:
    provider: claude
    model: opus
    settings: ${home}/.bmad-assist/settings.json
  multi: []
"""


@pytest.fixture
def valid_minimal_loop() -> str:
    """Minimal valid loop template YAML."""
    return """\
name: test-loop
description: "Test loop configuration"

sequence:
  - workflow: create-story
    required: true
  - workflow: dev-story
    required: true
"""


@pytest.fixture
def valid_full_loop() -> str:
    """Full loop template with all phases."""
    return """\
name: full-loop
description: "Full development loop with all phases"

sequence:
  - workflow: create-story
    required: true
  - workflow: validate-story
    required: true
  - workflow: validate-story-synthesis
    required: true
  - workflow: dev-story
    required: true
  - workflow: code-review
    required: true
  - workflow: code-review-synthesis
    required: true
"""


@pytest.fixture
def loop_with_optional_steps() -> str:
    """Loop template with optional (required=false) steps."""
    return """\
name: optional-loop
description: "Loop with optional steps"

sequence:
  - workflow: create-story
    required: true
  - workflow: validate-story
    required: false
  - workflow: dev-story
    required: true
"""


# Patch-set fixtures


@pytest.fixture
def patchsets_dir(tmp_path: Path) -> Path:
    """Create temp directory for patch-set manifests."""
    patchsets = tmp_path / "patch-sets"
    patchsets.mkdir()
    return patchsets


@pytest.fixture
def write_patchset(patchsets_dir: Path) -> Callable[[str, str], Path]:
    """Factory to write patch-set manifest files.

    Args:
        patchsets_dir: Directory for patch-set files.

    Returns:
        Function that writes content to a named file and returns the path.

    """

    def _write(content: str, filename: str = "test-patchset.yaml") -> Path:
        path = patchsets_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def valid_minimal_patchset() -> str:
    """Minimal valid patch-set manifest YAML."""
    return """\
name: test-patchset
description: "Test patch-set configuration"

patches: {}
"""


@pytest.fixture
def patchset_with_patches(tmp_path: Path) -> tuple[str, Path]:
    """Patch-set with actual patch files created."""
    # Create mock patch files
    patches_dir = tmp_path / "patches"
    patches_dir.mkdir()
    (patches_dir / "create-story.patch.yaml").write_text("# mock patch")
    (patches_dir / "dev-story.patch.yaml").write_text("# mock patch")

    content = f"""\
name: with-patches
description: "Patch-set with patch files"

patches:
  create-story: {patches_dir}/create-story.patch.yaml
  dev-story: {patches_dir}/dev-story.patch.yaml
"""
    return content, patches_dir


@pytest.fixture
def patchset_with_null_patches() -> str:
    """Patch-set with null (no patch) values."""
    return """\
name: null-patches
description: "Patch-set with null values"

patches:
  create-story: null
  dev-story: /path/to/patch.yaml
"""


@pytest.fixture
def patchset_with_workflow_overrides(tmp_path: Path) -> tuple[str, Path]:
    """Patch-set with workflow overrides."""
    # Create mock override directory
    override_dir = tmp_path / "overrides" / "create-story"
    override_dir.mkdir(parents=True)

    content = f"""\
name: with-overrides
description: "Patch-set with workflow overrides"

patches: {{}}
workflow_overrides:
  create-story: {override_dir}
"""
    return content, tmp_path


@pytest.fixture
def patchset_with_conflict(tmp_path: Path) -> tuple[str, Path]:
    """Patch-set with same workflow in both patches and workflow_overrides."""
    patches_dir = tmp_path / "patches"
    patches_dir.mkdir()
    (patches_dir / "create-story.patch.yaml").write_text("# mock patch")

    override_dir = tmp_path / "overrides" / "create-story"
    override_dir.mkdir(parents=True)

    content = f"""\
name: conflict-test
description: "Tests conflict warning"

workflow_overrides:
  create-story: {override_dir}

patches:
  create-story: {patches_dir}/create-story.patch.yaml
"""
    return content, tmp_path


# Fixture registry fixtures


@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    """Create temp directory for fixture registry."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    return fixtures


@pytest.fixture
def write_fixture_registry(fixtures_dir: Path) -> Callable[[str, str], Path]:
    """Factory to write fixture registry files.

    Args:
        fixtures_dir: Directory for fixture registry.

    Returns:
        Function that writes content to a named file and returns the path.

    """

    def _write(content: str, filename: str = "registry.yaml") -> Path:
        path = fixtures_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def valid_minimal_fixture_registry() -> str:
    """Minimal valid fixture registry YAML."""
    return """\
fixtures:
  - id: test-fixture
    name: "Test Fixture"
    description: "A test fixture for unit tests"
    path: ./test-fixture
    tags: [test]
    difficulty: easy
    estimated_cost: "$0.10"
"""


@pytest.fixture
def valid_full_fixture_registry() -> str:
    """Full fixture registry with multiple entries."""
    return """\
fixtures:
  - id: minimal
    name: "Minimal Project"
    description: "Single epic, 3 stories"
    path: ./minimal
    tags: [quick, baseline]
    difficulty: easy
    estimated_cost: "$0.10"

  - id: complex
    name: "Complex Project"
    description: "Multiple epics with dependencies"
    path: ./complex
    tags: [comprehensive, slow]
    difficulty: hard
    estimated_cost: "$1.00"

  - id: edge-cases
    name: "Edge Cases"
    description: "Error handling scenarios"
    path: ./edge-cases
    tags: [edge, validation]
    difficulty: medium
    estimated_cost: "$0.30"
"""


@pytest.fixture
def fixture_with_dirs(fixtures_dir: Path) -> tuple[str, Path]:
    """Registry with actual fixture directories created."""
    (fixtures_dir / "minimal" / "docs").mkdir(parents=True)
    (fixtures_dir / "minimal" / "docs" / "prd.md").write_text("# Minimal PRD")

    (fixtures_dir / "complex" / "docs").mkdir(parents=True)
    (fixtures_dir / "complex" / "docs" / "prd.md").write_text("# Complex PRD")

    content = """\
fixtures:
  - id: minimal
    name: "Minimal Project"
    path: ./minimal
    tags: [quick]
    difficulty: easy
    estimated_cost: "$0.10"

  - id: complex
    name: "Complex Project"
    path: ./complex
    tags: [slow]
    difficulty: hard
    estimated_cost: "$1.00"
"""
    return content, fixtures_dir


# Fixture isolation fixtures


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create temp directory for experiment runs."""
    runs = tmp_path / "runs"
    runs.mkdir()
    return runs


@pytest.fixture
def minimal_fixture(tmp_path: Path) -> Path:
    """Create minimal fixture for testing."""
    fixture = tmp_path / "fixtures" / "minimal"
    docs = fixture / "docs"
    docs.mkdir(parents=True)
    (docs / "prd.md").write_text("# Minimal PRD\n\nTest content.")
    (docs / "architecture.md").write_text("# Architecture\n\nTest content.")
    return fixture


@pytest.fixture
def fixture_with_git(minimal_fixture: Path) -> Path:
    """Fixture with .git directory (should be skipped)."""
    git_dir = minimal_fixture / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\nrepositoryformatversion = 0")
    objects_dir = git_dir / "objects"
    objects_dir.mkdir()
    (objects_dir / "pack").mkdir()
    return minimal_fixture


@pytest.fixture
def fixture_with_pycache(minimal_fixture: Path) -> Path:
    """Fixture with __pycache__ (should be skipped)."""
    src = minimal_fixture / "src"
    src.mkdir()
    pycache = src / "__pycache__"
    pycache.mkdir()
    (pycache / "module.cpython-311.pyc").write_bytes(b"compiled bytecode")
    (src / "module.py").write_text("# Python module\nprint('hello')")
    return minimal_fixture


@pytest.fixture
def fixture_with_venv(minimal_fixture: Path) -> Path:
    """Fixture with .venv directory (should be skipped)."""
    venv_dir = minimal_fixture / ".venv"
    venv_dir.mkdir()
    lib_dir = venv_dir / "lib" / "python3.11" / "site-packages"
    lib_dir.mkdir(parents=True)
    (lib_dir / "some_package.py").write_text("# Package code")
    return minimal_fixture


@pytest.fixture
def fixture_with_node_modules(minimal_fixture: Path) -> Path:
    """Fixture with node_modules directory (should be skipped)."""
    node_dir = minimal_fixture / "node_modules"
    node_dir.mkdir()
    pkg_dir = node_dir / "some-package"
    pkg_dir.mkdir()
    (pkg_dir / "index.js").write_text("module.exports = {}")
    return minimal_fixture


@pytest.fixture
def fixture_with_pytest_cache(minimal_fixture: Path) -> Path:
    """Fixture with .pytest_cache directory (should be skipped)."""
    cache_dir = minimal_fixture / ".pytest_cache"
    cache_dir.mkdir()
    (cache_dir / "README.md").write_text("pytest cache")
    v_dir = cache_dir / "v" / "cache"
    v_dir.mkdir(parents=True)
    (v_dir / "lastfailed").write_text("{}")
    return minimal_fixture


@pytest.fixture
def fixture_with_dotfiles(minimal_fixture: Path) -> Path:
    """Fixture with dotfiles that SHOULD be copied."""
    (minimal_fixture / ".gitignore").write_text("*.pyc\n__pycache__/")
    (minimal_fixture / ".env.example").write_text("API_KEY=your_key_here")
    (minimal_fixture / ".editorconfig").write_text("[*]\nindent_style = space")
    return minimal_fixture


@pytest.fixture
def fixture_with_empty_dirs(minimal_fixture: Path) -> Path:
    """Fixture with empty directories that should be preserved."""
    (minimal_fixture / "src").mkdir()
    (minimal_fixture / "tests").mkdir()
    (minimal_fixture / "tests" / "unit").mkdir()
    return minimal_fixture


@pytest.fixture
def fixture_with_symlinks(minimal_fixture: Path, tmp_path: Path) -> Path:
    """Fixture with various symlink scenarios."""
    # Internal symlink (should be dereferenced and copied)
    internal_link = minimal_fixture / "docs" / "link_to_prd.md"
    internal_link.symlink_to(minimal_fixture / "docs" / "prd.md")

    # External symlink (should be skipped with warning)
    external_target = tmp_path / "external_file.txt"
    external_target.write_text("External content")
    external_link = minimal_fixture / "external_link.txt"
    external_link.symlink_to(external_target)

    # Broken symlink (should be skipped with warning)
    broken_link = minimal_fixture / "broken_link.txt"
    broken_link.symlink_to(minimal_fixture / "nonexistent.txt")

    return minimal_fixture


@pytest.fixture
def fixture_with_dir_symlink(minimal_fixture: Path) -> Path:
    """Fixture with directory symlink that should be dereferenced."""
    # Create a source directory with content
    src_dir = minimal_fixture / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("# Main module\nprint('hello')")
    (src_dir / "utils.py").write_text("# Utils module\ndef helper(): pass")

    # Create internal directory symlink pointing to src
    link_dir = minimal_fixture / "linked_src"
    link_dir.symlink_to(src_dir)

    return minimal_fixture


@pytest.fixture
def large_fixture(tmp_path: Path) -> Path:
    """Create large fixture for stress testing."""
    fixture = tmp_path / "fixtures" / "large"
    docs = fixture / "docs"
    docs.mkdir(parents=True)
    (docs / "prd.md").write_text("# Large PRD\n\nContent.")

    # Create 1000+ files across directories
    for i in range(1100):
        subdir = fixture / f"dir_{i // 100}"
        subdir.mkdir(exist_ok=True)
        (subdir / f"file_{i}.md").write_text(f"# File {i}\n\nContent.\n" * 50)
    return fixture


@pytest.fixture
def fixture_only_skipped(tmp_path: Path) -> Path:
    """Fixture with only files that would be skipped (no copyable content)."""
    fixture = tmp_path / "fixtures" / "only_skipped"
    fixture.mkdir(parents=True)

    # Only .git and __pycache__
    git_dir = fixture / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]")

    pycache = fixture / "__pycache__"
    pycache.mkdir()
    (pycache / "module.pyc").write_bytes(b"bytecode")

    return fixture
