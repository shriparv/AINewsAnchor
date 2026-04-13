import os
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

# Elevate scope to manage the user's entire YouTube channel (required for building Playlists)
SCOPES = ["https://www.googleapis.com/auth/youtube"]

def authenticate_youtube():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    api_service_name = "youtube"
    api_version = "v3"
    import glob
    
    secret_files = glob.glob("client_secret*.json")
    client_secrets_file = secret_files[0] if secret_files else "client_secret.json"

    creds = None
    # We store the token to avoid forcing the user to log in every single run!
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token. Please delete token.pickle and re-authenticate. ({e})")
                return None
        else:
            if not os.path.exists(client_secrets_file):
                print(f"❌ Error: {client_secrets_file} not found! Place the downloaded Google Cloud OAuth JSON file in the root folder.")
                return None
                
            print("⚠️ Opening Browser for YouTube Authentication (This is a one-time operation!)...")
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return googleapiclient.discovery.build(
        api_service_name, api_version, credentials=creds)

def get_or_create_playlist(youtube, title="Technology news"):
    print(f"🔍 Searching for Playlist: '{title}'...")
    request = youtube.playlists().list(
        part="snippet",
        mine=True,
        maxResults=50
    )
    response = request.execute()
    for item in response.get("items", []):
        if item["snippet"]["title"].lower() == title.lower():
            print(f"✅ Playlist '{title}' found! ({item['id']})")
            return item["id"]
            
    # Create if not found natively
    print(f"➕ Playlist '{title}' not natively found. Generating a new Public Playlist now...")
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
          "snippet": {
            "title": title,
            "description": "Daily automated AI technology news updates."
          },
          "status": {
            "privacyStatus": "public" 
          }
        }
    )
    response = request.execute()
    return response["id"]


def add_video_to_playlist(youtube, video_id, playlist_id):
    print(f"📦 Nesting Video [{video_id}] securely into Playlist [{playlist_id}]...")
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
          "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
              "kind": "youtube#video",
              "videoId": video_id
            }
          }
        }
    )
    request.execute()
    print("✅ Successfully routed Video directly into the Playlist!")

def set_thumbnail(youtube, video_id, thumbnail_path):
    """Sets a custom thumbnail for the video using a local image file."""
    if not os.path.exists(thumbnail_path):
        print(f"⚠️ Warning: Thumbnail file {thumbnail_path} not found!")
        return False
        
    print(f"🖼️ Setting Custom Thumbnail: {thumbnail_path}...")
    try:
        request = youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        )
        request.execute()
        print("✅ Thumbnail successfully updated!")
        return True
    except Exception as e:
        print(f"⚠️ Error setting thumbnail: {e}")
        return False

def get_last_scheduled_publish_at(youtube):
    """Finds the furthest 'publishAt' date currently in the YouTube queue."""
    from dateutil import parser

    print("🔍 Checking YouTube schedule for existing videos...")
    try:
        # Step 1: Get the 'Uploads' playlist ID for the channel
        res = youtube.channels().list(mine=True, part='contentDetails').execute()
        uploads_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Step 2: Fetch latest items from that playlist
        res = youtube.playlistItems().list(
            playlistId=uploads_id, 
            part='contentDetails', 
            maxResults=10
        ).execute()
        
        video_ids = [item['contentDetails']['videoId'] for item in res.get('items', [])]
        if not video_ids:
            return None

        # Step 3: Fetch 'status' for those videos to find scheduled dates
        res = youtube.videos().list(id=",".join(video_ids), part='status').execute()
        
        future_dates = []
        for item in res.get('items', []):
            publish_at = item.get('status', {}).get('publishAt')
            if publish_at:
                future_dates.append(parser.parse(publish_at))

        if not future_dates:
            return None

        return max(future_dates)
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch schedule ({e}). Defaulting to 4 hours from now.")
        return None

def upload_video(file_path: str, title: str, description: str, tags: list, category_id="28", thumbnail_path=None):
    """
    Uploads a video file automatically securely into the user's YouTube Studio.
    `category_id` 28 correlates to 'Science & Technology'.
    """
    import datetime

    youtube = authenticate_youtube()
    if not youtube:
        return None

    # Calculate dynamic schedule (Last Scheduled Video + 4 Hours)
    last_publish = get_last_scheduled_publish_at(youtube)
    now = datetime.datetime.now().astimezone()
    
    if last_publish:
        # Ensure last_publish is in the future relative to now, otherwise start from now
        base_time = max(last_publish, now)
        schedule_time = base_time + datetime.timedelta(hours=4)
        print(f"📅 Queue Found! Last video at {last_publish.strftime('%H:%M %p, %b %d')}. Stacking next one at {schedule_time.strftime('%H:%M %p, %b %d')}.")
    else:
        schedule_time = now + datetime.timedelta(hours=4)
        print(f"📅 Queue Empty! Scheduling first video for {schedule_time.strftime('%H:%M %p, %b %d')} (4 hours from now).")

    publish_at = schedule_time.isoformat()

    print(f"🚀 Initiating YouTube Upload: {title}...")

    request = youtube.videos().insert(
        part="snippet,status",
        body={
          "snippet": {
            "categoryId": category_id,
            "description": description,
            "title": title,
            "tags": tags
          },
          "status": {
            "privacyStatus": "private", # Must strictly be private to support scheduling
            "publishAt": publish_at,    # Injects the ISO 8601 future string to auto-publish!
            "selfDeclaredMadeForKids": False
          }
        },
        media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
    )

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"Uploading Upload chunk... {int(status.progress() * 100)}%")
        except googleapiclient.errors.HttpError as e:
            print(f"❌ YouTube API HTTP Error: {e.resp.status}")
            print(f"❌ Details: {e.content.decode('utf-8')}")
            return None
        except Exception as e:
            print(f"❌ YouTube API Error: {e}")
            return None

    video_id = response.get('id')
    print(f"✅ Video Upload Complete! \n🌍 View in YouTube Studio: https://studio.youtube.com/video/{video_id}/edit")
    
    # 🔹 Add dynamically to playlist directly after upload succeeds!
    try:
        playlist_id = get_or_create_playlist(youtube, "Technology news")
        add_video_to_playlist(youtube, video_id, playlist_id)
    except Exception as e:
        print(f"⚠️ Warning: Successfully uploaded video, but failed appending to playlist: {e}")

    # 🔹 Set Custom Thumbnail if provided
    if thumbnail_path:
        set_thumbnail(youtube, video_id, thumbnail_path)

    return video_id
