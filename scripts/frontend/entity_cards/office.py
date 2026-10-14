from dataclasses import asdict
from datetime import datetime
from time import sleep

from maestro.domains import ON, UNAVAILABLE, UNKNOWN
from maestro.integrations import StateChangeEvent, StateManager
from maestro.triggers import (
    HassEvent,
    MaestroEvent,
    cron_trigger,
    hass_trigger,
    maestro_trigger,
    state_change_trigger,
)
from maestro.utils import local_now, log

from registry import maestro, sensor, switch
from scripts.common.event_type import UIEvent, ui_event_trigger
from scripts.common.finance import NET_SYMBOL, SPY_SYMBOL, get_stock_quote
from scripts.config.secrets import (
    CURRENT_SALARY,
    CURRENT_SHARES_PER_YEAR,
    NET_SALARY,
    NET_SHARES_PER_YEAR,
    SHARE_PRICE,
)
from scripts.frontend.common.entity_card import EntityCardAttributes, RowColor
from scripts.frontend.common.icons import Icon
from scripts.home.office.meetings import toggle_meeting_active

card = maestro.entity_card_4


@hass_trigger(HassEvent.STARTUP)
@maestro_trigger(MaestroEvent.STARTUP)
def initialize_card() -> None:
    attributes = EntityCardAttributes(
        title="Office",
        icon=Icon.CLOUD,
    )
    StateManager().initialize_hass_entity(
        entity_id=card.id,
        state="Loading...",
        attributes=asdict(attributes),
        restore_cached=True,
    )
    card.update(title=attributes.title, row_2_icon=Icon.FINANCE, row_3_icon=Icon.CLOUD_OUTLINE)


@state_change_trigger(maestro.meeting_active)
def set_state(state_change: StateChangeEvent) -> None:
    if state_change.new.state == ON:
        active = True
        state = "Busy"
        icon = Icon.HEADSET
    else:
        active = False
        state = "Available"
        icon = Icon.CLOUD

    card.update(state=state, active=active, icon=icon)


@state_change_trigger(
    sensor.office_ambient_sensor_temperature,
    sensor.office_ambient_sensor_humidity,
    switch.space_heater,
)
def set_row_1() -> None:
    if sensor.office_ambient_sensor_temperature.state in [UNKNOWN, UNAVAILABLE]:
        card.update(row_1_value="Offline", row_1_icon=Icon.THERMOMETER_OFF)
        return

    temperature = float(sensor.office_ambient_sensor_temperature.state)
    humidity = float(sensor.office_ambient_sensor_humidity.state)

    value = f"{temperature:.0f}° · {humidity:.0f}%"
    icon = Icon.RADIATOR if switch.space_heater.is_on else Icon.THERMOMETER_WATER
    card.update(row_1_value=value, row_1_icon=icon)


def build_stock_row(symbol: str) -> tuple[str, RowColor] | None:
    """Fetch stock quote and return current display value and color"""
    try:
        quote = get_stock_quote(symbol)
    except Exception as e:
        log.error("Finnhub API request failed", exception_type=type(e).__name__)
        return "API Error", RowColor.DEFAULT

    value = f"${quote.c:.0f}"
    color = RowColor.DEFAULT

    quote_last_updated = datetime.fromtimestamp(quote.t)
    if quote_last_updated.date() == local_now().date():
        plus_sign = "+" if quote.dp >= 0 else ""
        value += f" ({plus_sign}{quote.dp:.0f}%)"
        color = RowColor.GREEN if quote.dp > 5 else RowColor.RED if quote.dp < -5 else color

    return value, color


@cron_trigger("* 9-16 * * 1-5")
@cron_trigger(hour=1)
def set_stock_rows() -> None:
    attr_updates = {}

    if spy_result := build_stock_row(SPY_SYMBOL):
        value, color = spy_result
        attr_updates["row_2_value"] = value
        attr_updates["row_2_color"] = color

    if spy_result := build_stock_row(NET_SYMBOL):
        value, color = spy_result
        attr_updates["row_3_value"] = value
        attr_updates["row_3_color"] = color

    card.update(**attr_updates)


@cron_trigger(hour=8, minute=20, day_of_week=[0, 1, 2, 3, 4])
def daily_review_reminder() -> None:
    card.blink = True


@ui_event_trigger(UIEvent.ENTITY_CARD_4_TAP)
def handle_tap() -> None:
    if card.blink:
        card.blink = False
        return

    toggle_meeting_active()


@ui_event_trigger(UIEvent.ENTITY_CARD_4_DOUBLE_TAP)
def handle_double_tap() -> None:
    try:
        quote = get_stock_quote(NET_SYMBOL)
    except Exception:
        log.exception("Finnhub API request failed")
        card.update(row_2_value="Failed :(", row_3_value="Failed :(")
        return

    current_total_comp = CURRENT_SALARY + CURRENT_SHARES_PER_YEAR * SHARE_PRICE
    net_total_comp = NET_SALARY + NET_SHARES_PER_YEAR * quote.c

    card.update(
        row_2_value=f"${current_total_comp:,.0f}",
        row_2_color=RowColor.DEFAULT,
        row_3_value=f"${net_total_comp:,.0f}",
        row_3_color=RowColor.DEFAULT,
    )
    sleep(5)
    set_stock_rows()


@ui_event_trigger(UIEvent.ENTITY_CARD_4_HOLD)
def handle_hold() -> None:
    if switch.space_heater.is_on:
        switch.space_heater.turn_off()
    else:
        switch.space_heater.turn_on()
