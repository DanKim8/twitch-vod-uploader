import requests
import os

# Credentials retrieved from Environment Variables (TrueNAS App Config)
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")
CHANNEL_NAME = os.environ.get("TWITCH_CHANNEL_NAME")

def get_access_token() -> str:
    """Retrieves a new App Access Token."""
    url = "https://id.twitch.tv/oauth2/token"
    data = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()['access_token']

def get_channel_info(token: str):
    """Fetches User ID and determines current live status."""
    headers = {'Client-ID': TWITCH_CLIENT_ID, 'Authorization': f'Bearer {token}'}
    
    # 1. Get User ID
    user_url = f"https://api.twitch.tv/helix/users?login={CHANNEL_NAME}"
    user_response = requests.get(user_url, headers=headers)
    user_response.raise_for_status()
    user_id = user_response.json()['data'][0]['id']

    # 2. Check live status
    stream_url = f"https://api.twitch.tv/helix/streams?user_id={user_id}"
    stream_response = requests.get(stream_url, headers=headers)
    stream_response.raise_for_status()
    is_live = bool(stream_response.json()['data']) # True if data exists

    return user_id, is_live

def get_latest_vod_info(user_id: str, token: str) -> dict | None:
    """Retrieves the most recent VOD's ID, title, and creation time."""
    headers = {'Client-ID': TWITCH_CLIENT_ID, 'Authorization': f'Bearer {token}'}
    url = f"https://api.twitch.tv/helix/videos?user_id={user_id}&type=archive&first=1"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    if not response.json()['data']:
        return None
    
    vod = response.json()['data'][0]
    return {
        'id': vod['id'],
        'title': vod['title'],
        'created_at': vod['created_at'],
    }