import subprocess
import os
from datetime import datetime
import re
import json
import glob

STAGING_DIR = os.environ.get("STAGING_DIR", "/vods")

def generate_final_filename(metadata: dict) -> str:

    # 1. Get the Date
    created_date = metadata.get('created_at') or metadata.get('published_at') or ""
    if created_date:
        # Extract just the YYYY-MM-DD part from the ISO string
        date_str = created_date.split('T')[0]
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # 2. Clean the Title
    title = metadata.get('title', 'Unknown_Title')
    
    # Remove all non-alphanumeric characters (keep only letters, numbers, spaces, and hyphens)
    clean = re.sub(r'[^\w\s-]', '', title)
    
    # Replace all spaces and existing underscores with a single underscore
    clean = re.sub(r'[\s_]+', '_', clean)
    
    # Strip any leading/trailing underscores and convert to lowercase
    clean = clean.strip('_').lower()
    
    return f"{date_str}_{clean}.mp4"
    
"""
Fetches the VOD metadata (including creation date and title) 
using 'twitch-dl info --json'.
"""
def get_vod_metadata(vod_id: str) -> dict:

    # Command: twitch-dl info [VOD_ID] --json
    info_command = ['twitch-dl', 'info', vod_id, '--json']
    
    print(f"Fetching metadata for VOD {vod_id}...")
    
    try:
        # Execute the command and capture JSON output
        result = subprocess.run(
            info_command, 
            check=True, 
            capture_output=True, 
            text=True
        )
        
       # Load the raw JSON
        data = json.loads(result.stdout)
        
        # If it's a list, we want the first item
        if isinstance(data, list):
            if len(data) > 0:
                return data[0]
            else:
                raise ValueError(f"Twitch-dl returned an empty list for ID {vod_id}")
        
        # If it's already a dictionary, return it directly
        if isinstance(data, dict):
            return data
            
        raise ValueError(f"Unexpected data type from twitch-dl: {type(data)}")
        
    except subprocess.CalledProcessError as e:
        print(f"COMMAND FAILED: {e.stderr}")
        raise
    except Exception as e:
        print(f"FATAL ERROR processing VOD {vod_id}: {e}")
        raise

def download_vod(vod_id: str, raw_output_path: str):

    download_dir = os.path.dirname(raw_output_path)
    output_template = os.path.join(download_dir, "{date}_{id}_{title}.mp4")

    metadata = get_vod_metadata(vod_id)
    channel_name = metadata.get('owner', {}).get('displayName', 'Unknown')

    qualities_to_try = ['1440p60', '1440p','1080p60', '1080p', '720p60', '720p', '480p']
    download_success = False 

    print(f"Starting download for {channel_name}...")
 
    for q in qualities_to_try:
        print(f"Attempting to download with quality: {q}...")

        command = [
            'twitch-dl', 'download', str(vod_id),
            '-q', q,
            '-o', output_template
        ]

        print(f"📡 Starting Twitch download for VOD {vod_id}...") 
        result = subprocess.run(command)
        
        if result.returncode == 0:
            print(f"✅ Download successful at {q}!")
            download_success = True
            break
        else:
            if "not found" in result.stderr.lower():
                print(f"⚠️ Quality {q} not available. Trying next...")
                continue
            else:
                print(f"❌ Error: {result.stderr}")
                raise Exception(result.stderr)

    if not download_success:
        raise Exception(f"Failed to download VOD {vod_id}.")

    # We search the folder for any file that has the VOD ID in its name.
    search_pattern = os.path.join(download_dir, f"*{vod_id}*.mp4")
    found_files = glob.glob(search_pattern)

    if found_files:
        # This is the full path (e.g., /vods/2025-12-31_12345678_title.mp4)
        final_file_path = found_files[0]
        print(f"Found downloaded file: {final_file_path}")
        return final_file_path
    else:
        raise Exception("Download succeeded but the file could not be located in the directory.")