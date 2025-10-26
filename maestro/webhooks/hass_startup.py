from flask import Response, jsonify
from structlog.stdlib import get_logger

from maestro.triggers.hass import HassEvent, HassTriggerManager

log = get_logger()


def handle_hass_startup(_: dict) -> tuple[Response, int]:
    log.info("Event handled for Home Assistant startup")
    HassTriggerManager.fire_triggers(HassEvent.STARTUP)

    return jsonify({"status": "success"}), 200
