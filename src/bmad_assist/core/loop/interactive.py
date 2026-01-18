"""Interactive debug mode for phase execution.

Provides manual confirmation between phases and interactive prompt editing
when DEBUG logging is enabled.

Key bindings:
- [n] - proceed to next phase (no Enter needed)
- [i] - enter interactive prompt mode (no Enter needed)
- [q] - quit execution (no Enter needed)
- Esc + Enter - send prompt in interactive mode
- Ctrl+C - exit interactive mode (preserves text)
- Ctrl+U - clear all text in interactive mode

"""

import logging
import sys
import termios
import tty
from collections.abc import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent

from bmad_assist.providers.base import BaseProvider, ProviderResult

logger = logging.getLogger(__name__)


def _read_single_key() -> str:
    """Read a single key from stdin without waiting for Enter.

    Uses termios to set terminal to raw mode for single-char input.

    Returns:
        Single character pressed by user.

    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


class InteractiveDebugger:
    """Interactive debugger for phase execution in DEBUG mode.

    Provides:
    - Manual confirmation before proceeding to next phase
    - Interactive prompt mode to send custom prompts to provider
    - Preserved prompt buffer across interactions

    """

    def __init__(self) -> None:
        """Initialize the interactive debugger."""
        self._prompt_buffer: str = ""
        self._session: PromptSession[str] | None = None

    @property
    def is_enabled(self) -> bool:
        """Check if interactive debug mode should be active.

        Returns False if:
        - Non-interactive mode is forced via -n flag (overrides all)
        - DEBUG logging is not enabled
        """
        if _force_non_interactive:
            return False
        return logger.isEnabledFor(logging.DEBUG)

    def _get_session(self) -> PromptSession[str]:
        """Get or create the prompt session with key bindings."""
        if self._session is None:
            bindings = KeyBindings()

            @bindings.add("c-u")
            def clear_buffer(event: KeyPressEvent) -> None:
                """Clear all text with Ctrl+U (Unix standard clear-line)."""
                event.app.current_buffer.text = ""

            self._session = PromptSession(key_bindings=bindings)

        return self._session

    def prompt_for_action(self, phase_name: str, result_summary: str) -> str:
        """Prompt user to choose next action after phase completion.

        Args:
            phase_name: Name of the completed phase.
            result_summary: Short summary of phase result.

        Returns:
            Action key: "n" for next, "i" for interactive, "q" for quit.

        """
        if not self.is_enabled:
            return "n"  # Auto-continue if not in debug mode

        print(f"\n[{phase_name}] {result_summary}")
        sys.stdout.write("[n]ext  [i]nteractive  [q]uit: ")
        sys.stdout.flush()

        while True:
            try:
                choice = _read_single_key().lower()

                if choice in ("n", "i", "q"):
                    print(choice)  # Echo the choice
                    return choice

                if choice == "\x03":  # Ctrl+C
                    print("^C")
                    return "q"

            except (KeyboardInterrupt, EOFError):
                print("\nInterrupted.")
                return "q"

    def interactive_prompt(
        self,
        provider: BaseProvider,
        model: str | None,
        timeout: int,
        on_result: Callable[[ProviderResult], None] | None = None,
    ) -> bool:
        """Enter interactive prompt mode.

        Allows user to type multi-line prompt and send to provider.
        Ctrl+Enter submits, Esc cancels (preserving buffer).

        Args:
            provider: Provider instance to invoke.
            model: Model to use for invocation.
            timeout: Timeout in seconds.
            on_result: Optional callback for provider result.

        Returns:
            True to continue with next phase, False to re-prompt for action.

        """
        session = self._get_session()

        print("\n" + "-" * 60)
        print("Interactive Prompt Mode")
        print("-" * 60)
        print("Type your prompt (multi-line supported):")
        print("  - Esc + Enter: Send prompt")
        print("  - Ctrl+C: Cancel and return to action menu")
        print("  - Ctrl+U: Clear all text")
        print("-" * 60)

        # Show previous buffer if any
        if self._prompt_buffer:
            print(f"[Previous buffer restored: {len(self._prompt_buffer)} chars]")

        try:
            # Collect multi-line input
            lines: list[str] = []
            if self._prompt_buffer:
                # Pre-fill with previous buffer
                lines = self._prompt_buffer.split("\n")
                for line in lines:
                    print(f">>> {line}")

            prompt_text = session.prompt(
                ">>> ",
                multiline=True,
                default=self._prompt_buffer,
            )

            # Save buffer for next time
            self._prompt_buffer = prompt_text

            if not prompt_text.strip():
                print("[Empty prompt, returning to action menu]")
                return False

            # Invoke provider
            print(f"\n[Sending {len(prompt_text)} chars to provider...]")
            print("-" * 40)

            try:
                result = provider.invoke(
                    prompt_text,
                    model=model,
                    timeout=timeout,
                )

                # Display result
                print(f"\n[Provider returned: exit_code={result.exit_code}]")
                print("-" * 40)
                print(result.stdout)
                if result.stderr:
                    print(f"\n[stderr]\n{result.stderr}")
                print("-" * 40)

                if on_result:
                    on_result(result)

            except Exception as e:
                print(f"\n[Provider error: {e}]")
                logger.exception("Interactive prompt provider error")

            return False  # Return to action menu after interaction

        except KeyboardInterrupt:
            print("\n[Cancelled, returning to action menu]")
            return False

        except EOFError:
            # Ctrl+D with empty buffer
            print("\n[EOF, returning to action menu]")
            return False

    def clear_buffer(self) -> None:
        """Clear the preserved prompt buffer."""
        self._prompt_buffer = ""
        print("[Buffer cleared]")

    def run_debug_loop(
        self,
        phase_name: str,
        result_summary: str,
        provider: BaseProvider,
        model: str | None,
        timeout: int,
    ) -> bool:
        """Run the interactive debug loop after phase completion.

        Args:
            phase_name: Name of the completed phase.
            result_summary: Short summary of phase result.
            provider: Provider instance for interactive prompts.
            model: Model to use for interactive prompts.
            timeout: Timeout for interactive prompts.

        Returns:
            True to continue to next phase, False to halt execution.

        """
        if not self.is_enabled:
            return True  # Auto-continue if not in debug mode

        while True:
            action = self.prompt_for_action(phase_name, result_summary)

            if action == "n":
                return True  # Continue to next phase

            if action == "q":
                print("[User requested quit]")
                return False  # Halt execution

            if action == "i":
                # Interactive mode - loop until user chooses n or q
                continue_loop = self.interactive_prompt(
                    provider=provider,
                    model=model,
                    timeout=timeout,
                )
                if continue_loop:
                    return True
                # Otherwise, re-prompt for action


# Global singleton instance
_debugger: InteractiveDebugger | None = None

# Global flag to force non-interactive mode (set via -n flag)
_force_non_interactive: bool = False


def set_non_interactive(enabled: bool) -> None:
    """Set the global non-interactive mode.

    When enabled, all interactive prompts are skipped and auto-continue is used.
    This is set by the -n/--no-interactive CLI flag.

    Args:
        enabled: True to disable all interactive prompts.

    """
    global _force_non_interactive
    _force_non_interactive = enabled


def is_non_interactive() -> bool:
    """Check if non-interactive mode is forced."""
    return _force_non_interactive


def get_debugger() -> InteractiveDebugger:
    """Get the global interactive debugger instance."""
    global _debugger
    if _debugger is None:
        _debugger = InteractiveDebugger()
    return _debugger
