"""Office card pricing, compensation comparison, and normal-row restoration."""

from unittest.mock import patch

import pytest
from maestro.domains import OFF, UNAVAILABLE
from maestro.testing import MaestroTest

from registry import sensor, switch
from scripts.common.event_type import EventType, UIEvent
from scripts.common.finance import FinnhubResponse
from scripts.frontend.common.entity_card import RowColor
from scripts.frontend.common.icons import Icon

from .. import office


def test_normal_rows_show_environment_and_share_prices(mt: MaestroTest) -> None:
    office.initialize_card()
    mt.set_state(sensor.office_ambient_sensor_temperature, "72")
    mt.set_state(sensor.office_ambient_sensor_humidity, "45")
    mt.set_state(switch.space_heater, OFF)
    with (
        patch.object(office, "get_private_share_price", return_value=123.45),
        patch.object(
            office, "get_stock_quote", return_value=FinnhubResponse(125.5, 0, 0, 0, 0, 0, 0, 0)
        ),
    ):
        office.set_row_1()
        office.set_employer_stock_row()
        office.set_stock_rows()

    assert office.card.row_1_value == "72° · 45%"
    assert office.card.row_1_icon == Icon.THERMOMETER_WATER
    assert office.card.row_2_value == "$123.45"
    assert office.card.row_2_icon == Icon.SHIELD_AIRPLANE
    assert office.card.row_3_value == "$126"
    assert office.card.row_3_icon == Icon.CLOUD


@pytest.mark.parametrize(
    "private_failure,net_failure", [(False, False), (True, False), (False, True)]
)
def test_double_tap_shows_compensation_then_restores_rows(
    mt: MaestroTest, private_failure: bool, net_failure: bool
) -> None:
    office.initialize_card()
    mt.set_state(sensor.office_ambient_sensor_temperature, "72")
    mt.set_state(sensor.office_ambient_sensor_humidity, "45")
    mt.set_state(switch.space_heater, OFF)
    quote = FinnhubResponse(125.5, 0, 0, 0, 0, 0, 0, 0)
    displays: list[tuple[str, str, str]] = []

    def capture_display(seconds: float) -> None:
        assert seconds == 5
        displays.append((office.card.row_1_value, office.card.row_2_value, office.card.row_3_value))
        assert office.card.row_1_icon == Icon.SHIELD_AIRPLANE
        assert office.card.row_2_icon == Icon.SHIELD_MOON
        assert office.card.row_3_icon == Icon.CLOUD
        assert office.card.row_1_color == RowColor.DEFAULT
        assert office.card.row_2_color == RowColor.DEFAULT
        assert office.card.row_3_color == RowColor.DEFAULT

    with (
        patch.object(office, "CURRENT_SALARY", 100_000),
        patch.object(office, "CURRENT_SHARES_PER_YEAR", 1_000),
        patch.object(office, "SHARE_PRICE", 20),
        patch.object(office, "NET_SALARY", 90_000),
        patch.object(office, "NET_SHARES_PER_YEAR", 500),
        patch.object(
            office,
            "get_private_share_price",
            return_value=123.45,
            side_effect=RuntimeError() if private_failure else None,
        ),
        patch.object(
            office,
            "get_stock_quote",
            return_value=quote,
            side_effect=RuntimeError() if net_failure else None,
        ),
        patch.object(office, "sleep", side_effect=capture_display),
    ):
        mt.trigger_event(
            EventType.MAESTRO_UI_EVENT, data={"trigger": UIEvent.ENTITY_CARD_4_DOUBLE_TAP}
        )

    assert displays == [
        (
            "$120,000",
            "API Error" if private_failure else "$223,450",
            "Failed :(" if net_failure else "$152,750",
        )
    ]
    assert office.card.row_1_value == "72° · 45%"
    assert office.card.row_1_icon == Icon.THERMOMETER_WATER
    assert office.card.row_2_value == ("API Error" if private_failure else "$123.45")
    assert office.card.row_2_icon == Icon.SHIELD_AIRPLANE
    assert office.card.row_3_value == ("API Error" if net_failure else "$126")
    assert office.card.row_3_icon == Icon.CLOUD


def test_private_price_failure_replaces_previous_value(mt: MaestroTest) -> None:
    office.initialize_card()
    office.card.update(row_2_value="$100.00")
    with patch.object(office, "get_private_share_price", side_effect=RuntimeError()):
        office.set_employer_stock_row()
    assert office.card.row_2_value == "API Error"
    assert office.card.row_2_icon == Icon.SHIELD_AIRPLANE


def test_financial_rows_restore_even_if_environment_refresh_fails(mt: MaestroTest) -> None:
    office.initialize_card()
    with (
        patch.object(office, "get_private_share_price", return_value=123.45),
        patch.object(
            office, "get_stock_quote", return_value=FinnhubResponse(125.5, 0, 0, 0, 0, 0, 0, 0)
        ),
        patch.object(office, "sleep"),
        patch.object(office, "set_row_1", side_effect=ValueError()),
        pytest.raises(ValueError),
    ):
        office.handle_double_tap()

    assert office.card.row_2_value == "$123.45"
    assert office.card.row_2_icon == Icon.SHIELD_AIRPLANE
    assert office.card.row_3_value == "$126"


def test_unavailable_humidity_restores_offline_environment_row(mt: MaestroTest) -> None:
    office.initialize_card()
    office.card.update(row_1_value="$120,000", row_1_icon=Icon.SHIELD_AIRPLANE)
    mt.set_state(sensor.office_ambient_sensor_temperature, "72")
    mt.set_state(sensor.office_ambient_sensor_humidity, UNAVAILABLE)
    office.set_row_1()
    assert office.card.row_1_value == "Offline"
    assert office.card.row_1_icon == Icon.THERMOMETER_OFF
