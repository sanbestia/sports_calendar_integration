import json
import logging
import os
from datetime import datetime, timezone

from config import FETCH_THRESHOLDS

logger = logging.getLogger(__name__)

FETCH_LOG_FILE = "fetch_log.json"


class FetchTracker:
    def __init__(self):
        self.log = self._load()

    def _load(self) -> dict:
        """Load fetch log from file, or return empty dict if missing/corrupted."""
        if not os.path.exists(FETCH_LOG_FILE):
            return {}
        try:
            with open(FETCH_LOG_FILE, "r") as f:
                return json.loads(f.read())
        except (json.JSONDecodeError, KeyError):
            logger.error("Could not read fetch_log.json, starting fresh")
            return {}

    def _save(self) -> None:
        """Persist fetch log to file."""
        with open(FETCH_LOG_FILE, "w") as f:
            f.write(json.dumps(self.log, indent=2))

    def should_fetch(self, team_name: str) -> bool:
        """Return True if enough time has passed since the last fetch for this team."""
        entry = self.log.get(team_name)

        if not entry:
            return True

        last_fetched = datetime.fromisoformat(entry["last_fetched"])
        next_match_str = entry.get("next_match")
        next_match = datetime.fromisoformat(next_match_str) if next_match_str else None

        now = datetime.now(timezone.utc)
        hours_since_fetch = (now - last_fetched).total_seconds() / 3600
        recheck_hours = self._get_recheck_hours(next_match, now, entry.get("match_count", 0))

        if hours_since_fetch >= recheck_hours:
            return True

        logger.info(
            f"Skipping {team_name} — fetched {hours_since_fetch:.1f}h ago, "
            f"next check in {recheck_hours - hours_since_fetch:.1f}h"
        )
        return False

    def _get_recheck_hours(self, next_match: datetime | None, now: datetime, match_count: int = 0) -> float:
        """Return the recheck interval in hours based on how soon the next match is."""
        if next_match is None:
            return FETCH_THRESHOLDS["unknown"]["recheck_hours"]

        hours_until_match = (next_match - now).total_seconds() / 3600

        if match_count == 1 and hours_until_match <= FETCH_THRESHOLDS["imminent"]["hours"]:
            return FETCH_THRESHOLDS["imminent"]["recheck_hours"]
        
        days_until_match = hours_until_match / 24

        if days_until_match > FETCH_THRESHOLDS["far"]["days"]:
            return FETCH_THRESHOLDS["far"]["recheck_hours"]
        elif days_until_match > FETCH_THRESHOLDS["medium"]["days"]:
            return FETCH_THRESHOLDS["medium"]["recheck_hours"]
        else:
            return FETCH_THRESHOLDS["near"]["recheck_hours"]


    def record_fetch(self, team_name: str, next_match: datetime | None, match_count: int) -> None:
        """Record that a fetch was just performed for this team, along with their next match time."""
        self.log[team_name] = {
            "last_fetched": datetime.now(timezone.utc).isoformat(),
            "next_match": next_match.isoformat() if next_match else None,
            "match_count": match_count
        }
        self._save()