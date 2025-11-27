from contextlib import suppress

from maestro.integrations.home_assistant.domain import Domain
from maestro.testing import MaestroTest
from maestro.utils import local_now


def test_set_and_get_state(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", "off")
    state = maestro_test.get_state("light.bedroom")
    assert state == "off"


def test_set_state_with_attributes(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", "on", {"brightness": 255})
    brightness = maestro_test.get_attribute("light.bedroom", "brightness", int)
    assert brightness == 255


def test_mock_client_action_tracking(maestro_test: MaestroTest) -> None:
    """Test that mock client tracks action calls"""
    maestro_test.set_state("light.bedroom", "off")

    maestro_test.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
        brightness=255,
    )

    maestro_test.assert_action_called(
        Domain.LIGHT,
        "turn_on",
        entity_id="light.bedroom",
        brightness=255,
    )


def test_action_call_filtering(maestro_test: MaestroTest) -> None:
    """Test filtering action calls by various criteria"""
    maestro_test.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )
    maestro_test.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_off",
        entity_id="light.kitchen",
    )
    maestro_test.hass_client.perform_action(
        domain=Domain.SWITCH,
        action="turn_on",
        entity_id="switch.fan",
    )

    # Filter by domain
    light_calls = maestro_test.get_action_calls(domain=Domain.LIGHT)
    assert len(light_calls) == 2

    # Filter by action
    turn_on_calls = maestro_test.get_action_calls(action="turn_on")
    assert len(turn_on_calls) == 2

    # Filter by entity_id
    bedroom_calls = maestro_test.get_action_calls(entity_id="light.bedroom")
    assert len(bedroom_calls) == 1


def test_clear_action_calls(maestro_test: MaestroTest) -> None:
    maestro_test.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    maestro_test.assert_action_called(Domain.LIGHT, "turn_on")

    maestro_test.clear_action_calls()

    maestro_test.assert_action_not_called(Domain.LIGHT, "turn_on")


def test_assert_action_not_called(maestro_test: MaestroTest) -> None:
    maestro_test.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    maestro_test.assert_action_not_called(Domain.LIGHT, "turn_off")


def test_assert_action_times(maestro_test: MaestroTest) -> None:
    maestro_test.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )
    maestro_test.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    maestro_test.assert_action_called(Domain.LIGHT, "turn_on", call_count=2)


def test_assert_state(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", "on")
    maestro_test.assert_state("light.bedroom", "on")


def test_assert_attribute(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", "on", {"brightness": 255})
    maestro_test.assert_attribute("light.bedroom", "brightness", 255)


def test_reset_clears_state_and_actions(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", "on")
    maestro_test.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    maestro_test.reset()

    with suppress(ValueError):
        maestro_test.get_state("light.bedroom")
        assert False, "Expected ValueError for missing entity"

    maestro_test.assert_action_not_called(Domain.LIGHT, "turn_on")


def test_set_attribute(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", "on", {"brightness": 100})
    maestro_test.set_attribute("light.bedroom", "brightness", 255)
    brightness = maestro_test.get_attribute("light.bedroom", "brightness", int)
    assert brightness == 255


def test_multiple_entities(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", "on")
    maestro_test.set_state("light.kitchen", "off")
    maestro_test.set_state("switch.fan", "off")

    maestro_test.assert_state("light.bedroom", "on")
    maestro_test.assert_state("light.kitchen", "off")
    maestro_test.assert_state("switch.fan", "off")


def test_entity_with_complex_attributes(maestro_test: MaestroTest) -> None:
    now = local_now()
    maestro_test.set_state(
        "sensor.temperature",
        "72",
        {
            "unit": "°F",
            "battery": 90,
            "last_updated": now,
            "sensors": ["indoor", "outdoor"],
            "metadata": {"location": "bedroom"},
        },
    )

    unit = maestro_test.get_attribute("sensor.temperature", "unit", str)
    assert unit == "°F"

    battery = maestro_test.get_attribute("sensor.temperature", "battery", int)
    assert battery == 90

    sensors = maestro_test.get_attribute("sensor.temperature", "sensors", list)
    assert sensors == ["indoor", "outdoor"]
