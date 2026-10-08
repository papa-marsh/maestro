import os
from dataclasses import dataclass
from datetime import datetime
from typing import NotRequired, TypedDict, cast

import requests
from maestro.utils import local_now, log

BASE_URL = "https://api.balldontlie.io/nfl/v1"
DETROIT_LIONS_TEAM_ID = 25


class NFLTeamResponse(TypedDict):
    full_name: str


class NFLGameResponse(TypedDict):
    date: str
    visitor_team: NFLTeamResponse
    home_team: NFLTeamResponse
    status: str
    status_state: str
    visitor_team_score: int | None
    home_team_score: int | None


class NFLGamesResponse(TypedDict):
    data: list[NFLGameResponse]
    meta: NotRequired[dict[str, int | None]]


@dataclass
class NFLGameData:
    start: datetime
    away_team: str
    home_team: str
    status: str
    status_state: str
    away_score: int | None
    home_score: int | None


def get_next_nfl_game(team_id: int) -> NFLGameData | None:
    """Fetch today's or the next scheduled game, including a game still in progress."""
    api_key = os.environ.get("BALLDONTLIE_API_KEY")
    if not api_key:
        log.warning("BALLDONTLIE_API_KEY is not configured")
        return None

    now = local_now()
    params: dict[str, str | int | list[int]] = {
        "team_ids[]": team_id,
        # NFL seasons extend into the following calendar year.
        "seasons[]": [now.year - 1, now.year, now.year + 1],
        "per_page": 100,
    }
    games: list[NFLGameData] = []
    try:
        while True:
            response = requests.get(
                f"{BASE_URL}/games",
                params=params,
                headers={"Authorization": api_key},
                timeout=30,
            )
            response.raise_for_status()
            data = cast(NFLGamesResponse, response.json())
            for game in data["data"]:
                start = datetime.fromisoformat(game["date"]).astimezone(now.tzinfo)
                status_state = game["status_state"]
                if status_state in {"canceled", "postponed", "abandoned", "unknown"}:
                    continue
                if start.date() < now.date() and status_state not in {"in_progress", "suspended"}:
                    continue
                games.append(
                    NFLGameData(
                        start=start,
                        away_team=game["visitor_team"]["full_name"],
                        home_team=game["home_team"]["full_name"],
                        status=game["status"],
                        status_state=status_state,
                        away_score=game["visitor_team_score"],
                        home_score=game["home_team_score"],
                    )
                )
            cursor = data.get("meta", {}).get("next_cursor")
            if cursor is None:
                break
            params["cursor"] = cursor
    except requests.RequestException, ValueError, KeyError, TypeError:
        log.exception("Failed to fetch NFL game data from balldontlie", team_id=team_id)
        return None

    return min(games, key=lambda game: game.start, default=None)
