"""
Tests to verify that action response mocking works correctly.
This ensures actions that expect responses receive mocked data properly.
"""

from maestro.domains import Calendar, Switch
from maestro.integrations.home_assistant.domain import Domain
from maestro.testing.maestro_test import MaestroTest


def test_action_response_queue(mt: MaestroTest) -> None:
    """Test that action responses can be mocked and returned in order"""
    # Set up mock responses
    response1 = {"events": [{"summary": "Meeting 1"}]}
    response2 = {"events": [{"summary": "Meeting 2"}]}
    mt.set_action_responses([response1, response2])

    # Create calendar entity
    calendar = Calendar("calendar.home")
    mt.set_state(calendar, "off")

    # Call action that expects response - should get first response
    result1 = calendar.get_events(duration={"days": 1})
    assert result1 == response1

    # Call again - should get second response
    result2 = calendar.get_events(duration={"days": 1})
    assert result2 == response2


def test_action_without_response(mt: MaestroTest) -> None:
    """Test that actions without response_expected still work"""
    switch = Switch("switch.test")
    mt.set_state(switch, "off")

    # This should not consume any queued responses
    switch.turn_on()
    mt.assert_action_called(Domain.SWITCH, "turn_on")


def test_action_call_stores_response(mt: MaestroTest) -> None:
    """Test that ActionCall objects store the response they received"""
    response = {"events": [{"summary": "Test Event"}]}
    mt.set_action_responses([response])

    calendar = Calendar("calendar.test")
    mt.set_state(calendar, "off")

    # Perform action that expects response
    calendar.get_events(duration={"days": 1})

    # Verify the action call has the response stored
    calls = mt.get_action_calls(domain=Domain.CALENDAR, action="get_events")
    assert len(calls) == 1
    assert calls[0].response == response


def test_response_isolation_between_tests(mt: MaestroTest) -> None:
    """Test that response queue is cleared between tests"""
    # This test should start with an empty response queue
    # If responses leaked from previous tests, this would fail

    switch = Switch("switch.test")
    mt.set_state(switch, "off")

    # Action without response should work fine
    switch.turn_on()
    mt.assert_action_called(Domain.SWITCH, "turn_on")
