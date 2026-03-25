import sqlite3
from datetime import date, datetime, timezone

import pandas as pd

from config import MAX_API_CALLS, FETCH_THRESHOLDS
from objects.APICallTracker import DB_FILE as API_CALLS_DB
from objects.FetchTracker import DB_FILE as FETCH_LOG_DB


def _connect(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


# --- API calls ---

def calls_today(db_path: str = API_CALLS_DB) -> int:
    """Return the number of API calls made today."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT count FROM api_calls WHERE date = ?",
            (str(date.today()),)
        ).fetchone()
    return row[0] if row else 0


def calls_on(day: date, db_path: str = API_CALLS_DB) -> int:
    """Return the number of API calls made on a specific date."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT count FROM api_calls WHERE date = ?",
            (str(day),)
        ).fetchone()
    return row[0] if row else 0


def days_at_max(db_path: str = API_CALLS_DB, limit: int = MAX_API_CALLS) -> list[date]:
    """Return all dates where the API call count reached or exceeded the daily limit."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT date FROM api_calls WHERE count >= ? ORDER BY date",
            (limit,)
        ).fetchall()
    return [date.fromisoformat(row[0]) for row in rows]


def pct_days_at_max(db_path: str = API_CALLS_DB, limit: int = MAX_API_CALLS) -> float:
    """Return the percentage of recorded days where the API limit was reached."""
    with _connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM api_calls").fetchone()[0]
        at_max = conn.execute(
            "SELECT COUNT(*) FROM api_calls WHERE count >= ?", (limit,)
        ).fetchone()[0]
    return (at_max / total * 100) if total else 0.0


def avg_daily_calls(db_path: str = API_CALLS_DB) -> float:
    """Return the average number of API calls per recorded day."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT AVG(count) FROM api_calls").fetchone()
    return row[0] if row[0] is not None else 0.0


def all_calls_df(db_path: str = API_CALLS_DB, limit: int = MAX_API_CALLS) -> pd.DataFrame:
    """Return a DataFrame of all recorded days with columns: date, count, at_limit."""
    with _connect(db_path) as conn:
        df = pd.read_sql_query("SELECT date, count FROM api_calls ORDER BY date", conn)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["at_limit"] = df["count"] >= limit
    return df


def remaining_calls_today(db_path: str = API_CALLS_DB, limit: int = MAX_API_CALLS) -> int:
    """Return how many API calls remain before today's limit is reached (floor 0)."""
    return max(0, limit - calls_today(db_path))


def calls_in_range(start: date, end: date, db_path: str = API_CALLS_DB) -> int:
    """Return the total number of API calls made between start and end dates (inclusive)."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(count), 0) FROM api_calls WHERE date BETWEEN ? AND ?",
            (str(start), str(end))
        ).fetchone()
    return row[0]


def busiest_days(n: int = 5, db_path: str = API_CALLS_DB, limit: int = MAX_API_CALLS) -> pd.DataFrame:
    """Return the top N days by API call volume."""
    df = all_calls_df(db_path, limit=limit)
    return df.nlargest(n, "count").reset_index(drop=True)


def calls_per_period(freq: str = "W", db_path: str = API_CALLS_DB, limit: int = MAX_API_CALLS) -> pd.DataFrame:
    """Return API call totals grouped by time period.

    freq: any pandas offset alias — e.g. 'W' (week), 'ME' (month end), 'QE' (quarter end).
    Columns: date (period start), total_calls, days_recorded, days_at_limit.
    """
    df = all_calls_df(db_path, limit=limit)
    if df.empty:
        return pd.DataFrame(columns=["date", "total_calls", "days_recorded", "days_at_limit"])
    indexed = df.set_index(pd.to_datetime(df["date"]))
    result = pd.DataFrame({
        "total_calls": indexed["count"].resample(freq).sum(),
        "days_recorded": indexed["count"].resample(freq).count(),
        "days_at_limit": indexed["at_limit"].resample(freq).sum().astype(int),
    }).reset_index()
    result.rename(columns={"date": "period_start"}, inplace=True)
    result["period_start"] = result["period_start"].dt.date
    return result


def api_budget_forecast(db_path: str = API_CALLS_DB, limit: int = MAX_API_CALLS) -> dict:
    """Project today's total API calls based on the current rate since midnight.

    Returns a dict with: calls_so_far, hours_elapsed, rate_per_hour,
    projected_daily_total, limit, will_exceed_limit.
    """
    count = calls_today(db_path)
    now = datetime.now()
    hours_elapsed = now.hour + now.minute / 60 + now.second / 3600
    rate_per_hour = count / hours_elapsed if hours_elapsed > 0 else 0.0
    projected = round(rate_per_hour * 24)
    return {
        "calls_so_far": count,
        "hours_elapsed": round(hours_elapsed, 2),
        "rate_per_hour": round(rate_per_hour, 2),
        "projected_daily_total": projected,
        "limit": limit,
        "will_exceed_limit": projected >= limit,
    }


# --- Fetch log ---

def all_fetches_df(db_path: str = FETCH_LOG_DB) -> pd.DataFrame:
    """Return a DataFrame of all teams with their last fetch info."""
    with _connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT team_name, last_fetched, next_match, match_count FROM fetch_log ORDER BY team_name",
            conn
        )
    df["last_fetched"] = pd.to_datetime(df["last_fetched"], utc=True)
    df["next_match"] = pd.to_datetime(df["next_match"], utc=True, errors="coerce")
    return df


def fetch_gap_df(db_path: str = FETCH_LOG_DB) -> pd.DataFrame:
    """Return a DataFrame with derived timing columns per team.

    Columns: team_name, last_fetched, next_match, match_count,
             hours_since_fetch, hours_until_match
    """
    df = all_fetches_df(db_path)
    now = pd.Timestamp.now(tz="UTC")
    df["hours_since_fetch"] = (now - df["last_fetched"]).dt.total_seconds() / 3600
    df["hours_until_match"] = (df["next_match"] - now).dt.total_seconds() / 3600
    return df


def teams_due_now(db_path: str = FETCH_LOG_DB) -> list[str]:
    """Return team names that the scheduler would fetch right now.

    Reuses FetchTracker's threshold logic so results match actual scheduler behaviour.
    """
    from objects.FetchTracker import FetchTracker
    tracker = FetchTracker(db_path=db_path)
    df = all_fetches_df(db_path)
    return [name for name in df["team_name"] if tracker.should_fetch(name)]


def teams_with_no_upcoming_match(db_path: str = FETCH_LOG_DB) -> list[str]:
    """Return team names for which no upcoming match is recorded."""
    df = all_fetches_df(db_path)
    return df[df["next_match"].isna()]["team_name"].tolist()


def stale_teams(hours: float = 48, db_path: str = FETCH_LOG_DB) -> pd.DataFrame:
    """Return teams not fetched in the last `hours` hours, regardless of their schedule.

    Sorted by hours_since_fetch descending (stalest first).
    """
    df = fetch_gap_df(db_path)
    return df[df["hours_since_fetch"] > hours].sort_values("hours_since_fetch", ascending=False).reset_index(drop=True)
