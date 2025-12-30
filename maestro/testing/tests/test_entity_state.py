"""
Tests for entity state management in the testing framework.
Verifies that setting, getting, and asserting entity state and attributes works correctly.
"""

from contextlib import suppress

import pytest

from maestro.domains.entity import OFF, ON
from maestro.testing.maestro_test import MaestroTest
from maestro.utils.dates import local_now
from maestro.utils.exceptions import MockEntityDoesNotExistError


def test_set_and_get_state(mt: MaestroTest) -> None:
    """Test basic state setting and retrieval"""
    mt.set_state("light.bedroom", ON)
    state = mt.get_state("light.bedroom")
    assert state == ON

    mt.set_state("light.bedroom", OFF)
    state = mt.get_state("light.bedroom")
    assert state == OFF


def test_set_state_with_attributes(mt: MaestroTest) -> None:
    """Test setting state with attributes"""
    mt.set_state("light.bedroom", ON, {"brightness": 255})
    brightness = mt.get_attribute("light.bedroom", "brightness", int)
    assert brightness == 255


def test_assert_state(mt: MaestroTest) -> None:
    """Test state assertion helper"""
    mt.set_state("light.bedroom", ON)
    mt.assert_state("light.bedroom", ON)


def test_assert_attribute(mt: MaestroTest) -> None:
    """Test attribute assertion helper"""
    mt.set_state("light.bedroom", ON, {"brightness": 255})
    mt.assert_attribute("light.bedroom", "brightness", 255)


def test_set_attribute(mt: MaestroTest) -> None:
    """Test modifying an entity attribute after creation"""
    mt.set_state("light.bedroom", ON, {"brightness": 100})
    mt.set_attribute("light.bedroom", "brightness", 255)
    brightness = mt.get_attribute("light.bedroom", "brightness", int)
    assert brightness == 255


def test_multiple_entities(mt: MaestroTest) -> None:
    """Test managing state for multiple entities simultaneously"""
    mt.set_state("light.bedroom", ON)
    mt.set_state("light.kitchen", OFF)
    mt.set_state("switch.fan", OFF)

    mt.assert_state("light.bedroom", ON)
    mt.assert_state("light.kitchen", OFF)
    mt.assert_state("switch.fan", OFF)


def test_entity_with_complex_attributes(mt: MaestroTest) -> None:
    """Test entities with various attribute types (str, int, datetime, list, dict)"""
    now = local_now()
    mt.set_state(
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

    unit = mt.get_attribute("sensor.temperature", "unit", str)
    assert unit == "°F"

    battery = mt.get_attribute("sensor.temperature", "battery", int)
    assert battery == 90

    sensors = mt.get_attribute("sensor.temperature", "sensors", list)
    assert sensors == ["indoor", "outdoor"]


def test_assert_entity_exists(mt: MaestroTest) -> None:
    """Test assert_entity_exists passes when entity exists"""
    with pytest.raises(AssertionError):
        mt.assert_entity_exists("light.bedroom")

    mt.set_state("light.bedroom", ON)
    mt.assert_entity_exists("light.bedroom")


def test_assert_entity_does_not_exist(mt: MaestroTest) -> None:
    """Test assert_entity_does_not_exist passes when entity doesn't exist"""
    mt.assert_entity_does_not_exist("light.nonexistent")

    mt.set_state("light.bedroom", ON)
    with pytest.raises(AssertionError):
        mt.assert_entity_does_not_exist("light.bedroom")


def test_reset_clears_state(mt: MaestroTest) -> None:
    """Test that reset clears all entity state"""
    mt.set_state("light.bedroom", ON)

    mt.reset()

    with suppress(MockEntityDoesNotExistError):
        mt.get_state("light.bedroom")
        assert False, "Expected MockEntityDoesNotExistError for missing entity"
