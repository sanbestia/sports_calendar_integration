import datetime
import time


def wait(deadline, time_zone):
    """Sleep until the deadline, waking at most every 3 minutes to re-check."""
    now = datetime.datetime.now(time_zone)
    while now < deadline:
        time_remaining = int((deadline - now).total_seconds())
        time.sleep(min(180, time_remaining + 5))  # cap at 3 min so the deadline is re-checked periodically; +5s buffer avoids waking slightly early
        now = datetime.datetime.now(time_zone)
