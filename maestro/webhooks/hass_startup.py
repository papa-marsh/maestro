from flask import Response, jsonify

from maestro.triggers.hass import HassEvent, HassTriggerManager
from maestro.utils.logger import log


def handle_hass_startup(_request_body: dict) -> tuple[Response, int]:
    log.info("Event handled for Home Assistant startup")
    HassTriggerManager.fire_triggers(HassEvent.STARTUP)

    return jsonify({"status": "success"}), 200
