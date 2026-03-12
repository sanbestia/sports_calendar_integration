import logging
import os
from datetime import datetime, timezone

import pytz
import requests

from objects.Match import Match
from objects.APICallTracker import APICallTracker
from functions.utils import sanitize_for_log
import json

logger = logging.getLogger(__name__)


def _build_api_url(sport: str, player_type: str, team_id: str, endpoint: str, page: int | None = None) -> str:
    """Build an AllSports API URL for the given sport, entity, and endpoint."""
    sport_segment = f"{sport}/" if sport != "football" else ""
    event_type = "events" if sport == "tennis" else "matches"
    url = f"https://allsportsapi2.p.rapidapi.com/api/{sport_segment}{player_type}/{team_id}/{event_type}/{endpoint}"
    if page is not None:
        url += f"/{page}"
    return url


def get_next_matches(team_id: str, team_name: str, player_type: str, sport: str, time_zone: str, tracker: APICallTracker) -> list[Match]:
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        raise ValueError("RAPIDAPI_KEY environment variable is not set")

    logger.info(f"Looking for games featuring {sanitize_for_log(team_name)}...")
    logger.info("")

    headers: dict[str, str] = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "allsportsapi2.p.rapidapi.com"
    }

    next_games: list[Match] = []
    events: list = []

    read_next_page: bool = True
    page: int = 0
    while read_next_page:
        url = _build_api_url(sport, player_type, team_id, "next", page)

        try:
            request = requests.get(url, headers=headers, timeout=10)
            tracker.increment()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.error(f"Couldn't communicate with sports API: {e}")
            return []

        if page == 0 and not request.text:
            logger.info("No upcoming games found with 'next' endpoint, trying 'near'...")
            read_next_page = False
        else:
            if not request.text:
                logger.error(f"Empty response on page {page} for {sanitize_for_log(team_name)}")
                return next_games
            try:
                request_dict = json.loads(request.text)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response on page {page} for {sanitize_for_log(team_name)}: {sanitize_for_log(request.text[:200])}")
                return next_games

            if "events" not in request_dict:
                logger.error(f"Request error: 'events' key not found in response: {sanitize_for_log(str(request_dict))}")
                return []

            events += request_dict["events"]
            read_next_page = request_dict['hasNextPage']
            page += 1

    if not events:
        url = _build_api_url(sport, player_type, team_id, "near")

        try:
            request = requests.get(url, headers=headers, timeout=10)
            tracker.increment()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.error(f"Couldn't communicate with sports API: {e}")
            return []

        if not request.text:
            logger.error(f"Empty response from 'near' endpoint for {sanitize_for_log(team_name)}")
            return []
        try:
            request_dict = json.loads(request.text)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response from 'near' endpoint for {sanitize_for_log(team_name)}: {sanitize_for_log(request.text[:200])}")
            return []

        if "nextEvent" not in request_dict:
            logger.error(f"Request error: 'nextEvent' key not found in response: {sanitize_for_log(str(request_dict))}")
            return []

        if not request_dict["nextEvent"]:
            logger.info("No upcoming games found using any endpoints")
            return []

        events.append(request_dict["nextEvent"])

    logger.info("Got data:")
    logger.info("")
    for event in events:
        date_time = datetime.fromtimestamp(event['startTimestamp'], tz=timezone.utc)
        date_time = date_time.astimezone(pytz.timezone(time_zone))
        round_info = event.get('roundInfo')
        if round_info and 'name' not in round_info:
            round_info['name'] = f'Round {round_info["round"]}'
        game = Match(
            side_one=event['homeTeam']['name'],
            side_two=event['awayTeam']['name'],
            tournament=event['season']['name'],
            stage=round_info['name'] if round_info else event['tournament']['name'],
            game_id=event['id'],
            sport=sport,
            start_time=date_time
        )

        logger.info(f"{sanitize_for_log(str(game))} ({sanitize_for_log(time_zone)})")
        next_games.append(game)

    return next_games