# Sports Calendar Integration

A Python tool that automatically syncs upcoming sports matches to your Google Calendar. It fetches schedules for your favourite teams and players across multiple sports and keeps your calendar up to date, refreshing every few hours.

---

## Index

- [Features](#features)
- [Setup & Installation](#setup--installation)
- [Google Calendar API Setup](#google-calendar-api-setup)
- [Configuration](#configuration)
- [Running the Script](#running-the-script)
- [Database Analytics](#database-analytics)
- [Contributing](#contributing)

---

## Features

- Tracks multiple teams and players across different sports (football, basketball, tennis, esports and more)
- Automatically creates and updates Google Calendar events with match details
- Automatically removes calendar events for cancelled or rescheduled matches (detected via API status or disappearance from the schedule)
- Falls back to alternative API endpoints when the primary one returns no results
- Supports predefined query files for fully automated runs
- Interactive mode to search for teams and players on the fly
- Built-in analytics for querying API usage and fetch history via a standalone CLI or Python module

---

## Setup & Installation

### Requirements
- Python 3.13+
- A [RapidAPI](https://rapidapi.com) account with access to the [AllSports API](https://rapidapi.com/allsportsapi2/api/allsportsapi2)
- A Google account with the [Google Calendar API](https://console.cloud.google.com/) enabled

### Installation

1. Clone the repository:
```bash
    git clone https://github.com/your-username/sports-calendar-integration.git
    cd sports-calendar-integration
```

2. Install dependencies using [uv](https://github.com/astral-sh/uv):
```bash
    uv sync
```

3. Set up your environment variables (see [Configuration](#configuration))

4. Set up your Google Calendar API credentials (see [Google Calendar API Setup](#google-calendar-api-setup))

---

## Google Calendar API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.

2. Navigate to **APIs & Services → Library**, search for "Google Calendar API", and enable it.

3. Go to **APIs & Services → OAuth consent screen**. Choose **External**, fill in the app name and your email, and save. You don't need to publish the app; leaving it in testing mode is fine for personal use.

4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**. Choose **Desktop app**, give it a name, and download the resulting file. Rename it to `credentials.json` and place it in the root directory of the project.

5. On your first run, a browser window will open asking you to authorise the app with your Google account. After you confirm, a `token.json` file will be created automatically and reused in future runs.

> **Note:** If you see a "Google hasn't verified this app" warning, click **Advanced → Go to (app name)** to proceed. This appears because the app is in testing mode and is expected behaviour.

---

## Configuration

Create a `.env` file in the root directory with the following variables:
```env
RAPIDAPI_KEY=your_rapidapi_key_here

CALENDAR_ID_SPORT1=your_calendar_id_here
CALENDAR_ID_SPORT2=your_calendar_id_here
...
```

You may add as many Google Calendar IDs as you wish.

> **Note:** To find your Google Calendar ID, go to Google Calendar → Settings → select a calendar → scroll down to "Integrate calendar".

You can adjust the refresh interval and fetch thresholds in `config.py`. By default they are:
```python
MAIN_LOOP_SLEEP_MINUTES = 5  # how often the main loop runs

FETCH_THRESHOLDS = {
    "far":           {"days": 7,  "recheck_hours": 48},  # next match is more than 7 days away
    "medium":        {"days": 3,  "recheck_hours": 24},  # next match is 3-7 days away
    "near":          {"days": 0,  "recheck_hours": 12},   # next match is within 3 days
    "unknown":       {"recheck_hours": 8},               # no upcoming match found
    "imminent":      {"hours": 24, "recheck_hours": 4},  # single match within this many hours
    "imminent_close":{"hours": 3,  "recheck_hours": 1} # single match within this many hours
}
```

Each team is re-fetched at different rates depending on how soon their next match is, so the program avoids unnecessary API calls when games are far away, but checks often when matches are approaching. As a special case, if only one match is found the program applies stricter refresh rates: every `imminent.recheck_hours` when the match is within the `imminent` window, and every `imminent_close.recheck_hours` when it is within the closer `imminent_close` window.

### Local state files

On first run, the program automatically creates two SQLite database files in the working directory: `api_calls.db` to track your daily API usage, and `fetch_log.db` to remember when each team was last fetched. These are managed automatically and you don't need to touch them.

---

## Running the Script

### Looking up team and player IDs

The `id` values in `queries.json` come from the AllSports API. To look them up, run `get_ids` as a standalone script:

```bash
uv run python -m functions.get_ids
```

You will be prompted to enter a name and sport, shown a list of matches to choose from, and asked to confirm your selection. At the end, the script prints a summary of all selected entries with their IDs. API calls made during the search are tracked against your daily limit.

### Running the script with a predefined query file

Once you have your IDs, create a `queries.json` file in the root directory and run:
```bash
uv run python main.py --queries queries.json
```

**`queries.json` format example:**
```json
{
    "Carlos Alcaraz": {
        "id": "275923",
        "sport": "tennis",
        "player_type": "player",
        "calendar": "CALENDAR_ID_TENNIS"
    },
    "Argentina - Football National Team": {
        "id": "4819",
        "sport": "football",
        "player_type": "team",
        "calendar": "CALENDAR_ID_FOOTBALL"
    }
}
```

The `calendar` field should match one of the key names defined in your `.env` file. The `player_type` field should be `"player"` for individuals or `"team"` for organizations.

### Running the script in interactive mode

Run without arguments to search for teams and players interactively, without needing a `queries.json` file:
```bash
uv run python main.py
```

You will be prompted to enter team/player names, select from results, and provide calendar IDs. This uses the same search flow as `get_ids` but feeds directly into the main loop.

### Running tests
```bash
uv run pytest -v
```

---

## Database Analytics

`functions/db_stats.py` provides read-only functions for querying both databases (`api_calls.db` and `fetch_log.db`). It can be used in two ways:

**As a CLI** — call any function by name, with optional positional arguments:
```bash
uv run python functions/db_stats.py                        # list all available functions
uv run python functions/db_stats.py calls_today
uv run python functions/db_stats.py stale_teams 24
uv run python functions/db_stats.py calls_in_range 2026-01-01 2026-01-31
```

**As a module** — import directly in a Python script or notebook:
```python
from functions.db_stats import (
    calls_today, remaining_calls_today, calls_on, calls_in_range,
    days_at_max, pct_days_at_max, avg_daily_calls,
    busiest_days, calls_per_period, api_budget_forecast,
    all_calls_df, all_fetches_df, fetch_gap_df,
    teams_due_now, teams_with_no_upcoming_match, stale_teams,
)

# Examples
calls_today()                        # API calls made today
remaining_calls_today()              # calls left before hitting the daily limit
calls_in_range(date(2026,1,1), date(2026,1,31))  # total calls in January
pct_days_at_max()                    # % of days the limit was reached
busiest_days(5)                      # top 5 days by call volume (DataFrame)
calls_per_period("ME")               # monthly totals (DataFrame)
api_budget_forecast()                # projected end-of-day total based on current rate
teams_due_now()                      # teams the scheduler would fetch right now
stale_teams(hours=48)                # teams not fetched in over 48 hours (DataFrame)
```

Functions that return datetimes, percentages, or floats format their output for readability by default (datetimes as `DD-MM-YYYY HH:MM:SS +00:00`, percentages with `%`, floats rounded to 2 decimal places). Pass `raw=True` to get native Python types for programmatic use:
```python
pct_days_at_max()            # "50.00%"
pct_days_at_max(raw=True)    # 50.0
days_at_max()                # ["02-01-2026", "04-01-2026"]
days_at_max(raw=True)        # [datetime.date(2026, 1, 2), datetime.date(2026, 1, 4)]
```

---

## Contributing

Contributions are welcome! If you'd like to add support for a new sport, improve the calendar logic, or fix a bug:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Make your changes and make sure all tests pass (`uv run pytest -v`)
4. Submit a pull request

Please make sure any new functionality is covered by tests.

---