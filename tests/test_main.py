import pytest
import json
import os
import datetime
from unittest.mock import patch, MagicMock, mock_open
from main import main, load_queries, build_queries_from_get_ids


FAKE_RAW_QUERIES = {
    "San Antonio Spurs": {
        "id": "3429",
        "sport": "basketball",
        "player_type": "team",
        "calendar": "CALENDAR_ID_BASKETBALL"
    },
    "T1": {
        "id": "364366",
        "sport": "esport",
        "player_type": "team",
        "calendar": "CALENDAR_ID_ESPORTS"
    }
}


# --- load_queries tests ---

def test_load_queries_resolves_env_variables():
    """Resolves calendar env keys to actual IDs from environment."""
    with patch("builtins.open", mock_open(read_data=json.dumps(FAKE_RAW_QUERIES))), \
         patch.dict(os.environ, {
             "CALENDAR_ID_BASKETBALL": "real_basketball_calendar_id",
             "CALENDAR_ID_ESPORTS": "real_esports_calendar_id"
         }):
        result = load_queries("queries.json")

    assert result["San Antonio Spurs"]["calendar"] == "real_basketball_calendar_id"
    assert result["T1"]["calendar"] == "real_esports_calendar_id"


def test_load_queries_raises_when_env_variable_missing():
    """Raises ValueError when a calendar env key is not set."""
    with patch("builtins.open", mock_open(read_data=json.dumps(FAKE_RAW_QUERIES))), \
         patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="CALENDAR_ID_BASKETBALL"):
            load_queries("queries.json")


def test_load_queries_preserves_other_fields():
    """Preserves id, sport and player_type fields after loading."""
    with patch("builtins.open", mock_open(read_data=json.dumps(FAKE_RAW_QUERIES))), \
         patch.dict(os.environ, {
             "CALENDAR_ID_BASKETBALL": "real_basketball_calendar_id",
             "CALENDAR_ID_ESPORTS": "real_esports_calendar_id"
         }):
        result = load_queries("queries.json")

    assert result["San Antonio Spurs"]["id"] == "3429"
    assert result["San Antonio Spurs"]["sport"] == "basketball"
    assert result["San Antonio Spurs"]["player_type"] == "team"


# --- build_queries_from_get_ids tests ---

def test_build_queries_returns_correct_structure():
    """Returns correctly structured dict from get_ids output."""
    fake_id_dict = {
        "3429": {"name": "San Antonio Spurs", "sport": "basketball", "player_type": "team"}
    }

    with patch("main.get_ids", return_value=fake_id_dict), \
         patch("builtins.input", return_value="real_basketball_calendar_id"):
        result = build_queries_from_get_ids()

    assert "San Antonio Spurs" in result
    assert result["San Antonio Spurs"]["id"] == "3429"
    assert result["San Antonio Spurs"]["sport"] == "basketball"
    assert result["San Antonio Spurs"]["player_type"] == "team"
    assert result["San Antonio Spurs"]["calendar"] == "real_basketball_calendar_id"


def test_build_queries_preserves_player_type_for_player():
    """Preserves player_type 'player' when a player entry is built."""
    fake_id_dict = {
        "275923": {"name": "Carlos Alcaraz", "sport": "tennis", "player_type": "player"}
    }

    with patch("main.get_ids", return_value=fake_id_dict), \
         patch("builtins.input", return_value="real_tennis_calendar_id"):
        result = build_queries_from_get_ids()

    assert result["Carlos Alcaraz"]["player_type"] == "player"


def test_build_queries_handles_multiple_entries():
    """Correctly builds dict with multiple entries."""
    fake_id_dict = {
        "3429":   {"name": "San Antonio Spurs", "sport": "basketball", "player_type": "team"},
        "364366": {"name": "T1",                "sport": "esport",     "player_type": "team"}
    }

    with patch("main.get_ids", return_value=fake_id_dict), \
         patch("builtins.input", side_effect=[
             "real_basketball_calendar_id",
             "real_esports_calendar_id"
         ]):
        result = build_queries_from_get_ids()

    assert len(result) == 2
    assert "San Antonio Spurs" in result
    assert "T1" in result


