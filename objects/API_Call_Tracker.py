import json
import os
from datetime import date
from config import MAX_API_CALLS
import logging


logger = logging.getLogger(__name__)

LOG_FILE = "api_call_log.json"


class APICallTracker:
    def __init__(self):
        self.daily_limit = MAX_API_CALLS
        self.current_date = date.today()
        self.count = self._load()


    def _load(self) -> int:
        """Load count from file if it exists and is from today, otherwise return 0."""
        if not os.path.exists(LOG_FILE):
            return 0
        try:
            with open(LOG_FILE, "r") as f:
                data = json.loads(f.read())
            if data.get("date") == str(self.current_date):
                return data.get("count", 0)
            return 0
        except (json.JSONDecodeError, KeyError):
            logger.error("Could not read api_call_log.json, starting count from 0")
            return 0


    def _save(self) -> None:
        """Save current count and date to file."""
        with open(LOG_FILE, "w") as f:
            json.dump({"date": str(self.current_date), "count": self.count}, f)


    def _check_reset(self) -> None:
        """Reset counter if the date has changed since last call."""
        today = date.today()
        if today != self.current_date:
            logger.info(f"New day detected, resetting API call counter (was {self.count})")
            self.count = 0
            self.current_date = today
            self._save()


    def increment(self) -> None:
        """Register one API call."""
        self._check_reset()
        self.count += 1
        self._save()


    def status(self) -> str:
        """Return a human-readable status string."""
        self._check_reset()
        return f"API calls today: {self.count}/{self.daily_limit}"