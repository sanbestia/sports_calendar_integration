import logging
import os
from datetime import datetime, timezone

import pytz
from dotenv import load_dotenv

from objects.Match import Match
import requests
import json

load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

logger = logging.getLogger(__name__)


def get_next_matches(team_id: str, team_name: str, player_type: str, sport: str, time_zone: str, tracker=None) -> list[Match]:
    logger.info(f"Looking for games featuring {team_name}...\n")

    headers: dict[str, str] = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "allsportsapi2.p.rapidapi.com"
    }

    next_games: list[Match] = []
    events: list = []

    read_next_page: bool = True
    page: int = 0
    while read_next_page:
        url = (f"https://allsportsapi2.p.rapidapi.com/api/"
               f"{sport + '/' if sport != 'football' else ''}"
               f"{player_type}/"
               f"{team_id}/"
               f"{'events' if sport == 'tennis' else 'matches'}/"
               f"next/"
               f"{page}")

        try:
            request = requests.get(url, headers=headers)
            if tracker:
                tracker.increment()
        except (TimeoutError, ConnectionError) as e:
            logger.error(f"Couldn't communicate with sports API: {e}")
            return []

        if page == 0 and not request.text:
            logger.info("No upcoming games found with 'next' endpoint, trying 'near'...")
            read_next_page = False
        else:
            if not request.text:
                logger.error(f"Empty response on page {page} for {team_name}")
                return next_games
            request_dict = json.loads(request.text)

            if "events" not in request_dict:
                logger.error(f"Request error: 'events' key not found in response: {request_dict}")
                return []

            events += request_dict["events"]
            read_next_page = request_dict['hasNextPage']
            page += 1

    if not events:
        url = (f"https://allsportsapi2.p.rapidapi.com/api/"
               f"{sport + '/' if sport != 'football' else ''}"
               f"{player_type}/"
               f"{team_id}/"
               f"{'events' if sport == 'tennis' else 'matches'}/"
               f"near")

        try:
            request = requests.get(url, headers=headers)
            if tracker:
                tracker.increment()
        except (TimeoutError, ConnectionError) as e:
            logger.error(f"Couldn't communicate with sports API: {e}")
            return []

        if not request.text:
            logger.error(f"Empty response from 'near' endpoint for {team_name}")
            return []

        request_dict = json.loads(request.text)

        if "nextEvent" not in request_dict:
            logger.error(f"Request error: 'nextEvent' key not found in response: {request_dict}")
            return []

        if not request_dict["nextEvent"]:
            logger.info("No upcoming games found using any endpoints")
            return []

        events.append(request_dict["nextEvent"])

    logger.info("Got data:\n")
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

        logger.info(f"{game} ({time_zone})")
        next_games.append(game)

    logger.info("")  
    
    return next_games