from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict
from uuid import uuid4

from structlog.stdlib import get_logger

from maestro.config import DEFAULT_NOTIF_SOUND, DEFAULT_NOTIF_URL, NOTIFY_ACTION_MAPPINGS
from maestro.integrations.home_assistant.domain import Domain

if TYPE_CHECKING:
    from maestro.domains.person import Person

log = get_logger()


class NotifPriority(StrEnum):
    PASSIVE = auto()
    ACTIVE = auto()
    TIME_SENSITIVE = "time-sensitive"
    CRITICAL = auto()


class NotifAction(TypedDict):
    """
    Represents a single Action of an actionable notifiction.
    `action` is the action's unique identifier. `title` is what's shown on the button itself.
    Set behavior="textInput" to allow a text input response after pressing the button.
    `uri` can be used to bring user to a specific tab in the HA app (eg. /lovelace-mobile/view_name)
    """

    action: str
    title: str
    authenticationRequired: bool
    destructive: bool
    uri: NotRequired[str]
    behavior: NotRequired[str]


class Notif:
    """
    Comprehensive push notification class.
    Setting sound="passive" will send silently without waking screen.
    `url` must be a full web URL (https://example.com) or a lovelace mobile view (overview).
    `action_data` is included in the event payload when HASS
    receives an actionable notification's response.
    """

    def __init__(
        self,
        message: str,
        title: str = "",
        priority: NotifPriority = NotifPriority.ACTIVE,
        group: str | None = None,
        tag: str | None = None,
        sound: str | None = DEFAULT_NOTIF_SOUND,
        url: str = DEFAULT_NOTIF_URL,
        actions: list[NotifAction] = [],
        action_data: Any = None,
    ) -> None:
        self.payload = {
            "message": message,
            "title": title,
            "data": {
                "actions": actions if actions else None,
                "action_data": action_data,
                "group": group or str(uuid4()),
                "tag": tag or str(uuid4()),
                "url": url,
                "push": {
                    "sound": "none" if sound is None else sound,
                    "interruption-level": priority,
                },
            },
        }

    def send(self, target: "Person | list[Person]") -> None:
        target_list = [target] if not isinstance(target, list) else target
        for target in target_list:
            log.info("Sending notification", title=self.payload["title"], target=target.id)
            action_name = NOTIFY_ACTION_MAPPINGS.get(target.id)
            if action_name is None:
                raise KeyError(f"Couldn't map {target.id} to a notify action. Check .env file")

            target.state_manager.hass_client.perform_action(
                domain=Domain.NOTIFY,
                action=action_name,
                entity_id=None,
                **self.payload,
            )

    @classmethod
    def build_action(
        cls,
        name: str,
        title: str,
        destructive: bool = False,
        uri: str | None = None,
        input: bool = False,
        require_auth: bool = False,
    ) -> NotifAction:
        """Helper function to create a NotifAction with clean defaults"""
        action = NotifAction(
            action=name,
            title=title,
            authenticationRequired=require_auth,
            destructive=destructive,
        )
        if uri:
            action["uri"] = uri
        if input:
            action["behavior"] = "textInput"

        return action
