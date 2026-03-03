#!/usr/bin/env python

import subprocess
import sys


# packages_to_install = {
#     'google-api-python-client',
#     'google-auth-oauthlib',
#     'google-auth-httplib2',
#     'pytz',
#     'tzlocal'
# }
#
#
# for package in packages_to_install:
#     subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])


import os
import datetime
from dotenv import load_dotenv
from tzlocal import get_localzone

from functions.check_calendar_tokens import check_calendar_tokens
from functions.calendar_methods import update_events
from functions.get_next_matches import get_next_matches
from functions.get_ids import get_ids
from functions.time_keeper import wait

load_dotenv()

SEARCHES = {
    "Carlos Alcaraz": {
        "id": "275923",
        "sport": "tennis",
        "player_type": "player",
        "calendar": os.getenv("CALENDAR_ID_TENNIS")
    },
    "Jannik Sinner": {
        "id": "206570",
        "sport": "tennis",
        "player_type": "player",
        "calendar": os.getenv("CALENDAR_ID_TENNIS")
    },
    "Aryna Sabalenka": {
        "id": "157754",
        "sport": "tennis",
        "player_type": "player",
        "calendar": os.getenv("CALENDAR_ID_TENNIS")
    },
    "Argentina - Football National Team": {
        "id": "4819",
        "sport": "football",
        "player_type": "team",
        "calendar": os.getenv("CALENDAR_ID_FOOTBALL")
    },
    "Argentina - Football U23 National Team": {
        "id": "24246",
        "sport": "football",
        "player_type": "team",
        "calendar": os.getenv("CALENDAR_ID_FOOTBALL")
    },
    "San Antonio Spurs": {
        "id": "3429",
        "sport": "basketball",
        "player_type": "team",
        "calendar": os.getenv("CALENDAR_ID_BASKETBALL")
    },
    "Los Angeles Lakers": {
        "id": "3427",
        "sport": "basketball",
        "player_type": "team",
        "calendar": os.getenv("CALENDAR_ID_BASKETBALL")
    },
    "Indiana Fever": {
        "id": "3452",
        "sport": "basketball",
        "player_type": "team",
        "calendar": os.getenv("CALENDAR_ID_BASKETBALL")
    },
    "T1": {
        "id": "364366",
        "sport": "esport",
        "player_type": "team",
        "calendar": os.getenv("CALENDAR_ID_ESPORT")
    },
    "France - Basketball National Team": {
        "id": "6248",
        "sport": "basketball",
        "player_type": "team",
        "calendar": os.getenv("CALENDAR_ID_BASKETBALL")
    }
}


def main() -> None:
    tz = get_localzone()

    creds = check_calendar_tokens()

    refresh_hours = 6
    refresh_rate = refresh_hours * 60

    print()

    while True:
        for name, data_dict in SEARCHES.items():
            data = get_next_matches(
                team_id=data_dict["id"],
                team_name=name,
                sport=data_dict["sport"],
                player_type=data_dict["player_type"],
                time_zone=str(tz)
            )
            if data:
                update_events(
                    creds=creds,
                    calendar_id=data_dict["calendar"],
                    game_list=data,
                    time_zone=str(tz)
                )
            print("--------------------------------------------------\n")

        now = datetime.datetime.now(tz=tz)
        deadline = now + datetime.timedelta(minutes=refresh_rate)
        print(f"{now.hour:02}:{now.minute:02} - "
              f"Next update in {refresh_rate} minute{'' if refresh_rate == 1 else 's'}"
              f" (@ {deadline.hour:02}:{deadline.minute:02})")
        wait(deadline, tz)
        print("\n-----------------------------------------------------------------------------\n\n\n")


if __name__ == "__main__":
    main()