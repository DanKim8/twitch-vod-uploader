import requests
import time
import os
from typing import Optional

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

# Maximum number of VODs to fetch per API page
VODS_PER_PAGE = 100 

def get_all_new_vods(user_id: str, token: str, last_processed_id: Optional[str]) -> list:
    """
    Retrieves all VODs for the user until the last_processed_id is found.
    VODs are returned in chronological order (oldest first).
    """
    headers = {'Client-ID': TWITCH_CLIENT_ID, 'Authorization': f'Bearer {token}'}
    vods_to_process = []
    cursor = None
    
    while True:
        url = f"https://api.twitch.tv/helix/videos?user_id={user_id}&type=archive&first={VODS_PER_PAGE}"
        
        if cursor:
            url += f"&after={cursor}"
            
        print(f"Fetching VODs (Page {'first' if not cursor else cursor[:8]}...)")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        page_vods = data.get('data', [])
        
        found_last_id = False
        
        for vod in page_vods:
            if vod['id'] == last_processed_id:
                # Stop processing and terminate the loop
                found_last_id = True
                break
            
            # Store the new VOD for processing
            vods_to_process.append({
                'id': vod['id'],
                'title': vod['title'],
                'created_at': vod['created_at'],
            })
            
        if found_last_id:
            break

        # Check for pagination cursor
        pagination = data.get('pagination', {})
        cursor = pagination.get('cursor')
        
        # If no more pages and we haven't found the last ID, we stop
        if not cursor:
            break

        # Safety measure to prevent hitting rate limits too fast
        time.sleep(0.5) 

    # Twitch returns newest VODs first; we reverse the list to process oldest first
    # (Recommended, as it maintains order if a process fails mid-batch)
    vods_to_process.reverse()
    
    return vods_to_process