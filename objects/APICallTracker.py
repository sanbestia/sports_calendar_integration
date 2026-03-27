import sqlite3
import logging
from datetime import date
from config import MAX_API_CALLS

logger = logging.getLogger(__name__)

DB_FILE = "api_calls.db"


class APICallTracker:
    def __init__(self, db_path: str = DB_FILE):
        """Initialise the tracker, creating the database table and loading today's call count."""
        self.daily_limit = MAX_API_CALLS
        self.current_date = date.today()  # cached locally; compared in _check_reset to detect day rollover
        self._db_path = db_path
        # For :memory: databases, keep a single connection alive for the lifetime
        # of the object — each new connection() call would get its own empty database
        self._conn = sqlite3.connect(db_path, check_same_thread=False) if db_path == ":memory:" else None
        self._init_db()
        self.count = self._load()

    def _connect(self) -> sqlite3.Connection:
        """Return the persistent in-memory connection, or open a new file-based connection."""
        if self._conn is not None:
            return self._conn
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        """Create the table if it doesn't exist yet."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    date TEXT PRIMARY KEY,
                    count INTEGER NOT NULL DEFAULT 0
                )
            """)

    def _load(self) -> int:
        """Load today's count from the database, or return 0 if no entry exists."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT count FROM api_calls WHERE date = ?",
                (str(self.current_date),)
            ).fetchone()
        return row[0] if row else 0

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
        with self._connect() as conn:
            # UPSERT: 'excluded' refers to the row that was going to be inserted
            conn.execute("""
                INSERT INTO api_calls (date, count) VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET count = excluded.count
            """, (str(self.current_date), self.count))

    def is_limit_reached(self) -> bool:
        """Return True if the daily API call limit has been reached."""
        self._check_reset()
        return self.count >= self.daily_limit

    def status(self) -> str:
        """Return a human-readable status string."""
        self._check_reset()
        return f"API calls today: {self.count}/{self.daily_limit}"