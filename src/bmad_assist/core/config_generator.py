"""Configuration generator with interactive questionnaire.

This module provides interactive config generation via Rich prompts.
When bmad-assist runs without a config file, this wizard guides users
through creating a valid bmad-assist.yaml.

Usage:
    from bmad_assist.core.config_generator import run_config_wizard

    # Run wizard and get path to generated config
    config_path = run_config_wizard(project_path)
"""

import contextlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Final

import yaml
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

logger = logging.getLogger(__name__)

# Default config filename (same as PROJECT_CONFIG_NAME in config.py)
CONFIG_FILENAME: Final[str] = "bmad-assist.yaml"

# Provider and model definitions
AVAILABLE_PROVIDERS: Final[dict[str, dict[str, Any]]] = {
    "claude": {
        "display_name": "Claude (Anthropic)",
        "models": {
            "opus_4": "Claude Opus 4 (Most capable)",
            "sonnet_4": "Claude Sonnet 4 (Fast, capable)",
            "sonnet_3_5": "Claude Sonnet 3.5 (Balanced)",
            "haiku_3_5": "Claude Haiku 3.5 (Fast, economical)",
        },
        "default_model": "opus_4",
    },
    "codex": {
        "display_name": "Codex (OpenAI)",
        "models": {
            "gpt-4o": "GPT-4o (Multimodal)",
            "o3": "o3 (Advanced reasoning)",
        },
        "default_model": "gpt-4o",
    },
    "gemini": {
        "display_name": "Gemini (Google)",
        "models": {
            "gemini_2_5_pro": "Gemini 2.5 Pro",
            "gemini_2_5_flash": "Gemini 2.5 Flash (Fast)",
        },
        "default_model": "gemini_2_5_pro",
    },
}


