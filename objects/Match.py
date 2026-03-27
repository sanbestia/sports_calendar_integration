import datetime
from config import GRAND_SLAM_TOURNAMENTS, SPORT_DURATIONS


class Match:
    def __init__(
        self,
        side_one: str,
        side_two: str,
        tournament: str,
        stage: str,
        game_id: int | str,
        sport: str,
        start_time: datetime.datetime,
        home_team_id: int | str | None = None,
        away_team_id: int | str | None = None,
    ):
        """Construct a Match, normalising IDs to str and computing the expected end time."""
        self.side_one = side_one
        self.side_two = side_two
        self.tournament = tournament
        self.stage = stage
        self.game_id = str(game_id)  # normalize to str; API inconsistently returns int or str
        self.sport = sport
        self.start_time = start_time
        self.home_team_id = str(home_team_id) if home_team_id is not None else None  # normalize to str for consistent comparison with calendar event properties
        self.away_team_id = str(away_team_id) if away_team_id is not None else None
        self.define_expected_end_time()

    def define_expected_end_time(self) -> None:
        """Set expected_end_time from start_time using additive sport-specific duration offsets."""
        self.expected_end_time = self.start_time + datetime.timedelta(hours=SPORT_DURATIONS["default"])  # base for all sports; tennis and esport stack additional hours on top
        if self.sport == "tennis":
            self.expected_end_time += datetime.timedelta(hours=SPORT_DURATIONS["tennis"])
            if any(substr in self.tournament for substr in GRAND_SLAM_TOURNAMENTS):  # substring match because API returns names like "Australian Open 2025"
                self.expected_end_time += datetime.timedelta(hours=SPORT_DURATIONS["grand_slam"])
        if self.sport == "esport":
            self.expected_end_time += datetime.timedelta(hours=SPORT_DURATIONS["esport"])

    def __str__(self) -> str:
        """Return a one-line summary: sides, tournament, stage, and start time."""
        return (f'{self.side_one} vs {self.side_two} - {self.tournament} ({self.stage}) @ '
                f'{self.start_time.strftime("%Y-%m-%d %H:%M:%S")}')
