import os
import requests
import config
import datetime
import random

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
    if not schedule_time:
        # Independent mode: Calculate based on current FB queue
        last_publish_ts = get_last_scheduled_publish_at(config.FB_PAGE_ID, config.FB_PAGE_ACCESS_TOKEN)
        now_ts = int(datetime.datetime.now().timestamp())
        
        from modules.schedule import get_next_schedule_time
        
        base_ts = max(last_publish_ts, now_ts) if last_publish_ts else now_ts
        base_time = datetime.datetime.fromtimestamp(base_ts)
        
        schedule_time_obj = get_next_schedule_time(base_time)
        schedule_time_ts = int(schedule_time_obj.timestamp())
    else:
        # Sync mode: Use provided datetime object
        schedule_time_ts = int(schedule_time.timestamp())

    # Ensure it's at least 15 mins in the future (FB requirement is 10 mins)
    min_future = int(datetime.datetime.now().timestamp() + 900)
    if schedule_time_ts < min_future:
        schedule_time_ts = min_future

    schedule_dt_str = datetime.datetime.fromtimestamp(schedule_time_ts).strftime('%H:%M %p, %b %d')
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
