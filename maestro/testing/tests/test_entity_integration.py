"""
Tests for Entity object integration with the testing framework.
Verifies that Entity objects automatically use mocks and work seamlessly in tests.
"""

from maestro.domains import BinarySensor, Switch
from maestro.domains.entity import OFF, ON
from maestro.integrations.home_assistant.domain import Domain
from maestro.testing.maestro_test import MaestroTest


def test_entity_auto_uses_mock_state_manager(mt: MaestroTest) -> None:
    """Test that entities automatically use the mock state manager"""
    switch = Switch("switch.test_switch")

    mt.set_state("switch.test_switch", OFF)

    assert switch.state == OFF
    assert switch.state_manager.redis_client is mt.redis_client


def test_entity_methods_are_tracked_automatically(mt: MaestroTest) -> None:
    """Test that entity action methods are automatically tracked"""
    switch = Switch("switch.test_switch")
    mt.set_state("switch.test_switch", OFF)

    switch.turn_on()

    mt.assert_action_called(Domain.SWITCH, "turn_on")


def test_entity_state_access_without_manual_mocking(mt: MaestroTest) -> None:
    """Test that entity state/attribute access works without manual setup"""
    switch = Switch("switch.bedroom")
    mt.set_state("switch.bedroom", ON, {"power_usage": 50})

    assert switch.state == ON

    power = mt.get_attribute(switch, "power_usage", int)
    assert power == 50


def test_multiple_entities_use_same_mock(mt: MaestroTest) -> None:
    """Test that multiple entities all use the same mock state manager"""
    sensor = BinarySensor("binary_sensor.motion")
    switch = Switch("switch.fan")

    mt.set_state("binary_sensor.motion", OFF)
    mt.set_state("switch.fan", OFF)

    assert sensor.state_manager.hass_client is switch.state_manager.hass_client
    assert sensor.state_manager.redis_client is mt.redis_client

    switch.turn_on()
    switch.turn_off()

    switch_calls = mt.get_action_calls(domain=Domain.SWITCH)
    assert len(switch_calls) == 2
