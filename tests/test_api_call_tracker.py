import pytest
from datetime import date
from unittest.mock import patch
from objects.APICallTracker import APICallTracker


def make_tracker() -> APICallTracker:
    """Create a tracker backed by an in-memory SQLite database."""
    return APICallTracker(db_path=":memory:")


# --- Tests ---

def test_initial_count_is_zero_when_no_entry():
    """Counter starts at zero when no entry exists in the database."""
    tracker = make_tracker()
    assert tracker.count == 0


def test_loads_count_from_db_if_same_day():
    """Loads count from database when date matches today."""
    tracker = make_tracker()
    tracker.increment()
    tracker.increment()

    # Create a second tracker pointing to the same in-memory DB — not possible with :memory:
    # so we verify count is correctly persisted by reloading via _load()
    assert tracker._load() == 2


def test_increment_increases_count():
    """Each increment increases count by one."""
    tracker = make_tracker()
    tracker.increment()
    tracker.increment()
    assert tracker.count == 2


def test_increment_persists_to_db():
    """Increment writes updated count to the database."""
    tracker = make_tracker()
    tracker.increment()
    assert tracker._load() == 1


def test_status_returns_correct_string():
    """Status string reflects current count and daily limit."""
    tracker = make_tracker()
    tracker.increment()
    tracker.increment()
    assert tracker.status() == f"API calls today: 2/{tracker.daily_limit}"


def test_daily_limit_comes_from_config():
    """Daily limit is loaded from config."""
    from config import MAX_API_CALLS
    tracker = make_tracker()
    assert tracker.daily_limit == MAX_API_CALLS


def test_resets_on_new_day():
    """Resets count automatically when the date changes."""
    tracker = make_tracker()
    tracker.increment()
    tracker.increment()
    assert tracker.count == 2

    with patch("objects.APICallTracker.date") as mock_date:
        mock_date.today.return_value = date(2099, 1, 1)
        tracker.increment()

    assert tracker.count == 1


def test_status_triggers_reset_on_new_day():
    """Status check also triggers a reset if the date has changed."""
    tracker = make_tracker()
    tracker.increment()
    tracker.increment()

    with patch("objects.APICallTracker.date") as mock_date:
        mock_date.today.return_value = date(2099, 1, 1)
        status = tracker.status()

    assert status == f"API calls today: 0/{tracker.daily_limit}"


def test_is_limit_reached_returns_false_when_under_limit():
    """Returns False when count is below the daily limit."""
    tracker = make_tracker()
    tracker.increment()
    assert tracker.is_limit_reached() is False


def test_is_limit_reached_returns_true_when_at_limit():
    """Returns True when count equals the daily limit."""
    tracker = make_tracker()
    tracker.count = tracker.daily_limit
    assert tracker.is_limit_reached() is True


def test_is_limit_reached_returns_true_when_over_limit():
    """Returns True when count exceeds the daily limit."""
    tracker = make_tracker()
    tracker.count = tracker.daily_limit + 1
    assert tracker.is_limit_reached() is True


def test_is_limit_reached_resets_on_new_day():
    """Returns False after a day reset even if count was at the limit."""
    tracker = make_tracker()
    tracker.count = tracker.daily_limit

    with patch("objects.APICallTracker.date") as mock_date:
        mock_date.today.return_value = date(2099, 1, 1)
        result = tracker.is_limit_reached()

    assert result is False