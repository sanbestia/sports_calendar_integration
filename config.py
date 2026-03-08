FETCH_THRESHOLDS = {
    "far":           {"days": 7,  "recheck_hours": 48},  # next match is more than 7 days away
    "medium":        {"days": 2,  "recheck_hours": 18},  # next match is 2-7 days away
    "near":          {"days": 0,  "recheck_hours": 9},   # next match is within 2 days
    "unknown":       {"recheck_hours": 4},               # no upcoming match found
    "imminent":      {"hours": 24, "recheck_hours": 3},  # single match within this many hours
    "imminent_close":{"hours": 4,  "recheck_hours": 0.75} # single match within this many hours
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