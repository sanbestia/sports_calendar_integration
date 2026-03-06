import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, mock_open, MagicMock
from objects.Fetch_Tracker import FetchTracker, FETCH_LOG_FILE


# --- Helpers ---

def make_entry(hours_ago: float, days_until_match: float | None) -> dict:
    """Create a fake fetch log entry."""
    last_fetched = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    next_match = datetime.now(timezone.utc) + timedelta(days=days_until_match) if days_until_match is not None else None
    return {
        "last_fetched": last_fetched.isoformat(),
        "next_match": next_match.isoformat() if next_match else None
    }


def make_log(entries: dict) -> str:
    return json.dumps(entries)


# --- _load tests ---

def test_load_returns_empty_dict_when_no_file():
    """Returns empty dict when fetch log file does not exist."""
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=False):
        tracker = FetchTracker()
    assert tracker.log == {}


def test_load_returns_parsed_log_when_file_exists():
    """Returns parsed dict when fetch log file exists and is valid."""
    fake_log = {"Carlos Alcaraz": {"last_fetched": "2026-01-01T00:00:00+00:00", "next_match": None}}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert "Carlos Alcaraz" in tracker.log


def test_load_returns_empty_dict_on_corrupted_file():
    """Returns empty dict gracefully when fetch log file is corrupted."""
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="not valid json")):
        tracker = FetchTracker()
    assert tracker.log == {}


# --- should_fetch tests ---

def test_should_fetch_returns_true_when_no_entry():
    """Returns True when team has never been fetched."""
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=False):
        tracker = FetchTracker()
    assert tracker.should_fetch("Carlos Alcaraz") is True


def test_should_fetch_returns_false_when_recently_fetched_far_match():
    """Returns False when fetched 1h ago and next match is >7 days away (threshold: 24h)."""
    fake_log = {"Carlos Alcaraz": make_entry(hours_ago=1, days_until_match=10)}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Carlos Alcaraz") is False


def test_should_fetch_returns_true_when_threshold_exceeded_far_match():
    """Returns True when fetched 25h ago and next match is >7 days away (threshold: 24h)."""
    fake_log = {"Carlos Alcaraz": make_entry(hours_ago=25, days_until_match=10)}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Carlos Alcaraz") is True


def test_should_fetch_returns_false_when_recently_fetched_medium_match():
    """Returns False when fetched 3h ago and next match is 2-7 days away (threshold: 6h)."""
    fake_log = {"San Antonio Spurs": make_entry(hours_ago=3, days_until_match=4)}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("San Antonio Spurs") is False


def test_should_fetch_returns_true_when_threshold_exceeded_medium_match():
    """Returns True when fetched 7h ago and next match is 2-7 days away (threshold: 6h)."""
    fake_log = {"San Antonio Spurs": make_entry(hours_ago=7, days_until_match=4)}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("San Antonio Spurs") is True


def test_should_fetch_returns_false_when_recently_fetched_near_match():
    """Returns False when fetched 1h ago and next match is <2 days away (threshold: 2h)."""
    fake_log = {"T1": make_entry(hours_ago=1, days_until_match=0.5)}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("T1") is False


def test_should_fetch_returns_true_when_threshold_exceeded_near_match():
    """Returns True when fetched 3h ago and next match is <2 days away (threshold: 2h)."""
    fake_log = {"T1": make_entry(hours_ago=3, days_until_match=0.5)}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("T1") is True


def test_should_fetch_returns_false_when_recently_fetched_no_match():
    """Returns False when fetched 1h ago and no next match is known (threshold: 24h)."""
    fake_log = {"Indiana Fever": make_entry(hours_ago=1, days_until_match=None)}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Indiana Fever") is False


def test_should_fetch_returns_true_when_threshold_exceeded_no_match():
    """Returns True when fetched 25h ago and no next match is known (threshold: 24h)."""
    fake_log = {"Indiana Fever": make_entry(hours_ago=25, days_until_match=None)}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Indiana Fever") is True


# --- record_fetch tests ---

def test_record_fetch_saves_entry_with_next_match():
    """Saves last_fetched and next_match correctly for a team."""
    next_match = datetime.now(timezone.utc) + timedelta(days=3)

    with patch("objects.Fetch_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()) as mock_file:
        tracker = FetchTracker()
        tracker.record_fetch("Carlos Alcaraz", next_match)

    assert "Carlos Alcaraz" in tracker.log
    assert tracker.log["Carlos Alcaraz"]["next_match"] == next_match.isoformat()


def test_record_fetch_saves_entry_without_next_match():
    """Saves None for next_match when no upcoming match is known."""
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = FetchTracker()
        tracker.record_fetch("Indiana Fever", None)

    assert tracker.log["Indiana Fever"]["next_match"] is None


def test_record_fetch_overwrites_previous_entry():
    """Overwrites an existing entry when a team is fetched again."""
    old_entry = make_entry(hours_ago=10, days_until_match=5)
    fake_log = {"Carlos Alcaraz": old_entry}
    next_match = datetime.now(timezone.utc) + timedelta(days=2)

    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
        tracker.record_fetch("Carlos Alcaraz", next_match)

    assert tracker.log["Carlos Alcaraz"]["next_match"] == next_match.isoformat()


def test_record_fetch_persists_to_file():
    """Calls open for writing after recording a fetch."""
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()) as mock_file:
        tracker = FetchTracker()
        tracker.record_fetch("T1", None)

    mock_file.assert_called_with(FETCH_LOG_FILE, "w")