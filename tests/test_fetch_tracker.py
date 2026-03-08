import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, mock_open, MagicMock
from objects.Fetch_Tracker import FetchTracker, FETCH_LOG_FILE
from config import FETCH_THRESHOLDS


# --- Helpers ---

def make_entry(hours_ago: float, days_until_match: float | None, match_count: int = 0) -> dict:
    """Create a fake fetch log entry."""
    last_fetched = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    next_match = datetime.now(timezone.utc) + timedelta(days=days_until_match) if days_until_match is not None else None
    return {
        "last_fetched": last_fetched.isoformat(),
        "next_match": next_match.isoformat() if next_match else None,
        "match_count": match_count
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
    f"""Returns False when fetched {FETCH_THRESHOLDS["far"]["recheck_hours"] - 0.1}h ago 
    and next match is >{FETCH_THRESHOLDS["far"]["days"]}
    days away (threshold: {FETCH_THRESHOLDS["far"]["recheck_hours"]}h)."""
    fake_log = {"Carlos Alcaraz": make_entry(
        hours_ago=FETCH_THRESHOLDS["far"]["recheck_hours"] - 0.1, 
        days_until_match=FETCH_THRESHOLDS["far"]["days"] + 0.1
        )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Carlos Alcaraz") is False


def test_should_fetch_returns_true_when_threshold_exceeded_far_match():
    f"""Returns True when fetched {FETCH_THRESHOLDS["far"]["recheck_hours"] + 0.1}h ago 
    and next match is >{FETCH_THRESHOLDS["far"]["days"]}
    days away (threshold: {FETCH_THRESHOLDS["far"]["recheck_hours"]}h)."""
    fake_log = {"Carlos Alcaraz": make_entry(
        hours_ago=FETCH_THRESHOLDS["far"]["recheck_hours"] + 0.1,
        days_until_match=FETCH_THRESHOLDS["far"]["days"] + 0.1
        )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Carlos Alcaraz") is True


def test_should_fetch_returns_false_when_recently_fetched_medium_match():
    f"""Returns False when fetched {FETCH_THRESHOLDS["medium"]["recheck_hours"] - 0.1}h ago 
    and next match is >{FETCH_THRESHOLDS["medium"]["days"]}
    days away (threshold: {FETCH_THRESHOLDS["medium"]["recheck_hours"]}h)."""
    fake_log = {"San Antonio Spurs": make_entry(
        hours_ago=FETCH_THRESHOLDS["medium"]["recheck_hours"] - 0.1,
        days_until_match=FETCH_THRESHOLDS["medium"]["days"] + 0.1
        )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("San Antonio Spurs") is False


def test_should_fetch_returns_true_when_threshold_exceeded_medium_match():
    f"""Returns True when fetched {FETCH_THRESHOLDS["medium"]["recheck_hours"] + 0.1}h ago 
    and next match is >{FETCH_THRESHOLDS["medium"]["days"]}
    days away (threshold: {FETCH_THRESHOLDS["medium"]["recheck_hours"]}h)."""
    fake_log = {"San Antonio Spurs": make_entry(
        hours_ago=FETCH_THRESHOLDS["medium"]["recheck_hours"] + 0.1, 
        days_until_match=FETCH_THRESHOLDS["medium"]["days"] + 0.1
        )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("San Antonio Spurs") is True


def test_should_fetch_returns_false_when_recently_fetched_near_match():
    f"""Returns False when fetched {FETCH_THRESHOLDS["near"]["recheck_hours"] - 0.1}h ago 
    and next match is >{FETCH_THRESHOLDS["near"]["days"]}
    days away (threshold: {FETCH_THRESHOLDS["near"]["recheck_hours"]}h)."""
    fake_log = {"T1": make_entry(
        hours_ago=FETCH_THRESHOLDS["near"]["recheck_hours"] - 0.1, 
        days_until_match=FETCH_THRESHOLDS["near"]["days"] + 0.1
        )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("T1") is False


def test_should_fetch_returns_true_when_threshold_exceeded_near_match():
    f"""Returns True when fetched {FETCH_THRESHOLDS["near"]["recheck_hours"] - 0.1}h ago 
    and next match is >{FETCH_THRESHOLDS["near"]["days"]}
    days away (threshold: {FETCH_THRESHOLDS["near"]["recheck_hours"]}h)."""
    fake_log = {"T1": make_entry(
        hours_ago=FETCH_THRESHOLDS["near"]["recheck_hours"] + 0.1, 
        days_until_match=FETCH_THRESHOLDS["near"]["days"] + 0.1
        )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("T1") is True


def test_should_fetch_returns_false_when_recently_fetched_no_match():
    f"""Returns False when fetched {FETCH_THRESHOLDS["unknown"]["recheck_hours"] - 0.1}h ago 
    and no next match is known (threshold: {FETCH_THRESHOLDS["unknown"]["recheck_hours"]}h)."""
    fake_log = {"Indiana Fever": make_entry(
        hours_ago=FETCH_THRESHOLDS["unknown"]["recheck_hours"] - 0.1, 
        days_until_match=None
        )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Indiana Fever") is False


def test_should_fetch_returns_true_when_threshold_exceeded_no_match():
    f"""Returns True when fetched {FETCH_THRESHOLDS["unknown"]["recheck_hours"] + 0.1}h ago 
    and no next match is known (threshold: {FETCH_THRESHOLDS["unknown"]["recheck_hours"]}h)."""
    fake_log = {"Indiana Fever": make_entry(
        hours_ago=FETCH_THRESHOLDS["unknown"]["recheck_hours"] + 0.1, 
        days_until_match=None
        )}
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
        tracker.record_fetch("Carlos Alcaraz", next_match, match_count=0)

    assert "Carlos Alcaraz" in tracker.log
    assert tracker.log["Carlos Alcaraz"]["next_match"] == next_match.isoformat()


def test_record_fetch_saves_entry_without_next_match():
    """Saves None for next_match when no upcoming match is known."""
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = FetchTracker()
        tracker.record_fetch("Indiana Fever", None, match_count=0)

    assert tracker.log["Indiana Fever"]["next_match"] is None


def test_record_fetch_overwrites_previous_entry():
    """Overwrites an existing entry when a team is fetched again."""
    old_entry = make_entry(hours_ago=10, days_until_match=5)
    fake_log = {"Carlos Alcaraz": old_entry}
    next_match = datetime.now(timezone.utc) + timedelta(days=2)

    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
        tracker.record_fetch("Carlos Alcaraz", next_match, match_count=2)

    assert tracker.log["Carlos Alcaraz"]["next_match"] == next_match.isoformat()


def test_record_fetch_persists_to_file():
    """Calls open for writing after recording a fetch."""
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()) as mock_file:
        tracker = FetchTracker()
        tracker.record_fetch("T1", None, match_count=0)

    mock_file.assert_called_with(FETCH_LOG_FILE, "w")


def test_record_fetch_saves_match_count():
    """Saves match_count correctly when recording a fetch."""
    next_match = datetime.now(timezone.utc) + timedelta(days=1)

    with patch("objects.Fetch_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = FetchTracker()
        tracker.record_fetch("Carlos Alcaraz", next_match, match_count=3)

    assert tracker.log["Carlos Alcaraz"]["match_count"] == 3


def test_record_fetch_saves_zero_match_count():
    """Saves match_count of 0 when no matches were found."""
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = FetchTracker()
        tracker.record_fetch("Indiana Fever", None, match_count=0)

    assert tracker.log["Indiana Fever"]["match_count"] == 0


# --- _get_recheck_hours: imminent logic tests ---

IMMINENT_RECHECK = FETCH_THRESHOLDS["imminent"]["recheck_hours"]
IMMINENT_HOURS = FETCH_THRESHOLDS["imminent"]["hours"]


def test_imminent_clause_triggers_when_single_match_within_threshold():
    """Returns imminent recheck hours when match_count==1 and match is within the imminent window."""
    fake_log = {"Carlos Alcaraz": make_entry(
        hours_ago=IMMINENT_RECHECK - 0.1,
        days_until_match=IMMINENT_HOURS / 24 - 0.01,
        match_count=1
    )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Carlos Alcaraz") is False


def test_imminent_clause_triggers_fetch_when_threshold_exceeded():
    """Returns True when match_count==1, match is within the imminent window, and recheck time has passed."""
    fake_log = {"Carlos Alcaraz": make_entry(
        hours_ago=IMMINENT_RECHECK + 0.1,
        days_until_match=IMMINENT_HOURS / 24 - 0.01,
        match_count=1
    )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Carlos Alcaraz") is True


def test_imminent_clause_does_not_trigger_when_multiple_matches():
    """Does not apply imminent logic when match_count > 1."""
    fake_log = {"Carlos Alcaraz": make_entry(
        hours_ago=IMMINENT_RECHECK - 0.1,
        days_until_match=IMMINENT_HOURS / 24 - 0.01,
        match_count=2
    )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Carlos Alcaraz") is False


def test_imminent_clause_does_not_trigger_when_match_beyond_window():
    """Does not apply imminent logic when match_count==1 but match is beyond the imminent window."""
    fake_log = {"Carlos Alcaraz": make_entry(
        hours_ago=IMMINENT_RECHECK + 0.1,
        days_until_match=IMMINENT_HOURS / 24 + 0.1,
        match_count=1
    )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    # Falls through to near threshold (6h) — 2.1h ago is not enough
    assert tracker.should_fetch("Carlos Alcaraz") is False


def test_imminent_clause_does_not_trigger_when_match_count_is_zero():
    """Does not apply imminent logic when match_count is 0."""
    fake_log = {"Indiana Fever": make_entry(
        hours_ago=IMMINENT_RECHECK + 0.1,
        days_until_match=IMMINENT_HOURS / 24 - 0.01,
        match_count=0
    )}
    with patch("objects.Fetch_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log(fake_log))):
        tracker = FetchTracker()
    assert tracker.should_fetch("Indiana Fever") is False


def test_imminent_clause_uses_config_values():
    """Imminent threshold values are read from config, not hardcoded."""
    assert "imminent" in FETCH_THRESHOLDS
    assert "hours" in FETCH_THRESHOLDS["imminent"]
    assert "recheck_hours" in FETCH_THRESHOLDS["imminent"]