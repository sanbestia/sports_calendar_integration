import datetime
import pytest
from unittest.mock import patch, MagicMock
from objects.Match import Match
from functions.calendar_methods import update_events

START_TIME = datetime.datetime(2025, 6, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)


def make_match(game_id="123", side_one="Team A", side_two="Team B", start_time=START_TIME):
    return Match(
        side_one=side_one,
        side_two=side_two,
        tournament="Some League",
        stage="Round 1",
        game_id=game_id,
        sport="football",
        start_time=start_time
    )


def make_existing_event(game_id="123", side_one="Team A", side_two="Team B", start_time=START_TIME):
    """Helper to create a fake existing calendar event matching the real description format."""
    return {
        "id": "google_event_id_abc",
        "summary": f"{side_one} vs {side_two} - Some League (Round 1)",
        "description": (
            f"{side_one}\n"
            f"{side_two}\n"
            f"{start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{game_id}\n"
            f"Last changed at 2025-01-01 00:00:00"
        )
    }


def make_mock_service(existing_events: list) -> MagicMock:
    """Helper to create a fake Google Calendar service."""
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {"items": existing_events}
    mock_service.events().get().execute.return_value = existing_events[0] if existing_events else {}
    return mock_service


# --- Tests ---

def test_creates_new_event_when_no_existing():
    """Creates a new event when the game doesn't exist in the calendar yet."""
    match = make_match(game_id="999")

    with patch("functions.calendar_methods.build") as mock_build:
        mock_service = make_mock_service(existing_events=[])
        mock_build.return_value = mock_service

        update_events(
            creds=MagicMock(),
            calendar_id="fake_calendar_id",
            game_list=[match],
            time_zone="UTC"
        )

    mock_service.events().insert.assert_called_once()


def test_does_not_create_event_when_already_exists_and_unchanged():
    """Skips creation and update when event already exists and nothing has changed."""
    match = make_match(game_id="123")
    existing = make_existing_event(game_id="123")

    with patch("functions.calendar_methods.build") as mock_build:
        mock_service = make_mock_service(existing_events=[existing])
        mock_build.return_value = mock_service

        update_events(
            creds=MagicMock(),
            calendar_id="fake_calendar_id",
            game_list=[match],
            time_zone="UTC"
        )

    mock_service.events().insert.assert_not_called()
    mock_service.events().update.assert_not_called()


def test_updates_event_when_start_time_changed():
    """Updates an existing event when the start time has changed."""
    original_time = START_TIME
    new_time = START_TIME + datetime.timedelta(hours=3)

    existing = make_existing_event(game_id="123", start_time=original_time)
    match = make_match(game_id="123", start_time=new_time)

    with patch("functions.calendar_methods.build") as mock_build:
        mock_service = make_mock_service(existing_events=[existing])
        mock_build.return_value = mock_service

        update_events(
            creds=MagicMock(),
            calendar_id="fake_calendar_id",
            game_list=[match],
            time_zone="UTC"
        )

    mock_service.events().update.assert_called_once()
    mock_service.events().insert.assert_not_called()


def test_updates_event_when_team_name_changed():
    """Updates an existing event when a team name has changed."""
    existing = make_existing_event(game_id="123", side_one="Old Team A")
    match = make_match(game_id="123", side_one="New Team A")

    with patch("functions.calendar_methods.build") as mock_build:
        mock_service = make_mock_service(existing_events=[existing])
        mock_build.return_value = mock_service

        update_events(
            creds=MagicMock(),
            calendar_id="fake_calendar_id",
            game_list=[match],
            time_zone="UTC"
        )

    mock_service.events().update.assert_called_once()
    mock_service.events().insert.assert_not_called()


def test_handles_multiple_matches():
    """Correctly processes a list of multiple matches."""
    match_1 = make_match(game_id="111")
    match_2 = make_match(game_id="222")

    with patch("functions.calendar_methods.build") as mock_build:
        mock_service = make_mock_service(existing_events=[])
        mock_build.return_value = mock_service

        update_events(
            creds=MagicMock(),
            calendar_id="fake_calendar_id",
            game_list=[match_1, match_2],
            time_zone="UTC"
        )

    assert mock_service.events().insert.call_count == 2