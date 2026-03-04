import pytest
import json
from unittest.mock import patch, MagicMock
from functions.get_ids import get_ids

FAKE_SINGLE_HIT = {
    "results": [
        {
            "type": "team",
            "entity": {
                "id": 3429,
                "name": "San Antonio Spurs",
                "slug": "san-antonio-spurs",
                "gender": "M"
            }
        }
    ]
}

FAKE_MULTIPLE_HITS = {
    "results": [
        {
            "type": "team",
            "entity": {
                "id": 3429,
                "name": "San Antonio Spurs",
                "slug": "san-antonio-spurs",
                "gender": "M"
            }
        },
        {
            "type": "team",
            "entity": {
                "id": 9999,
                "name": "San Antonio FC",
                "slug": "san-antonio-fc",
                "gender": "M"
            }
        }
    ]
}


def make_mock_response(data: dict) -> MagicMock:
    mock = MagicMock()
    mock.text = json.dumps(data)
    return mock


def make_mock_empty_response() -> MagicMock:
    mock = MagicMock()
    mock.text = ""
    return mock


# --- Tests ---

def test_returns_correct_dict_on_single_hit():
    """Returns a correctly structured dict when one result is found and confirmed."""
    with patch("functions.get_ids.requests.get") as mock_get, \
         patch("builtins.input", side_effect=[
             "San Antonio Spurs",  # player/team name
             "basketball",         # sport
             "Y",                  # confirm selection
             "N"                   # search for another?
         ]):
        mock_get.return_value = make_mock_response(FAKE_SINGLE_HIT)
        result = get_ids()

    assert "3429" in result
    assert result["3429"]["name"] == "San Antonio Spurs"
    assert result["3429"]["sport"] == "basketball"


def test_skips_entry_when_not_confirmed():
    """Does not add entry to dict when user rejects the selection."""
    with patch("functions.get_ids.requests.get") as mock_get, \
         patch("builtins.input", side_effect=[
             "San Antonio Spurs",  # player/team name
             "basketball",         # sport
             "N",                  # reject selection
             "N"                   # search for another?
         ]):
        mock_get.return_value = make_mock_response(FAKE_SINGLE_HIT)
        result = get_ids()

    assert result == {}


def test_handles_multiple_hits():
    """Lets user pick from multiple results and adds the chosen one."""
    with patch("functions.get_ids.requests.get") as mock_get, \
         patch("builtins.input", side_effect=[
             "San Antonio",  # player/team name
             "basketball",   # sport
             "1",            # pick first option
             "Y",            # confirm selection
             "N"             # search for another?
         ]):
        mock_get.return_value = make_mock_response(FAKE_MULTIPLE_HITS)
        result = get_ids()

    assert "3429" in result
    assert result["3429"]["name"] == "San Antonio Spurs"


def test_retries_when_no_results_found():
    """Loops and retries when first search returns no results, succeeds on second."""
    with patch("functions.get_ids.requests.get") as mock_get, \
         patch("builtins.input", side_effect=[
             "zzzzz",              # first search - bad name
             "basketball",         # sport
             "San Antonio Spurs",  # second search - good name
             "basketball",         # sport
             "Y",                  # confirm
             "N"                   # search for another?
         ]):
        mock_get.side_effect = [
            make_mock_empty_response(),
            make_mock_response(FAKE_SINGLE_HIT)
        ]
        result = get_ids()

    assert "3429" in result


def test_returns_multiple_entries():
    """Correctly builds dict with multiple confirmed entries."""
    with patch("functions.get_ids.requests.get") as mock_get, \
         patch("builtins.input", side_effect=[
             "San Antonio Spurs",  # first search
             "basketball",
             "Y",                  # confirm
             "Y",                  # search for another?
             "San Antonio Spurs",  # second search
             "basketball",
             "Y",                  # confirm
             "N"                   # search for another?
         ]):
        mock_get.return_value = make_mock_response(FAKE_SINGLE_HIT)
        result = get_ids()

    assert len(result) == 1  # same id both times, so dict only has one entry
