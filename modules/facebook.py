import os
import requests
import config
import datetime


# Facebook accepts scheduled posts only within a bounded window.  Keep a small
# margin below the documented 75-day limit so network/API clock differences do
# not turn an otherwise valid timestamp into a rejected request.
FACEBOOK_MIN_LEAD = datetime.timedelta(minutes=15)
FACEBOOK_MAX_LEAD = datetime.timedelta(days=75, minutes=-5)


def _as_utc(value):
    """Return a datetime as timezone-aware UTC."""
    if value.tzinfo is None:
        # Existing callers may pass naive local datetimes.
        value = value.replace(tzinfo=datetime.datetime.now().astimezone().tzinfo)
    return value.astimezone(datetime.timezone.utc)


def _facebook_schedule_time(schedule_time=None):
    """Return a Facebook-valid scheduled publish datetime.

    YouTube and Facebook have different scheduling limits.  A YouTube queue
    date can therefore be valid for YouTube but invalid for Facebook.  When
    that happens, calculate the next local Facebook slot instead of forwarding
    the invalid date.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    earliest = now + FACEBOOK_MIN_LEAD
    latest = now + FACEBOOK_MAX_LEAD

    if schedule_time is not None:
        candidate = _as_utc(schedule_time)

        if candidate > latest:
            print(
                "⚠️ Facebook schedule is too far in the future "
                f"({candidate.isoformat()}); recalculating a valid slot."
            )
            from modules.schedule import get_next_schedule_time

            candidate = _as_utc(get_next_schedule_time(now.astimezone()))
        elif candidate < earliest:
            candidate = earliest
    else:
        candidate = None

    if candidate is None:
        last_publish_ts = get_last_scheduled_publish_at(
            config.FB_PAGE_ID, config.FB_PAGE_ACCESS_TOKEN
        )

        from modules.schedule import get_next_schedule_time

        if last_publish_ts:
            try:
                last_publish_ts = int(last_publish_ts)
            except (TypeError, ValueError):
                last_publish_ts = None

        base_time = now.astimezone()
        if last_publish_ts:
            queued_time = datetime.datetime.fromtimestamp(
                last_publish_ts, tz=datetime.timezone.utc
            )
            # Do not let a stale/invalid Facebook queue push this upload past
            # Facebook's maximum scheduling horizon.
            if now < queued_time <= latest:
                base_time = queued_time.astimezone()

        candidate = _as_utc(get_next_schedule_time(base_time))
        if candidate < earliest:
            candidate = earliest

    return candidate

def get_last_scheduled_publish_at(page_id, access_token):
    """Fetches the furthest 'scheduled_publish_time' currently in the Facebook queue."""
    url = f"https://graph.facebook.com/v19.0/{page_id}/scheduled_posts"
    params = {
        'fields': 'scheduled_publish_time',
        'access_token': access_token,
        'limit': 10
    }
    try:
        response = requests.get(url, params=params).json()
        data = response.get('data', [])
        if not data:
            return None
        
        # Facebook returns unix timestamps
        times = [d['scheduled_publish_time'] for d in data if 'scheduled_publish_time' in d]
        if not times:
            return None
            
        return max(times)
    except Exception as e:
        print(f"Warning: Could not fetch Facebook schedule ({e})")
        return None

def upload_video_to_facebook(file_path, title, description, schedule_time=None):
    """
    Uploads a video to a Facebook Page using the Graph API with scheduling support.
    """
    if not config.UPLOAD_TO_FACEBOOK:
        print("Facebook upload is disabled in config.")
        return None

    if config.FB_PAGE_ID == "YOUR_FB_PAGE_ID" or config.FB_PAGE_ACCESS_TOKEN == "YOUR_FB_PAGE_ACCESS_TOKEN":
        print("Warning: Facebook credentials not set in config.py. Skipping upload.")
        return None

    if not os.path.exists(file_path):
        print(f"Error: Video file not found at {file_path}")
        return None

    # --- Scheduling Logic ---
    schedule_time_obj = _facebook_schedule_time(schedule_time)
    schedule_time_ts = int(schedule_time_obj.timestamp())
    schedule_dt_str = schedule_time_obj.astimezone().strftime('%I:%M %p, %b %d')
    print(f"🚀 Initiating Facebook Upload (Scheduled for {schedule_dt_str}): {title}...")

    # Truncate description to a reasonable length to avoid Facebook API errors
    max_desc_length = 5000
    safe_description = description[:max_desc_length] if description else ""
    payload = {
        'title': title,
        'description': safe_description,
        'access_token': config.FB_PAGE_ACCESS_TOKEN,
        'published': 'false',
        'scheduled_publish_time': schedule_time_ts
    }

    url = f"https://graph-video.facebook.com/v19.0/{config.FB_PAGE_ID}/videos"

    try:
        with open(file_path, 'rb') as video_file:
            files = {
                'source': video_file
            }
            
            response = requests.post(url, data=payload, files=files, timeout=300)
            
        response.raise_for_status()
        result = response.json()
        
        video_id = result.get('id')
        print(f"Facebook Video Upload Complete! (Waiting for scheduled time: {schedule_dt_str})")
        print(f"Video ID: {video_id}")
        
        return video_id

    except requests.exceptions.HTTPError as e:
        print(f"Facebook API HTTP Error: {e.response.status_code}")
        print(f"Details: {e.response.text}")
        return None
    except Exception as e:
        print(f"Facebook API Error: {e}")
        return None
