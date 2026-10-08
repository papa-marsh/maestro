"""Next-game card rendering and Tigers/Lions selection."""

from datetime import datetime, timedelta
from unittest.mock import PropertyMock, patch
from zoneinfo import ZoneInfo

import pytest
from maestro.testing import MaestroTest

from custom_domains import GoogleCalendar
from registry import calendar
from scripts.common.balldontlie import InningHalf, LiveGameData
from scripts.common.balldontlie_nfl import NFLGameData

from .. import next_game

NOW = datetime(2026, 10, 11, 12, tzinfo=ZoneInfo("America/New_York"))


def lions_game(
    days: int = 0, status_state: str = "scheduled", status: str = "10/11 - 4:25 PM EDT"
) -> NFLGameData:
    return NFLGameData(
        start=NOW.replace(hour=16, minute=25) + timedelta(days=days),
        away_team="Detroit Lions",
        home_team="Green Bay Packers",
        status=status,
        status_state=status_state,
        away_score=0,
        home_score=7,
    )


def tigers_game(days: int = 0) -> GoogleCalendar.Event:
    start = NOW.replace(hour=19) + timedelta(days=days)
    return GoogleCalendar.Event(
        title="Detroit Tigers @ Cleveland Guardians",
        description="",
        start=start,
        end=start + timedelta(hours=3),
        calendar=calendar.detroit_tigers.id,
        location="",
        all_day=False,
    )


@pytest.mark.parametrize(
    ("days", "status_state", "status", "active", "blink", "bottom_row"),
    [
        (1, "scheduled", "10/12 - 4:25 PM EDT", False, False, "4:25 PM"),
        (0, "scheduled", "10/11 - 4:25 PM EDT", True, False, "4:25 PM"),
        (0, "scheduled", "TBD", True, False, "TBD"),
        (0, "in_progress", "3rd Qtr - 10:41", True, True, "0 - 7"),
        (0, "in_progress", "Halftime", True, True, "0 - 7"),
        (0, "final", "Final/OT", False, False, "0 - 7"),
        (-1, "in_progress", "Overtime", True, True, "0 - 7"),
    ],
)
def test_lions_display(
    mt: MaestroTest,
    days: int,
    status_state: str,
    status: str,
    active: bool,
    blink: bool,
    bottom_row: str,
) -> None:
    """Highlight game day, blink during play, and render local time or away/home scores."""
    game = lions_game(days, status_state, status)
    with mt.mock_datetime_as(NOW):
        next_game.initialize_card()
        next_game.update_card_lions(game)

    assert mt.get_attribute(next_game.card, "top_row", str) == "Detroit Lions @ Green Bay Packers"
    assert mt.get_attribute(next_game.card, "bottom_row", str) == bottom_row
    assert mt.get_attribute(next_game.card, "active", bool) is active
    assert mt.get_attribute(next_game.card, "blink", bool) is blink
    assert mt.get_attribute(next_game.card, "icon", str) == "mdi:football"
    assert (
        mt.get_attribute(next_game.card, "left_icon_path", str)
        == "/local/nfl_logos/Detroit Lions.png"
    )
    assert (
        mt.get_attribute(next_game.card, "right_icon_path", str)
        == "/local/nfl_logos/Green Bay Packers.png"
    )
    if status_state != "scheduled":
        assert mt.get_attribute(next_game.card, "middle_row", str) == status


@pytest.mark.parametrize(
    ("tigers_days", "lions_days", "expected_icon"),
    [
        (0, 0, "mdi:football"),
        (0, 1, "mdi:baseball"),
        (1, 0, "mdi:football"),
        (-1, 1, "mdi:football"),
    ],
)
def test_choose_earlier_date_with_lions_tiebreak(
    mt: MaestroTest, tigers_days: int, lions_days: int, expected_icon: str
) -> None:
    """Prefer Lions on same-day ties and ignore stale Tigers events."""
    with (
        mt.mock_datetime_as(NOW),
        patch.object(
            GoogleCalendar,
            "next_event",
            new_callable=PropertyMock,
            return_value=tigers_game(tigers_days),
        ),
        patch.object(next_game, "get_next_nfl_game", return_value=lions_game(lions_days)),
    ):
        next_game.initialize_card()
        next_game.update_card()

    assert mt.get_attribute(next_game.card, "icon", str) == expected_icon


def test_tigers_fallback_clears_football_blink(mt: MaestroTest) -> None:
    """Retain baseball behavior when NFL is unavailable without leaking its blink state."""
    with (
        mt.mock_datetime_as(NOW),
        patch.object(next_game, "get_next_nfl_game", return_value=None),
        patch.object(
            GoogleCalendar, "next_event", new_callable=PropertyMock, return_value=tigers_game()
        ),
    ):
        next_game.initialize_card()
        next_game.update_card_lions(lions_game(status_state="in_progress"))
        next_game.update_card()

    assert mt.get_attribute(next_game.card, "icon", str) == "mdi:baseball"
    assert mt.get_attribute(next_game.card, "blink", bool) is False
    assert mt.get_attribute(next_game.card, "active", bool) is False
    assert (
        mt.get_attribute(next_game.card, "left_icon_path", str)
        == "/local/mlb_logos/Detroit Tigers.png"
    )


def test_lions_without_tigers_calendar(mt: MaestroTest) -> None:
    """Render NFL when the baseball calendar has no usable event."""
    with (
        mt.mock_datetime_as(NOW),
        patch.object(next_game, "get_next_nfl_game", return_value=lions_game()),
    ):
        next_game.initialize_card()
        next_game.update_card()

    assert mt.get_attribute(next_game.card, "icon", str) == "mdi:football"


def test_no_games_clears_card(mt: MaestroTest) -> None:
    """Clear live presentation when neither team has a usable game."""
    with mt.mock_datetime_as(NOW), patch.object(next_game, "get_next_nfl_game", return_value=None):
        next_game.initialize_card()
        next_game.update_card_lions(lions_game(status_state="in_progress"))
        next_game.update_card()

    assert mt.get_attribute(next_game.card, "top_row", str) == "No upcoming games"
    assert mt.get_attribute(next_game.card, "active", bool) is False
    assert mt.get_attribute(next_game.card, "blink", bool) is False
    assert mt.get_attribute(next_game.card, "left_icon_path", str) == ""


def test_tigers_live_score_unchanged(mt: MaestroTest) -> None:
    """Continue displaying MLB inning and away/home score after adding football."""
    game = LiveGameData(
        away_runs=3, home_runs=2, status="STATUS_IN_PROGRESS", period=5, inning_half=InningHalf.TOP
    )
    with (
        mt.mock_datetime_as(NOW.replace(hour=20)),
        patch.object(next_game, "get_live_game", return_value=game),
    ):
        next_game.initialize_card()
        next_game.update_card_tigers(tigers_game())

    assert mt.get_attribute(next_game.card, "bottom_row", str) == "3 - 2"
    assert "Top 5" in mt.get_attribute(next_game.card, "middle_row", str)
    assert mt.get_attribute(next_game.card, "active", bool) is True
    assert mt.get_attribute(next_game.card, "blink", bool) is False