# --- BrokenPipeError reconnection tests ---

def test_reconnects_calendar_service_on_broken_pipe():
    """Rebuilds the calendar service and retries update_events on BrokenPipeError."""
    fake_args = MagicMock()
    fake_args.queries = "queries.json"

    fake_queries = {
        "Carlos Alcaraz": {
            "id": "275923",
            "sport": "tennis",
            "player_type": "player",
            "calendar": "tennis_calendar_id"
        }
    }

    fake_match = MagicMock()
    fake_match.start_time = datetime.datetime(2026, 3, 22, 15, 0, 0)

    mock_api_tracker = MagicMock()
    mock_api_tracker.is_limit_reached.return_value = False
    mock_api_tracker.status.return_value = "API calls today: 1/100"

    mock_fetch_tracker = MagicMock()
    mock_fetch_tracker.should_fetch.return_value = True

    mock_service1 = MagicMock()
    mock_service2 = MagicMock()

    with patch("argparse.ArgumentParser.parse_args", return_value=fake_args), \
         patch("main.get_localzone", return_value=datetime.timezone.utc), \
         patch("main.check_calendar_tokens", return_value=MagicMock()) as mock_check_creds, \
         patch("main.build", side_effect=[mock_service1, mock_service2]) as mock_build, \
         patch("main.APICallTracker", return_value=mock_api_tracker), \
         patch("main.FetchTracker", return_value=mock_fetch_tracker), \
         patch("main.load_queries", return_value=fake_queries), \
         patch("main.get_next_matches", return_value=[fake_match]), \
         patch("main.update_events", side_effect=[BrokenPipeError, 1]) as mock_update, \
         patch("main.wait", side_effect=SystemExit):
        with pytest.raises(SystemExit):
            main()

    # Service rebuilt: build() called at startup + once after BrokenPipeError
    assert mock_build.call_count == 2
    # Credentials refreshed at startup + once after BrokenPipeError
    assert mock_check_creds.call_count == 2
    # update_events retried with the freshly built service
    assert mock_update.call_count == 2
    assert mock_update.call_args_list[1][1]["service"] is mock_service2


def test_continues_loop_when_retry_also_fails():
    """Logs the error and continues the loop when the reconnect retry also fails."""
    fake_args = MagicMock()
    fake_args.queries = "queries.json"

    fake_queries = {
        "Carlos Alcaraz": {
            "id": "275923",
            "sport": "tennis",
            "player_type": "player",
            "calendar": "tennis_calendar_id"
        }
    }

    fake_match = MagicMock()
    fake_match.start_time = datetime.datetime(2026, 3, 22, 15, 0, 0)

    mock_api_tracker = MagicMock()
    mock_api_tracker.is_limit_reached.return_value = False
    mock_api_tracker.status.return_value = "API calls today: 1/100"

    mock_fetch_tracker = MagicMock()
    mock_fetch_tracker.should_fetch.return_value = True

    with patch("argparse.ArgumentParser.parse_args", return_value=fake_args), \
         patch("main.get_localzone", return_value=datetime.timezone.utc), \
         patch("main.check_calendar_tokens", return_value=MagicMock()), \
         patch("main.build"), \
         patch("main.APICallTracker", return_value=mock_api_tracker), \
         patch("main.FetchTracker", return_value=mock_fetch_tracker), \
         patch("main.load_queries", return_value=fake_queries), \
         patch("main.get_next_matches", return_value=[fake_match]), \
         patch("main.update_events", side_effect=[BrokenPipeError, OSError("still down")]) as mock_update, \
         patch("main.wait", side_effect=SystemExit):
        with pytest.raises(SystemExit):
            main()

    # Both calls were made; the second failure was absorbed and the loop continued
    assert mock_update.call_count == 2
    mock_fetch_tracker.record_fetch.assert_called_once()