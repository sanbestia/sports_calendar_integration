FETCH_THRESHOLDS = {
    "far":           {"days": 7,  "recheck_hours": 24},
    "medium":        {"days": 2,  "recheck_hours": 12},
    "near":          {"days": 0,  "recheck_hours": 6},
    "unknown":       {"recheck_hours": 4},
    "imminent":      {"hours": 24, "recheck_hours": 2},
    "imminent_close":{"hours": 4,  "recheck_hours": 0.5},
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