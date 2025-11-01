from flask import Response, jsonify

from maestro.triggers.hass import HassEvent, HassTriggerManager
from maestro.utils.logger import log


def handle_hass_shutdown(_: dict) -> tuple[Response, int]:
    log.info("Event handled for Home Assistant shutdown")
    HassTriggerManager.fire_triggers(HassEvent.SHUTDOWN)

    return jsonify({"status": "success"}), 200
