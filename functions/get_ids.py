import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")


def get_ids() -> dict[str, dict[str, str]]:
    id_dict: dict[str, dict[str, str]] = dict()
    while True:
        name: str = input(f"Enter player/team name: ")
        sport: str = input("Enter sport to look for: ")

        url: str = (f"https://allsportsapi2.p.rapidapi.com/api/"
               f"{'' if sport.lower() == 'football' else sport.lower() + '/'}"
               f"search/"
               f"{name.lower()}")

        headers: dict[str, str] = {
            "X-RapidAPI-Key": "REPLACED_API_KEY",
            "X-RapidAPI-Host": "allsportsapi2.p.rapidapi.com"
        }

        # THIS SHOULD BE UNDER A TRY STATEMENT

        print(f"Looking for players/teams...\n")

        request: requests.Response = requests.get(url, headers=headers)

        if not request.text:
            print(f"No player/team found with that name")
            continue

        hits: list[filter] = list(filter(lambda result: result['type'] == 'team', json.loads(request.text)['results']))
        chosen: int = 0

        if len(hits) > 1:
            print("Multiple hits satisfy the query:")
            for order, hit in enumerate(hits):
                team_name: str = " ".join(x.capitalize() for x in hit["entity"]["slug"].split("-"))
                team_gender: str = hit["entity"].get("gender")
                print(f'{order + 1}: {team_name} {"(" + team_gender + ")" if team_gender else ""}')
            chosen = int(input("Type the number associated to the correct option: ")) - 1

        print()
        confirmed: str = input(f'{hits[chosen]["entity"]["name"]} added to the search list. Is this correct? Y/N: ')
        if confirmed.upper() == 'Y':
            id_dict[str(hits[chosen]["entity"]["id"])] = {
                "name": hits[chosen]["entity"]["name"],
                "sport": sport
            }
        else:
            print("Choice deleted.")

        if input(f'Search for another player/team? Y/N: ').upper() == "N":
            print()
            return id_dict

        print()


def main():
    print(get_ids())


if __name__ == '__main__':
    main()
