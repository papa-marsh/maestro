"""
Tests for action call tracking and assertions in the testing framework.
Verifies that performed actions are recorded and can be asserted against.
"""

from maestro.domains.entity import OFF, ON
from maestro.integrations.home_assistant.domain import Domain
from maestro.testing.maestro_test import MaestroTest


def test_mock_client_action_tracking(mt: MaestroTest) -> None:
    """Test that mock client tracks action calls"""
    mt.set_state("light.bedroom", OFF)

    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
        brightness=255,
    )

    mt.assert_action_called(
        Domain.LIGHT,
        "turn_on",
        entity_id="light.bedroom",
        brightness=255,
    )


def test_action_call_filtering(mt: MaestroTest) -> None:
    """Test filtering action calls by various criteria"""
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_off",
        entity_id="light.kitchen",
    )
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_off",
        entity_id="light.kitchen",
    )
    mt.hass_client.perform_action(
        domain=Domain.SWITCH,
        action="turn_on",
        entity_id="switch.fan",
    )

    light_calls = mt.get_action_calls(domain=Domain.LIGHT)
    assert len(light_calls) == 3

    turn_on_calls = mt.get_action_calls(action="turn_on")
    assert len(turn_on_calls) == 2

    bedroom_calls = mt.get_action_calls(entity_id="light.bedroom")
    assert len(bedroom_calls) == 1


def test_clear_action_calls(mt: MaestroTest) -> None:
    """Test clearing action call history"""
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    mt.assert_action_called(Domain.LIGHT, "turn_on")

    mt.clear_action_calls()

    mt.assert_action_not_called(Domain.LIGHT, "turn_on")


def test_assert_action_not_called(mt: MaestroTest) -> None:
    """Test asserting that an action was NOT called"""
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    mt.assert_action_not_called(Domain.LIGHT, "turn_off")


def test_assert_action_times(mt: MaestroTest) -> None:
    """Test asserting specific number of action calls"""
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    mt.assert_action_called(Domain.LIGHT, "turn_on", call_count=2)


def test_reset_clears_actions(mt: MaestroTest) -> None:
    """Test that reset clears action call history"""
    mt.hass_client.perform_action(
        domain=Domain.LIGHT,
        action="turn_on",
        entity_id="light.bedroom",
    )

    mt.reset()

    mt.assert_action_not_called(Domain.LIGHT, "turn_on")
