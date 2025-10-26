from flask import Response, jsonify
from structlog.stdlib import get_logger

from maestro.triggers.hass import HassEvent, HassTriggerManager

log = get_logger()


def handle_hass_shutdown(_: dict) -> tuple[Response, int]:
    log.info("Event handled for Home Assistant shutdown")
    HassTriggerManager.fire_triggers(HassEvent.SHUTDOWN)

    return jsonify({"status": "success"}), 200
