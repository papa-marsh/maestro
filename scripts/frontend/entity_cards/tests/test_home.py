"""Home card bedroom climate display and normal-row restoration."""

from unittest.mock import patch

import pytest
from maestro.domains import UNAVAILABLE, UNKNOWN
from maestro.testing import MaestroTest

from registry import climate, sensor
from scripts.common.event_type import EventType, UIEvent
from scripts.frontend.common.entity_card import RowColor
from scripts.frontend.common.icons import Icon

from .. import home


@pytest.mark.parametrize("missing_state", [None, UNKNOWN, UNAVAILABLE])
def test_double_tap_shows_bedrooms_then_restores_rows(
    mt: MaestroTest, missing_state: str | None
) -> None:
    home.initialize_card()
    home.card.update(
        state="All Shut",
        blink=True,
        row_1_value="72° · 45%",
        row_1_icon=Icon.THERMOMETER,
        row_2_value="idle",
        row_2_icon=Icon.HVAC_OFF,
        row_3_value="6:30 AM",
        row_3_color=RowColor.RED,
    )
    mt.set_state(sensor.master_bedroom_temperature_sensor, "71.6")
    mt.set_state(sensor.master_bedroom_temperature_sensor_humidity, "42.3")
    mt.set_state(sensor.ellies_room_temperature_sensor_temperature, missing_state or "70.2")
    mt.set_state(sensor.ellies_room_temperature_sensor_humidity, "44.8")
    mt.set_state(sensor.olivias_room_temperature_sensor_temperature, "73.1")
    mt.set_state(sensor.olivias_room_temperature_sensor_humidity, missing_state or "47.7")
    mt.set_state(climate.thermostat, UNAVAILABLE)

    def check_display(seconds: float) -> None:
        assert seconds == 5
        assert home.bedroom_view_active()
        home.handle_double_tap()
        home.set_row_1()
        home.set_row_2()
        assert home.card.row_1_value == "72° · 42%"
        assert home.card.row_2_value == ("Offline" if missing_state else "70° · 45%")
        assert home.card.row_3_value == ("Offline" if missing_state else "73° · 48%")
        assert home.card.row_1_icon == Icon.HUMAN_MALE_FEMALE
        assert home.card.row_2_icon == Icon.HUMAN_FEMALE_DANCE
        assert home.card.row_3_icon == Icon.CRADLE
        assert home.card.row_3_color == RowColor.DEFAULT
        assert home.card.state == "All Shut"
        assert home.card.blink

    redis = home.card.state_manager.redis_client
    with (
        patch.object(home, "sleep", side_effect=check_display) as pause,
        patch.object(redis, "set", wraps=redis.set) as cache_set,
    ):
        mt.trigger_event(
            EventType.MAESTRO_UI_EVENT, data={"trigger": UIEvent.ENTITY_CARD_3_DOUBLE_TAP}
        )
    pause.assert_called_once()
    cache_set.assert_any_call(redis.build_key(home.BEDROOM_VIEW_CACHE_PREFIX), "1", ttl_seconds=5)

    assert home.card.row_1_value == "72° · 45%"
    assert home.card.row_1_icon == Icon.THERMOMETER
    assert home.card.row_2_value == "idle"
    assert home.card.row_2_icon == Icon.HVAC_OFF
    assert home.card.row_3_value == "6:30 AM"
    assert home.card.row_3_icon == Icon.DOG
    assert home.card.row_3_color == RowColor.RED
    assert home.card.blink
    assert not home.bedroom_view_active()
    home.set_row_1()
    home.set_row_2()
    assert home.card.row_1_value == "Offline"
    assert home.card.row_2_value == "Offline"


def test_interrupted_display_restores_reminder(mt: MaestroTest) -> None:
    home.initialize_card()
    home.card.update(row_3_value="6:30 AM", row_3_color=RowColor.RED)
    with (
        patch.object(home, "bedroom_environment", return_value="72° · 45%"),
        patch.object(home, "sleep", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        home.handle_double_tap()
    assert home.card.row_3_value == "6:30 AM"
    assert home.card.row_3_icon == Icon.DOG
    assert home.card.row_3_color == RowColor.RED
    assert not home.bedroom_view_active()
