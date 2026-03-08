import logging
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from objects.Match import Match

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


def new_calendar(service: Resource, calendar_name: str) -> dict | None:
    try:
        created_calendar = service.calendars().insert(body={"summary": calendar_name}).execute()
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
            'private': {
                'game_id': str(game.game_id),
                'side_one': game.side_one,
                'side_two': game.side_two,
                'start_time': game.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        }
    }


def update_events(service: Resource, calendar_id: str, game_list: list[Match], time_zone: str) -> int:
    logger.info("Updating calendar...")

    logger.info("Looking up future events...")
    logger.info("")
    time_min = (datetime.now()-timedelta(hours=12)).astimezone().replace(microsecond=0).isoformat()
    existing_events = []

    response = service.events().list(calendarId=calendar_id, timeMin=time_min).execute()
    existing_events.extend(response.get("items", []))
    next_page_token = response.get("nextPageToken")

    while next_page_token:
        response = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            pageToken=next_page_token
        ).execute()
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
            logger.warning(f"Skipping event '{event.get('summary', 'unknown')}' — no game_id in extendedProperties")

    newly_created = 0

    for game in game_list:
        event = existing_by_game_id.get(str(game.game_id))

        if event:
            props = event.get("extendedProperties", {}).get("private", {})
            if (
                props.get("start_time") != game.start_time.strftime("%Y-%m-%d %H:%M:%S")
                or props.get("side_one") != game.side_one
                or props.get("side_two") != game.side_two
            ):
                logger.info("Found change in event schedule. Updating...")
                event_to_update = service.events().get(calendarId=calendar_id, eventId=event["id"]).execute()
                event_to_update.update(_build_event_body(game, time_zone))
                updated_event = service.events().update(
                    calendarId=calendar_id,
                    eventId=event['id'],
                    body=event_to_update
                ).execute()
                logger.info(f'Event updated: {updated_event.get("summary")} — {updated_event.get("htmlLink")}')
            else:
                logger.info(f"'{event['summary']}' already up to date")
        else:
            logger.info("New match upcoming! Creating event...")
            try:
                created_event = service.events().insert(
                    calendarId=calendar_id,
                    body=_build_event_body(game, time_zone)
                ).execute()
                logger.info(f'Event created: {created_event.get("summary")} — {created_event.get("htmlLink")}')
                newly_created += 1
            except HttpError as error:
                logger.error(f"An error occurred: {error}")

    matched_event_ids = {str(game.game_id) for game in game_list}
    team_event_count = sum(
        1 for event in existing_events
        if event.get("extendedProperties", {}).get("private", {}).get("game_id") in matched_event_ids
    )

    return team_event_count + newly_created