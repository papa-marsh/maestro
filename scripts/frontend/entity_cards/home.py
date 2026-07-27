from calendar import Day
from contextlib import suppress
from dataclasses import asdict
from datetime import timedelta

from maestro.domains import ON, UNAVAILABLE, UNKNOWN
from maestro.exceptions import AttributeDoesNotExistError
from maestro.integrations import StateManager
from maestro.triggers import (
    HassEvent,
    MaestroEvent,
    cron_trigger,
    hass_trigger,
    maestro_trigger,
    state_change_trigger,
)
from maestro.utils import local_now

from registry import binary_sensor, climate, maestro
from scripts.common.event_type import UIEvent, ui_event_trigger
from scripts.frontend.common.entity_card import EntityCardAttributes, RowColor
from scripts.frontend.common.icons import Icon
from scripts.home.doors import EXTERIOR_DOORS

card = maestro.entity_card_3


@hass_trigger(HassEvent.STARTUP)
@maestro_trigger(MaestroEvent.STARTUP)
def initialize_card() -> None:
    attributes = EntityCardAttributes(
        title="Home",
        icon=Icon.HOME,
    )
    StateManager().initialize_hass_entity(
        entity_id=card.id,
        state="Loading...",
        attributes=asdict(attributes),
        restore_cached=True,
    )
    card.update(title=attributes.title, row_3_icon=Icon.DOG)


@state_change_trigger(*EXTERIOR_DOORS)
def set_state() -> None:
    open_doors = [door for door in EXTERIOR_DOORS if door.state == "on"]
    open_count = len(open_doors)
    if open_count == 1:
        state = open_doors[0].friendly_name.split(" ")[0]
        icon = Icon.DOOR_OPEN
        active = True
    elif open_count > 1:
        state = f"{open_count} Doors"
        icon = Icon.DOOR_OPEN
        active = True
    else:
        state = "All Shut"
        icon = Icon.HOME
        active = False

    card.update(state=state, icon=icon, active=active)


@state_change_trigger(climate.thermostat)
@cron_trigger("*/10 * * * *")
def set_row_1() -> None:
    if climate.thermostat.state in [UNKNOWN, UNAVAILABLE]:
        card.update(row_1_value="Offline", row_1_icon=Icon.THERMOMETER_OFF)
        return

    temperature = climate.thermostat.current_temperature
    humidity = climate.thermostat.current_humidity

    value = f"{temperature:.0f}° · {humidity:.0f}%"
    card.update(row_1_value=value, row_1_icon=Icon.THERMOMETER)


@state_change_trigger(climate.thermostat)
@cron_trigger("*/10 * * * *")
def set_row_2() -> None:
    if climate.thermostat.state in [UNKNOWN, UNAVAILABLE]:
        card.update(row_2_value="Offline", row_2_icon=Icon.HVAC)
        return

    value = climate.thermostat.hvac_action
    current_temp = climate.thermostat.current_temperature

    with suppress(AttributeDoesNotExistError):
        setpoint = climate.thermostat.temperature
        if current_temp != setpoint:
            value += f" ({setpoint})"

    icon_map = {"cool": Icon.SNOWFLAKE, "heat": Icon.FIRE, "off": Icon.HVAC_OFF}
    icon = icon_map.get(climate.thermostat.state, Icon.HELP)
    card.update(row_2_value=value, row_2_icon=icon)


@state_change_trigger(binary_sensor.chelsea_cabinet, to_state=ON)
def set_row_3() -> None:
    value = local_now().strftime("%-I:%M %p")
    card.update(row_3_value=value, row_3_color=RowColor.DEFAULT)


@cron_trigger(hour=18, day_of_week=Day.MONDAY)
def garbage_bin_reminder() -> None:
    card.blink = True


@cron_trigger(hour=7)
@cron_trigger(hour=19)
def feed_chelsea_reminder() -> None:
    last_changed = binary_sensor.chelsea_cabinet.last_changed
    if local_now() - last_changed > timedelta(hours=1):
        card.row_3_color = RowColor.RED


@ui_event_trigger(UIEvent.ENTITY_CARD_3_TAP)
def handle_tap() -> None:
    if card.blink:
        card.blink = False
        return

    card.row_3_color = RowColor.DEFAULT if card.row_3_color == RowColor.RED else RowColor.RED
