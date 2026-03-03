import datetime
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'objects'))

from Match import Match

# A fixed start time to use across all tests
START_TIME = datetime.datetime(2025, 6, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)


def make_match(sport="football", tournament="Some League", **kwargs):
    """Helper to create a Match with sensible defaults, overridable via kwargs."""
    return Match(
        side_one="Team A",
        side_two="Team B",
        tournament=tournament,
        stage="Round 1",
        game_id=1,
        sport=sport,
        start_time=START_TIME,
        **kwargs
    )


def test_str_output():
    match = make_match()
    assert str(match) == "Team A vs Team B - Some League (Round 1) @ 2025-06-15 14:00:00"


def test_game_id_stored_as_string():
    match = make_match()
    assert isinstance(match.game_id, str)
    assert match.game_id == "1"


def test_expected_end_time_default():
    match = make_match(sport="football")
    assert match.expected_end_time == START_TIME + datetime.timedelta(hours=2)


def test_expected_end_time_tennis():
    match = make_match(sport="tennis", tournament="ATP 500")
    assert match.expected_end_time == START_TIME + datetime.timedelta(hours=3)


def test_expected_end_time_grand_slam():
    for grand_slam in ["US Open", "Wimbledon", "Australian Open", "French Open"]:
        match = make_match(sport="tennis", tournament=grand_slam)
        assert match.expected_end_time == START_TIME + datetime.timedelta(hours=5), \
            f"Failed for {grand_slam}"


def test_expected_end_time_esport():
    match = make_match(sport="esport")
    assert match.expected_end_time == START_TIME + datetime.timedelta(hours=5)
