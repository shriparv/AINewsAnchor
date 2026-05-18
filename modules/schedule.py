import datetime
import config

def get_next_schedule_time(base_time: datetime.datetime) -> datetime.datetime:
    """
    Calculates the next optimal upload time based on the Tech Niche Golden Strategy rules.
    """
    # Detect if we are producing a YouTube Short (Vertical Video) or Long-Form (Horizontal)
    is_short = config.SIZE_PORTRAIT[0] < config.SIZE_PORTRAIT[1]
    
    current_day = base_time
    
    # Keep iterating day by day until we find the next valid future slot
    while True:
        weekday = current_day.weekday() # 0 = Monday, 5 = Saturday, 6 = Sunday
        is_weekend = weekday >= 5
        
        slots = []
        if is_short:
            # Best Times for Tech Shorts (Snackable News & Quick Tips)
            # 12:00 PM - 2:00 PM (Lunch hour scroll) 
            # 6:00 PM - 8:00 PM (Post-work/evening relaxation)
            # We use the start of the windows: 12 PM and 6 PM
            slots = [12, 18]
        else:
            # Best Times for Long-Form Tech Videos (8+ Minutes)
            if is_weekend:
                # Weekends (Sat & Sun) 8:00 AM - 10:00 AM
                # Pre-Peak Rule: upload 2-3 hours before peak viewing
                slots = [8]
            else:
                # Weekdays (Wed, Thu, Fri - but applied to all weekdays for consistency)
                # 2:00 PM - 4:00 PM
                slots = [14]
                
        for slot in slots:
            candidate = current_day.replace(hour=slot, minute=0, second=0, microsecond=0)
            # Give a 5 minute margin to ensure we don't pick the exact same slot again
            if candidate > base_time + datetime.timedelta(minutes=5):
                return candidate
                
        # If no slots are left for the current day, advance to midnight of the next day
        current_day += datetime.timedelta(days=1)
        current_day = current_day.replace(hour=0, minute=0, second=0, microsecond=0)
