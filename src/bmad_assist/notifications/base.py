"""Abstract base class for notification provider implementations.

This module defines the contract that all notification providers (Telegram,
Discord, etc.) must implement. The NotificationProvider ABC enables the
adapter pattern for extensible notification support.

Providers MUST implement async send() that NEVER raises exceptions.
All errors are logged internally and return False. This is critical
for fire-and-forget notification semantics per FR72 and NFR12.

Example:
    >>> class TelegramProvider(NotificationProvider):
    ...     @property
    ...     def provider_name(self) -> str:
    ...         return "telegram"
    ...
    ...     async def send(self, event: EventType, payload: EventPayload) -> bool:
    ...         try:
    ...             # Send notification via Telegram API
    ...             ...
    ...             return True
    ...         except Exception as e:
    ...             logger.error(
    ...                 "Notification failed: event=%s, provider=%s, error=%s",
    ...                 event, self.provider_name, str(e)
    ...             )
    ...             return False

"""

import logging
from abc import ABC, abstractmethod

from .events import EventPayload, EventType

logger = logging.getLogger(__name__)


class NotificationProvider(ABC):
    """Abstract base class for notification providers.

    Concrete implementations must implement:
        - provider_name: Unique identifier for this provider
        - send(): Async method to send notification (NEVER raises)

    All implementations must follow the fire-and-forget pattern:
    - send() must NEVER raise exceptions
    - All errors are logged internally at ERROR level
    - Return True on success, False on failure

    This design ensures notification failures don't interrupt the main
    development loop workflow.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g., 'telegram', 'discord')."""
        ...

    @abstractmethod
    async def send(self, event: EventType, payload: EventPayload) -> bool:
        """Send notification. Returns True on success, False on failure.

        MUST NOT raise exceptions - all errors logged internally.

        Args:
            event: The event type being sent.
            payload: Validated event payload.

        Returns:
            True if notification sent successfully, False otherwise.

        Note:
            Implementations must:
            - Catch all exceptions internally
            - Log failures at ERROR level with context:
              logger.error("Notification failed: event=%s, provider=%s, error=%s",
                          event, self.provider_name, str(e))
            - Return False for any failure condition
            - Use async HTTP clients (httpx.AsyncClient recommended)

        """
        ...
