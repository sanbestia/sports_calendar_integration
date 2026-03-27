import sqlite3
import logging
from datetime import datetime, timezone

from config import FETCH_THRESHOLDS

logger = logging.getLogger(__name__)

DB_FILE = "fetch_log.db"


class FetchTracker:
    def __init__(self, db_path: str = DB_FILE):
        """Initialise the tracker and create the fetch_log table if it doesn't exist."""
        self._db_path = db_path
        # For :memory: databases, keep a single connection alive for the lifetime
        # of the object — each new connection() call would get its own empty database
        self._conn = sqlite3.connect(db_path, check_same_thread=False) if db_path == ":memory:" else None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Return the persistent in-memory connection, or open a new file-based connection."""
        if self._conn is not None:
            return self._conn
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        """Create the table if it doesn't exist yet."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fetch_log (
                    team_name TEXT PRIMARY KEY,
                    last_fetched TEXT NOT NULL,
                    next_match TEXT,
                    match_count INTEGER NOT NULL DEFAULT 0
                )
            """)

    def should_fetch(self, team_name: str) -> bool:
        """Return True if enough time has passed since the last fetch for this team."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_fetched, next_match, match_count FROM fetch_log WHERE team_name = ?",
                (team_name,)
            ).fetchone()

        if not row:  # no entry for this team yet; first fetch is always allowed
            return True

        last_fetched = datetime.fromisoformat(row[0])
        next_match = datetime.fromisoformat(row[1]) if row[1] else None
        match_count = row[2]

        now = datetime.now(timezone.utc)
        hours_since_fetch = (now - last_fetched).total_seconds() / 3600
        recheck_hours = self._get_recheck_hours(next_match, now, match_count)

        if hours_since_fetch >= recheck_hours:
            return True

        return False

    def hours_until_next_fetch(self, team_name: str) -> float:
        """Return how many hours until this team is due for a fetch (0.0 if due now or no record)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_fetched, next_match, match_count FROM fetch_log WHERE team_name = ?",
                (team_name,)
            ).fetchone()

        if not row:
            return 0.0

        last_fetched = datetime.fromisoformat(row[0])
        next_match = datetime.fromisoformat(row[1]) if row[1] else None
        match_count = row[2]

        now = datetime.now(timezone.utc)
        hours_since_fetch = (now - last_fetched).total_seconds() / 3600
        recheck_hours = self._get_recheck_hours(next_match, now, match_count)
        return max(0.0, recheck_hours - hours_since_fetch)

    def _get_recheck_hours(self, next_match: datetime | None, now: datetime, match_count: int = 0) -> float:
        """Return the recheck interval in hours based on how soon the next match is."""
        if next_match is None:
            return FETCH_THRESHOLDS["unknown"]["recheck_hours"]

        hours_until_match = (next_match - now).total_seconds() / 3600

        if match_count == 1:  # imminent-interval checks only apply when a single upcoming match is known
            if hours_until_match <= FETCH_THRESHOLDS["imminent_close"]["hours"]:
                return FETCH_THRESHOLDS["imminent_close"]["recheck_hours"]
            if hours_until_match <= FETCH_THRESHOLDS["imminent"]["hours"]:
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
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO fetch_log (team_name, last_fetched, next_match, match_count) VALUES (?, ?, ?, ?)
                ON CONFLICT(team_name) DO UPDATE SET
                    last_fetched = excluded.last_fetched,
                    next_match = excluded.next_match,
                    match_count = excluded.match_count
            """, (
                team_name,
                datetime.now(timezone.utc).isoformat(),
                next_match.isoformat() if next_match else None,
                match_count
            ))