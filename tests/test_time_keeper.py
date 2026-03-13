import datetime
import pytest
from unittest.mock import patch, call
from functions.time_keeper import wait

TIME_ZONE = datetime.timezone.utc


def make_deadline(seconds_from_now: float) -> datetime.datetime:
    return datetime.datetime.now(TIME_ZONE) + datetime.timedelta(seconds=seconds_from_now)


# --- Already past deadline ---

def test_does_not_sleep_when_deadline_already_passed():
    """Does not call time.sleep at all when the deadline is in the past."""
    deadline = datetime.datetime.now(TIME_ZONE) - datetime.timedelta(seconds=1)
    with patch("functions.time_keeper.time.sleep") as mock_sleep:
        wait(deadline, TIME_ZONE)
    mock_sleep.assert_not_called()


# --- Short wait (under 180 seconds) ---

def test_sleeps_once_for_short_remaining_time():
    """Sleeps once with time_remaining + 5 when the deadline is close."""
    now = datetime.datetime.now(TIME_ZONE)
    deadline = now + datetime.timedelta(seconds=10)

    # First call to datetime.now() returns 'now', second returns past the deadline
    with patch("functions.time_keeper.datetime") as mock_dt, \
         patch("functions.time_keeper.time.sleep") as mock_sleep:
        mock_dt.datetime.now.side_effect = [now, deadline + datetime.timedelta(seconds=1)]
        wait(deadline, TIME_ZONE)

    mock_sleep.assert_called_once_with(15)  # 10 + 5


def test_sleep_duration_capped_at_180_seconds():
    """Caps sleep at 180 seconds even when remaining time is much larger."""
    now = datetime.datetime.now(TIME_ZONE)
    deadline = now + datetime.timedelta(seconds=3600)  # 1 hour away

    with patch("functions.time_keeper.datetime") as mock_dt, \
         patch("functions.time_keeper.time.sleep") as mock_sleep:
        mock_dt.datetime.now.side_effect = [now, deadline + datetime.timedelta(seconds=1)]
        wait(deadline, TIME_ZONE)

    mock_sleep.assert_called_once_with(180)


def test_sleeps_multiple_times_until_deadline_reached():
    """Loops and sleeps multiple times until the deadline is finally passed."""
    now = datetime.datetime.now(TIME_ZONE)
    deadline = now + datetime.timedelta(seconds=3600)

    tick_1 = now
    tick_2 = now + datetime.timedelta(seconds=180)
    tick_3 = deadline + datetime.timedelta(seconds=1)  # past deadline — exits loop

    with patch("functions.time_keeper.datetime") as mock_dt, \
         patch("functions.time_keeper.time.sleep") as mock_sleep:
        mock_dt.datetime.now.side_effect = [tick_1, tick_2, tick_3]
        wait(deadline, TIME_ZONE)

    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(180)


def test_sleep_duration_shrinks_as_deadline_approaches():
    """Sleep duration decreases correctly as the deadline gets closer."""
    now = datetime.datetime.now(TIME_ZONE)
    deadline = now + datetime.timedelta(seconds=3600)

    tick_1 = now                                             # 3600s remaining → sleep 180
    tick_2 = now + datetime.timedelta(seconds=3420)          # 180s remaining → sleep 185 → capped to 180... actually 180+5=185 but min(180, 185)=180
    tick_3 = now + datetime.timedelta(seconds=3595)          # 5s remaining → sleep min(180, 10) = 10
    tick_4 = deadline + datetime.timedelta(seconds=1)        # past deadline

    with patch("functions.time_keeper.datetime") as mock_dt, \
         patch("functions.time_keeper.time.sleep") as mock_sleep:
        mock_dt.datetime.now.side_effect = [tick_1, tick_2, tick_3, tick_4]
        wait(deadline, TIME_ZONE)

    assert mock_sleep.call_count == 3
    assert mock_sleep.call_args_list == [call(180), call(180), call(10)]


def test_uses_provided_time_zone():
    """Calls datetime.now with the provided time_zone argument."""
    tz = datetime.timezone(datetime.timedelta(hours=-3))
    now = datetime.datetime.now(tz)
    deadline = now - datetime.timedelta(seconds=1)  # already past, so no loop

    with patch("functions.time_keeper.datetime") as mock_dt, \
         patch("functions.time_keeper.time.sleep"):
        mock_dt.datetime.now.return_value = now + datetime.timedelta(seconds=1)
        wait(deadline, tz)

    mock_dt.datetime.now.assert_called_with(tz)