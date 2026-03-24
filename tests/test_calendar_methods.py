import datetime
import pytest
from unittest.mock import MagicMock
from googleapiclient.errors import HttpError
from objects.Match import Match
from functions.calendar_methods import update_events, new_calendar


START_TIME = datetime.datetime(2025, 6, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)


def make_match(game_id="123", side_one="Team A", side_two="Team B", start_time=START_TIME,
               home_team_id="h1", away_team_id="a1"):
    return Match(
        side_one=side_one,
        side_two=side_two,
        tournament="Some League",
        stage="Round 1",
        game_id=game_id,
        sport="football",
        start_time=start_time,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
    )


def make_existing_event(game_id="123", side_one="Team A", side_two="Team B", start_time=START_TIME,
                        home_team_id="h1", away_team_id="a1"):
    """Helper to create a fake existing calendar event using extendedProperties."""
    return {
        "id": "google_event_id_abc",
        "summary": f"{side_one} vs {side_two} - Some League (Round 1)",
        "description": "Last updated: 2025-01-01 00:00:00",
        "extendedProperties": {
            "private": {
                "game_id": str(game_id),
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "side_one": side_one,
                "side_two": side_two,
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        }
    }


def make_mock_service(existing_events: list) -> MagicMock:
    """Helper to create a fake Google Calendar service."""
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {"items": existing_events}  # no nextPageToken — single page
    mock_service.events().get().execute.return_value = existing_events[0] if existing_events else {}
    return mock_service


# --- new_calendar tests ---

def test_new_calendar_returns_created_calendar():
    """Returns the created calendar dict on success."""
    fake_calendar = {"id": "new_calendar_id", "summary": "My Sports Calendar"}
    mock_service = MagicMock()
    mock_service.calendars().insert().execute.return_value = fake_calendar

    result = new_calendar(service=mock_service, calendar_name="My Sports Calendar")

    assert result == fake_calendar
    assert result["summary"] == "My Sports Calendar"


def test_new_calendar_returns_none_on_http_error():
    """Returns None when an HttpError occurs."""
    mock_service = MagicMock()
    mock_service.calendars().insert().execute.side_effect = HttpError(
        resp=MagicMock(status=403),
        content=b"Forbidden"
    )

    result = new_calendar(service=mock_service, calendar_name="My Sports Calendar")

    assert result is None


# --- update_events tests ---

def test_skips_event_missing_extended_properties():
    """Does not crash when an existing event has no extendedProperties game_id."""
    match = make_match(game_id="999")
    event_without_props = {
        "id": "google_event_id_xyz",
        "summary": "Some manually created event",
    }
    mock_service = make_mock_service(existing_events=[event_without_props])

    result = update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    mock_service.events().insert.assert_called_once()
    assert result == 1


def test_creates_new_event_when_no_existing():
    """Creates a new event when the game doesn't exist in the calendar yet."""
    match = make_match(game_id="999")
    mock_service = make_mock_service(existing_events=[])

    result = update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    mock_service.events().insert.assert_called_once()
    assert result == 1


def test_does_not_create_event_when_already_exists_and_unchanged():
    """Skips creation and update when event already exists and nothing has changed."""
    match = make_match(game_id="123", home_team_id="h1", away_team_id="a1")
    existing = make_existing_event(game_id="123", home_team_id="h1", away_team_id="a1")
    mock_service = make_mock_service(existing_events=[existing])

    result = update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    mock_service.events().insert.assert_not_called()
    mock_service.events().update.assert_not_called()
    assert result == 1


def test_updates_event_when_start_time_changed():
    """Updates an existing event when the start time has changed."""
    original_time = START_TIME
    new_time = START_TIME + datetime.timedelta(hours=3)

    existing = make_existing_event(game_id="123", start_time=original_time, home_team_id="h1", away_team_id="a1")
    match = make_match(game_id="123", start_time=new_time, home_team_id="h1", away_team_id="a1")
    mock_service = make_mock_service(existing_events=[existing])

    result = update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    mock_service.events().update.assert_called_once()
    mock_service.events().insert.assert_not_called()
    assert result == 1


def test_updates_event_when_team_name_changed():
    """Updates an existing event when a team name has changed."""
    existing = make_existing_event(game_id="123", side_one="Old Team A", home_team_id="h1", away_team_id="a1")
    match = make_match(game_id="123", side_one="New Team A", home_team_id="h1", away_team_id="a1")
    mock_service = make_mock_service(existing_events=[existing])

    result = update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    mock_service.events().update.assert_called_once()
    mock_service.events().insert.assert_not_called()
    assert result == 1


def test_updates_event_when_team_ids_missing():
    """Patches an existing event missing home/away team IDs (migration path for old events)."""
    existing = make_existing_event(game_id="123")
    del existing["extendedProperties"]["private"]["home_team_id"]
    del existing["extendedProperties"]["private"]["away_team_id"]
    match = make_match(game_id="123", home_team_id="h1", away_team_id="a1")
    mock_service = make_mock_service(existing_events=[existing])

    result = update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    mock_service.events().update.assert_called_once()
    mock_service.events().insert.assert_not_called()
    assert result == 1


def test_handles_multiple_matches():
    """Correctly processes a list of multiple matches."""
    match_1 = make_match(game_id="111")
    match_2 = make_match(game_id="222")
    mock_service = make_mock_service(existing_events=[])

    result = update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match_1, match_2],
        time_zone="UTC",
        team_id="h1"
    )

    assert mock_service.events().insert.call_count == 2
    assert result == 2


