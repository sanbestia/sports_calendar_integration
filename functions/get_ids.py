import logging
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

logger = logging.getLogger(__name__)


def get_ids(tracker=None) -> dict[str, dict[str, str]]:
    id_dict: dict[str, dict[str, str]] = dict()
    while True:
        name: str = input(f"Enter player/team name: ")
        sport: str = input("Enter sport to look for: ")

        url: str = (f"https://allsportsapi2.p.rapidapi.com/api/"
               f"{'' if sport.lower() == 'football' else sport.lower() + '/'}"
               f"search/"
               f"{name.lower()}")

        headers: dict[str, str] = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "allsportsapi2.p.rapidapi.com"
        }

        logger.info("Looking for players/teams...")

        try:
            request: requests.Response = requests.get(url, headers=headers)
            if tracker:
                tracker.increment()
        except (TimeoutError, ConnectionError) as e:
            logger.error(f"Couldn't communicate with sports API: {e}")
            continue

        if not request.text:
            logger.info("No player/team found with that name, try again")
            continue

        hits: list[filter] = list(filter(lambda result: result['type'] == 'team', json.loads(request.text)['results']))
        chosen: int = 0

        if len(hits) > 1:
            logger.info("Multiple hits found:")
            for order, hit in enumerate(hits):
                team_name: str = " ".join(x.capitalize() for x in hit["entity"]["slug"].split("-"))
                team_gender: str = hit["entity"].get("gender")
                logger.info(f'  {order + 1}: {team_name} {"(" + team_gender + ")" if team_gender else ""}')
            chosen = int(input("Type the number associated to the correct option: ")) - 1

        print()
        confirmed: str = input(f'{hits[chosen]["entity"]["name"]} added to the search list. Is this correct? Y/N: ')
        if confirmed.upper() == 'Y':
            id_dict[str(hits[chosen]["entity"]["id"])] = {
                "name": hits[chosen]["entity"]["name"],
                "sport": sport
            }
        else:
            logger.info("Choice discarded")

        if input(f'Search for another player/team? Y/N: ').upper() == "N":
            return id_dict

        print()


def main():
    print(get_ids())


if __name__ == '__main__':
    main()