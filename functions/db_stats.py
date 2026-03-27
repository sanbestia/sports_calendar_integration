import os
import sys

# When run directly, the script's directory (functions/) is on sys.path, not the project root.
# This must happen before the project-relative imports below.
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import inspect
import logging
import sqlite3
from datetime import date, datetime, timezone

import pandas as pd

from config import MAX_API_CALLS, FETCH_THRESHOLDS
from objects.APICallTracker import DB_FILE as API_CALLS_DB
from objects.FetchTracker import DB_FILE as FETCH_LOG_DB


def _connect(db_path: str) -> sqlite3.Connection:
    """Open a read-only connection to the given SQLite database file."""
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)  # read-only URI prevents analytics code from accidentally writing


def _fmt_datetime(dt) -> str:
    """Format a pandas Timestamp or datetime as 'DD-MM-YYYY HH:MM:SS +00:00'; returns '' for NaT/None."""
    if pd.isna(dt):
        return ""
    return pd.Timestamp(dt).tz_convert("UTC").strftime("%d-%m-%Y %H:%M:%S +00:00")


def _fmt_float(f: float) -> float:
    """Round a float to 2 decimal places."""
    return round(f, 2)


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


def days_at_max(db_path: str = API_CALLS_DB, limit: int = MAX_API_CALLS, raw: bool = False) -> list:
    """Return all dates where the API call count reached or exceeded the daily limit.

    raw=False (default): returns dates as 'DD-MM-YYYY' strings.
    raw=True: returns datetime.date objects for programmatic use.
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT date FROM api_calls WHERE count >= ? ORDER BY date",
            (limit,)
        ).fetchall()
    dates = [date.fromisoformat(row[0]) for row in rows]
    if raw:
        return dates
    return [d.strftime("%d-%m-%Y") for d in dates]


def pct_days_at_max(db_path: str = API_CALLS_DB, limit: int = MAX_API_CALLS, raw: bool = False) -> float | str:
    """Return the percentage of recorded days where the API limit was reached.

    raw=False (default): returns a formatted string like '42.50%'.
    raw=True: returns a raw float for programmatic use.
    """
    with _connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM api_calls").fetchone()[0]
        at_max = conn.execute(
            "SELECT COUNT(*) FROM api_calls WHERE count >= ?", (limit,)
        ).fetchone()[0]
    value = (at_max / total * 100) if total else 0.0
    if raw:
        return value
    return f"{value:.2f}%"


def avg_daily_calls(db_path: str = API_CALLS_DB, raw: bool = False) -> float:
    """Return the average number of API calls per recorded day.

    raw=False (default): returns value rounded to 2 decimal places.
    raw=True: returns full-precision float for programmatic use.
    """
    with _connect(db_path) as conn:
        row = conn.execute("SELECT AVG(count) FROM api_calls").fetchone()
    value = row[0] if row[0] is not None else 0.0
    if raw:
        return value
    return _fmt_float(value)


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
    indexed = df.set_index(pd.to_datetime(df["date"]))  # DatetimeIndex is required for resample()
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
    projected = round(rate_per_hour * 24)  # linear extrapolation to end of day assuming constant rate
    return {
        "calls_so_far": count,
        "hours_elapsed": round(hours_elapsed, 2),
        "rate_per_hour": round(rate_per_hour, 2),
        "projected_daily_total": projected,
        "limit": limit,
        "will_exceed_limit": projected >= limit,
    }


# --- Fetch log ---

def all_fetches_df(db_path: str = FETCH_LOG_DB, raw: bool = False) -> pd.DataFrame:
    """Return a DataFrame of all teams with their last fetch info.

    raw=False (default): datetime columns formatted as 'DD-MM-YYYY HH:MM:SS +00:00' strings.
    raw=True: datetime columns as pandas Timestamps for programmatic use.
    """
    with _connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT team_name, last_fetched, next_match, match_count FROM fetch_log ORDER BY team_name",
            conn
        )
    df["last_fetched"] = pd.to_datetime(df["last_fetched"], utc=True)
    df["next_match"] = pd.to_datetime(df["next_match"], utc=True, errors="coerce")
    if raw:
        return df
    df["last_fetched"] = df["last_fetched"].map(_fmt_datetime)
    df["next_match"] = df["next_match"].map(_fmt_datetime)
    return df


def fetch_gap_df(db_path: str = FETCH_LOG_DB, raw: bool = False) -> pd.DataFrame:
    """Return a DataFrame with derived timing columns per team.

    Columns: team_name, last_fetched, next_match, match_count,
             hours_since_fetch, hours_until_match

    raw=False (default): datetime columns formatted as strings, floats rounded to 2dp.
    raw=True: native types for programmatic use.
    """
    df = all_fetches_df(db_path, raw=True)  # raw=True so Timestamps are available for arithmetic
    now = pd.Timestamp.now(tz="UTC")
    df["hours_since_fetch"] = (now - df["last_fetched"]).dt.total_seconds() / 3600
    df["hours_until_match"] = (df["next_match"] - now).dt.total_seconds() / 3600
    if raw:
        return df
    df["last_fetched"] = df["last_fetched"].map(_fmt_datetime)
    df["next_match"] = df["next_match"].map(_fmt_datetime)
    df["hours_since_fetch"] = df["hours_since_fetch"].map(_fmt_float)
    df["hours_until_match"] = df["hours_until_match"].map(_fmt_float)
    return df


def teams_due_now(db_path: str = FETCH_LOG_DB) -> list[str]:
    """Return team names that the scheduler would fetch right now.

    Reuses FetchTracker's threshold logic so results match actual scheduler behaviour.
    """
    from objects.FetchTracker import FetchTracker
    tracker = FetchTracker(db_path=db_path)
    df = all_fetches_df(db_path, raw=True)  # raw=True; team_name column is unaffected by formatting
    return [name for name in df["team_name"] if tracker.should_fetch(name)]


def teams_with_no_upcoming_match(db_path: str = FETCH_LOG_DB) -> list[str]:
    """Return team names for which no upcoming match is recorded."""
    df = all_fetches_df(db_path, raw=True)  # raw=True so isna() works on Timestamps (not empty strings)
    return df[df["next_match"].isna()]["team_name"].tolist()


def stale_teams(hours: float = 48, db_path: str = FETCH_LOG_DB, raw: bool = False) -> pd.DataFrame:
    """Return teams not fetched in the last `hours` hours, regardless of their schedule.

    Sorted by hours_since_fetch descending (stalest first).

    raw=False (default): datetime columns formatted as strings, floats rounded to 2dp.
    raw=True: native types for programmatic use.
    """
    df = fetch_gap_df(db_path, raw=True)  # raw=True so numeric comparison on hours_since_fetch works
    result = df[df["hours_since_fetch"] > hours].sort_values("hours_since_fetch", ascending=False).reset_index(drop=True)
    if raw:
        return result
    result = result.copy()
    result["last_fetched"] = result["last_fetched"].map(_fmt_datetime)
    result["next_match"] = result["next_match"].map(_fmt_datetime)
    result["hours_since_fetch"] = result["hours_since_fetch"].map(_fmt_float)
    result["hours_until_match"] = result["hours_until_match"].map(_fmt_float)
    return result


def main() -> None:
    """CLI entry point: call any public function in this module by name."""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    _log = logging.getLogger(__name__)

    # Collect all public functions defined in this file (exclude imported symbols)
    _this_file = os.path.abspath(__file__)
    _available_fns: dict = {}
    for _name, _obj in inspect.getmembers(sys.modules[__name__], inspect.isfunction):
        if _name.startswith("_") or _name == "main":
            continue
        try:
            if inspect.getfile(_obj) == _this_file:
                _available_fns[_name] = _obj
        except TypeError:
            pass

    _parser = argparse.ArgumentParser(prog="db_stats.py", add_help=True)
    _parser.add_argument("function", nargs="?", metavar="FUNCTION")
    _parser.add_argument("params", nargs="*", metavar="PARAM")
    _args = _parser.parse_args()

    if not _args.function:
        _log.warning("No function specified.")
        _log.warning("Usage: python db_stats.py <function> [params...]")
        _log.warning("")
        _log.warning("Available functions:")
        for _fn_name, _fn in sorted(_available_fns.items()):
            _signature = inspect.signature(_fn)
            _first_doc_line = (_fn.__doc__ or "").split("\n")[0].strip()
            _log.warning(f" * {_fn_name} {_signature}")
            if _first_doc_line:
                _log.warning(f"     {_first_doc_line}")
                _log.warning("  ------")
        sys.exit(0)

    if _args.function not in _available_fns:
        _log.error(f"Unknown function '{_args.function}'. Run without arguments to see available functions.")
        sys.exit(1)

    _fn = _available_fns[_args.function]
    _fn_params = list(inspect.signature(_fn).parameters.values())

    # Parameters without a default value must be supplied on the command line
    _required_params = [(p.name, p) for p in _fn_params if p.default is inspect.Parameter.empty]

    if len(_args.params) < len(_required_params):
        _missing_params = [name for name, _ in _required_params[len(_args.params):]]
        _log.error(f"'{_args.function}' requires: {', '.join(n for n, _ in _required_params)}")
        _log.error(f"Missing: {', '.join(_missing_params)}")
        _log.error(f"Usage: python db_stats.py {_args.function} {' '.join(f'<{n}>' for n, _ in _required_params)}")
        sys.exit(1)

    # Convert each CLI string to the type declared in the parameter's annotation
    _coerced_args = []
    for _raw_value, _param in zip(_args.params, _fn_params):
        _annotation = _param.annotation
        try:
            if _annotation is date:
                _coerced_args.append(date.fromisoformat(_raw_value))
            elif _annotation is int:
                _coerced_args.append(int(_raw_value))
            elif _annotation is float:
                _coerced_args.append(float(_raw_value))
            elif _annotation is bool:
                if _raw_value.lower() in ("true", "1", "yes"):
                    _coerced_args.append(True)
                elif _raw_value.lower() in ("false", "0", "no"):
                    _coerced_args.append(False)
                else:
                    _log.error(f"Bad value for '{_param.name}': expected true/false, got '{_raw_value}'")
                    sys.exit(1)
            else:
                _coerced_args.append(_raw_value)  # str or unannotated — pass through as-is
        except (ValueError, TypeError) as _e:
            _log.error(f"Bad value for '{_param.name}': {_e}")
            sys.exit(1)

    try:
        _result = _fn(*_coerced_args)
    except Exception as _e:
        _log.error(f"Error running '{_args.function}': {_e}")
        sys.exit(1)

    # Format output based on the return type
    if isinstance(_result, pd.DataFrame):
        _log.info(_result.to_string(index=False) if not _result.empty else "(no data)")
    elif isinstance(_result, dict):
        for _key, _value in _result.items():
            _log.info(f"  {_key}: {_value}")
    elif isinstance(_result, list):
        for _item in _result:
            _log.info(f"  {_item}")
        if not _result:
            _log.info("(none)")
    else:
        _log.info(_result)


if __name__ == "__main__":
    main()
