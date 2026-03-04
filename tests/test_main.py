import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
from main import load_queries, build_queries_from_get_ids


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
        "3429": {"name": "San Antonio Spurs", "sport": "basketball"}
    }

    with patch("main.get_ids", return_value=fake_id_dict), \
         patch("builtins.input", return_value="real_basketball_calendar_id"):
        result = build_queries_from_get_ids()

    assert "San Antonio Spurs" in result
    assert result["San Antonio Spurs"]["id"] == "3429"
    assert result["San Antonio Spurs"]["sport"] == "basketball"
    assert result["San Antonio Spurs"]["calendar"] == "real_basketball_calendar_id"


def test_build_queries_handles_multiple_entries():
    """Correctly builds dict with multiple entries."""
    fake_id_dict = {
        "3429": {"name": "San Antonio Spurs", "sport": "basketball"},
        "364366": {"name": "T1", "sport": "esport"}
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
