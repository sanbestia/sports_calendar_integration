import datetime
import re
import time
import logging

logger = logging.getLogger(__name__)


def wait(deadline, time_zone):
    """Sleep until the deadline, waking at most every 3 minutes to re-check."""
    now = datetime.datetime.now(time_zone)
    while now < deadline:
        time_remaining = int((deadline - now).total_seconds())
        time.sleep(min(180, time_remaining + 5))  # cap at 3 min so the deadline is re-checked periodically; +5s buffer avoids waking slightly early
        now = datetime.datetime.now(time_zone)


def sanitize_for_log(value: str) -> str:
    """Strip ANSI escape codes and normalize newlines from external strings before logging.

    Prevents log injection from malicious or malformed API responses containing
    escape sequences or embedded newlines that could spoof log entries.
    """
    value = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', value)  # ANSI escape codes
    value = value.replace('\n', ' ').replace('\r', ' ')
    return value.strip()

def _ask_yes_no(prompt: str) -> bool:
    """Prompt the user with a Y/N question, re-asking until a valid answer is given."""
    while True:
        answer = input(prompt).strip().upper()
        if answer in ("Y", "N"):
            return answer == "Y"
        logger.info("Please answer Y or N.")