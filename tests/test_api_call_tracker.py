import json
import pytest
import os
from datetime import date
from unittest.mock import patch, mock_open, MagicMock
from objects.API_Call_Tracker import APICallTracker, LOG_FILE


def make_log_data(count: int, log_date: date) -> str:
    return json.dumps({"date": str(log_date), "count": count})


# --- Tests ---

def test_initial_count_is_zero_when_no_file():
    """Counter starts at zero when no log file exists."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False):
        tracker = APICallTracker()
    assert tracker.count == 0


def test_loads_count_from_file_if_same_day():
    """Loads count from file when date matches today."""
    today = date.today()
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log_data(42, today))):
        tracker = APICallTracker()
    assert tracker.count == 42


def test_resets_count_if_file_is_from_previous_day():
    """Starts from 0 when log file is from a previous day."""
    yesterday = date(2025, 1, 1)
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=make_log_data(99, yesterday))):
        tracker = APICallTracker()
    assert tracker.count == 0


def test_increment_increases_count():
    """Each increment increases count by one."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = APICallTracker()
        tracker.increment()
        tracker.increment()
    assert tracker.count == 2


def test_increment_saves_to_file():
    """Increment writes updated count to file."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()) as mock_file:
        tracker = APICallTracker()
        tracker.increment()
    mock_file.assert_called_with(LOG_FILE, "w")


def test_status_returns_correct_string():
    """Status string reflects current count and daily limit."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = APICallTracker()
        tracker.increment()
        tracker.increment()
    assert tracker.status() == f"API calls today: 2/{tracker.daily_limit}"


def test_daily_limit_comes_from_config():
    """Daily limit is loaded from config."""
    from config import MAX_API_CALLS
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False):
        tracker = APICallTracker()
    assert tracker.daily_limit == MAX_API_CALLS


def test_resets_on_new_day():
    """Resets count automatically when the date changes."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = APICallTracker()
        tracker.increment()
        tracker.increment()
        assert tracker.count == 2

        with patch("objects.API_Call_Tracker.date") as mock_date:
            mock_date.today.return_value = date(2099, 1, 1)
            tracker.increment()

    assert tracker.count == 1


def test_handles_corrupted_log_file():
    """Starts from 0 gracefully when log file is corrupted."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="not valid json")):
        tracker = APICallTracker()
    assert tracker.count == 0


def test_status_triggers_reset_on_new_day():
    """Status check also triggers a reset if the date has changed."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = APICallTracker()
        tracker.increment()
        tracker.increment()

        with patch("objects.API_Call_Tracker.date") as mock_date:
            mock_date.today.return_value = date(2099, 1, 1)
            status = tracker.status()

    assert status == f"API calls today: 0/{tracker.daily_limit}"
    
    
def test_is_limit_reached_returns_false_when_under_limit():
    """Returns False when count is below the daily limit."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = APICallTracker()
        tracker.increment()
    assert tracker.is_limit_reached() is False


def test_is_limit_reached_returns_true_when_at_limit():
    """Returns True when count equals the daily limit."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = APICallTracker()
        tracker.count = tracker.daily_limit
    assert tracker.is_limit_reached() is True


def test_is_limit_reached_returns_true_when_over_limit():
    """Returns True when count exceeds the daily limit."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = APICallTracker()
        tracker.count = tracker.daily_limit + 1
    assert tracker.is_limit_reached() is True


def test_is_limit_reached_resets_on_new_day():
    """Returns False after a day reset even if count was at the limit."""
    with patch("objects.API_Call_Tracker.os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        tracker = APICallTracker()
        tracker.count = tracker.daily_limit

        with patch("objects.API_Call_Tracker.date") as mock_date:
            mock_date.today.return_value = date(2099, 1, 1)
            result = tracker.is_limit_reached()

    assert result is False