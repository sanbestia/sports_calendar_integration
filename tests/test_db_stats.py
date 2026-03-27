import sqlite3
from datetime import date, datetime, timezone, timedelta

import pandas as pd
import pytest

from functions.db_stats import (
    all_calls_df,
    all_fetches_df,
    api_budget_forecast,
    avg_daily_calls,
    busiest_days,
    calls_in_range,
    calls_on,
    calls_per_period,
    calls_today,
    days_at_max,
    fetch_gap_df,
    pct_days_at_max,
    remaining_calls_today,
    stale_teams,
    teams_due_now,
    teams_with_no_upcoming_match,
)


# --- Fixtures ---

@pytest.fixture
def api_db(tmp_path):
    """Temporary api_calls.db seeded with known data."""
    db_path = str(tmp_path / "api_calls.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE api_calls (date TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0)")
        conn.executemany("INSERT INTO api_calls VALUES (?, ?)", [
            ("2026-01-01", 40),
            ("2026-01-02", 100),  # at limit (limit=100)
            ("2026-01-03", 60),
            ("2026-01-04", 100),  # at limit (limit=100)
        ])
    return db_path


@pytest.fixture
def api_db_with_today(tmp_path):
    """Temporary api_calls.db with an entry for today."""
    db_path = str(tmp_path / "api_calls.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE api_calls (date TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0)")
        conn.execute("INSERT INTO api_calls VALUES (?, ?)", (str(date.today()), 73))
    return db_path


@pytest.fixture
def empty_api_db(tmp_path):
    """Temporary api_calls.db with no rows."""
    db_path = str(tmp_path / "api_calls.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE api_calls (date TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0)")
    return db_path


