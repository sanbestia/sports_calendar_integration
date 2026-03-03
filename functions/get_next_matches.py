from datetime import datetime, timezone

import pytz

from objects.Match import Match

import requests
import json

import os
from dotenv import load_dotenv

load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")


def get_next_matches(team_id: str, team_name: str, player_type: str, sport: str, time_zone: str) -> list[Match]:
    print(f"* Looking for games featuring {team_name}:\n")

    headers: dict[str, str] = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "allsportsapi2.p.rapidapi.com"
    }

    next_games: list[Match] = []

    events: list = []

    # Try with endpoint "next" (gets all future scheduled events)
    read_next_page: bool = True
    page: int = 0
    while read_next_page:
        url = (f"https://allsportsapi2.p.rapidapi.com/api/"
               f"{sport + '/' if sport != 'football' else ""}"
               f"{player_type}/"
               f"{team_id}/"
               f"{'events' if sport == 'tennis' else 'matches'}/"
               f"next/"
               f"{page}")

        try:
            request = requests.get(url, headers=headers)

        except (TimeoutError, ConnectionError) as e:
            print("Couldn't communicate with sports API")
            print(e)
            return []

        if page == 0 and not request.text:
            print("No upcoming games found with endpoint 'next'\n"
                  "Trying with endpoint 'near'\n")
            read_next_page = False

        else:
            request_dict = json.loads(request.text)

            if "events" not in request_dict:
                print(f"Request Error: 'events' key not found in\n"
                      f"{request_dict}")
                return []

            events += request_dict["events"]

            read_next_page = request_dict['hasNextPage']
            page += 1

    # If endpoint "next" doesn't work, try with endpoint "near" (only gets next event -and previous, ignored-)
    if not events:
        url = (f"https://allsportsapi2.p.rapidapi.com/api/"
               f"{sport + '/' if sport != 'football' else ''}"
               f"{player_type}/"
               f"{team_id}/"
               f"{'events' if sport == 'tennis' else 'matches'}/"
               f"near")

        try:
            request = requests.get(url, headers=headers)

        except (TimeoutError, ConnectionError) as e:
            print("Couldn't communicate with sports API")
            print(e)
            return []

        request_dict = json.loads(request.text)

        if "nextEvent" not in request_dict:
            print(f"Request Error: 'nextEvent' key not found in\n"
                  f"{request_dict}")
            return []

        if not request_dict["nextEvent"]:
            print("No upcoming games found using any endpoints\n")
            return []

        events.append(request_dict["nextEvent"])

    print("Got data:")
    for event in events:
        date_time = datetime.fromtimestamp(event['startTimestamp'], tz=timezone.utc)
        date_time = date_time.astimezone(pytz.timezone(time_zone))
        round_info = event.get('roundInfo')
        if round_info and 'name' not in round_info:
            round_info['name'] = f'Round {round_info['round']}'
        game = Match(
            side_one=event['homeTeam']['name'],
            side_two=event['awayTeam']['name'],
            tournament=event['season']['name'],
            stage=round_info['name'] if round_info else event['tournament']['name'],
            game_id=event['id'],
            sport=sport,
            start_time=date_time
        )

        print(game, time_zone)
        next_games.append(game)

    print()
    return next_games


def main():
    from tzlocal import get_localzone
    matches = []

    matches += get_next_matches(
        team_id="275923",
        team_name="Carlos Alcaraz",
        player_type="player",
        sport="tennis",
        time_zone=str(get_localzone()))

    matches += get_next_matches(
        team_id="24246",
        team_name="Argentina - Football U23 National Team",
        player_type="team",
        sport="football",
        time_zone=str(get_localzone()))

    matches += get_next_matches(
        team_id="3429",
        team_name="San Antonio Spurs",
        player_type="team",
        sport="basketball",
        time_zone=str(get_localzone()))

    for match in matches:
        print(match)


if __name__ == '__main__':
    main()
