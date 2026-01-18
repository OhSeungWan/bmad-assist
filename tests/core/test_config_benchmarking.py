"""Tests for benchmarking configuration options.

Story 13.4: Orchestrator Integration (AC7)
- benchmarking.enabled: bool = True (default: enabled)
- benchmarking.extraction_provider: str = "claude"
- benchmarking.extraction_model: str = "haiku"
- workflow_variant: str = "default"
"""

import pytest

from bmad_assist.core.config import (
    BenchmarkingConfig,
    Config,
    MasterProviderConfig,
    ProviderConfig,
)


class TestBenchmarkingConfigDefaults:
    """Test AC7: Default values for benchmarking config options."""

    def test_benchmarking_enabled_default_true(self) -> None:
        """Default benchmarking.enabled is True."""
        config = Config(
            providers=ProviderConfig(master=MasterProviderConfig(provider="claude", model="opus_4"))
        )
        assert config.benchmarking.enabled is True

    def test_benchmarking_extraction_defaults(self) -> None:
        """Default extraction provider/model are claude/haiku."""
        config = Config(
            providers=ProviderConfig(master=MasterProviderConfig(provider="claude", model="opus_4"))
        )
        assert config.benchmarking.extraction_provider == "claude"
        assert config.benchmarking.extraction_model == "haiku"

    def test_workflow_variant_default_value(self) -> None:
        """Default workflow_variant is 'default'."""
        config = Config(
            providers=ProviderConfig(master=MasterProviderConfig(provider="claude", model="opus_4"))
        )
        assert config.workflow_variant == "default"


class TestBenchmarkingConfigExplicitValues:
    """Test AC7: Explicit values for benchmarking config options."""

    def test_benchmarking_enabled_false(self) -> None:
        """benchmarking.enabled can be set to False."""
        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(provider="claude", model="opus_4")
            ),
            benchmarking=BenchmarkingConfig(enabled=False),
        )
        assert config.benchmarking.enabled is False

    def test_benchmarking_custom_extraction_settings(self) -> None:
        """Extraction provider/model can be customized."""
        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(provider="claude", model="opus_4")
            ),
            benchmarking=BenchmarkingConfig(
                extraction_provider="anthropic-sdk",
                extraction_model="claude-3-5-haiku-latest",
            ),
        )
        assert config.benchmarking.extraction_provider == "anthropic-sdk"
        assert config.benchmarking.extraction_model == "claude-3-5-haiku-latest"

    def test_workflow_variant_custom_value(self) -> None:
        """workflow_variant can be set to custom value."""
        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(provider="claude", model="opus_4")
            ),
            workflow_variant="experiment-a",
        )
        assert config.workflow_variant == "experiment-a"

    def test_workflow_variant_ab_testing_values(self) -> None:
        """workflow_variant supports A/B testing values."""
        for variant in ["baseline", "v2", "experiment-a", "experiment-b"]:
            config = Config(
                providers=ProviderConfig(
                    master=MasterProviderConfig(provider="claude", model="opus_4")
                ),
                workflow_variant=variant,
            )
            assert config.workflow_variant == variant


class TestBenchmarkingConfigFromDict:
    """Test backward compatibility - loading from dict with defaults."""

    def test_load_without_benchmarking_fields(self) -> None:
        """Config loads without benchmarking fields (backward compat)."""
        config = Config.model_validate(
            {"providers": {"master": {"provider": "claude", "model": "opus_4"}}}
        )
        # Defaults should be applied
        assert config.benchmarking.enabled is True
        assert config.benchmarking.extraction_provider == "claude"
        assert config.benchmarking.extraction_model == "haiku"
        assert config.workflow_variant == "default"

    def test_load_with_benchmarking_fields(self) -> None:
        """Config loads with benchmarking fields explicitly set."""
        config = Config.model_validate(
            {
                "providers": {"master": {"provider": "claude", "model": "opus_4"}},
                "benchmarking": {
                    "enabled": False,
                    "extraction_provider": "gemini",
                    "extraction_model": "flash",
                },
                "workflow_variant": "v2",
            }
        )
        assert config.benchmarking.enabled is False
        assert config.benchmarking.extraction_provider == "gemini"
        assert config.benchmarking.extraction_model == "flash"
        assert config.workflow_variant == "v2"

    def test_load_with_partial_benchmarking_fields(self) -> None:
        """Config loads with partial benchmarking fields - defaults fill in."""
        config = Config.model_validate(
            {
                "providers": {"master": {"provider": "claude", "model": "opus_4"}},
                "benchmarking": {
                    "enabled": False,
                },
            }
        )
        assert config.benchmarking.enabled is False
        # Other fields get defaults
        assert config.benchmarking.extraction_provider == "claude"
        assert config.benchmarking.extraction_model == "haiku"


class TestBenchmarkingConfigFieldTypes:
    """Test AC7: Type validation for benchmarking fields."""

    def test_benchmarking_enabled_type_coercion(self) -> None:
        """benchmarking.enabled coerces to bool."""
        config = Config.model_validate(
            {
                "providers": {"master": {"provider": "claude", "model": "opus_4"}},
                "benchmarking": {"enabled": False},
            }
        )
        assert config.benchmarking.enabled is False

    def test_workflow_variant_must_be_string(self) -> None:
        """workflow_variant must be a string."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Config.model_validate(
                {
                    "providers": {"master": {"provider": "claude", "model": "opus_4"}},
                    "workflow_variant": 123,  # Invalid type
                }
            )
