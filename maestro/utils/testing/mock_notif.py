"""Mock notification system for testing without sending real notifications."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from maestro.utils.dates import local_now

if TYPE_CHECKING:
    from maestro.domains.person import Person


@dataclass
class SentNotification:
    """Records a notification that was sent during testing."""

    title: str
    message: str
    target_entity_ids: list[str]
    priority: str
    group: str
    tag: str
    url: str
    actions: list[dict] | None
    action_data: Any
    sent_at: datetime = field(default_factory=local_now)


class MockNotif:
    """
    Mock notification class that records notifications instead of sending them.

    This replaces the real Notif class during testing to avoid sending
    actual push notifications while still allowing verification.
    """

    _sent_notifications: list[SentNotification] = []

    class Priority:
        """Mirror the Priority enum from the real Notif class."""

        PASSIVE = "passive"
        ACTIVE = "active"
        TIME_SENSITIVE = "time-sensitive"
        CRITICAL = "critical"

    def __init__(
        self,
        message: str,
        title: str = "",
        priority: str = Priority.ACTIVE,
        group: str | None = None,
        tag: str | None = None,
        sound: str | None = None,
        url: str = "",
        actions: list[dict] | None = None,
        action_data: Any = None,
    ) -> None:
        from uuid import uuid4

        self.message = message
        self.title = title
        self.priority = priority
        self.group = group or str(uuid4())
        self.tag = tag or str(uuid4())
        self.url = url
        self.actions = actions
        self.action_data = action_data

    def send(self, *targets: "Person") -> None:
        """Record the notification instead of actually sending it."""
        target_ids = [str(target.id) for target in targets]

        notification = SentNotification(
            title=self.title,
            message=self.message,
            target_entity_ids=target_ids,
            priority=self.priority,
            group=self.group,
            tag=self.tag,
            url=self.url,
            actions=self.actions,
            action_data=self.action_data,
        )

        MockNotif._sent_notifications.append(notification)

    @classmethod
    def build_action(
        cls,
        name: str,
        title: str,
        destructive: bool = False,
        uri: str | None = None,
        input: bool = False,
        require_auth: bool = False,
    ) -> dict:
        """Build a notification action dict (same interface as real Notif)."""
        action = {
            "action": name,
            "title": title,
            "authenticationRequired": require_auth,
            "destructive": destructive,
        }
        if uri:
            action["uri"] = uri
        if input:
            action["behavior"] = "textInput"

        return action

    @classmethod
    def get_sent_notifications(cls) -> list[SentNotification]:
        """Get all sent notifications for assertions."""
        return cls._sent_notifications.copy()

    @classmethod
    def get_notifications_for_target(cls, entity_id: str) -> list[SentNotification]:
        """Get notifications sent to a specific target."""
        return [
            notif for notif in cls._sent_notifications if entity_id in notif.target_entity_ids
        ]

    @classmethod
    def clear_sent_notifications(cls) -> None:
        """Clear the sent notifications list."""
        cls._sent_notifications.clear()
