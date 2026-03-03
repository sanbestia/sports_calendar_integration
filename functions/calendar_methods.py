from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta


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


def datetime_to_calendar_format(date_time: datetime) -> str:
    date_format: str = "%Y-%m-%dT%H:%M:%S%:z"
    return date_time.strftime(date_format)


def new_calendar(creds) -> None:
    try:
        service = build("calendar", "v3", credentials=creds)

        created_calendar = service.calendars().insert(body="calendar").execute()

        return created_calendar

    except HttpError as error:
        print(f"An error occurred:\n{error}")


def update_events(creds, calendar_id, game_list, time_zone):
    print("* Updating calendar...\n")
    service = build("calendar", "v3", credentials=creds)

    print("Looking up future events...")
    event_list = service.events().list(
        calendarId=calendar_id,
        timeMin=(datetime.now()-timedelta(hours=12)).astimezone().replace(microsecond=0).isoformat()).execute()

    for game in game_list:
        should_create_new = True
        for event in event_list["items"]:
            side_one, side_two, event_start_time, event_game_id, last_updated = event["description"].split("\n")
            if event_game_id == game.game_id:
                should_create_new = False
                if event_start_time != str(game.start_time)[:-6] or game.side_one != side_one or game.side_two != side_two:
                    print("Found change in event schedule. Updating...")
                    event_to_update = service.events().get(calendarId=calendar_id, eventId=event["id"]).execute()
                    event_to_update['summary'] = \
                        f'{ICONS[game.sport]} {game.side_one} vs {game.side_two} - {game.tournament} ({game.stage})'
                    event_to_update['start'] = {
                        'dateTime': datetime_to_calendar_format(game.start_time),
                        'timeZone': time_zone,
                    }
                    event_to_update['end'] = {
                        'dateTime': datetime_to_calendar_format(game.expected_end_time),
                        'timeZone': time_zone,
                    }
                    event_to_update['description'] = (f'{game.side_one}\n'
                                                      f'{game.side_two}\n'
                                                      f'{game.start_time.strftime("%Y-%m-%d %H:%M:%S")}\n'
                                                      f'{game.game_id}\n'
                                                      f'Last changed at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

                    updated_event = service.events().update(calendarId=calendar_id,
                                                            eventId=event['id'],
                                                            body=event_to_update
                                                            ).execute()
                    print(f'Event updated: {updated_event.get("summary")}\nLink: {updated_event.get("htmlLink")}')
                else:
                    print(f"'{event['summary']}' already up to date!")

        if should_create_new:
            print("New match upcoming! Creating event...")
            try:
                event = {
                    'summary': f'{ICONS[game.sport]} {game.side_one} vs {game.side_two} - {game.tournament} ({game.stage})',
                    'start': {
                        'dateTime': datetime_to_calendar_format(game.start_time),
                        'timeZone': time_zone,
                    },
                    'end': {
                        'dateTime': datetime_to_calendar_format(game.expected_end_time),
                        'timeZone': time_zone,
                    },
                    'description':
                        f'{game.side_one}\n'
                        f'{game.side_two}\n'
                        f'{game.start_time.strftime("%Y-%m-%d %H:%M:%S")}\n'
                        f'{game.game_id}\n'
                        f'Last changed at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                }

                event = service.events().insert(calendarId=calendar_id, body=event).execute()
                print(f'Event created: {event.get("summary")}\nLink: {event.get("htmlLink")}')

            except HttpError as error:
                print(f"An error occurred: {error}")
    print()


def main():
    pass


if __name__ == '__main__':
    main()
