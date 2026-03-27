import os
import json
import logging
import argparse
import datetime
from dotenv import load_dotenv
from tzlocal import get_localzone
from googleapiclient.discovery import build

from functions.check_calendar_tokens import check_calendar_tokens
from functions.calendar_methods import update_events
from functions.get_next_matches import get_next_matches
from functions.get_ids import get_ids
from functions.time_keeper import wait
from objects.APICallTracker import APICallTracker
from objects.FetchTracker import FetchTracker
from config import MAIN_LOOP_SLEEP_MINUTES

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)  # suppress the verbose 'file_cache unavailable' warning emitted by the Google client
logger = logging.getLogger(__name__)


_REQUIRED_QUERY_FIELDS = {"id", "sport", "player_type", "calendar"}


def load_queries(filepath: str) -> dict:
    """Load queries from a JSON file, resolving calendar IDs from environment variables."""
    with open(filepath, "r") as f:
        raw = json.load(f)

    for name, data in raw.items():
        missing = _REQUIRED_QUERY_FIELDS - data.keys()
        if missing:
            raise ValueError(f"Query '{name}' is missing required fields: {', '.join(sorted(missing))}")
        env_key = data["calendar"]
        resolved = os.getenv(env_key)
        if not resolved:
            raise ValueError(f"Environment variable '{env_key}' not found for '{name}'")
        data["calendar"] = resolved  # replace the env var key with the actual calendar ID so callers get the resolved value

    return raw


def build_queries_from_get_ids(tracker: APICallTracker | None = None) -> dict:
    """Interactively build queries using get_ids(), prompting for calendar IDs."""
    id_dict = get_ids(tracker=tracker)
    queries = {}
    for team_id, data in id_dict.items():
        calendar_id = input(f"Enter calendar id for {data['name']}: ")
        queries[data["name"]] = {
            "id": team_id,
            "sport": data["sport"],
            "player_type": data["player_type"],
            "calendar": calendar_id
        }
    return queries


def main() -> None:
    """Parse args, initialise services, and run the main fetch-and-sync loop."""
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
    calendar_service = build("calendar", "v3", credentials=creds)
    api_tracker = APICallTracker()
    fetch_tracker = FetchTracker()

    if args.queries:
        queries = load_queries(args.queries)
    else:
        queries = build_queries_from_get_ids(tracker=api_tracker)

    sleep_minutes = MAIN_LOOP_SLEEP_MINUTES

    while True:
        for name, data_dict in queries.items():

            if api_tracker.is_limit_reached():
                logger.warning(
                    f"Daily API limit of {api_tracker.daily_limit} calls reached — "
                    f"skipping remaining fetches until tomorrow"
                    )
                break

            if not fetch_tracker.should_fetch(name):
                hours_left = fetch_tracker.hours_until_next_fetch(name)
                logger.info(f"Skipping {name} — next fetch in {hours_left:.1f}h")
                logger.info("--------------------------------------------------")
                logger.info("")
                continue

            matches = get_next_matches(
                team_id=data_dict["id"],
                team_name=name,
                sport=data_dict["sport"],
                player_type=data_dict["player_type"],
                time_zone=str(tz),
                tracker=api_tracker
            )

            earliest = min((m.start_time for m in matches), default=None)  # default=None avoids ValueError when matches is empty

            match_count = 0
            if matches:
                try:
                    match_count = update_events(
                        service=calendar_service,
                        calendar_id=data_dict["calendar"],
                        game_list=matches,
                        time_zone=str(tz),
                        team_id=data_dict["id"]
                    )
                except BrokenPipeError:
                    logger.warning("Calendar connection lost (post-sleep?). Reconnecting and retrying...")
                    creds = check_calendar_tokens()
                    calendar_service = build("calendar", "v3", credentials=creds)
                    try:
                        match_count = update_events(
                            service=calendar_service,
                            calendar_id=data_dict["calendar"],
                            game_list=matches,
                            time_zone=str(tz),
                            team_id=data_dict["id"]
                        )
                    except Exception as e:
                        logger.error(f"Calendar update failed after reconnect for '{name}': {e}")

            fetch_tracker.record_fetch(name, earliest, match_count)

            logger.info("")
            logger.info("--------------------------------------------------")
            logger.info("")

        now = datetime.datetime.now(tz=tz)
        deadline = now + datetime.timedelta(minutes=sleep_minutes)
        logger.info(api_tracker.status())
        logger.info(
            f"Next cycle in {sleep_minutes} minute{'' if sleep_minutes == 1 else 's'} "
            f"(@ {deadline.hour:02}:{deadline.minute:02})"
        )
        wait(deadline, tz)

        logger.info("")
        logger.info("------------------------------------------------------------------------")
        logger.info("")


if __name__ == "__main__":
    main()