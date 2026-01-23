from maestro.integrations.home_assistant.types import WebSocketEvent
from maestro.triggers.hass import HassEvent, HassTriggerManager
from maestro.utils.logging import log


def handle_hass_shutdown(_event: WebSocketEvent) -> None:
    log.info("Processing Home Assistant shutdown event")
    HassTriggerManager.fire_triggers(HassEvent.SHUTDOWN)
