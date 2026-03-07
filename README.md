# Sports Calendar Integration

A Python tool that automatically syncs upcoming sports matches to your Google Calendar. It fetches schedules for your favourite teams and players across multiple sports and keeps your calendar up to date, refreshing every few hours.

---

## Features

- Tracks multiple teams and players across different sports (football, basketball, tennis, esports and more)
- Automatically creates and updates Google Calendar events with match details
- Falls back to alternative API endpoints when the primary one returns no results
- Supports predefined query files for fully automated runs
- Interactive mode to search for teams and players on the fly

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

3. Go to **APIs & Services → OAuth consent screen**. Choose **External**, fill in the app name and your email, and save. You don't need to publish the app — leaving it in testing mode is fine for personal use.

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

To find your Google Calendar ID, go to Google Calendar → Settings → select a calendar → scroll down to "Integrate calendar".

You can adjust the refresh interval and fetch thresholds in `config.py`. By default they are:
```python
MAIN_LOOP_SLEEP_MINUTES = 5  # how often the main loop runs

FETCH_THRESHOLDS = {
    "far":     {"days": 7, "recheck_hours": 24},  # next match is more than 7 days away
    "medium":  {"days": 2, "recheck_hours": 12},   # next match is 2–7 days away
    "near":    {"days": 0, "recheck_hours": 6},   # next match is within 2 days
    "unknown": {"recheck_hours": 2},             # no upcoming match found
}
```

Each team is re-fetched at different rates depending on how soon their next match is, so the program avoids unnecessary API calls when games are far away, but checks often if new matches are scheduled.

---

## Usage

### With a predefined query file

Create a `queries.json` file in the root directory (see format below) and run:
```bash
uv run python main.py --queries queries.json
```

**`queries.json` format example:**
```json
{
    "San Antonio Spurs": {
        "id": "3429",
        "sport": "basketball",
        "player_type": "team",
        "calendar": "CALENDAR_ID_BASKETBALL"
    },
    "Argentina - Football National Team": {
        "id": "4819",
        "sport": "football",
        "player_type": "team",
        "calendar": "CALENDAR_ID_FOOTBALL"
    }
}
```

The `calendar` field should match one of the key names defined in your `.env` file.

### Interactive mode

Run without arguments to search for teams and players interactively:
```bash
uv run python main.py
```

You will be prompted to enter team/player names, select from results, and provide calendar IDs.

### Running tests
```bash
uv run pytest -v
```

---

## Contributing

Contributions are welcome! If you'd like to add support for a new sport, improve the calendar logic, or fix a bug:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Make your changes and make sure all tests pass (`uv run pytest -v`)
4. Submit a pull request

Please make sure any new functionality is covered by tests.