class ConfigGenerator:
    """Interactive configuration generator using Rich prompts.

    This class provides an interactive wizard for generating bmad-assist
    configuration files. It prompts users for provider and model selection,
    displays a summary, and saves the config with atomic write semantics.

    Attributes:
        console: Rich console for output.

    Example:
        >>> generator = ConfigGenerator()
        >>> config_path = generator.run(Path("./my-project"))
        >>> print(f"Config saved to {config_path}")

    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize ConfigGenerator.

        Args:
            console: Optional Rich console for output. Creates new if None.

        """
        self.console = console or Console()

    def run(self, project_path: Path) -> Path:
        """Run the configuration wizard.

        Guides user through provider/model selection, displays summary,
        confirms save, and writes the config file atomically.

        Args:
            project_path: Path to project directory where config will be saved.

        Returns:
            Path to the generated config file.

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C.
            EOFError: If running in non-interactive environment (piped input).
            OSError: If config file cannot be written.
            SystemExit: If user rejects save confirmation (exit code 1).

        """
        self._display_welcome()

        # Prompt for provider and model
        provider = self._prompt_provider()
        model = self._prompt_model(provider)

        # Build config dictionary
        config = self._build_config(provider, model)

        # Display summary and confirm
        self._display_summary(config)

        if not self._confirm_save():
            self.console.print("[yellow]Setup cancelled - no configuration saved[/yellow]")
            raise SystemExit(1)

        # Save config with atomic write
        config_path = self._save_config(project_path, config)

        self.console.print(f"[green]✓[/green] Configuration saved to {config_path}")
        logger.info("Generated config at %s", config_path)

        return config_path

    def _display_welcome(self) -> None:
        """Display welcome message with Rich formatting."""
        self.console.print()
        self.console.print("[bold blue]bmad-assist Setup Wizard[/bold blue]")
        self.console.print("[dim]─────────────────────────[/dim]")
        self.console.print()
        self.console.print(
            "This wizard will create a [cyan]bmad-assist.yaml[/cyan] configuration file."
        )
        self.console.print()

    def _prompt_provider(self) -> str:
        """Prompt user to select CLI provider.

        Returns:
            Selected provider key (e.g., "claude", "codex", "gemini").

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C.
            EOFError: If no input available (piped input scenario).

        """
        # Display provider options with descriptions
        self.console.print("[bold]Available CLI providers:[/bold]")
        for provider_key, provider_info in AVAILABLE_PROVIDERS.items():
            marker = "[green]→[/green]" if provider_key == "claude" else "  "
            display_name = provider_info["display_name"]
            self.console.print(f"  {marker} [cyan]{provider_key}[/cyan]: {display_name}")
        self.console.print()

        choices = list(AVAILABLE_PROVIDERS.keys())
        return Prompt.ask(
            "[bold]Select CLI provider[/bold]",
            choices=choices,
            default="claude",
        )

    def _prompt_model(self, provider: str) -> str:
        """Prompt user to select model for chosen provider.

        Args:
            provider: Provider key (e.g., "claude").

        Returns:
            Selected model key (e.g., "opus_4").

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C.
            EOFError: If no input available (piped input scenario).

        """
        provider_info = AVAILABLE_PROVIDERS[provider]
        models = provider_info["models"]
        default = provider_info["default_model"]

        # Display available models with descriptions
        self.console.print()
        self.console.print(f"[bold]Available models for {provider_info['display_name']}:[/bold]")
        for model_id, description in models.items():
            marker = "[green]→[/green]" if model_id == default else "  "
            self.console.print(f"  {marker} [cyan]{model_id}[/cyan]: {description}")
        self.console.print()

        return Prompt.ask(
            "[bold]Select model[/bold]",
            choices=list(models.keys()),
            default=default,
        )

    def _build_config(self, provider: str, model: str) -> dict[str, Any]:
        """Build configuration dictionary with selected values and defaults.

        Args:
            provider: Selected provider key.
            model: Selected model key.

        Returns:
            Configuration dictionary ready for YAML serialization.

        """
        return {
            "providers": {
                "master": {
                    "provider": provider,
                    "model": model,
                },
            },
            # state_path not set - defaults to {project}/.bmad-assist/state.yaml
            "timeout": 300,
        }

    def _display_summary(self, config: dict[str, Any]) -> None:
        """Display configuration summary in a Rich table.

        Args:
            config: Configuration dictionary to summarize.

        """
        self.console.print()

        table = Table(title="Configuration Summary", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        master = config["providers"]["master"]
        provider_name = AVAILABLE_PROVIDERS[master["provider"]]["display_name"]

        table.add_row("Provider", f"{master['provider']} ({provider_name})")
        table.add_row("Model", master["model"])
        state_path = config.get("state_path", "{project}/.bmad-assist/state.yaml")
        table.add_row("State Path", state_path)
        table.add_row("Timeout", f"{config['timeout']} seconds")
        table.add_row("Config File", CONFIG_FILENAME)

        self.console.print(table)
        self.console.print()

    def _confirm_save(self) -> bool:
        """Ask user to confirm saving the configuration.

        Returns:
            True if user confirms, False if user rejects.

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C.
            EOFError: If no input available (piped input scenario).

        """
        return Confirm.ask(
            "[bold]Save this configuration?[/bold]",
            default=True,
        )

    def _save_config(self, project_path: Path, config: dict[str, Any]) -> Path:
        """Save config to YAML file using atomic write pattern.

        Uses temp file + os.rename() per architecture.md NFR2 requirements
        to ensure no partial/corrupted config files can exist.

        Args:
            project_path: Directory where config file will be saved.
            config: Configuration dictionary to serialize.

        Returns:
            Path to the saved config file.

        Raises:
            OSError: If write fails (permission denied, disk full, etc.)

        """
        config_path = project_path / CONFIG_FILENAME

        # Build YAML content with header comments
        header = """# bmad-assist configuration
# Generated by interactive setup wizard
# See docs/architecture.md for full schema

"""
        content = header + yaml.dump(
            config,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

        # Atomic write: temp file in same directory + rename
        # Same directory ensures same filesystem for atomic rename
        fd: int | None = None
        tmp_path_str: str | None = None

        try:
            fd, tmp_path_str = tempfile.mkstemp(
                dir=project_path,
                prefix=".bmad-assist-",
                suffix=".yaml.tmp",
            )
            # Inner try/finally ensures fd is closed if fdopen fails
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    fd = None  # os.fdopen takes ownership
                    f.write(content)
            finally:
                # Close fd if fdopen failed before taking ownership
                if fd is not None:
                    os.close(fd)

            os.rename(tmp_path_str, config_path)
            logger.debug("Atomic write completed: %s -> %s", tmp_path_str, config_path)
            tmp_path_str = None  # Rename succeeded, no cleanup needed

        except Exception:
            # Clean up temp file on any failure
            if tmp_path_str is not None and os.path.exists(tmp_path_str):
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path_str)
            raise

        return config_path


def run_config_wizard(
    project_path: Path,
    console: Console | None = None,
) -> Path:
    """Run the configuration wizard and return path to generated config.

    This is the main entry point for config generation. It creates a
    ConfigGenerator instance and runs the interactive wizard.

    Args:
        project_path: Path to project directory.
        console: Optional Rich console for output.

    Returns:
        Path to the generated config file.

    Raises:
        KeyboardInterrupt: If user cancels with Ctrl+C.
        EOFError: If running in non-interactive environment (piped input).
        OSError: If config file cannot be written (permission denied, disk full).
        SystemExit: If user rejects save confirmation (exit code 1).

    Example:
        >>> from pathlib import Path
        >>> from bmad_assist.core.config_generator import run_config_wizard
        >>> config_path = run_config_wizard(Path("./my-project"))

    """
    generator = ConfigGenerator(console)
    return generator.run(project_path)
