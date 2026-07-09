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
            target_times = [(20, 30), (23, 0)]
        else:
            target_times = [(14, 15), (20, 30), (23, 0)]

        for hour, minute in target_times:
            candidate = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate > margin:
                return candidate
        # Advance to the next day midnight
        day = (day + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
