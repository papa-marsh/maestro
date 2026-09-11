"""Livi card duration display."""

from datetime import timedelta

import pytest
from maestro.testing import MaestroTest
from maestro.utils import local_now

from scripts.sleep_tracking.queries import save_sleep_event

from .. import livi


@pytest.mark.parametrize(
    ("current_seconds", "previous_seconds", "current_display", "previous_display"),
    [
        (0, 30, "0m", "0m"),
        (59.999, 59.999, "0m", "0m"),
        (60, 60, "1m", "1m"),
        (125, 125, "2m", "2m"),
        (7500, 7500, "2h 5m", "2h 5m"),
    ],
)
def test_card_duration_display(
    mt: MaestroTest,
    current_seconds: float,
    previous_seconds: float,
    current_display: str,
    previous_display: str,
) -> None:
    """Display sub-minute durations as zero minutes across all three rows."""
    now = local_now().replace(hour=12, minute=0, second=0, microsecond=0)
    asleep_at = now - timedelta(seconds=current_seconds)
    save_sleep_event(timestamp=asleep_at - timedelta(seconds=previous_seconds), wakeup=True)
    save_sleep_event(timestamp=asleep_at, wakeup=False)

    with mt.mock_datetime_as(now):
        livi.initialize_card()
        livi.update_card()

    mt.assert_state(livi.card, "Asleep")
    assert livi.card.row_1_value == current_display
    assert livi.card.row_2_value == previous_display
    assert livi.card.row_3_value == previous_display
