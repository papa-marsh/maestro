from flask import Response, jsonify

from maestro.triggers.hass import HassEvent, HassTriggerManager
from maestro.utils.logger import log


def handle_hass_startup(_: dict) -> tuple[Response, int]:
    log.info("Event handled for Home Assistant startup")
    HassTriggerManager.fire_triggers(HassEvent.STARTUP_NOT_WORKING_YET)

    return jsonify({"status": "success"}), 200
