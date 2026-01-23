from maestro.integrations.home_assistant.types import NotifActionEvent, WebSocketEvent
from maestro.triggers.notif_action import NotifActionTriggerManager
from maestro.utils.logging import log


def handle_notif_action(event: WebSocketEvent) -> None:
    user_id = event.context.user_id
    action_name = event.data["actionName"]
    device_name = device_name = event.data["sourceDeviceName"]

    log.debug("Processing notif action event", action=action_name, device=device_name)

    ios_notif_action = NotifActionEvent(
        time_fired=event.time_fired,
        type=event.event_type,
        data=event.data,
        user_id=user_id,
        name=action_name,
        action_data=event.data["action_data"],
        device_id=event.data["sourceDeviceID"],
        device_name=device_name,
    )

    NotifActionTriggerManager.fire_triggers(ios_notif_action)
