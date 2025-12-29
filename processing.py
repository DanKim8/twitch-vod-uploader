import subprocess
import os
from datetime import datetime
import re
import json

STAGING_DIR = os.environ.get("STAGING_DIR", "/vods")

def generate_final_filename(metadata: dict) -> str:
    """
    Creates a consistent, clean filename: YYYY-MM-DD_title.mp4
    Example: 'yo :> happy holidays :>' -> '2025-12-18_yo_happy_holidays.mp4'
    """
    # 1. Get the Date
    created_date = metadata.get('created_at') or metadata.get('published_at') or ""
    if created_date:
        # Extract just the YYYY-MM-DD part from the ISO string
        date_str = created_date.split('T')[0]
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # 2. Clean the Title
    title = metadata.get('title', 'Unknown_Title')
    
    # Step A: Remove all non-alphanumeric characters (keep only letters, numbers, spaces, and hyphens)
    clean = re.sub(r'[^\w\s-]', '', title)
    
    # Step B: Replace all spaces and existing underscores with a single underscore
    clean = re.sub(r'[\s_]+', '_', clean)
    
    # Step C: Strip any leading/trailing underscores and convert to lowercase
    clean = clean.strip('_').lower()
    
    return f"{date_str}_{clean}.mp4"

"""Creates the final, structured filename: [YYYY-MM-DD]_safe_title.mp4"""
def generate_safe_filename(vod_info: dict, date_prefix: str) -> str:
    
    # Sanitize title by replacing unsafe characters with underscores
    title = vod_info['title']
    safe_title = re.sub(r'[^\w\-_\. ]', '_', title).replace(' ', '_')
    
    return f"{date_prefix}_{safe_title}.mp4"
    
def get_vod_metadata(vod_id: str) -> dict:
    """
    Fetches the VOD metadata (including creation date and title) 
    using 'twitch-dl info --json'.
    """
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
        
        # --- ROBUST PARSING ---
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

    # --- STEP 1: RETRIEVE METADATA ---
    metadata = get_vod_metadata(vod_id)
    channel_name = metadata.get('owner', {}).get('displayName', 'Unknown')

    # --- STEP 2: FORMAT DATE AND CLEAN TITLE ---
    
    # 2a. Robust Date Fetching
    # Try 'created_at', then 'published_at', then use 'today' as a fallback
    created_date = metadata.get('createdAt') or metadata.get('publishedAt')
    
    if created_date:
        dt_object = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
        date_str = dt_object.strftime('%Y-%m-%d')
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')
        print("Warning: Could not find date in metadata. Using today's date.")
    
    # 2b. Clean the Title
    title = metadata.get('title', 'Unknown_Title')
    cleaned_title = re.sub(r'[^\w\s-]', '', title).strip()
    cleaned_title = re.sub(r'\s+', '_', cleaned_title).lower()
    
    final_filename = f"{date_str}_{cleaned_title}.mp4"
    base_dir = os.path.dirname(raw_output_path)

    # --- STEP 3: CONSTRUCT THE FINAL PATH ---
    final_file_path = os.path.join(base_dir, final_filename)

    print(f"VOD Title: '{title}'")
    
    # --- STEP 4: EXECUTE DOWNLOAD ---
    # Dig into 'owner' first, then 'display_name'
    qualities_to_try = ['1440p60', '1440p','1080p60', '1080p', '720p60', '720p', '480p']
    download_success = False

    channel_name = metadata.get('owner', {}).get('displayName', 'UnknownChannel')
    print(f"Starting download of {channel_name}'s VOD...")
 
    for q in qualities_to_try:
        print(f"Attempting to download with quality: {q}...")
        command = [
            'twitch-dl', 'download', str(vod_id),
            '-q', q,
            '-o', final_file_path,
        ]
    
        # Run the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Download successful at {q}!")
            download_success = True
            break
        else:
            # Check if the error was just 'Quality not found'
            if "not found" in result.stderr:
                print(f"⚠️ Quality {q} not available. Trying next...")
                continue
            else:
                # If it's a different error (e.g., disk full), stop immediately
                print(f"❌ Critical download error: {result.stderr}")
                raise Exception(result.stderr)

    if not download_success:
        raise Exception(f"Could not download VOD {vod_id} in any acceptable quality.")
    return final_file_path