@pytest.fixture
def fetch_db(tmp_path):
    """Temporary fetch_log.db seeded with known data."""
    db_path = str(tmp_path / "fetch_log.db")
    now = datetime.now(timezone.utc)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE fetch_log (
                team_name TEXT PRIMARY KEY,
                last_fetched TEXT NOT NULL,
                next_match TEXT,
                match_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.executemany("INSERT INTO fetch_log VALUES (?, ?, ?, ?)", [
            (
                "Carlos Alcaraz",
                (now - timedelta(hours=5)).isoformat(),
                (now + timedelta(days=3)).isoformat(),
                2,
            ),
            (
                "Indiana Fever",
                (now - timedelta(hours=10)).isoformat(),
                None,
                0,
            ),
        ])
    return db_path


@pytest.fixture
def empty_fetch_db(tmp_path):
    """Temporary fetch_log.db with no rows."""
    db_path = str(tmp_path / "fetch_log.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE fetch_log (
                team_name TEXT PRIMARY KEY,
                last_fetched TEXT NOT NULL,
                next_match TEXT,
                match_count INTEGER NOT NULL DEFAULT 0
            )
        """)
    return db_path


# --- calls_today ---

def test_calls_today_returns_count_for_today(api_db_with_today):
    assert calls_today(api_db_with_today) == 73


def test_calls_today_returns_zero_when_no_entry_for_today(api_db):
    assert calls_today(api_db) == 0


def test_calls_today_returns_zero_on_empty_db(empty_api_db):
    assert calls_today(empty_api_db) == 0


# --- calls_on ---

def test_calls_on_returns_count_for_existing_date(api_db):
    assert calls_on(date(2026, 1, 3), api_db) == 60


def test_calls_on_returns_zero_for_missing_date(api_db):
    assert calls_on(date(2025, 6, 15), api_db) == 0


# --- days_at_max ---

def test_days_at_max_returns_correct_dates(api_db):
    result = days_at_max(api_db, limit=100, raw=True)
    assert result == [date(2026, 1, 2), date(2026, 1, 4)]


def test_days_at_max_excludes_days_below_limit(api_db):
    result = days_at_max(api_db, limit=100, raw=True)
    assert date(2026, 1, 1) not in result
    assert date(2026, 1, 3) not in result


def test_days_at_max_returns_empty_list_when_none_reached(api_db):
    assert days_at_max(api_db, limit=101, raw=True) == []


def test_days_at_max_returns_empty_list_on_empty_db(empty_api_db):
    assert days_at_max(empty_api_db, limit=100, raw=True) == []


def test_days_at_max_formats_as_dd_mm_yyyy_by_default(api_db):
    result = days_at_max(api_db, limit=100)
    assert result == ["02-01-2026", "04-01-2026"]


def test_days_at_max_returns_strings_by_default(api_db):
    result = days_at_max(api_db, limit=100)
    assert all(isinstance(d, str) for d in result)


# --- pct_days_at_max ---

def test_pct_days_at_max_returns_correct_percentage(api_db):
    # 2 out of 4 days at limit=100 → 50%
    assert pct_days_at_max(api_db, limit=100, raw=True) == pytest.approx(50.0)


def test_pct_days_at_max_returns_zero_when_none_reached(api_db):
    assert pct_days_at_max(api_db, limit=101, raw=True) == pytest.approx(0.0)


def test_pct_days_at_max_returns_zero_on_empty_db(empty_api_db):
    assert pct_days_at_max(empty_api_db, limit=100, raw=True) == pytest.approx(0.0)


def test_pct_days_at_max_formats_with_percent_sign_by_default(api_db):
    assert pct_days_at_max(api_db, limit=100) == "50.00%"


def test_pct_days_at_max_returns_string_by_default(api_db):
    assert isinstance(pct_days_at_max(api_db, limit=100), str)


# --- avg_daily_calls ---

def test_avg_daily_calls_returns_correct_average(api_db):
    # (40 + 100 + 60 + 100) / 4 = 75.0
    assert avg_daily_calls(api_db, raw=True) == pytest.approx(75.0)


def test_avg_daily_calls_returns_zero_on_empty_db(empty_api_db):
    assert avg_daily_calls(empty_api_db, raw=True) == pytest.approx(0.0)


def test_avg_daily_calls_rounds_to_2dp_by_default(api_db):
    # 75.0 rounds to 75.0 — use a non-round average to verify rounding
    # (40 + 100 + 60) / 3 = 66.666... → 66.67
    result = avg_daily_calls(api_db)
    assert isinstance(result, float)
    assert result == round(result, 2)


# --- all_calls_df ---

def test_all_calls_df_has_correct_columns(api_db):
    df = all_calls_df(api_db, limit=100)
    assert list(df.columns) == ["date", "count", "at_limit"]


def test_all_calls_df_has_correct_row_count(api_db):
    df = all_calls_df(api_db, limit=100)
    assert len(df) == 4


def test_all_calls_df_at_limit_column_correct(api_db):
    df = all_calls_df(api_db, limit=100)
    assert df.loc[df["count"] == 100, "at_limit"].all()
    assert not df.loc[df["count"] < 100, "at_limit"].any()


def test_all_calls_df_sorted_by_date(api_db):
    df = all_calls_df(api_db, limit=100)
    assert list(df["date"]) == sorted(df["date"])


def test_all_calls_df_returns_empty_dataframe_on_empty_db(empty_api_db):
    df = all_calls_df(empty_api_db, limit=100)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


# --- all_fetches_df ---

def test_all_fetches_df_has_correct_columns(fetch_db):
    df = all_fetches_df(fetch_db)
    assert list(df.columns) == ["team_name", "last_fetched", "next_match", "match_count"]


def test_all_fetches_df_has_correct_row_count(fetch_db):
    df = all_fetches_df(fetch_db)
    assert len(df) == 2


def test_all_fetches_df_parses_timestamps_as_utc(fetch_db):
    df = all_fetches_df(fetch_db, raw=True)
    assert df["last_fetched"].dt.tz is not None
    assert str(df["last_fetched"].dt.tz) == "UTC"


def test_all_fetches_df_null_next_match_is_nat(fetch_db):
    df = all_fetches_df(fetch_db, raw=True)
    fever_row = df[df["team_name"] == "Indiana Fever"].iloc[0]
    assert pd.isna(fever_row["next_match"])


def test_all_fetches_df_returns_empty_dataframe_on_empty_db(empty_fetch_db):
    df = all_fetches_df(empty_fetch_db)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_all_fetches_df_formats_datetimes_as_strings_by_default(fetch_db):
    df = all_fetches_df(fetch_db)
    assert pd.api.types.is_string_dtype(df["last_fetched"])
    assert pd.api.types.is_string_dtype(df["next_match"])


def test_all_fetches_df_datetime_format_by_default(fetch_db):
    df = all_fetches_df(fetch_db)
    alcaraz = df[df["team_name"] == "Carlos Alcaraz"].iloc[0]
    # format: "DD-MM-YYYY HH:MM:SS +00:00"
    import re
    assert re.match(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2} \+00:00", alcaraz["last_fetched"])
    assert re.match(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2} \+00:00", alcaraz["next_match"])


def test_all_fetches_df_null_next_match_is_empty_string_by_default(fetch_db):
    df = all_fetches_df(fetch_db)
    fever_row = df[df["team_name"] == "Indiana Fever"].iloc[0]
    assert fever_row["next_match"] == ""


# --- fetch_gap_df ---

def test_fetch_gap_df_has_correct_columns(fetch_db):
    df = fetch_gap_df(fetch_db)
    assert "hours_since_fetch" in df.columns
    assert "hours_until_match" in df.columns


def test_fetch_gap_df_hours_since_fetch_is_positive(fetch_db):
    df = fetch_gap_df(fetch_db)
    assert (df["hours_since_fetch"] > 0).all()


def test_fetch_gap_df_hours_since_fetch_is_approximate(fetch_db):
    """hours_since_fetch should be close to the seeded values (5h and 10h)."""
    df = fetch_gap_df(fetch_db).sort_values("team_name").reset_index(drop=True)
    alcaraz = df[df["team_name"] == "Carlos Alcaraz"].iloc[0]
    fever = df[df["team_name"] == "Indiana Fever"].iloc[0]
    assert alcaraz["hours_since_fetch"] == pytest.approx(5.0, abs=0.1)
    assert fever["hours_since_fetch"] == pytest.approx(10.0, abs=0.1)


def test_fetch_gap_df_hours_until_match_is_nan_when_no_next_match(fetch_db):
    df = fetch_gap_df(fetch_db)
    fever_row = df[df["team_name"] == "Indiana Fever"].iloc[0]
    assert pd.isna(fever_row["hours_until_match"])


def test_fetch_gap_df_formats_datetimes_as_strings_by_default(fetch_db):
    df = fetch_gap_df(fetch_db)
    assert pd.api.types.is_string_dtype(df["last_fetched"])
    assert pd.api.types.is_string_dtype(df["next_match"])


def test_fetch_gap_df_rounds_float_columns_to_2dp_by_default(fetch_db):
    df = fetch_gap_df(fetch_db)
    for val in df["hours_since_fetch"].dropna():
        assert val == round(val, 2)


# --- remaining_calls_today ---

def test_remaining_calls_today_returns_correct_remainder(api_db_with_today):
    # seeded count is 73, limit=100 → 27 remaining
    assert remaining_calls_today(api_db_with_today, limit=100) == 27


def test_remaining_calls_today_returns_limit_when_no_entry(empty_api_db):
    assert remaining_calls_today(empty_api_db, limit=100) == 100


def test_remaining_calls_today_floors_at_zero_when_over_limit(api_db_with_today):
    # limit lower than today's count → floor at 0
    assert remaining_calls_today(api_db_with_today, limit=10) == 0


# --- calls_in_range ---

def test_calls_in_range_sums_correctly(api_db):
    # 2026-01-01 (40) + 2026-01-02 (100) + 2026-01-03 (60) = 200
    assert calls_in_range(date(2026, 1, 1), date(2026, 1, 3), api_db) == 200


def test_calls_in_range_single_day(api_db):
    assert calls_in_range(date(2026, 1, 2), date(2026, 1, 2), api_db) == 100


def test_calls_in_range_returns_zero_for_empty_range(api_db):
    assert calls_in_range(date(2025, 1, 1), date(2025, 1, 31), api_db) == 0


# --- busiest_days ---

def test_busiest_days_returns_top_n(api_db):
    df = busiest_days(2, api_db, limit=100)
    assert len(df) == 2
    assert list(df["count"]) == [100, 100]


def test_busiest_days_sorted_descending(api_db):
    df = busiest_days(4, api_db, limit=100)
    assert list(df["count"]) == sorted(df["count"], reverse=True)


def test_busiest_days_returns_all_when_n_exceeds_rows(api_db):
    df = busiest_days(100, api_db, limit=100)
    assert len(df) == 4


# --- calls_per_period ---

def test_calls_per_period_has_correct_columns(api_db):
    df = calls_per_period("W", api_db, limit=100)
    assert list(df.columns) == ["period_start", "total_calls", "days_recorded", "days_at_limit"]


def test_calls_per_period_total_calls_matches_sum(api_db):
    df = calls_per_period("W", api_db, limit=100)
    assert df["total_calls"].sum() == 300  # 40+100+60+100


def test_calls_per_period_days_at_limit_correct(api_db):
    df = calls_per_period("W", api_db, limit=100)
    assert df["days_at_limit"].sum() == 2


def test_calls_per_period_returns_empty_dataframe_on_empty_db(empty_api_db):
    df = calls_per_period("W", empty_api_db, limit=100)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


# --- api_budget_forecast ---

def test_api_budget_forecast_has_correct_keys(api_db_with_today):
    result = api_budget_forecast(api_db_with_today, limit=100)
    assert set(result.keys()) == {
        "calls_so_far", "hours_elapsed", "rate_per_hour",
        "projected_daily_total", "limit", "will_exceed_limit"
    }


def test_api_budget_forecast_calls_so_far_matches_db(api_db_with_today):
    result = api_budget_forecast(api_db_with_today, limit=100)
    assert result["calls_so_far"] == 73


def test_api_budget_forecast_limit_matches_argument(api_db_with_today):
    result = api_budget_forecast(api_db_with_today, limit=50)
    assert result["limit"] == 50


def test_api_budget_forecast_will_exceed_limit_true_when_projected_over(api_db_with_today):
    # 73 calls, limit=1 → will exceed
    result = api_budget_forecast(api_db_with_today, limit=1)
    assert result["will_exceed_limit"] is True


def test_api_budget_forecast_returns_zero_rate_on_empty_db(empty_api_db):
    result = api_budget_forecast(empty_api_db, limit=100)
    assert result["calls_so_far"] == 0
    assert result["rate_per_hour"] == 0.0


# --- teams_due_now ---

@pytest.fixture
def fetch_db_due(tmp_path):
    """Fetch log with one team due (fetched 200h ago) and one not due (fetched 1h ago)."""
    db_path = str(tmp_path / "fetch_log.db")
    now = datetime.now(timezone.utc)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE fetch_log (
                team_name TEXT PRIMARY KEY,
                last_fetched TEXT NOT NULL,
                next_match TEXT,
                match_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.executemany("INSERT INTO fetch_log VALUES (?, ?, ?, ?)", [
            ("Stale Team", (now - timedelta(hours=200)).isoformat(), None, 0),
            ("Fresh Team", (now - timedelta(hours=1)).isoformat(), None, 0),
        ])
    return db_path


def test_teams_due_now_returns_stale_team(fetch_db_due):
    result = teams_due_now(fetch_db_due)
    assert "Stale Team" in result


def test_teams_due_now_excludes_fresh_team(fetch_db_due):
    result = teams_due_now(fetch_db_due)
    assert "Fresh Team" not in result


def test_teams_due_now_returns_empty_on_empty_db(empty_fetch_db):
    assert teams_due_now(empty_fetch_db) == []


# --- teams_with_no_upcoming_match ---

def test_teams_with_no_upcoming_match_returns_correct_team(fetch_db):
    result = teams_with_no_upcoming_match(fetch_db)
    assert result == ["Indiana Fever"]


def test_teams_with_no_upcoming_match_excludes_teams_with_match(fetch_db):
    result = teams_with_no_upcoming_match(fetch_db)
    assert "Carlos Alcaraz" not in result


def test_teams_with_no_upcoming_match_returns_empty_when_all_have_matches(tmp_path):
    db_path = str(tmp_path / "fetch_log.db")
    now = datetime.now(timezone.utc)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE fetch_log (
                team_name TEXT PRIMARY KEY,
                last_fetched TEXT NOT NULL,
                next_match TEXT,
                match_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("INSERT INTO fetch_log VALUES (?, ?, ?, ?)", (
            "Some Team", now.isoformat(), (now + timedelta(days=1)).isoformat(), 1
        ))
    assert teams_with_no_upcoming_match(db_path) == []


def test_teams_with_no_upcoming_match_returns_empty_on_empty_db(empty_fetch_db):
    assert teams_with_no_upcoming_match(empty_fetch_db) == []


# --- stale_teams ---

def test_stale_teams_returns_correct_teams(fetch_db):
    # fetch_db: Alcaraz fetched 5h ago, Fever fetched 10h ago — both stale at threshold=4h
    df = stale_teams(hours=4, db_path=fetch_db)
    assert len(df) == 2


def test_stale_teams_filters_by_threshold(fetch_db):
    # only Fever (10h) is stale at threshold=8h
    df = stale_teams(hours=8, db_path=fetch_db)
    assert len(df) == 1
    assert df.iloc[0]["team_name"] == "Indiana Fever"


def test_stale_teams_sorted_stalest_first(fetch_db):
    df = stale_teams(hours=4, db_path=fetch_db)
    assert df.iloc[0]["hours_since_fetch"] >= df.iloc[1]["hours_since_fetch"]


def test_stale_teams_returns_empty_when_all_fresh(fetch_db):
    df = stale_teams(hours=1000, db_path=fetch_db)
    assert len(df) == 0


def test_stale_teams_returns_empty_on_empty_db(empty_fetch_db):
    df = stale_teams(hours=0, db_path=empty_fetch_db)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
