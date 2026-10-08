"""NFL schedule selection and API failure handling."""

from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest
import requests
from maestro.testing import MaestroTest

from .. import balldontlie_nfl

NOW = datetime(2026, 10, 11, 12, tzinfo=ZoneInfo("America/New_York"))


def game_response(date: str, status_state: str = "scheduled") -> balldontlie_nfl.NFLGameResponse:
    return {
        "date": date,
        "visitor_team": {"full_name": "Detroit Lions", "location": "Detroit"},
        "home_team": {"full_name": "Green Bay Packers", "location": "Green Bay"},
        "status": "Final" if status_state == "final" else "10/11 - 4:25 PM EDT",
        "status_state": status_state,
        "visitor_team_score": 0 if status_state == "final" else None,
        "home_team_score": 7 if status_state == "final" else None,
    }


def test_today_final_selected_in_local_timezone(
    mt: MaestroTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep a final through local game day even when its UTC date is tomorrow."""
    monkeypatch.setenv("BALLDONTLIE_API_KEY", "test-key")
    response = Mock()
    response.json.return_value = {
        "data": [
            game_response("2026-10-18T20:25:00Z"),
            game_response("2026-10-12T00:20:00Z", "final"),
            game_response("2026-10-04T20:25:00Z", "final"),
        ]
    }
    with (
        patch.object(balldontlie_nfl, "local_now", return_value=NOW),
        patch.object(balldontlie_nfl.requests, "get", return_value=response) as get,
    ):
        game = balldontlie_nfl.get_next_nfl_game(25)

    assert game is not None
    assert game.start == datetime(2026, 10, 11, 20, 20, tzinfo=NOW.tzinfo)
    assert game.away_score == 0
    assert game.home_score == 7
    assert game.away_team == "Detroit Lions"
    assert game.away_location == "Detroit"
    assert game.home_location == "Green Bay"
    assert game.status_state == "final"
    assert get.call_args.kwargs["headers"] == {"Authorization": "test-key"}
    assert get.call_args.kwargs["params"]["seasons[]"] == [2025, 2026, 2027]


@pytest.mark.parametrize(
    "status", ["final", "canceled", "postponed", "abandoned", "unknown", "scheduled"]
)
def test_skip_ineligible_games(
    mt: MaestroTest, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    """Skip past games and games whose lifecycle does not establish a playable date."""
    monkeypatch.setenv("BALLDONTLIE_API_KEY", "test-key")
    date = "2026-10-10T20:25:00Z" if status in {"final", "scheduled"} else "2026-10-11T20:25:00Z"
    response = Mock()
    response.json.return_value = {
        "data": [game_response(date, status), game_response("2026-10-18T20:25:00Z")]
    }
    with (
        patch.object(balldontlie_nfl, "local_now", return_value=NOW),
        patch.object(balldontlie_nfl.requests, "get", return_value=response),
    ):
        game = balldontlie_nfl.get_next_nfl_game(25)

    assert game is not None
    assert game.start.date().isoformat() == "2026-10-18"


def test_live_game_survives_midnight_and_pagination(
    mt: MaestroTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Find a game still playing after midnight, even on a later API page."""
    monkeypatch.setenv("BALLDONTLIE_API_KEY", "test-key")
    first = Mock()
    first.json.return_value = {
        "data": [game_response("2026-10-18T20:25:00Z")],
        "meta": {"next_cursor": 123},
    }
    second = Mock()
    second.json.return_value = {
        "data": [game_response("2026-10-11T00:20:00Z", "in_progress")],
        "meta": {"per_page": 100},
    }
    with (
        patch.object(balldontlie_nfl, "local_now", return_value=NOW),
        patch.object(balldontlie_nfl.requests, "get", side_effect=[first, second]),
    ):
        game = balldontlie_nfl.get_next_nfl_game(25)

    assert game is not None
    assert game.start.date().isoformat() == "2026-10-10"
    assert game.status_state == "in_progress"


@pytest.mark.parametrize("failure", [requests.Timeout(), requests.HTTPError(), ValueError()])
def test_api_failure_returns_none(
    mt: MaestroTest, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    """Let the card fall back safely on network, authorization, or JSON failures."""
    monkeypatch.setenv("BALLDONTLIE_API_KEY", "test-key")
    with patch.object(balldontlie_nfl.requests, "get", side_effect=failure):
        assert balldontlie_nfl.get_next_nfl_game(25) is None


def test_missing_key_returns_none(mt: MaestroTest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not make an unauthenticated request when the environment key is absent."""
    monkeypatch.delenv("BALLDONTLIE_API_KEY", raising=False)
    with patch.object(balldontlie_nfl.requests, "get") as get:
        assert balldontlie_nfl.get_next_nfl_game(25) is None
    get.assert_not_called()
