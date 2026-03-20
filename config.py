FETCH_THRESHOLDS = {
    "far":           {"days": 7,  "recheck_hours": 48},  # next match is more than 7 days away
    "medium":        {"days": 3,  "recheck_hours": 24},  # next match is 3-7 days away
    "near":          {"days": 0,  "recheck_hours": 12},   # next match is within 3 days
    "unknown":       {"recheck_hours": 8},               # no upcoming match found
    "imminent":      {"hours": 24, "recheck_hours": 4},  # single match within this many hours
    "imminent_close":{"hours": 3,  "recheck_hours": 1} # single match within this many hours
}

MAIN_LOOP_SLEEP_MINUTES = 5

MAX_API_CALLS = 100

GRAND_SLAM_TOURNAMENTS = ["US Open", "Wimbledon", "Australian Open", "French Open"]
SPORT_DURATIONS = {
    "default": 2,
    "tennis": 1,
    "grand_slam": 2,
    "esport": 3
}