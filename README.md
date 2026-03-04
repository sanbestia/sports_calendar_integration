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

4. Add your Google Calendar API credentials file (`credentials.json`) to the root directory. You can download it from the [Google Cloud Console](https://console.cloud.google.com/) after enabling the Calendar API.

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

You can adjust the refresh interval in `config.py`:
```python
REFRESH_HOURS = 6  # how often the calendar is updated
```

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
    },
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


### To do list:
- [x] Allow multiple teams in one run
- [ ] Install dependencies automatically
- [ ] Make the credential creation process easier
- [ ] Restrict input possibilities
- [ ] Create user interface?
- [ ] Create webapp to host it?
- [ ] Implement database keeping module

