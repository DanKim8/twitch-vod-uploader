import os
import http.client
import httplib2
import json
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# This scope allows us to upload videos
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# If the /data folder exists (TrueNAS), use it. Otherwise, use the local folder.
if os.path.exists("/data"):
    TOKEN_PATH = "/data/token.json"
    VOD_OUTPUT_DIR = "/vods"
else:
    # Local PC path (current directory)
    TOKEN_PATH = "token.json"
    VOD_OUTPUT_DIR = "./test_vods"

# Ensure the output directory exists
os.makedirs(VOD_OUTPUT_DIR, exist_ok=True)

def get_authenticated_service():
    """
    Handles authentication using the token.json file.
    Automatically refreshes the token if it's expired.
    """
    creds = None

    # 1. Load the credentials from the token.json file
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_info(
            json.load(open(TOKEN_PATH)), 
            YOUTUBE_SCOPES
        )

    # 2. Refresh the token if it is expired
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing YouTube access token...")
            creds.refresh(Request())
            # Save the refreshed token back to the file so it stays valid
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        else:
            raise Exception("token.json is missing or invalid. Please re-run auth locally.")

    # 3. Build the service
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)


# --- MAIN UPLOAD FUNCTION ---

def upload_video(final_file_path: str, vod: dict):
    """
    Uploads a video file to YouTube using the stored refresh token.
    Derives a safe title from the filename to avoid HTTP 400 errors.
    """
    
    youtube = get_authenticated_service()
    
    # --- STEP 1: GENERATE A SAFE YOUTUBE TITLE ---
    # Get the filename (e.g., "2025-12-18_yo_happy_holidays.mp4")
    file_name = os.path.basename(final_file_path)
    
    # Remove extension and replace underscores with spaces
    # Result: "2025-12-18 yo happy holidays"
    clean_display_title = os.path.splitext(file_name)[0].replace('_', ' ')
    
    # Final safety check: YouTube API hates < and >. 
    # This regex keeps letters, numbers, spaces, and basic punctuation only.
    video_title = re.sub(r'[^a-zA-Z0-9\s\-\.\!\(\)]', '', clean_display_title).strip()

    # Fallback if title becomes empty after cleaning
    if not video_title:
        video_title = f"Twitch VOD Archive {vod.get('id')}"

    # Placeholder description
    video_description = (
        f"Original Title: {vod.get('title')}\n"
        f"Full stream VOD from our Twitch channel.\n\n"
        "Link to the original channel here: [CHANNEL LINK]"
    )

    channel_tag = vod.get('owner', {}).get('display_name', 'TwitchStreamer') 

    # --- STEP 2: PREPARE THE METADATA ---
    body = {
        'snippet': {
            'title': video_title[:100], # Force YouTube 100 char limit
            'description': video_description,
            'tags': ['twitch', channel_tag, 'vod', 'gaming'],
            'categoryId': '20', 
        },
        'status': {
            'privacyStatus': 'private'
        }
    }

    # --- STEP 3: EXECUTE UPLOAD ---
    media_body = MediaFileUpload(final_file_path, chunksize=-1, resumable=True)
    
    print(f"Uploading to YouTube as: '{video_title}'...")

    try:
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media_body
        )
        
        # Resumable upload progress loop
        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                print(f"Upload Progress: {int(status.progress() * 100)}%")
        
        # 4. Success message
        print(f"✅ Successfully uploaded video! YouTube ID: {response.get('id')}")
        return response.get('id')

    except HttpError as e:
        print(f"❌ An HTTP error occurred: {e.resp.status} - {e.content.decode()}")
        raise
    except Exception as e:
        print(f"❌ An unexpected error occurred during upload: {e}")
        raise