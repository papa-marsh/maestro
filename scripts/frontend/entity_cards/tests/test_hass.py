"""Home Assistant card uptime display."""

from datetime import timedelta

import pytest
from maestro.domains import UNAVAILABLE
from maestro.testing import MaestroTest
from maestro.utils import local_now

from registry import sensor

from .. import hass


@pytest.mark.parametrize(
    ("uptime", "expected_value"),
    [
        (timedelta(hours=24, minutes=59), "24 Hours"),
        (timedelta(hours=25), "1 Days"),
        (timedelta(hours=49, minutes=59), "2 Days"),
    ],
)
def test_uptime_display(
    mt: MaestroTest,
    uptime: timedelta,
    expected_value: str,
) -> None:
    """Display completed hours below 25 hours and completed days thereafter."""
    now = local_now().replace(hour=12, minute=0, second=0, microsecond=0)
    mt.set_state(sensor.uptime, (now - uptime).isoformat())

    with mt.mock_datetime_as(now):
        hass.initialize_card()
        hass.set_row_1()

    assert hass.card.row_1_value == expected_value


def test_resource_rows(mt: MaestroTest) -> None:
    """Show rounded CPU/memory and disk/swap pairs, or Offline when a sensor is unavailable."""
    mt.set_state(sensor.uptime, local_now().isoformat())
    mt.set_state(sensor.system_monitor_processor_use, "2")
    mt.set_state(sensor.system_monitor_memory_usage, "49.4")
    mt.set_state(sensor.system_monitor_disk_usage, "33.6")
    mt.set_state(sensor.system_monitor_swap_usage, UNAVAILABLE)

    hass.initialize_card()
    hass.set_resource_rows()

    assert hass.card.row_2_value == "2% · 49%"
    assert hass.card.row_3_value == "Offline"
