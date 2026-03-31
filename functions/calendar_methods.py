import logging
import time
import random
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from objects.Match import Match
from functions.utils import sanitize_for_log

logger = logging.getLogger(__name__)

ICONS: dict[str, str] = {
    "football": "⚽",
    "baseball": "⚾",
    "basketball": "🏀",
    "volleyball": "🏐",
    "american-football": "🏈",
    "rugby": "🏉",
    "tennis": "🎾",
    "cricket": "🏏",
    "ice-hockey": "🏒",
    "motorsport": "🏎️",
    "esport": "🎮"
}

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 4
_BASE_DELAY = 1.0  # seconds


def _execute_with_retry(request) -> dict:
    """Execute a Google API request with exponential backoff on transient errors."""
    for attempt in range(_MAX_RETRIES):
        try:
            return request.execute()
        except HttpError as e:
            if e.status_code not in _RETRYABLE_STATUS_CODES or attempt == _MAX_RETRIES - 1:
                raise
            delay = _BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Google API error {e.status_code}, retrying in {delay:.1f}s (attempt {attempt + 1}/{_MAX_RETRIES})")
            time.sleep(delay)


def new_calendar(service: Resource, calendar_name: str) -> dict | None:
    """Create a new Google Calendar with the given name and return its resource dict, or None on failure."""
    try:
        created_calendar = _execute_with_retry(service.calendars().insert(body={"summary": calendar_name}))
        return created_calendar
    except HttpError as error:
        logger.error(f"An error occurred creating calendar: {error}")
        return None


def _build_event_body(game: Match, time_zone: str) -> dict:
    """Build a Google Calendar event body for a given match."""
    return {
        'summary': f'{ICONS[game.sport]} {game.side_one} vs {game.side_two} - {game.tournament} ({game.stage})',
        'description': f'Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        'start': {
            'dateTime': game.start_time.isoformat(),
            'timeZone': time_zone,
        },
        'end': {
            'dateTime': game.expected_end_time.isoformat(),
            'timeZone': time_zone,
        },
        'extendedProperties': {
            'private': {  # these fields are compared in update_events to detect reschedules; must stay in sync with that check
                'game_id': str(game.game_id),
                'home_team_id': str(game.home_team_id) if game.home_team_id is not None else '',
                'away_team_id': str(game.away_team_id) if game.away_team_id is not None else '',
                'side_one': game.side_one,
                'side_two': game.side_two,
                'start_time': game.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        }
    }


def update_events(service: Resource, calendar_id: str, game_list: list[Match], time_zone: str, team_id: str) -> int:
    """Sync a list of matches to Google Calendar: create new events, update changed ones, and delete orphans."""
    logger.info("Updating calendar...")

    logger.info("Looking up future events...")
    logger.info("")
    lookback = datetime.now() - timedelta(hours=12)  # -12h to catch in-progress games
    time_min = lookback.astimezone().replace(microsecond=0).isoformat()  # microsecond=0 because GCal API rejects sub-second precision
    existing_events = []

    response = _execute_with_retry(service.events().list(calendarId=calendar_id, timeMin=time_min))
    existing_events.extend(response.get("items", []))
    next_page_token = response.get("nextPageToken")

    while next_page_token:
        response = _execute_with_retry(service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            pageToken=next_page_token
        ))
        existing_events.extend(response.get("items", []))
        next_page_token = response.get("nextPageToken")

    # Build a dict keyed by game_id for O(1) lookup instead of scanning the full list per game
    existing_by_game_id: dict[str, dict] = {}
    for event in existing_events:
        props = event.get("extendedProperties", {}).get("private", {})
        game_id = props.get("game_id")
        if game_id:
            existing_by_game_id[game_id] = event
        else:
            logger.warning(f"Skipping event '{sanitize_for_log(event.get('summary', 'unknown'))}' — no game_id in extendedProperties")

    newly_created = 0

    for game in game_list:
        event = existing_by_game_id.get(str(game.game_id))

        if event:
            props = event.get("extendedProperties", {}).get("private", {})
            # compare stored private properties (not the Calendar's own start time) to detect reschedules or team changes
            if (
                props.get("start_time") != game.start_time.strftime("%Y-%m-%d %H:%M:%S")
                or props.get("side_one") != game.side_one
                or props.get("side_two") != game.side_two
                or props.get("home_team_id") != game.home_team_id
                or props.get("away_team_id") != game.away_team_id
            ):
                logger.info("Found change in event schedule. Updating...")
                event_to_update = _execute_with_retry(service.events().get(calendarId=calendar_id, eventId=event["id"]))  # fetch full event first to preserve fields not in _build_event_body (e.g. attendees)
                event_to_update.update(_build_event_body(game, time_zone))
                updated_event = _execute_with_retry(service.events().update(
                    calendarId=calendar_id,
                    eventId=event['id'],
                    body=event_to_update
                ))
                logger.info(f'Event updated: {sanitize_for_log(str(updated_event.get("summary", "")))} — {sanitize_for_log(str(updated_event.get("htmlLink", "")))}')
            else:
                logger.info(f"'{sanitize_for_log(event['summary'])}' already up to date")
        else:
            logger.info("New match upcoming! Creating event...")
            try:
                created_event = _execute_with_retry(service.events().insert(
                    calendarId=calendar_id,
                    body=_build_event_body(game, time_zone)
                ))
                logger.info(f'Event created: {sanitize_for_log(str(created_event.get("summary", "")))} — {sanitize_for_log(str(created_event.get("htmlLink", "")))}')
                newly_created += 1
            except HttpError as error:
                logger.error(f"An error occurred: {error}")

    matched_event_ids = {str(game.game_id) for game in game_list}

    # Delete future events for this team that are no longer in the game list
    # (cancelled matches or matches whose API id changed)
    for event in existing_events:
        props = event.get("extendedProperties", {}).get("private", {})
        if team_id not in (props.get("home_team_id"), props.get("away_team_id")):  # skip events belonging to other teams that share this calendar
            continue
        game_id = props.get("game_id")
        if game_id and game_id not in matched_event_ids:
            # Don't delete events that have already started — the sports API only returns upcoming games,
            # so past events will never appear in game_list even if they weren't cancelled
            event_start_str = event.get("start", {}).get("dateTime", "")
            if event_start_str:
                event_start = datetime.fromisoformat(event_start_str).astimezone()
                # Skip deletion of past/in-progress events
                if event_start <= datetime.now().astimezone():
                    continue
            try:
                _execute_with_retry(service.events().delete(calendarId=calendar_id, eventId=event["id"]))
                logger.info(f"Deleted cancelled/orphaned event: '{sanitize_for_log(event.get('summary', ''))}'")
            except HttpError as error:
                logger.error(f"Error deleting event '{sanitize_for_log(event.get('summary', ''))}': {error}")

    # count existing events that survived (not deleted); add newly_created for the total returned to FetchTracker
    team_event_count = sum(
        1 for event in existing_events
        if event.get("extendedProperties", {}).get("private", {}).get("game_id") in matched_event_ids
    )

    return team_event_count + newly_created