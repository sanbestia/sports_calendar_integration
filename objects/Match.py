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
        start_time: datetime.datetime
    ):
        self.side_one = side_one
        self.side_two = side_two
        self.tournament = tournament
        self.stage = stage
        self.game_id = str(game_id)
        self.sport = sport
        self.start_time = start_time
        self.define_expected_end_time()

    def define_expected_end_time(self) -> None:
        self.expected_end_time = self.start_time + datetime.timedelta(hours=SPORT_DURATIONS["default"])
        if self.sport == "tennis":
            self.expected_end_time += datetime.timedelta(hours=SPORT_DURATIONS["tennis"])
            if any(substr in self.tournament for substr in GRAND_SLAM_TOURNAMENTS):
                self.expected_end_time += datetime.timedelta(hours=SPORT_DURATIONS["grand_slam"])
        if self.sport == "esport":
            self.expected_end_time += datetime.timedelta(hours=SPORT_DURATIONS["esport"])

    def __str__(self) -> str:
        return (f'{self.side_one} vs {self.side_two} - {self.tournament} ({self.stage}) @ '
                f'{self.start_time.strftime("%Y-%m-%d %H:%M:%S")}')
