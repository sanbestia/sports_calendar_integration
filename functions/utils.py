import re
import logging

logger = logging.getLogger(__name__)


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