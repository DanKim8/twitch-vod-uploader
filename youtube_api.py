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

   # Verify the file actually exists before starting Google Auth
    if not os.path.exists(final_file_path):
        print(f"❌ Error: The file {final_file_path} was not found on disk.")
        return 

    youtube = get_authenticated_service()
    
    # --- STEP 1: GENERATE A SAFE YOUTUBE TITLE ---
    file_name = os.path.basename(final_file_path)
    
    # Remove extension and replace underscores with spaces
    clean_display_title = os.path.splitext(file_name)[0].replace('_', ' ')
    
    # Final safety check: YouTube API hates < and >. 
    video_title = re.sub(r'[^a-zA-Z0-9\s\-\.\!\(\)]', '', clean_display_title).strip()

    # Fallback if title becomes empty after cleaning
    if not video_title:
        video_title = f"Twitch VOD Archive {vod.get('id')}"

    # Fetch date from metadata; format: 2025-12-31
    raw_date = vod.get('createdAt') or vod.get('publishedAt') or ""
    formatted_date = raw_date.split('T')[0] if raw_date else "Unknown Date"

    # Placeholder description
    video_description = (
        f"Livestreamed on: {formatted_date}\n"
        f"Check out twitch.tv/lilypichu for more"
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
    media_body = MediaFileUpload(final_file_path, chunksize=1024*1024, resumable=True)    

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