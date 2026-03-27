import logging
import os
from datetime import datetime, timezone

import pytz
import requests

from objects.Match import Match
from objects.APICallTracker import APICallTracker
from objects.schemas import NextPageResponse, NearResponse
from functions.utils import sanitize_for_log
import json

logger = logging.getLogger(__name__)


def _build_api_url(sport: str, player_type: str, team_id: str, endpoint: str, page: int | None = None) -> str:
    """Build an AllSports API URL for the given sport, entity, and endpoint."""
    sport_segment = f"{sport}/" if sport != "football" else ""  # football is the AllSports API default — no sport prefix in the URL path
    event_type = "events" if sport == "tennis" else "matches"  # the API uses 'events' for tennis and 'matches' for all other sports
    url = f"https://allsportsapi2.p.rapidapi.com/api/{sport_segment}{player_type}/{team_id}/{event_type}/{endpoint}"
    if page is not None:
        url += f"/{page}"
    return url


def _get_stage(round_info: dict | None, fallback: str) -> str:
    """Resolve the match stage from round info, synthesising a name from the round number if needed."""
    if round_info and round_info.get('name'):
        return round_info['name']
    if round_info and round_info.get('round') is not None:
        return f'Round {round_info["round"]}'
    return fallback


def get_next_matches(team_id: str, team_name: str, player_type: str, sport: str, time_zone: str, tracker: APICallTracker) -> list[Match]:
    """Fetch upcoming matches for a team from the AllSports API and return them as Match objects."""
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

    page: int = 0
    while True:
        url = _build_api_url(sport, player_type, team_id, "next", page)

        try:
            request = requests.get(url, headers=headers, timeout=10)
            tracker.increment()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.error(f"Couldn't communicate with sports API: {e}")
            return []

        if page == 0 and not request.text:  # empty body on page 0 means zero results; on later pages it would be an error
            logger.info("No upcoming games found with 'next' endpoint, trying 'near'...")
            break

        if not request.text:
            logger.error(f"Empty response on page {page} for {sanitize_for_log(team_name)}")
            return []
        try:
            request_dict = json.loads(request.text)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response on page {page} for {sanitize_for_log(team_name)}: {sanitize_for_log(request.text[:200])}")
            return []

        try:
            parsed = NextPageResponse.model_validate(request_dict)
        except Exception as e:
            logger.error(f"Unexpected response structure on page {page} for {sanitize_for_log(team_name)}: {e}")
            return []

        events += [e.model_dump() for e in parsed.events]  # convert back to dict; subsequent code uses raw key access like event['homeTeam']
        if not parsed.hasNextPage:
            break
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

        try:
            parsed = NearResponse.model_validate(request_dict)
        except Exception as e:
            logger.error(f"Unexpected response structure from 'near' endpoint for {sanitize_for_log(team_name)}: {e}")
            return []

        if not parsed.nextEvent:
            logger.info("No upcoming games found using any endpoints")
            return []

        events += [e.model_dump() for e in parsed.nextEvent]  # convert to dict; same reason as in the paginated path above

    logger.info("Got data:")
    logger.info("")
    for event in events:
        if event.get('status', {}).get('type') == 'canceled':
            logger.info(f"Skipping cancelled match: {sanitize_for_log(event['homeTeam']['name'])} vs {sanitize_for_log(event['awayTeam']['name'])}")
            continue

        date_time = datetime.fromtimestamp(event['startTimestamp'], tz=timezone.utc)
        date_time = date_time.astimezone(pytz.timezone(time_zone))
        round_info = event.get('roundInfo')
        game = Match(
            side_one=event['homeTeam']['name'],
            side_two=event['awayTeam']['name'],
            tournament=event['season']['name'],
            stage=_get_stage(round_info, event['tournament']['name']),
            game_id=event['id'],
            sport=sport,
            start_time=date_time,
            home_team_id=event['homeTeam']['id'],
            away_team_id=event['awayTeam']['id'],
        )

        logger.info(f"{sanitize_for_log(str(game))} ({sanitize_for_log(time_zone)})")
        next_games.append(game)

    return next_games