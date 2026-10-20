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
from scripts.common.finance import NET_SYMBOL, get_private_share_price, get_stock_quote
from scripts.config.secrets import (
    CURRENT_SALARY,
    CURRENT_SHARES_PER_YEAR,
    EMPLOYER_SYMBOL,
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
    card.update(title=attributes.title, row_2_icon=Icon.SHIELD_AIRPLANE, row_3_icon=Icon.CLOUD)


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
    if sensor.office_ambient_sensor_temperature.state in [UNKNOWN, UNAVAILABLE] or (
        sensor.office_ambient_sensor_humidity.state in [UNKNOWN, UNAVAILABLE]
    ):
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

    if spy_result := build_stock_row(NET_SYMBOL):
        value, color = spy_result
        attr_updates["row_3_value"] = value
        attr_updates["row_3_color"] = color

    card.update(**attr_updates)


def fetch_employer_price() -> float | None:
    try:
        return get_private_share_price(EMPLOYER_SYMBOL)
    except Exception as e:
        log.error("Private-market price request failed", exception_type=type(e).__name__)
        return None


def show_employer_price(price: float | None) -> None:
    card.update(
        row_2_value=f"${price:,.0f}" if price is not None else "API Error",
        row_2_icon=Icon.SHIELD_AIRPLANE,
        row_2_color=RowColor.DEFAULT,
    )


@hass_trigger(HassEvent.STARTUP)
@maestro_trigger(MaestroEvent.STARTUP)
@cron_trigger(hour=1)
def set_employer_stock_row() -> None:
    show_employer_price(fetch_employer_price())


@cron_trigger(hour=8, minute=20, day_of_week=[0, 1, 2, 3, 4])
def daily_review_reminder() -> None:
    card.blink = True


@ui_event_trigger(UIEvent.ENTITY_CARD_4_TAP)
def handle_tap() -> None:
    if card.blink:
        card.blink = False
        return

    toggle_meeting_active()


def format_compensation(value: float) -> str:
    thousands = round(value / 1_000)
    if abs(thousands) >= 1_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${thousands}K"


@ui_event_trigger(UIEvent.ENTITY_CARD_4_DOUBLE_TAP)
def handle_double_tap() -> None:
    price = fetch_employer_price()
    net_value = "Failed :("
    try:
        quote = get_stock_quote(NET_SYMBOL)
        net_total_comp = NET_SALARY + NET_SHARES_PER_YEAR * quote.c
        net_value = format_compensation(net_total_comp)
    except Exception as e:
        log.error("Finnhub API request failed", exception_type=type(e).__name__)

    current_total_comp = CURRENT_SALARY + CURRENT_SHARES_PER_YEAR * SHARE_PRICE
    market_value = (
        format_compensation(CURRENT_SALARY + CURRENT_SHARES_PER_YEAR * price)
        if price is not None
        else "API Error"
    )

    card.update(
        row_1_value=format_compensation(current_total_comp),
        row_1_icon=Icon.SHIELD_AIRPLANE,
        row_1_color=RowColor.DEFAULT,
        row_2_value=market_value,
        row_2_icon=Icon.SHIELD_MOON,
        row_2_color=RowColor.DEFAULT,
        row_3_value=net_value,
        row_3_icon=Icon.CLOUD,
        row_3_color=RowColor.DEFAULT,
    )
    try:
        sleep(5)
    finally:
        try:
            set_row_1()
        finally:
            show_employer_price(price)
            set_stock_rows()


@ui_event_trigger(UIEvent.ENTITY_CARD_4_HOLD)
def handle_hold() -> None:
    if switch.space_heater.is_on:
        switch.space_heater.turn_off()
    else:
        switch.space_heater.turn_on()
