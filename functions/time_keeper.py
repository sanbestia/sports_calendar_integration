import datetime
import time


def wait(deadline, time_zone):
    now = datetime.datetime.now(time_zone)
    while now < deadline:
        time_remaining = int((deadline - now).total_seconds())
        time.sleep(min(180, time_remaining + 5))
        now = datetime.datetime.now(time_zone)


def main():
    pass


if __name__ == "__main__":
    main()
