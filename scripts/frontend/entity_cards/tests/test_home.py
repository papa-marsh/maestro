"""Home card bedroom climate display and normal-row restoration."""

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import pytest
from flask import current_app
from maestro.domains import UNAVAILABLE, UNKNOWN
from maestro.testing import MaestroTest

from registry import sensor
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

    def check_display(seconds: float) -> None:
        assert seconds == 5
        home.handle_double_tap()
        assert home.card.row_1_value == "72° · 42%"
        assert home.card.row_2_value == ("Offline" if missing_state else "70° · 45%")
        assert home.card.row_3_value == ("Offline" if missing_state else "73° · 48%")
        assert home.card.row_1_icon == Icon.HUMAN_MALE_FEMALE
        assert home.card.row_2_icon == Icon.HUMAN_FEMALE_GIRL
        assert home.card.row_3_icon == Icon.BABY_FACE_OUTLINE
        assert home.card.row_3_color == RowColor.DEFAULT
        assert home.card.state == "All Shut"
        assert home.card.blink

    with patch.object(home, "sleep", side_effect=check_display) as pause:
        mt.trigger_event(
            EventType.MAESTRO_UI_EVENT, data={"trigger": UIEvent.ENTITY_CARD_3_DOUBLE_TAP}
        )
    pause.assert_called_once()

    assert home.card.row_1_value == "72° · 45%"
    assert home.card.row_1_icon == Icon.THERMOMETER
    assert home.card.row_2_value == "idle"
    assert home.card.row_2_icon == Icon.HVAC_OFF
    assert home.card.row_3_value == "6:30 AM"
    assert home.card.row_3_icon == Icon.DOG
    assert home.card.row_3_color == RowColor.RED
    assert home.card.blink


def test_feeding_update_during_alternate_view_is_preserved(mt: MaestroTest) -> None:
    home.initialize_card()
    home.card.update(row_3_value="6:30 AM", row_3_color=RowColor.RED)
    app_context = current_app.app_context
    update_started = Event()
    updates: list[Future[None]] = []
    feeding_time = home.local_now().strftime("%-I:%M %p")

    def feed_chelsea() -> None:
        with app_context():
            update_started.set()
            home.set_row_3()

    with ThreadPoolExecutor(max_workers=1) as executor:

        def check_display(seconds: float) -> None:
            updates.append(executor.submit(feed_chelsea))
            assert update_started.wait(timeout=1)
            assert home.card.row_3_icon == Icon.BABY_FACE_OUTLINE

        with (
            patch.object(home, "bedroom_environment", return_value="72° · 45%"),
            patch.object(home, "sleep", side_effect=check_display),
        ):
            home.handle_double_tap()

    updates[0].result()
    assert home.card.row_3_value == feeding_time
    assert home.card.row_3_icon == Icon.DOG
    assert home.card.row_3_color == RowColor.DEFAULT


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
