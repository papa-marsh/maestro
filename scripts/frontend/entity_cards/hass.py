import socket
from contextlib import suppress
from dataclasses import asdict

from maestro.domains import ON
from maestro.integrations import StateManager
from maestro.triggers import (
    HassEvent,
    MaestroEvent,
    cron_trigger,
    hass_trigger,
    maestro_trigger,
    state_change_trigger,
)

from registry import maestro, sensor, update
from scripts.frontend.common.entity_card import EntityCardAttributes, RowColor
from scripts.frontend.common.icons import Icon

card = maestro.entity_card_6

ZWAVE_CHECK_JOB_ID = "post_startup_zwave_check"


@hass_trigger(HassEvent.STARTUP)
@maestro_trigger(MaestroEvent.STARTUP)
def initialize_card() -> None:
    attributes = EntityCardAttributes(
        title="Hass",
        icon=Icon.RASPBERRY_PI,
    )
    StateManager().initialize_hass_entity(
        entity_id=card.id,
        state="Loading...",
        attributes=asdict(attributes),
        restore_cached=True,
    )
    card.update(
        title=attributes.title,
        row_1_value=" - ",
        row_1_icon=Icon.HOME_ASSISTANT,
        row_2_icon=Icon.THERMOMETER,
        row_3_icon=Icon.MEMORY,
    )


@cron_trigger("* * * * *")
def set_state() -> None:
    update_available = (
        update.home_assistant_core_update.state == ON
        or update.home_assistant_supervisor_update.state == ON
    )
    if not check_internet_connection():
        state = "Offline"
        icon = Icon.WEB_OFF
        blink = True
    else:
        state = update.home_assistant_core_update.installed_version[2:]
        icon = Icon.UPDATE if update_available else Icon.HOME_ASSISTANT
        blink = False

    card.update(state=state, icon=icon, active=update_available, blink=blink)


@state_change_trigger(sensor.cpu_temperature)
def set_row_2() -> None:
    cpu_temp = float(sensor.cpu_temperature.state)
    value = f"{cpu_temp:.0f} °F"
    color = RowColor.RED if cpu_temp >= 110 else RowColor.DEFAULT
    card.update(row_2_value=value, row_2_color=color)


@state_change_trigger(sensor.memory_use_percent)
def set_row_3() -> None:
    memory_use = float(sensor.memory_use_percent.state)
    value = f"{memory_use:.1f}%"
    color = RowColor.RED if memory_use >= 85 else RowColor.DEFAULT
    card.update(row_3_value=value, row_3_color=color)


def check_internet_connection() -> bool:
    """Check internet connection by attempting TCP connections"""
    for host in [("8.8.8.8", 53), ("1.1.1.1", 53)]:
        with suppress(OSError), socket.create_connection(host, timeout=3):
            return True
    return False
