"""Tests for config singleton pattern and advanced model behaviors.

Story 1.2 tests (AC6 and edge cases):
- AC6: Config singleton pattern
- Frozen model tests (immutability)
- Path expansion tests
- Additional edge cases

Extracted from test_config.py as part of Story 1.8 (Test Suite Refactoring).
"""

import pytest
from pydantic import ValidationError

from bmad_assist.core.config import (
    BmadPathsConfig,
    Config,
    MasterProviderConfig,
    MultiProviderConfig,
    PowerPromptConfig,
    ProviderConfig,
    _reset_config,
    get_config,
    load_config,
)
from bmad_assist.core.exceptions import ConfigError

# === AC6: Config Singleton Pattern ===


class TestConfigSingletonPattern:
    """Tests for AC6: Config singleton pattern."""

    def test_get_config_before_load_raises_error(self) -> None:
        """get_config() before load_config() raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            get_config()
        assert "Config not loaded" in str(exc_info.value)

    def test_get_config_error_suggests_load_config(self) -> None:
        """get_config() error message suggests calling load_config()."""
        with pytest.raises(ConfigError) as exc_info:
            get_config()
        assert "load_config()" in str(exc_info.value)

    def test_load_config_enables_get_config(self) -> None:
        """After load_config(), get_config() returns config."""
        config_dict = {"providers": {"master": {"provider": "claude", "model": "opus_4"}}}
        loaded = load_config(config_dict)
        retrieved = get_config()
        assert loaded is retrieved

    def test_get_config_returns_same_instance(self) -> None:
        """Multiple get_config() calls return same instance."""
        config_dict = {"providers": {"master": {"provider": "claude", "model": "opus_4"}}}
        load_config(config_dict)
        first = get_config()
        second = get_config()
        third = get_config()
        assert first is second
        assert second is third

    def test_load_config_non_dict_raises_config_error(self) -> None:
        """load_config() with non-dict raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            load_config("not a dict")  # type: ignore[arg-type]
        assert "must be a dict" in str(exc_info.value)
        assert "str" in str(exc_info.value)

    def test_load_config_none_raises_config_error(self) -> None:
        """load_config() with None raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            load_config(None)  # type: ignore[arg-type]
        assert "must be a dict" in str(exc_info.value)
        assert "NoneType" in str(exc_info.value)

    def test_load_config_list_raises_config_error(self) -> None:
        """load_config() with list raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            load_config([1, 2, 3])  # type: ignore[arg-type]
        assert "must be a dict" in str(exc_info.value)
        assert "list" in str(exc_info.value)

    def test_load_config_invalid_dict_raises_config_error(self) -> None:
        """load_config() with invalid dict raises ConfigError (wrapping ValidationError)."""
        with pytest.raises(ConfigError) as exc_info:
            load_config({"invalid": "config"})
        assert "validation failed" in str(exc_info.value).lower()

    def test_load_config_returns_config_instance(self) -> None:
        """load_config() returns a Config instance."""
        config_dict = {"providers": {"master": {"provider": "claude", "model": "opus_4"}}}
        result = load_config(config_dict)
        assert isinstance(result, Config)

    def test_reset_config_allows_reload(self) -> None:
        """_reset_config() allows loading a new config."""
        config_dict_1 = {"providers": {"master": {"provider": "claude", "model": "opus_4"}}}
        config_dict_2 = {"providers": {"master": {"provider": "codex", "model": "o3"}}}
        load_config(config_dict_1)
        first = get_config()
        assert first.providers.master.provider == "claude"

        _reset_config()
        load_config(config_dict_2)
        second = get_config()
        assert second.providers.master.provider == "codex"
        assert first is not second


# === Additional Edge Cases ===


