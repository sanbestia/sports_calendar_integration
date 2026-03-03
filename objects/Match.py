import datetime


class Match:
    def __init__(self, side_one, side_two, tournament, stage, game_id, sport, start_time):
        self.side_one = side_one
        self.side_two = side_two
        self.tournament = tournament
        self.stage = stage
        self.game_id = str(game_id)
        self.sport = sport
        self.start_time = start_time
        self.define_expected_end_time()

    def define_expected_end_time(self):
        self.expected_end_time = self.start_time + datetime.timedelta(hours=2)
        if self.sport == "tennis":
            self.expected_end_time += datetime.timedelta(hours=1)
            if any(substr in self.tournament for substr in ["US Open", "Wimbledon", "Australian Open", "French Open"]):
                self.expected_end_time += datetime.timedelta(hours=2)
        if self.sport == "esport":
            self.expected_end_time += datetime.timedelta(hours=3)

    def __str__(self):
        return f'{self.side_one} vs {self.side_two} - {self.tournament} ({self.stage}) @ ' \
               f'{self.start_time.strftime("%Y-%m-%d %H:%M:%S")}'


def main():
    pass


if __name__ == '__main__':
    main()
