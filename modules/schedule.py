import datetime
import config

def get_next_schedule_time(base_time: datetime.datetime) -> datetime.datetime:
    """Return the next upload time at 07:30, 13:30, or 22:30.
    If all slots for the current day have passed, move to the next day.
    """
    # Fixed target times (hour, minute)
    target_times = [(7, 30), (13, 30), (22, 30)]
    # Margin to avoid picking the exact current slot
    margin = base_time + datetime.timedelta(minutes=5)
    day = base_time
    while True:
        for hour, minute in target_times:
            candidate = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate > margin:
                return candidate
        # Advance to the next day midnight
        day = (day + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
