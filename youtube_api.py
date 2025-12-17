import os
import http.client
import httplib2
import json
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

# --- UTILITY FUNCTION FOR AUTHORIZATION ---

def get_authenticated_service():
    """
    Handles authentication using the Refresh Token and returns the YouTube service object.
    Requires YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN 
    to be set as environment variables.
    """
    
    # Check for required environment variables
    if not all(os.environ.get(v) for v in ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]):
        raise EnvironmentError(
            "Missing YouTube environment variables. Ensure YOUTUBE_CLIENT_ID, "
            "YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN are set."
        )

    # 1. Manually build the Credentials object using the Refresh Token
    credentials_data = {
        'token': None,
        'refresh_token': os.environ.get("YOUTUBE_REFRESH_TOKEN"),
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': os.environ.get("YOUTUBE_CLIENT_ID"),
        'client_secret': os.environ.get("YOUTUBE_CLIENT_SECRET"),
        'scopes': YOUTUBE_SCOPES,
        'id_token': None,
        'revoke_uri': None,
        'id_token_jwt': None,
        'universe_domain': 'googleapis.com'
    }

    credentials = Credentials.from_authorized_user_info(info=credentials_data, scopes=YOUTUBE_SCOPES)
    
    # 2. Refresh the token if necessary (always try to refresh if token is None)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            # If the refresh token fails or is missing, raise an error
            raise Exception("Failed to refresh YouTube access token. Check your refresh token validity.")

    # 3. Build the service
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)


# --- MAIN UPLOAD FUNCTION ---

def upload_video(final_file_path: str, vod: dict):
    """
    Uploads a video file to YouTube using the stored refresh token.
    
    Args:
        final_file_path (str): The local path to the video file to upload.
        vod (dict): The VOD metadata dictionary (used for title/description).
    """
    
    youtube = get_authenticated_service()
    
    # 1. Determine the YouTube Title and Description
    # The title of the file is derived from the VOD title + date, 
    # but we will use the clean title from the VOD metadata dictionary for best quality.
    
    # Extract the clean title (The title of the VOD stream)
    video_title = vod['title']
    
    # Placeholder description
    video_description = (
        "Full stream VOD from our Twitch channel. \n\n"
        "Link to the original channel here: [CHANNEL LINK]"
    )
    
    # 2. Prepare the video resource metadata
    body = {
        'snippet': {
            'title': video_title,
            'description': video_description,
            'tags': ['twitch', vod['channel_name'], 'vod', 'gaming'], # Example tags
            'categoryId': '20', # Example: 'Gaming' category ID
        },
        'status': {
            'privacyStatus': 'private' # Recommended: 'unlisted', 'private', or 'public'
        }
    }

    # 3. Call the API to upload the file
    media_body = MediaFileUpload(final_file_path, chunksize=-1, resumable=True)
    
    print(f"Uploading '{video_title}' to YouTube...")

    try:
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media_body
        )
        response = insert_request.execute()
        
        # 4. Success message
        print(f"Successfully uploaded video! YouTube ID: {response.get('id')}")
        return response.get('id')

    except HttpError as e:
        print(f"An HTTP error occurred: {e.resp.status} - {e.content.decode()}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during upload: {e}")
        raise