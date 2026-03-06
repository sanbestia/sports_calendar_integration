import pytest
from datetime import date
from unittest.mock import patch
from objects.API_Call_Tracker import APICallTracker


def test_initial_count_is_zero():
    """Counter starts at zero."""
    tracker = APICallTracker()
    assert tracker.count == 0


def test_increment_increases_count():
    """Each increment increases count by one."""
    tracker = APICallTracker()
    tracker.increment()
    tracker.increment()
    assert tracker.count == 2


def test_status_returns_correct_string():
    """Status string reflects current count and daily limit."""
    tracker = APICallTracker()
    tracker.increment()
    tracker.increment()
    assert tracker.status() == f"API calls today: 2/{tracker.daily_limit}"


def test_daily_limit_comes_from_config():
    """Daily limit is loaded from config."""
    from config import MAX_API_CALLS
    tracker = APICallTracker()
    assert tracker.daily_limit == MAX_API_CALLS


def test_resets_on_new_day():
    """Resets count automatically when the date changes."""
    tracker = APICallTracker()
    tracker.increment()
    tracker.increment()
    assert tracker.count == 2

    with patch("objects.API_Call_Tracker.date") as mock_date:
        mock_date.today.return_value = date(2099, 1, 1)
        tracker.increment()

    assert tracker.count == 1


def test_does_not_reset_on_same_day():
    """Does not reset count when the date has not changed."""
    tracker = APICallTracker()
    tracker.increment()
    tracker.increment()
    tracker.increment()
    assert tracker.count == 3


def test_status_triggers_reset_on_new_day():
    """Status check also triggers a reset if the date has changed."""
    tracker = APICallTracker()
    tracker.increment()
    tracker.increment()

    with patch("objects.API_Call_Tracker.date") as mock_date:
        mock_date.today.return_value = date(2099, 1, 1)
        status = tracker.status()

    assert status == f"API calls today: 0/{tracker.daily_limit}"