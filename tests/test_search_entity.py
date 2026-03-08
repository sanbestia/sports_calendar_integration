import json
import pytest
from unittest.mock import patch, MagicMock
from functions.search_entity import search_entity, pick_entity


# --- Helpers ---

def make_mock_response(data: dict) -> MagicMock:
    mock = MagicMock()
    mock.text = json.dumps(data)
    return mock


def make_mock_empty_response() -> MagicMock:
    mock = MagicMock()
    mock.text = ""
    return mock


def make_mock_invalid_response() -> MagicMock:
    mock = MagicMock()
    mock.text = "<html>Internal Server Error</html>"
    return mock


FAKE_TEAM_ENTITY = {
    "results": [
        {
            "type": "team",
            "entity": {
                "id": 3429,
                "name": "San Antonio Spurs",
                "gender": "M",
                "sport": {"slug": "basketball"}
            }
        }
    ]
}

FAKE_PLAYER_ENTITY = {
    "results": [
        {
            "type": "team",  # API labels tennis players as "team"
            "entity": {
                "id": 275923,
                "name": "Carlos Alcaraz",
                "gender": "M",
                "sport": {"slug": "tennis"},
                "playerTeamInfo": {"id": 3111}
            }
        }
    ]
}

FAKE_MULTIPLE_ENTITIES = {
    "results": [
        {
            "type": "team",
            "entity": {
                "id": 3429,
                "name": "San Antonio Spurs",
                "gender": "M",
                "sport": {"slug": "basketball"}
            }
        },
        {
            "type": "player",
            "entity": {
                "id": 998725,
                "name": "Victor Wembanyama",
                "gender": "M",
                "sport": {"slug": "basketball"},
                "playerTeamInfo": {"id": 3429}
            }
        }
    ]
}


# --- search_entity tests ---

def test_search_entity_returns_list_of_hits():
    """Returns a list of hits for a valid search."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(FAKE_TEAM_ENTITY)
        result = search_entity("spurs", "basketball", MagicMock())

    assert len(result) == 1
    assert result[0]["id"] == "3429"
    assert result[0]["name"] == "San Antonio Spurs"
    assert result[0]["sport"] == "basketball"


def test_search_entity_sets_player_type_team_when_no_player_team_info():
    """Sets player_type to 'team' when entity has no playerTeamInfo."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(FAKE_TEAM_ENTITY)
        result = search_entity("spurs", "basketball", MagicMock())

    assert result[0]["player_type"] == "team"


def test_search_entity_sets_player_type_player_when_player_team_info_present():
    """Sets player_type to 'player' when entity has playerTeamInfo."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(FAKE_PLAYER_ENTITY)
        result = search_entity("alcaraz", "tennis", MagicMock())

    assert result[0]["player_type"] == "player"
    assert result[0]["id"] == "275923"


def test_search_entity_returns_empty_list_on_empty_response():
    """Returns empty list when API returns an empty response."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.return_value = make_mock_empty_response()
        result = search_entity("zzzzz", "basketball", MagicMock())

    assert result == []


def test_search_entity_returns_empty_list_on_invalid_json():
    """Returns empty list when API returns invalid JSON."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.return_value = make_mock_invalid_response()
        result = search_entity("spurs", "basketball", MagicMock())

    assert result == []


def test_search_entity_returns_empty_list_on_connection_error():
    """Returns empty list gracefully when a network error occurs."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.side_effect = ConnectionError
        result = search_entity("spurs", "basketball", MagicMock())

    assert result == []


def test_search_entity_returns_empty_list_on_timeout():
    """Returns empty list gracefully when a timeout occurs."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.side_effect = TimeoutError
        result = search_entity("spurs", "basketball", MagicMock())

    assert result == []


def test_search_entity_increments_tracker():
    """Increments the tracker on a successful request."""
    mock_tracker = MagicMock()
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(FAKE_TEAM_ENTITY)
        search_entity("spurs", "basketball", mock_tracker)

    mock_tracker.increment.assert_called_once()


def test_search_entity_does_not_increment_tracker_on_error():
    """Does not increment the tracker when a network error occurs."""
    mock_tracker = MagicMock()
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.side_effect = ConnectionError
        search_entity("spurs", "basketball", mock_tracker)

    mock_tracker.increment.assert_not_called()


def test_search_entity_omits_sport_segment_for_football():
    """Builds URL without sport segment for football."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(FAKE_TEAM_ENTITY)
        search_entity("argentina", "football", MagicMock())

    called_url = mock_get.call_args[0][0]
    assert "/football/" not in called_url
    assert "/search/argentina" in called_url


