from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict
from uuid import uuid4

from maestro.config import DEFAULT_NOTIF_SOUND, DEFAULT_NOTIF_URL
from maestro.integrations.home_assistant.domain import Domain

if TYPE_CHECKING:
    from maestro.domains.person import Person

from maestro.utils.exceptions import NotifActionMappingError
from maestro.utils.logging import log


class Notif:
    """
    Comprehensive push notification class.
    Setting sound="passive" will send silently without waking screen.
    `url` must be a full web URL (https://example.com) or a lovelace view.
    `action_data` is included in the event payload when HASS
    receives an actionable notification's response.
    """

    class Priority(StrEnum):
        PASSIVE = auto()
        ACTIVE = auto()
        TIME_SENSITIVE = "time-sensitive"
        CRITICAL = auto()

    class Action(TypedDict):
        """
        Represents a single Action of an actionable notifiction.
        `action` is the action's unique identifier. `title` is what's shown on the button itself.
        Set behavior="textInput" to allow a text input response after pressing the button.
        `uri` can be used to bring user to a specific url or HA tab.
        """

        action: str
        title: str
        authenticationRequired: bool
        destructive: bool
        uri: NotRequired[str]
        behavior: NotRequired[str]

    def __init__(
        self,
        message: str,
        title: str = "",
        priority: Priority = Priority.ACTIVE,
        group: str | None = None,
        tag: str | None = None,
        sound: str | None = DEFAULT_NOTIF_SOUND,
        url: str = DEFAULT_NOTIF_URL,
        actions: list[Action] = [],
        action_data: Any = None,
    ) -> None:
        if tag and not group:
            group = tag
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

    def send(self, *targets: "Person") -> None:
        for target in targets:
            log.info(
                "Sending notification",
                title=self.payload["title"],
                message=self.payload["message"],
                target=target.id,
            )
            if not target.notify_action_name:
                raise NotifActionMappingError(f"Couldn't map {target.id} to an action. Check .env")

            target.state_manager.hass_client.perform_action(
                domain=Domain.NOTIFY,
                action=target.notify_action_name,
                entity_id=None,
                response_expected=False,
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
    ) -> Action:
        """Helper function to create a NotifAction with clean defaults"""
        action = cls.Action(
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
