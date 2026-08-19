import datetime
import config

def get_next_schedule_time(base_time: datetime.datetime) -> datetime.datetime:
    """Return the next upload time based on the Dynamic Tech News Schedule.
    Mon-Fri: 14:15, 20:30, 23:00.
    Sat-Sun: 20:30, 23:00 (Skip 14:15 slot).
    If all slots for the current day have passed, move to the next day.
    """
    # Margin to avoid picking the exact current slot
    margin = base_time + datetime.timedelta(minutes=5)
    day = base_time
    while True:
        is_weekend = day.weekday() >= 5
        
        if is_weekend:
            target_times = [(8, 30), (20, 30), (23, 0)]
        else:
            target_times = [(8, 30), (14, 15), (20, 30), (23, 0)]

        for hour, minute in target_times:
            candidate = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate > margin:
                return candidate
        # Advance to the next day midnight
        day = (day + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def get_next_sunday_schedule_time(base_time: datetime.datetime) -> datetime.datetime:
    """Return the next Sunday at the configured SUNDAY_DIGEST_TIME slot.

    Used when the number of available tech news articles exceeds
    config.SUNDAY_DIGEST_THRESHOLD, scheduling a special weekly Tech Digest.
    The slot is read from config.SUNDAY_DIGEST_TIME (hour, minute).
    """
    hour, minute = config.SUNDAY_DIGEST_TIME  # e.g. (20, 30)

    # weekday(): 0=Mon ... 6=Sun
    days_until_sunday = (6 - base_time.weekday()) % 7

    # If today IS Sunday, check whether the slot is still in the future
    if days_until_sunday == 0:
        candidate = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > base_time + datetime.timedelta(minutes=5):
            return candidate
        # This Sunday's slot has passed → jump to next Sunday
        days_until_sunday = 7

    target_sunday = (base_time + datetime.timedelta(days=days_until_sunday)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return target_sunday
