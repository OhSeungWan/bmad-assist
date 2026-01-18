"""Tests for experiments fixture discovery system.

Tests cover:
- FixtureEntry model validation
- discover_fixtures() directory scanning
- FixtureManager discovery and filtering
- Cost parsing utility
- Metadata loading from .bmad-assist.yaml
"""

import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from bmad_assist.core.exceptions import ConfigError
from bmad_assist.experiments.config import NAME_PATTERN
from bmad_assist.experiments.fixture import (
    COST_PATTERN,
    FixtureEntry,
    FixtureManager,
    FixtureRegistryManager,  # Deprecated alias
    discover_fixtures,
    parse_cost,
)


class TestFixtureEntry:
    """Tests for FixtureEntry Pydantic model."""

    def test_valid_minimal_entry(self, tmp_path: Path) -> None:
        """Test creating a minimal valid fixture entry."""
        entry = FixtureEntry(
            id="test-fixture",
            name="Test Fixture",
            path=tmp_path / "test-fixture",
        )
        assert entry.id == "test-fixture"
        assert entry.name == "Test Fixture"
        assert entry.description is None
        assert entry.path == tmp_path / "test-fixture"
        assert entry.tags == []
        assert entry.difficulty is None
        assert entry.estimated_cost is None

    def test_valid_full_entry(self, tmp_path: Path) -> None:
        """Test creating a full fixture entry with all fields."""
        entry = FixtureEntry(
            id="complex-fixture",
            name="Complex Fixture",
            description="A complex test fixture with detailed description",
            path=tmp_path / "complex",
            tags=["comprehensive", "slow", "integration"],
            difficulty="hard",
            estimated_cost="$5.00",
        )
        assert entry.id == "complex-fixture"
        assert entry.name == "Complex Fixture"
        assert entry.description == "A complex test fixture with detailed description"
        assert entry.tags == ["comprehensive", "slow", "integration"]
        assert entry.difficulty == "hard"
        assert entry.estimated_cost == "$5.00"

    def test_entry_is_frozen(self, tmp_path: Path) -> None:
        """Test that fixture entry is immutable."""
        entry = FixtureEntry(
            id="test",
            name="Test",
            path=tmp_path / "test",
        )
        with pytest.raises(ValidationError, match="frozen"):
            entry.id = "new-id"  # type: ignore[misc]

    # ID Validation Tests

    def test_empty_id_raises_error(self, tmp_path: Path) -> None:
        """Test that empty id raises ValueError."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            FixtureEntry(
                id="",
                name="Test",
                path=tmp_path / "test",
            )

    def test_whitespace_id_raises_error(self, tmp_path: Path) -> None:
        """Test that whitespace-only id raises ValueError."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            FixtureEntry(
                id="   ",
                name="Test",
                path=tmp_path / "test",
            )

    def test_id_with_spaces_raises_error(self, tmp_path: Path) -> None:
        """Test that id with spaces raises ValueError."""
        with pytest.raises(ValueError, match="Invalid id"):
            FixtureEntry(
                id="has spaces",
                name="Test",
                path=tmp_path / "test",
            )

    def test_id_with_special_chars_raises_error(self, tmp_path: Path) -> None:
        """Test that id with special characters raises ValueError."""
        with pytest.raises(ValueError, match="Invalid id"):
            FixtureEntry(
                id="has@special",
                name="Test",
                path=tmp_path / "test",
            )

    def test_id_starting_with_number_raises_error(self, tmp_path: Path) -> None:
        """Test that id starting with number raises ValueError."""
        with pytest.raises(ValueError, match="Invalid id"):
            FixtureEntry(
                id="123fixture",
                name="Test",
                path=tmp_path / "test",
            )

    def test_id_starting_with_hyphen_raises_error(self, tmp_path: Path) -> None:
        """Test that id starting with hyphen raises ValueError."""
        with pytest.raises(ValueError, match="Invalid id"):
            FixtureEntry(
                id="-fixture",
                name="Test",
                path=tmp_path / "test",
            )

    # Cost Validation Tests

    def test_valid_cost_formats(self, tmp_path: Path) -> None:
        """Test valid cost formats."""
        valid_costs = ["$0.00", "$0.10", "$1.00", "$10.50", "$99.99"]
        for cost in valid_costs:
            entry = FixtureEntry(
                id="test",
                name="Test",
                path=tmp_path / "test",
                estimated_cost=cost,
            )
            assert entry.estimated_cost == cost

    def test_cost_missing_dollar_sign_raises_error(self, tmp_path: Path) -> None:
        """Test that cost without dollar sign raises error."""
        with pytest.raises(ValueError, match="Invalid estimated_cost"):
            FixtureEntry(
                id="test",
                name="Test",
                path=tmp_path / "test",
                estimated_cost="0.10",
            )

    def test_cost_wrong_decimals_raises_error(self, tmp_path: Path) -> None:
        """Test that cost with wrong decimal places raises error."""
        invalid_costs = ["$0.1", "$0.100", "$0", "$10"]
        for cost in invalid_costs:
            with pytest.raises(ValueError, match="Invalid estimated_cost"):
                FixtureEntry(
                    id="test",
                    name="Test",
                    path=tmp_path / "test",
                    estimated_cost=cost,
                )

    def test_cost_invalid_format_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid cost format raises error."""
        invalid_costs = ["free", "$abc", "$$1.00", "$1.00$"]
        for cost in invalid_costs:
            with pytest.raises(ValueError, match="Invalid estimated_cost"):
                FixtureEntry(
                    id="test",
                    name="Test",
                    path=tmp_path / "test",
                    estimated_cost=cost,
                )

    # Difficulty Validation Tests

    def test_valid_difficulty_values(self, tmp_path: Path) -> None:
        """Test all valid difficulty values."""
        for difficulty in ["easy", "medium", "hard"]:
            entry = FixtureEntry(
                id="test",
                name="Test",
                path=tmp_path / "test",
                difficulty=difficulty,  # type: ignore[arg-type]
            )
            assert entry.difficulty == difficulty

    def test_invalid_difficulty_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid difficulty raises error."""
        with pytest.raises(ValidationError):
            FixtureEntry(
                id="test",
                name="Test",
                path=tmp_path / "test",
                difficulty="impossible",  # type: ignore[arg-type]
            )


