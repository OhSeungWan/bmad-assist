"""Event dispatcher for notification system.

This module provides the EventDispatcher class for routing events
to configured notification providers, and global accessor functions
for singleton access.

Example:
    >>> from bmad_assist.notifications import init_dispatcher, get_dispatcher
    >>> from bmad_assist.notifications.config import NotificationConfig
    >>> config = NotificationConfig(enabled=True, events=["story_started"])
    >>> init_dispatcher(config)
    >>> dispatcher = get_dispatcher()
    >>> await dispatcher.dispatch(EventType.STORY_STARTED, payload)

"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from .base import NotificationProvider
from .config import NotificationConfig, ProviderConfigItem
from .events import EventPayload, EventType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Dispatches events to configured notification providers.

    Sends notifications to all configured providers concurrently.
    Implements fire-and-forget pattern - failures are logged but don't
    interrupt the main workflow.

    Example:
        >>> config = NotificationConfig(enabled=True, providers=[...], events=["story_started"])
        >>> dispatcher = EventDispatcher(config)
        >>> payload = StoryStartedPayload(project="p", epic=1, story="1-1", phase="C")
        >>> await dispatcher.dispatch(EventType.STORY_STARTED, payload)

    """

    def __init__(self, config: NotificationConfig) -> None:
        """Initialize dispatcher with configuration.

        Args:
            config: Notification configuration with providers and events.

        """
        self._config = config
        self._providers: list[NotificationProvider] = []
        self._enabled_events = config.enabled_events

        # Lazy instantiation - only create providers if enabled
        if config.enabled:
            self._providers = self._create_providers(config.providers)
            logger.info(
                "Notification dispatcher initialized with %d providers",
                len(self._providers),
            )

    def _create_providers(
        self, provider_configs: list[ProviderConfigItem]
    ) -> list[NotificationProvider]:
        """Create provider instances from configuration.

        Args:
            provider_configs: List of provider configurations.

        Returns:
            List of instantiated providers.

        """
        providers: list[NotificationProvider] = []

        for provider_config in provider_configs:
            provider = self._create_provider(provider_config)
            if provider is not None:
                providers.append(provider)

        return providers

    def _create_provider(self, config: ProviderConfigItem) -> NotificationProvider | None:
        """Create single provider instance.

        Args:
            config: Provider configuration with credentials.

        Returns:
            Provider instance or None if creation failed.

        """
        try:
            if config.type == "telegram":
                from .telegram import TelegramProvider

                # Pass credentials from config (env vars already substituted)
                return TelegramProvider(
                    bot_token=config.bot_token or "",
                    chat_id=config.chat_id or "",
                )
            elif config.type == "discord":
                from .discord import DiscordProvider

                return DiscordProvider(webhook_url=config.webhook_url or "")
            else:
                logger.warning("Unknown provider type: %s", config.type)
                return None
        except Exception as e:
            logger.error("Failed to create provider %s: %s", config.type, str(e))
            return None

    def _should_dispatch(self, event: EventType) -> bool:
        """Check if event should be dispatched based on configuration.

        Args:
            event: Event type to check.

        Returns:
            True if event should be dispatched.

        """
        if not self._config.enabled:
            logger.debug("Notifications disabled, skipping dispatch")
            return False

        if not self._providers:
            logger.debug("No providers configured, skipping dispatch")
            return False

        if event not in self._enabled_events:
            logger.debug("Event %s filtered out, not in configured events list", event)
            return False

        return True

    async def dispatch(self, event: EventType, payload: EventPayload) -> None:
        """Dispatch event to all configured providers concurrently.

        Fire-and-forget: failures are logged but don't raise exceptions.

        Args:
            event: Event type to dispatch.
            payload: Event payload.

        """
        if not self._should_dispatch(event):
            return

        # Create coroutines for all providers
        coros = [provider.send(event, payload) for provider in self._providers]

        # Execute concurrently with exception handling
        results = await asyncio.gather(*coros, return_exceptions=True)

        # Log aggregate results
        success_count = sum(1 for r in results if r is True)
        logger.info(
            "Dispatched event=%s to %d/%d providers",
            event.value,
            success_count,
            len(self._providers),
        )

        # Log individual failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Provider %s raised exception: %s",
                    self._providers[i].provider_name,
                    str(result),
                )
            elif result is False:
                logger.warning(
                    "Provider %s failed to send event %s",
                    self._providers[i].provider_name,
                    event.value,
                )


# Global dispatcher instance
_dispatcher: EventDispatcher | None = None


def init_dispatcher(config: NotificationConfig | None) -> None:
    """Initialize global dispatcher with configuration.

    Called from cli.py after load_config_with_project() completes.
    Logs warning if called when dispatcher already initialized.

    Args:
        config: Notification configuration, or None to disable.

    """
    global _dispatcher

    if _dispatcher is not None:
        logger.warning("Notification dispatcher already initialized, re-initializing")

    if config is None or not config.enabled:
        _dispatcher = None
        logger.debug("Notification dispatcher disabled")
        return

    _dispatcher = EventDispatcher(config)


def get_dispatcher() -> EventDispatcher | None:
    """Get global dispatcher instance.

    Returns:
        EventDispatcher if initialized, None otherwise.

    """
    return _dispatcher


def reset_dispatcher() -> None:
    """Reset global dispatcher (for testing)."""
    global _dispatcher
    _dispatcher = None
