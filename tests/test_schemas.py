import pytest
from pydantic import ValidationError
from objects.schemas import (
    Event, NextPageResponse, NearResponse,
    SearchEntity, SearchResult, SearchResponse
)


# --- Helpers ---

def make_event(**overrides) -> dict:
    base = {
        "id": 1,
        "startTimestamp": 1772823600,
        "homeTeam": {"name": "Carlos Alcaraz"},
        "awayTeam": {"name": "Jannik Sinner"},
        "season": {"name": "ATP Tour"},
        "tournament": {"name": "ATP Finals"},
        "roundInfo": {"round": 1, "name": "Finals"}
    }
    base.update(overrides)
    return base


def make_search_result(**overrides) -> dict:
    base = {
        "entity": {
            "id": 3429,
            "name": "San Antonio Spurs",
            "gender": "M"
        }
    }
    base.update(overrides)
    return base


# --- Event ---

def test_event_valid():
    """Parses a complete valid event."""
    event = Event.model_validate(make_event())
    assert event.id == 1
    assert event.homeTeam.name == "Carlos Alcaraz"
    assert event.awayTeam.name == "Jannik Sinner"
    assert event.season.name == "ATP Tour"
    assert event.tournament.name == "ATP Finals"


def test_event_round_info_optional():
    """Parses an event without roundInfo."""
    event = Event.model_validate(make_event(roundInfo=None))
    assert event.roundInfo is None


def test_event_round_info_without_name():
    """Parses roundInfo that has round number but no name."""
    event = Event.model_validate(make_event(roundInfo={"round": 5}))
    assert event.roundInfo.round == 5
    assert event.roundInfo.name is None


def test_event_missing_required_field_raises():
    """Raises ValidationError when a required field is missing."""
    data = make_event()
    del data["startTimestamp"]
    with pytest.raises(ValidationError):
        Event.model_validate(data)


def test_event_missing_home_team_raises():
    """Raises ValidationError when homeTeam is missing."""
    data = make_event()
    del data["homeTeam"]
    with pytest.raises(ValidationError):
        Event.model_validate(data)


def test_event_id_can_be_string():
    """Accepts event id as a string."""
    event = Event.model_validate(make_event(id="abc123"))
    assert event.id == "abc123"


# --- NextPageResponse ---

def test_next_page_response_valid():
    """Parses a valid next page response."""
    data = {"events": [make_event()], "hasNextPage": False}
    parsed = NextPageResponse.model_validate(data)
    assert len(parsed.events) == 1
    assert parsed.hasNextPage is False


def test_next_page_response_empty_events():
    """Parses a response with an empty events list."""
    data = {"events": [], "hasNextPage": False}
    parsed = NextPageResponse.model_validate(data)
    assert parsed.events == []


def test_next_page_response_multiple_events():
    """Parses a response with multiple events."""
    data = {"events": [make_event(), make_event(id=2)], "hasNextPage": True}
    parsed = NextPageResponse.model_validate(data)
    assert len(parsed.events) == 2
    assert parsed.hasNextPage is True


def test_next_page_response_missing_has_next_page_raises():
    """Raises ValidationError when hasNextPage is missing."""
    data = {"events": [make_event()]}
    with pytest.raises(ValidationError):
        NextPageResponse.model_validate(data)


def test_next_page_response_missing_events_raises():
    """Raises ValidationError when events key is missing."""
    data = {"hasNextPage": False}
    with pytest.raises(ValidationError):
        NextPageResponse.model_validate(data)


def test_next_page_response_invalid_event_raises():
    """Raises ValidationError when an event inside the list is malformed."""
    bad_event = {"id": 1, "startTimestamp": 123}  # missing required fields
    data = {"events": [bad_event], "hasNextPage": False}
    with pytest.raises(ValidationError):
        NextPageResponse.model_validate(data)


# --- NearResponse ---

def test_near_response_valid_list():
    """Parses a near response when nextEvent is a list."""
    data = {"nextEvent": [make_event()]}
    parsed = NearResponse.model_validate(data)
    assert len(parsed.nextEvent) == 1


def test_near_response_normalises_single_dict_to_list():
    """Normalises nextEvent from a single dict to a list of one."""
    data = {"nextEvent": make_event()}
    parsed = NearResponse.model_validate(data)
    assert isinstance(parsed.nextEvent, list)
    assert len(parsed.nextEvent) == 1


def test_near_response_none_next_event():
    """Handles nextEvent being null."""
    data = {"nextEvent": None}
    parsed = NearResponse.model_validate(data)
    assert parsed.nextEvent is None


def test_near_response_missing_next_event_defaults_to_none():
    """nextEvent defaults to None when key is absent."""
    parsed = NearResponse.model_validate({})
    assert parsed.nextEvent is None


def test_near_response_invalid_event_raises():
    """Raises ValidationError when the event inside nextEvent is malformed."""
    bad_event = {"id": 1}  # missing required fields
    data = {"nextEvent": [bad_event]}
    with pytest.raises(ValidationError):
        NearResponse.model_validate(data)


# --- SearchResponse ---

def test_search_response_valid():
    """Parses a valid search response."""
    data = {"results": [make_search_result()]}
    parsed = SearchResponse.model_validate(data)
    assert len(parsed.results) == 1
    assert parsed.results[0].entity.name == "San Antonio Spurs"


def test_search_response_empty_results():
    """Parses a response with no results."""
    parsed = SearchResponse.model_validate({"results": []})
    assert parsed.results == []


def test_search_response_missing_results_defaults_to_empty():
    """Results defaults to empty list when key is absent."""
    parsed = SearchResponse.model_validate({})
    assert parsed.results == []


def test_search_response_player_with_player_team_info():
    """Parses a player entity that includes playerTeamInfo."""
    data = {"results": [make_search_result(entity={
        "id": 275923,
        "name": "Carlos Alcaraz",
        "gender": "M",
        "playerTeamInfo": {"id": 3111}
    })]}
    parsed = SearchResponse.model_validate(data)
    assert parsed.results[0].entity.playerTeamInfo == {"id": 3111}


def test_search_entity_gender_optional():
    """Parses a search entity without gender."""
    data = {"results": [make_search_result(entity={
        "id": 3429,
        "name": "San Antonio Spurs"
    })]}
    parsed = SearchResponse.model_validate(data)
    assert parsed.results[0].entity.gender is None


def test_search_response_missing_entity_raises():
    """Raises ValidationError when a result is missing the entity key."""
    data = {"results": [{"no_entity_key": True}]}
    with pytest.raises(ValidationError):
        SearchResponse.model_validate(data)


def test_search_entity_missing_name_raises():
    """Raises ValidationError when entity is missing required name field."""
    data = {"results": [make_search_result(entity={"id": 1})]}
    with pytest.raises(ValidationError):
        SearchResponse.model_validate(data)