class TestEdgeCases:
    """Additional edge case tests for comprehensive coverage."""

    def test_power_prompts_with_variables(self) -> None:
        """PowerPromptConfig accepts custom variables."""
        config = PowerPromptConfig(
            set_name="python-cli",
            variables={"project_name": "my-project", "tech_stack": "python"},
        )
        assert config.set_name == "python-cli"
        assert config.variables["project_name"] == "my-project"
        assert config.variables["tech_stack"] == "python"

    def test_bmad_paths_with_values(self) -> None:
        """BmadPathsConfig accepts all path values."""
        config = BmadPathsConfig(
            prd="./docs/prd.md",
            architecture="./docs/architecture.md",
            epics="./docs/epics.md",
            stories="./docs/stories/",
        )
        assert config.prd == "./docs/prd.md"
        assert config.architecture == "./docs/architecture.md"
        assert config.epics == "./docs/epics.md"
        assert config.stories == "./docs/stories/"

    def test_full_config_with_all_values(self) -> None:
        """Full Config with all values set works correctly."""
        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(
                    provider="claude",
                    model="opus_4",
                    settings="./master.json",
                    model_name="glm-4.7",
                ),
                multi=[
                    MultiProviderConfig(provider="gemini", model="gemini_2_5_pro"),
                    MultiProviderConfig(provider="codex", model="o3", settings="./codex.json"),
                ],
            ),
            power_prompts=PowerPromptConfig(
                set_name="python-cli",
                variables={"key": "value"},
            ),
            state_path="/custom/state.yaml",
            bmad_paths=BmadPathsConfig(
                prd="./docs/prd.md",
                architecture="./docs/arch.md",
            ),
        )
        assert config.providers.master.provider == "claude"
        assert config.providers.master.display_model == "glm-4.7"
        assert len(config.providers.multi) == 2
        assert config.power_prompts.set_name == "python-cli"
        assert config.state_path == "/custom/state.yaml"
        assert config.bmad_paths.prd == "./docs/prd.md"

    def test_config_error_inherits_from_bmad_assist_error(self) -> None:
        """ConfigError inherits from BmadAssistError."""
        from bmad_assist.core.exceptions import BmadAssistError

        error = ConfigError("test error")
        assert isinstance(error, BmadAssistError)
        assert isinstance(error, Exception)

    def test_empty_multi_list_explicitly_set(self) -> None:
        """Explicitly setting multi=[] works."""
        config = ProviderConfig(
            master=MasterProviderConfig(provider="claude", model="opus_4"),
            multi=[],
        )
        assert config.multi == []

    def test_multi_provider_settings_optional(self) -> None:
        """MultiProviderConfig settings is optional."""
        config = MultiProviderConfig(provider="gemini", model="gemini_2_5_pro")
        assert config.settings is None
        assert config.model_name is None
        assert config.display_model == "gemini_2_5_pro"


# === Frozen Model Tests (Immutability) ===


class TestFrozenModels:
    """Tests for model immutability (frozen=True)."""

    def test_config_is_frozen(self) -> None:
        """Config model is frozen and cannot be mutated."""
        config = Config(
            providers=ProviderConfig(master=MasterProviderConfig(provider="claude", model="opus_4"))
        )
        with pytest.raises(ValidationError):
            config.state_path = "/tmp/evil.yaml"  # type: ignore[misc]

    def test_master_provider_config_is_frozen(self) -> None:
        """MasterProviderConfig is frozen and cannot be mutated."""
        config = MasterProviderConfig(provider="claude", model="opus_4")
        with pytest.raises(ValidationError):
            config.provider = "hacked"  # type: ignore[misc]

    def test_provider_config_is_frozen(self) -> None:
        """ProviderConfig is frozen and cannot be mutated."""
        config = ProviderConfig(master=MasterProviderConfig(provider="claude", model="opus_4"))
        with pytest.raises(ValidationError):
            config.multi = []  # type: ignore[misc]

    def test_power_prompt_config_is_frozen(self) -> None:
        """PowerPromptConfig is frozen and cannot be mutated."""
        config = PowerPromptConfig(set_name="test")
        with pytest.raises(ValidationError):
            config.set_name = "hacked"  # type: ignore[misc]

    def test_bmad_paths_config_is_frozen(self) -> None:
        """BmadPathsConfig is frozen and cannot be mutated."""
        config = BmadPathsConfig(prd="./docs/prd.md")
        with pytest.raises(ValidationError):
            config.prd = "/etc/passwd"  # type: ignore[misc]


# === Path Expansion Tests ===


class TestPathExpansion:
    """Tests for path expansion in config fields."""

    def test_state_path_tilde_is_expanded(self) -> None:
        """State path with ~ is expanded to absolute path."""
        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(provider="claude", model="opus_4")
            ),
            state_path="~/custom/state.yaml",
        )
        assert "~" not in config.state_path
        assert config.state_path.startswith("/")

    def test_state_path_without_tilde_unchanged(self) -> None:
        """State path without ~ is preserved as-is."""
        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(provider="claude", model="opus_4")
            ),
            state_path="relative/state.yaml",
        )
        assert config.state_path == "relative/state.yaml"

    def test_state_path_absolute_unchanged(self) -> None:
        """Absolute state path is preserved as-is."""
        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(provider="claude", model="opus_4")
            ),
            state_path="/absolute/path/state.yaml",
        )
        assert config.state_path == "/absolute/path/state.yaml"

    def test_load_config_expands_state_path(self) -> None:
        """load_config() expands ~ in state_path from dict."""
        config_dict = {
            "providers": {"master": {"provider": "claude", "model": "opus_4"}},
            "state_path": "~/.bmad-assist/state.yaml",
        }
        config = load_config(config_dict)
        assert "~" not in config.state_path
        assert config.state_path.startswith("/")