class TestDiscoverFixtures:
    """Tests for discover_fixtures function."""

    @pytest.fixture
    def fixtures_dir(self, tmp_path: Path) -> Path:
        """Create temp directory for fixtures."""
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        return fixtures

    def test_discover_empty_directory(self, fixtures_dir: Path) -> None:
        """Test discovering fixtures in empty directory."""
        fixtures = discover_fixtures(fixtures_dir)
        assert fixtures == []

    def test_discover_single_fixture(self, fixtures_dir: Path) -> None:
        """Test discovering single fixture directory."""
        (fixtures_dir / "my-fixture").mkdir()
        fixtures = discover_fixtures(fixtures_dir)

        assert len(fixtures) == 1
        assert fixtures[0].id == "my-fixture"
        assert fixtures[0].name == "my-fixture"  # No metadata, same as id
        assert fixtures[0].path == (fixtures_dir / "my-fixture").resolve()

    def test_discover_multiple_fixtures(self, fixtures_dir: Path) -> None:
        """Test discovering multiple fixture directories."""
        (fixtures_dir / "fixture-a").mkdir()
        (fixtures_dir / "fixture-b").mkdir()
        (fixtures_dir / "fixture-c").mkdir()

        fixtures = discover_fixtures(fixtures_dir)

        assert len(fixtures) == 3
        ids = [f.id for f in fixtures]
        # Should be sorted alphabetically
        assert ids == ["fixture-a", "fixture-b", "fixture-c"]

    def test_discover_ignores_files(self, fixtures_dir: Path) -> None:
        """Test that files (including .tar) are ignored."""
        (fixtures_dir / "valid-fixture").mkdir()
        (fixtures_dir / "archive.tar").write_text("tar content")
        (fixtures_dir / "readme.md").write_text("readme")

        fixtures = discover_fixtures(fixtures_dir)

        assert len(fixtures) == 1
        assert fixtures[0].id == "valid-fixture"

    def test_discover_ignores_hidden_directories(self, fixtures_dir: Path) -> None:
        """Test that hidden directories are ignored."""
        (fixtures_dir / "visible-fixture").mkdir()
        (fixtures_dir / ".hidden-fixture").mkdir()

        fixtures = discover_fixtures(fixtures_dir)

        assert len(fixtures) == 1
        assert fixtures[0].id == "visible-fixture"

    def test_discover_ignores_invalid_names(
        self, fixtures_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that directories with invalid names are skipped with warning."""
        (fixtures_dir / "valid-fixture").mkdir()
        (fixtures_dir / "123-invalid").mkdir()  # Starts with number

        with caplog.at_level(logging.WARNING):
            fixtures = discover_fixtures(fixtures_dir)

        assert len(fixtures) == 1
        assert fixtures[0].id == "valid-fixture"
        assert "invalid fixture ID format" in caplog.text

    def test_discover_nonexistent_directory_raises_error(self, tmp_path: Path) -> None:
        """Test that nonexistent directory raises ConfigError."""
        with pytest.raises(ConfigError, match="not found"):
            discover_fixtures(tmp_path / "nonexistent")

    def test_discover_file_instead_of_directory_raises_error(self, tmp_path: Path) -> None:
        """Test that file path raises ConfigError."""
        file_path = tmp_path / "not-a-dir"
        file_path.write_text("content")

        with pytest.raises(ConfigError, match="not a directory"):
            discover_fixtures(file_path)


class TestDiscoverFixturesWithMetadata:
    """Tests for discover_fixtures with .bmad-assist.yaml metadata."""

    @pytest.fixture
    def fixtures_dir(self, tmp_path: Path) -> Path:
        """Create temp directory for fixtures."""
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        return fixtures

    def test_load_metadata_from_bmad_assist_yaml(self, fixtures_dir: Path) -> None:
        """Test loading metadata from .bmad-assist.yaml."""
        fixture_dir = fixtures_dir / "my-fixture"
        fixture_dir.mkdir()

        config_content = """\
fixture:
  name: "My Custom Name"
  description: "A detailed description"
  tags: [quick, baseline]
  difficulty: easy
  estimated_cost: "$0.50"
"""
        (fixture_dir / ".bmad-assist.yaml").write_text(config_content)

        fixtures = discover_fixtures(fixtures_dir)

        assert len(fixtures) == 1
        f = fixtures[0]
        assert f.id == "my-fixture"
        assert f.name == "My Custom Name"
        assert f.description == "A detailed description"
        assert f.tags == ["quick", "baseline"]
        assert f.difficulty == "easy"
        assert f.estimated_cost == "$0.50"

    def test_load_metadata_from_bmad_assist_yaml_without_dot(self, fixtures_dir: Path) -> None:
        """Test loading metadata from bmad-assist.yaml (without dot)."""
        fixture_dir = fixtures_dir / "other-fixture"
        fixture_dir.mkdir()

        config_content = """\
fixture:
  name: "Other Name"
  tags: [test]
"""
        (fixture_dir / "bmad-assist.yaml").write_text(config_content)

        fixtures = discover_fixtures(fixtures_dir)

        assert len(fixtures) == 1
        assert fixtures[0].name == "Other Name"
        assert fixtures[0].tags == ["test"]

    def test_dotted_config_takes_precedence(self, fixtures_dir: Path) -> None:
        """Test that .bmad-assist.yaml takes precedence over bmad-assist.yaml."""
        fixture_dir = fixtures_dir / "precedence-test"
        fixture_dir.mkdir()

        (fixture_dir / ".bmad-assist.yaml").write_text("fixture:\n  name: From Dotted\n")
        (fixture_dir / "bmad-assist.yaml").write_text("fixture:\n  name: From Non-Dotted\n")

        fixtures = discover_fixtures(fixtures_dir)

        assert fixtures[0].name == "From Dotted"

    def test_partial_metadata(self, fixtures_dir: Path) -> None:
        """Test partial metadata (only some fields)."""
        fixture_dir = fixtures_dir / "partial"
        fixture_dir.mkdir()

        config_content = """\
fixture:
  description: "Only description provided"
"""
        (fixture_dir / ".bmad-assist.yaml").write_text(config_content)

        fixtures = discover_fixtures(fixtures_dir)

        f = fixtures[0]
        assert f.id == "partial"
        assert f.name == "partial"  # Falls back to id
        assert f.description == "Only description provided"
        assert f.tags == []
        assert f.difficulty is None

    def test_no_fixture_section_uses_defaults(self, fixtures_dir: Path) -> None:
        """Test config without fixture section uses defaults."""
        fixture_dir = fixtures_dir / "no-section"
        fixture_dir.mkdir()

        config_content = """\
other:
  key: value
"""
        (fixture_dir / ".bmad-assist.yaml").write_text(config_content)

        fixtures = discover_fixtures(fixtures_dir)

        f = fixtures[0]
        assert f.id == "no-section"
        assert f.name == "no-section"
        assert f.description is None

    def test_invalid_yaml_continues_with_defaults(
        self, fixtures_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid YAML logs debug and uses defaults."""
        fixture_dir = fixtures_dir / "bad-yaml"
        fixture_dir.mkdir()

        (fixture_dir / ".bmad-assist.yaml").write_text("invalid: yaml: [")

        with caplog.at_level(logging.DEBUG):
            fixtures = discover_fixtures(fixtures_dir)

        assert len(fixtures) == 1
        assert fixtures[0].name == "bad-yaml"


class TestFixtureManager:
    """Tests for FixtureManager class."""

    @pytest.fixture
    def fixtures_dir(self, tmp_path: Path) -> Path:
        """Create temp directory with fixtures."""
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        return fixtures

    @pytest.fixture
    def populated_fixtures_dir(self, fixtures_dir: Path) -> Path:
        """Create fixtures with varying metadata."""
        # Minimal fixture
        minimal = fixtures_dir / "minimal"
        minimal.mkdir()
        (minimal / ".bmad-assist.yaml").write_text("""\
fixture:
  name: "Minimal Project"
  description: "Single epic, 3 stories"
  tags: [quick, baseline]
  difficulty: easy
  estimated_cost: "$0.10"
""")

        # Complex fixture
        complex_dir = fixtures_dir / "complex"
        complex_dir.mkdir()
        (complex_dir / ".bmad-assist.yaml").write_text("""\
fixture:
  name: "Complex Project"
  description: "Multiple epics with dependencies"
  tags: [comprehensive, slow]
  difficulty: hard
  estimated_cost: "$1.00"
""")

        # Edge cases fixture
        edge = fixtures_dir / "edge-cases"
        edge.mkdir()
        (edge / ".bmad-assist.yaml").write_text("""\
fixture:
  name: "Edge Cases"
  description: "Error handling scenarios"
  tags: [edge, validation]
  difficulty: medium
  estimated_cost: "$0.30"
""")

        return fixtures_dir

    def test_manager_discover_returns_fixtures(self, populated_fixtures_dir: Path) -> None:
        """Test discover() returns list of fixtures."""
        manager = FixtureManager(populated_fixtures_dir)
        fixtures = manager.discover()

        assert len(fixtures) == 3
        ids = [f.id for f in fixtures]
        assert "minimal" in ids
        assert "complex" in ids
        assert "edge-cases" in ids

    def test_manager_list_returns_sorted_ids(self, populated_fixtures_dir: Path) -> None:
        """Test list() returns sorted fixture IDs."""
        manager = FixtureManager(populated_fixtures_dir)
        ids = manager.list()

        assert ids == ["complex", "edge-cases", "minimal"]

    def test_manager_get_returns_entry(self, populated_fixtures_dir: Path) -> None:
        """Test get() returns correct fixture entry."""
        manager = FixtureManager(populated_fixtures_dir)

        entry = manager.get("minimal")
        assert entry.id == "minimal"
        assert entry.name == "Minimal Project"

    def test_manager_get_unknown_id_raises_error(self, populated_fixtures_dir: Path) -> None:
        """Test get() raises ConfigError for unknown ID."""
        manager = FixtureManager(populated_fixtures_dir)

        with pytest.raises(ConfigError, match="not found") as exc_info:
            manager.get("nonexistent")

        # Should list available fixtures
        assert "minimal" in str(exc_info.value)
        assert "complex" in str(exc_info.value)

    def test_manager_get_path_returns_absolute_path(self, populated_fixtures_dir: Path) -> None:
        """Test get_path() returns absolute path."""
        manager = FixtureManager(populated_fixtures_dir)

        path = manager.get_path("minimal")
        assert path.is_absolute()
        assert path == (populated_fixtures_dir / "minimal").resolve()

    def test_manager_filter_by_tags_single_tag(self, populated_fixtures_dir: Path) -> None:
        """Test filter_by_tags() with single tag."""
        manager = FixtureManager(populated_fixtures_dir)

        fixtures = manager.filter_by_tags(["quick"])
        assert len(fixtures) == 1
        assert fixtures[0].id == "minimal"

    def test_manager_filter_by_tags_multiple_tags(self, populated_fixtures_dir: Path) -> None:
        """Test filter_by_tags() with multiple tags (AND logic)."""
        manager = FixtureManager(populated_fixtures_dir)

        # minimal has [quick, baseline]
        fixtures = manager.filter_by_tags(["quick", "baseline"])
        assert len(fixtures) == 1
        assert fixtures[0].id == "minimal"

        # No fixture has both "quick" and "slow"
        fixtures = manager.filter_by_tags(["quick", "slow"])
        assert len(fixtures) == 0

    def test_manager_filter_by_tags_empty_list_returns_all(
        self, populated_fixtures_dir: Path
    ) -> None:
        """Test filter_by_tags() with empty list returns all fixtures."""
        manager = FixtureManager(populated_fixtures_dir)

        fixtures = manager.filter_by_tags([])
        assert len(fixtures) == 3

    def test_manager_filter_by_difficulty(self, populated_fixtures_dir: Path) -> None:
        """Test filter_by_difficulty() returns matching fixtures."""
        manager = FixtureManager(populated_fixtures_dir)

        easy = manager.filter_by_difficulty("easy")
        assert len(easy) == 1
        assert easy[0].id == "minimal"

        hard = manager.filter_by_difficulty("hard")
        assert len(hard) == 1
        assert hard[0].id == "complex"

        medium = manager.filter_by_difficulty("medium")
        assert len(medium) == 1
        assert medium[0].id == "edge-cases"

    def test_manager_has_fixtures_true(self, populated_fixtures_dir: Path) -> None:
        """Test has_fixtures() returns True when fixtures exist."""
        manager = FixtureManager(populated_fixtures_dir)
        assert manager.has_fixtures() is True

    def test_manager_has_fixtures_false(self, fixtures_dir: Path) -> None:
        """Test has_fixtures() returns False for empty directory."""
        manager = FixtureManager(fixtures_dir)
        assert manager.has_fixtures() is False

    def test_manager_refresh_clears_cache(self, fixtures_dir: Path) -> None:
        """Test refresh() clears cache and rediscovers."""
        manager = FixtureManager(fixtures_dir)

        # Initially empty
        assert manager.list() == []

        # Add a fixture
        (fixtures_dir / "new-fixture").mkdir()

        # Still cached as empty
        assert manager.list() == []

        # After refresh, should see new fixture
        manager.refresh()
        assert manager.list() == ["new-fixture"]

    def test_manager_caches_discovery(self, populated_fixtures_dir: Path) -> None:
        """Test manager caches discovered fixtures."""
        manager = FixtureManager(populated_fixtures_dir)

        # First discover
        fixtures1 = manager.discover()

        # Second discover should return same list
        fixtures2 = manager.discover()

        assert fixtures1 is fixtures2  # Same list object (cached)


class TestFixtureRegistryManagerAlias:
    """Test that FixtureRegistryManager is alias for FixtureManager."""

    def test_alias_is_same_class(self) -> None:
        """Test that FixtureRegistryManager is FixtureManager."""
        assert FixtureRegistryManager is FixtureManager


class TestParseCost:
    """Tests for parse_cost utility function."""

    def test_parse_cost_small_value(self) -> None:
        """Test parsing small cost value."""
        assert parse_cost("$0.10") == 0.10

    def test_parse_cost_one_dollar(self) -> None:
        """Test parsing one dollar."""
        assert parse_cost("$1.00") == 1.00

    def test_parse_cost_large_value(self) -> None:
        """Test parsing large cost value."""
        assert parse_cost("$99.99") == 99.99

    def test_parse_cost_zero(self) -> None:
        """Test parsing zero cost."""
        assert parse_cost("$0.00") == 0.00

    def test_parse_cost_invalid_format_raises_error(self) -> None:
        """Test parsing invalid cost format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cost format"):
            parse_cost("invalid")

    def test_parse_cost_missing_dollar_sign_raises_error(self) -> None:
        """Test parsing cost without dollar sign raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cost format"):
            parse_cost("0.10")


class TestCostPattern:
    """Tests for COST_PATTERN regex."""

    def test_valid_cost_patterns(self) -> None:
        """Test valid cost patterns match."""
        valid = ["$0.00", "$0.10", "$1.00", "$10.50", "$99.99"]
        for cost in valid:
            assert COST_PATTERN.match(cost), f"Expected '{cost}' to match"

    def test_invalid_cost_patterns(self) -> None:
        """Test invalid cost patterns don't match."""
        invalid = [
            "0.10",  # Missing $
            "$0.1",  # One decimal
            "$0.100",  # Three decimals
            "$0",  # No decimals
            "free",  # Text
            "$$1.00",  # Double $
            "$1.00$",  # Trailing $
            "-$1.00",  # Negative
        ]
        for cost in invalid:
            assert not COST_PATTERN.match(cost), f"Expected '{cost}' not to match"


class TestNamePattern:
    """Tests for name validation pattern (same as config/loop)."""

    def test_valid_names(self) -> None:
        """Test valid name patterns."""
        valid_names = [
            "minimal",
            "edge-cases",
            "complex_fixture",
            "_private",
            "Fixture123",
            "my_test_fixture",
        ]
        for name in valid_names:
            assert NAME_PATTERN.match(name), f"Expected '{name}' to be valid"

    def test_invalid_names(self) -> None:
        """Test invalid name patterns."""
        invalid_names = [
            "123-start",  # starts with number
            "-hyphen-start",  # starts with hyphen
            "has spaces",  # contains space
            "has.dots",  # contains dot
            "has@special",  # contains special char
            "",  # empty
        ]
        for name in invalid_names:
            assert not NAME_PATTERN.match(name), f"Expected '{name}' to be invalid"


class TestDefaultFixtures:
    """Tests for default fixtures in experiments/fixtures/.

    These tests verify that auto-discovery works with real fixtures
    when they are unpacked from tar archives.
    """

    @pytest.fixture
    def default_fixtures_dir(self) -> Path:
        """Path to default fixtures directory."""
        return Path("experiments/fixtures")

    def test_default_directory_exists(self, default_fixtures_dir: Path) -> None:
        """Test experiments/fixtures directory exists."""
        assert default_fixtures_dir.exists(), "fixtures directory should exist"
        assert default_fixtures_dir.is_dir(), "fixtures should be a directory"

    def test_manager_works_with_empty_or_tar_only(self, default_fixtures_dir: Path) -> None:
        """Test FixtureManager works even with no unpacked fixtures."""
        # This should not raise, even if only tars exist
        manager = FixtureManager(default_fixtures_dir)

        # list() should work (may be empty if only tars)
        ids = manager.list()
        assert isinstance(ids, list)

    def test_manager_discovers_unpacked_fixtures(self, default_fixtures_dir: Path) -> None:
        """Test FixtureManager discovers unpacked fixture directories."""
        manager = FixtureManager(default_fixtures_dir)
        fixtures = manager.discover()

        # If fixtures are unpacked, verify their structure
        for fixture in fixtures:
            assert fixture.path.is_dir()
            assert fixture.id  # Has valid ID
            assert fixture.name  # Has name (from metadata or id)
