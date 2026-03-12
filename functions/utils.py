import re


def sanitize_for_log(value: str) -> str:
    """Strip ANSI escape codes and normalize newlines from external strings before logging.

    Prevents log injection from malicious or malformed API responses containing
    escape sequences or embedded newlines that could spoof log entries.
    """
    value = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', value)  # ANSI escape codes
    value = value.replace('\n', ' ').replace('\r', ' ')
    return value.strip()