import logging
from datetime import date
from config import MAX_API_CALLS

logger = logging.getLogger(__name__)


class APICallTracker:
    def __init__(self):
        self.daily_limit = MAX_API_CALLS
        self.count = 0
        self.current_date = date.today()

    def _check_reset(self) -> None:
        """Reset counter if the date has changed since last call."""
        today = date.today()
        if today != self.current_date:
            logger.info(f"New day detected, resetting API call counter (was {self.count})")
            self.count = 0
            self.current_date = today

    def increment(self) -> None:
        """Register one API call."""
        self._check_reset()
        self.count += 1

    def status(self) -> str:
        """Return a human-readable status string."""
        self._check_reset()
        return f"API calls today: {self.count}/{self.daily_limit}"