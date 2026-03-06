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
import json
import logging
import argparse
import datetime
from dotenv import load_dotenv
from tzlocal import get_localzone

from functions.check_calendar_tokens import check_calendar_tokens
from functions.calendar_methods import update_events
from functions.get_next_matches import get_next_matches
from functions.get_ids import get_ids
from functions.time_keeper import wait
from objects.API_Call_Tracker import APICallTracker
from config import REFRESH_HOURS

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)



def load_queries(filepath: str) -> dict:
    """Load queries from a JSON file, resolving calendar IDs from environment variables."""
    with open(filepath, "r") as f:
        raw = json.load(f)

    for name, data in raw.items():
        env_key = data.get("calendar")
        resolved = os.getenv(env_key)
        if not resolved:
            raise ValueError(f"Environment variable '{env_key}' not found for '{name}'")
        data["calendar"] = resolved

    return raw


def build_queries_from_get_ids(tracker=None) -> dict:
    """Interactively build queries using get_ids(), prompting for calendar IDs."""
    id_dict = get_ids(tracker=tracker)
    queries = {}
    for team_id, data in id_dict.items():
        calendar_id = input(f"Enter calendar id for {data['name']}: ")
        queries[data["name"]] = {
            "id": team_id,
            "sport": data["sport"],
            "player_type": "team",
            "calendar": calendar_id
        }
    return queries


def main() -> None:
    parser = argparse.ArgumentParser(description="Sports Calendar Integration")
    parser.add_argument(
        "--queries",
        type=str,
        help="Path to a JSON file containing search queries",
        default=None
    )
    args = parser.parse_args()

    tz = get_localzone()
    creds = check_calendar_tokens()
    tracker = APICallTracker()

    if args.queries:
        queries = load_queries(args.queries)
    else:
        queries = build_queries_from_get_ids(tracker=tracker)

    refresh_rate = REFRESH_HOURS * 60

    while True:
        for name, data_dict in queries.items():
            data = get_next_matches(
                team_id=data_dict["id"],
                team_name=name,
                sport=data_dict["sport"],
                player_type=data_dict["player_type"],
                time_zone=str(tz),
                tracker=tracker
            )
            if data:
                update_events(
                    creds=creds,
                    calendar_id=data_dict["calendar"],
                    game_list=data,
                    time_zone=str(tz)
                )
            logger.info("--------------------------------------------------\n")

        now = datetime.datetime.now(tz=tz)
        deadline = now + datetime.timedelta(minutes=refresh_rate)
        logger.info(tracker.status())
        logger.info(f"Next update in {refresh_rate} minute{'' if refresh_rate == 1 else 's'} "
                    f"(@ {deadline.hour:02}:{deadline.minute:02})")
        wait(deadline, tz)


if __name__ == "__main__":
    main()