def test_search_entity_includes_sport_segment_for_non_football():
    """Builds URL with sport segment for non-football sports."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(FAKE_TEAM_ENTITY)
        search_entity("spurs", "basketball", MagicMock())

    called_url = mock_get.call_args[0][0]
    assert "/basketball/search/spurs" in called_url


def test_search_entity_returns_multiple_hits():
    """Returns all hits when API returns multiple results."""
    with patch("functions.search_entity.requests.get") as mock_get:
        mock_get.return_value = make_mock_response(FAKE_MULTIPLE_ENTITIES)
        result = search_entity("spurs", "basketball", MagicMock())

    assert len(result) == 2


# --- pick_entity tests ---

FAKE_HITS = [
    {"id": "3429", "name": "San Antonio Spurs", "player_type": "team", "gender": "M", "sport": "basketball"},
    {"id": "9999", "name": "San Antonio FC",    "player_type": "team", "gender": "M", "sport": "basketball"},
]

FAKE_SINGLE_HIT = [
    {"id": "3429", "name": "San Antonio Spurs", "player_type": "team", "gender": "M", "sport": "basketball"},
]


def test_pick_entity_returns_none_on_empty_list():
    """Returns None when hits list is empty."""
    result = pick_entity([])
    assert result is None


def test_pick_entity_returns_chosen_when_confirmed():
    """Returns the chosen hit when user confirms."""
    with patch("builtins.input", side_effect=["1", "Y"]):
        result = pick_entity(FAKE_HITS)

    assert result["id"] == "3429"


def test_pick_entity_returns_none_when_rejected():
    """Returns None when user rejects the selection."""
    with patch("builtins.input", side_effect=["1", "N"]):
        result = pick_entity(FAKE_HITS)

    assert result is None


def test_pick_entity_skips_selection_prompt_for_single_hit():
    """Skips the number selection prompt when there is only one result."""
    with patch("builtins.input", return_value="Y") as mock_input:
        result = pick_entity(FAKE_SINGLE_HIT)

    assert result["id"] == "3429"
    # Only one input call — the confirmation — no number selection
    assert mock_input.call_count == 1


def test_pick_entity_returns_correct_hit_when_second_option_chosen():
    """Returns the second hit when user selects option 2."""
    with patch("builtins.input", side_effect=["2", "Y"]):
        result = pick_entity(FAKE_HITS)

    assert result["id"] == "9999"
    assert result["name"] == "San Antonio FC"


# --- _ask_yes_no tests ---

from functions.search_entity import _ask_yes_no

def test_ask_yes_no_returns_true_on_y():
    """Returns True when user inputs Y."""
    with patch("builtins.input", return_value="Y"):
        assert _ask_yes_no("Continue? Y/N: ") is True


def test_ask_yes_no_returns_false_on_n():
    """Returns False when user inputs N."""
    with patch("builtins.input", return_value="N"):
        assert _ask_yes_no("Continue? Y/N: ") is False


def test_ask_yes_no_is_case_insensitive():
    """Accepts lowercase y and n."""
    with patch("builtins.input", side_effect=["y"]):
        assert _ask_yes_no("Continue? Y/N: ") is True
    with patch("builtins.input", side_effect=["n"]):
        assert _ask_yes_no("Continue? Y/N: ") is False


def test_ask_yes_no_retries_on_invalid_input():
    """Re-prompts when user enters something other than Y or N."""
    with patch("builtins.input", side_effect=["maybe", "yes", "Y"]):
        result = _ask_yes_no("Continue? Y/N: ")
    assert result is True


# --- pick_entity input validation tests ---

def test_pick_entity_retries_on_non_numeric_input():
    """Re-prompts when user enters a non-numeric selection."""
    with patch("builtins.input", side_effect=["abc", "1", "Y"]):
        result = pick_entity(FAKE_HITS)
    assert result["id"] == "3429"


def test_pick_entity_retries_on_out_of_range_input():
    """Re-prompts when user enters a number outside valid range."""
    with patch("builtins.input", side_effect=["0", "99", "1", "Y"]):
        result = pick_entity(FAKE_HITS)
    assert result["id"] == "3429"


def test_pick_entity_retries_on_invalid_confirmation():
    """Re-prompts when user enters something other than Y/N at confirmation."""
    with patch("builtins.input", side_effect=["1", "maybe", "Y"]):
        result = pick_entity(FAKE_HITS)
    assert result["id"] == "3429"