from contextlib import suppress

import pytest

from maestro.domains import BinarySensor, Switch
from maestro.domains.entity import OFF, ON
from maestro.integrations.home_assistant.domain import Domain
from maestro.testing.maestro_test import MaestroTest
from maestro.utils.dates import local_now
from maestro.utils.exceptions import MockEntityDoesNotExistError


def test_set_and_get_state(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", ON)
    state = maestro_test.get_state("light.bedroom")
    assert state == ON

    maestro_test.set_state("light.bedroom", OFF)
    state = maestro_test.get_state("light.bedroom")
    assert state == OFF


def test_set_state_with_attributes(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", ON, {"brightness": 255})
    brightness = maestro_test.get_attribute("light.bedroom", "brightness", int)
    assert brightness == 255


def test_mock_client_action_tracking(maestro_test: MaestroTest) -> None:
    """Test that mock client tracks action calls"""
    maestro_test.set_state("light.bedroom", OFF)

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
        action="turn_off",
        entity_id="light.kitchen",
    )
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

    light_calls = maestro_test.get_action_calls(domain=Domain.LIGHT)
    assert len(light_calls) == 3

    turn_on_calls = maestro_test.get_action_calls(action="turn_on")
    assert len(turn_on_calls) == 2

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
    maestro_test.set_state("light.bedroom", ON)
    maestro_test.assert_state("light.bedroom", ON)


def test_assert_attribute(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", ON, {"brightness": 255})
    maestro_test.assert_attribute("light.bedroom", "brightness", 255)


def test_reset_clears_state_and_actions(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", ON)
    maestro_test.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    maestro_test.reset()

    with suppress(MockEntityDoesNotExistError):
        maestro_test.get_state("light.bedroom")
        assert False, "Expected ValueError for missing entity"

    maestro_test.assert_action_not_called(Domain.LIGHT, "turn_on")


def test_set_attribute(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", ON, {"brightness": 100})
    maestro_test.set_attribute("light.bedroom", "brightness", 255)
    brightness = maestro_test.get_attribute("light.bedroom", "brightness", int)
    assert brightness == 255


def test_multiple_entities(maestro_test: MaestroTest) -> None:
    maestro_test.set_state("light.bedroom", ON)
    maestro_test.set_state("light.kitchen", OFF)
    maestro_test.set_state("switch.fan", OFF)

    maestro_test.assert_state("light.bedroom", ON)
    maestro_test.assert_state("light.kitchen", OFF)
    maestro_test.assert_state("switch.fan", OFF)


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


def test_entity_auto_uses_mock_state_manager(maestro_test: MaestroTest) -> None:
    """Test that entities automatically use the mock state manager"""

    switch = Switch("switch.test_switch")

    maestro_test.set_state("switch.test_switch", OFF)

    assert switch.state == OFF
    assert switch.state_manager.redis_client is maestro_test.redis_client


def test_entity_methods_are_tracked_automatically(maestro_test: MaestroTest) -> None:
    """Test that entity action methods are automatically tracked"""

    switch = Switch("switch.test_switch")
    maestro_test.set_state("switch.test_switch", OFF)

    switch.turn_on()

    maestro_test.assert_action_called(Domain.SWITCH, "turn_on")


def test_entity_state_access_without_manual_mocking(maestro_test: MaestroTest) -> None:
    """Test that entity state/attribute access works without manual setup"""

    switch = Switch("switch.bedroom")
    maestro_test.set_state("switch.bedroom", ON, {"power_usage": 50})

    assert switch.state == ON

    power = maestro_test.get_attribute(switch, "power_usage", int)
    assert power == 50


def test_multiple_entities_use_same_mock(maestro_test: MaestroTest) -> None:
    """Test that multiple entities all use the same mock state manager"""

    sensor = BinarySensor("binary_sensor.motion")
    switch = Switch("switch.fan")

    maestro_test.set_state("binary_sensor.motion", OFF)
    maestro_test.set_state("switch.fan", OFF)

    assert sensor.state_manager.hass_client is switch.state_manager.hass_client
    assert sensor.state_manager.redis_client is maestro_test.redis_client

    switch.turn_on()
    switch.turn_off()

    switch_calls = maestro_test.get_action_calls(domain=Domain.SWITCH)
    assert len(switch_calls) == 2


def test_assert_entity_exists(maestro_test: MaestroTest) -> None:
    """Test assert_entity_exists passes when entity exists"""
    with pytest.raises(AssertionError):
        maestro_test.assert_entity_exists("light.bedroom")

    maestro_test.set_state("light.bedroom", ON)
    maestro_test.assert_entity_exists("light.bedroom")


def test_assert_entity_does_not_exist(maestro_test: MaestroTest) -> None:
    """Test assert_entity_does_not_exist passes when entity doesn't exist"""
    maestro_test.assert_entity_does_not_exist("light.nonexistent")

    maestro_test.set_state("light.bedroom", ON)
    with pytest.raises(AssertionError):
        maestro_test.assert_entity_does_not_exist("light.bedroom")