def test_returns_correct_count_with_multiple_existing_events():
    """Returns the total number of existing calendar events."""
    match = make_match(game_id="999", home_team_id="h1", away_team_id="a1")
    existing_1 = make_existing_event(game_id="111", home_team_id="other_h", away_team_id="other_a")
    existing_2 = make_existing_event(game_id="222", home_team_id="other_h", away_team_id="other_a")
    mock_service = make_mock_service(existing_events=[existing_1, existing_2])

    result = update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    assert result == 1


# --- orphan deletion tests ---

def test_deletes_orphaned_event_for_same_team():
    """Deletes a future event whose game_id is no longer in the game list (same team)."""
    match = make_match(game_id="new_id", home_team_id="h1", away_team_id="a1")
    orphan = make_existing_event(game_id="old_id", home_team_id="h1", away_team_id="a1")
    mock_service = make_mock_service(existing_events=[orphan])

    update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    mock_service.events().delete.assert_called_once_with(
        calendarId="fake_calendar_id", eventId="google_event_id_abc"
    )


def test_deletes_orphaned_event_when_queried_team_is_away():
    """Deletes a future orphaned event when the queried team is the away side."""
    match = make_match(game_id="new_id", home_team_id="h1", away_team_id="a1")
    orphan = make_existing_event(game_id="old_id", home_team_id="h1", away_team_id="a1")
    mock_service = make_mock_service(existing_events=[orphan])

    update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="a1"  # queried team is the away side
    )

    mock_service.events().delete.assert_called_once_with(
        calendarId="fake_calendar_id", eventId="google_event_id_abc"
    )


def test_does_not_delete_event_for_different_team():
    """Does not delete a future event belonging to a different team."""
    match = make_match(game_id="new_id", home_team_id="h1", away_team_id="a1")
    other_team_event = make_existing_event(game_id="other_id", home_team_id="other_h", away_team_id="other_a")
    mock_service = make_mock_service(existing_events=[other_team_event])

    update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    mock_service.events().delete.assert_not_called()


def test_does_not_delete_event_without_team_ids():
    """Does not delete a future event that has no team IDs (old manually created events)."""
    match = make_match(game_id="new_id")
    legacy_event = make_existing_event(game_id="legacy_id")
    del legacy_event["extendedProperties"]["private"]["home_team_id"]
    del legacy_event["extendedProperties"]["private"]["away_team_id"]
    mock_service = make_mock_service(existing_events=[legacy_event])

    update_events(
        service=mock_service,
        calendar_id="fake_calendar_id",
        game_list=[match],
        time_zone="UTC",
        team_id="h1"
    )

    mock_service.events().delete.assert_not_called()
