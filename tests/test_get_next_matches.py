import datetime
import pytest
import json
from unittest.mock import patch, MagicMock
from functions.get_next_matches import get_next_matches

# Fake event matching the real API structure
FAKE_EVENT = {
    "id": 1,
    "startTimestamp": 1772823600,
    "homeTeam": {"name": "Carlos Alcaraz"},
    "awayTeam": {"name": "Jannik Sinner"},
    "season": {"name": "ATP"},
    "roundInfo": {"round": 1, "name": "Finals"},
    "tournament": {"name": "ATP Ultra Finals, Mars"}
}

FAKE_NEAR_RESPONSE = {
    "nextEvent": FAKE_EVENT
}

FAKE_NEXT_RESPONSE_SINGLE_PAGE = {
    "events": [FAKE_EVENT],
    "hasNextPage": False
}

FAKE_NEXT_RESPONSE_PAGE_1 = {
    "events": [FAKE_EVENT],
    "hasNextPage": True
}

FAKE_NEXT_RESPONSE_PAGE_2 = {
    "events": [FAKE_EVENT],
    "hasNextPage": False
}


def make_mock_response(data: dict) -> MagicMock:
    """Helper to create a fake requests.Response object."""
    mock = MagicMock()
    mock.text = json.dumps(data)
    return mock


def make_mock_empty_response() -> MagicMock:
    """Helper to create a fake empty requests.Response object."""
    mock = MagicMock()
    mock.text = ""
    return mock


def make_mock_invalid_json_response() -> MagicMock:
    mock = MagicMock()
    mock.text = "<html>Internal Server Error</html>"
    return mock


# --- Tests ---

def test_returns_list_of_matches():
    """'next' endpoint returns one page of results."""
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(FAKE_NEXT_RESPONSE_SINGLE_PAGE)
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert len(result) == 1
    assert result[0].side_one == "Carlos Alcaraz"
    assert result[0].side_two == "Jannik Sinner"
    assert result[0].game_id == "1"


def test_paginates_correctly():
    """'next' endpoint paginates and collects events from all pages."""
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.side_effect = [
            make_mock_response(FAKE_NEXT_RESPONSE_PAGE_1),
            make_mock_response(FAKE_NEXT_RESPONSE_PAGE_2)
        ]
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert len(result) == 2
    assert mock_get.call_count == 2


def test_falls_back_to_near_endpoint():
    """Falls back to 'near' endpoint when 'next' returns empty."""
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.side_effect = [
            make_mock_empty_response(),
            make_mock_response(FAKE_NEAR_RESPONSE)
        ]
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert len(result) == 1
    assert result[0].game_id == "1"


def test_returns_empty_list_on_connection_error():
    """Returns empty list gracefully when a network error occurs."""
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.side_effect = ConnectionError
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert result == []


def test_returns_empty_list_on_timeout():
    """Returns empty list gracefully when a timeout occurs."""
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.side_effect = TimeoutError
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert result == []


def test_match_sport_is_set_correctly():
    """Match objects are created with the correct sport."""
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(FAKE_NEXT_RESPONSE_SINGLE_PAGE)
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert result[0].sport == "tennis"


def test_round_info_without_name_uses_round_number():
    """When roundInfo has no 'name', it falls back to 'Round X' format."""
    event_no_round_name = {**FAKE_EVENT, "roundInfo": {"round": 5}}
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.return_value = make_mock_response({
            "events": [event_no_round_name],
            "hasNextPage": False
        })
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert result[0].stage == "Round 5"


def test_no_round_info_uses_tournament_name():
    """When roundInfo is absent, stage falls back to tournament name."""
    event_no_round = {**FAKE_EVENT, "roundInfo": None}
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.return_value = make_mock_response({
            "events": [event_no_round],
            "hasNextPage": False
        })
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert result[0].stage == "ATP Ultra Finals, Mars"
    
    
def test_returns_empty_list_on_empty_near_response():
    """Returns empty list when 'near' endpoint returns an empty response."""
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.side_effect = [
            make_mock_empty_response(),  # 'next' endpoint empty
            make_mock_empty_response()   # 'near' endpoint also empty
        ]
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert result == []
    

def test_returns_partial_results_on_invalid_json_in_pagination():
    """Returns empty list when a paginated response contains invalid JSON."""
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.side_effect = [
            make_mock_response(FAKE_NEXT_RESPONSE_PAGE_1),
            make_mock_invalid_json_response()
        ]
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert result == []


def test_returns_empty_list_on_invalid_json_from_near_endpoint():
    """Returns empty list when 'near' endpoint returns invalid JSON."""
    with patch("functions.get_next_matches.requests.get") as mock_get:
        mock_get.side_effect = [
            make_mock_empty_response(),
            make_mock_invalid_json_response()
        ]
        result = get_next_matches("206570", "Jannik Sinner", "player", "tennis", "UTC")

    assert result == []
