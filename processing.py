import subprocess
import os
import datetime
import re
import json

STAGING_DIR = os.environ.get("STAGING_DIR", "/vods")

# Environment variables used to signal GPU availability in Docker/Linux:
# Set these to '1' in your TrueNAS Custom App Env Vars if the corresponding GPU is passed through.
USE_INTEL_QSV = os.environ.get("USE_INTEL_QSV") # For Intel Arc
USE_NVIDIA_NVENC = os.environ.get("USE_NVIDIA_NVENC") # For NVIDIA

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
        
        # Parse the JSON output (twitch-dl info returns a list of VODs)
        metadata_list = json.loads(result.stdout)
        
        if not metadata_list:
            raise ValueError(f"Metadata not found for VOD ID {vod_id}.")
            
        return metadata_list[0]
        
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
        print(f"FATAL ERROR: Could not fetch or parse metadata for VOD {vod_id}.")
        print(f"Details: {e}")
        # Re-raise the error to halt the script
        raise

def download_vod(vod_id: str, raw_output_path: str):

# --- STEP 1: RETRIEVE METADATA ---
    metadata = get_vod_metadata(vod_id)

# --- STEP 2: FORMAT DATE AND CLEAN TITLE ---
    
    # 2a. Format the Date (e.g., '2023-11-20')
    # The 'created_at' is an ISO timestamp string (e.g., "2023-11-20T19:00:00Z")
    created_date = metadata['created_at']
    dt_object = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
    date_str = dt_object.strftime('%Y-%m-%d')
    
    # 2b. Clean the Title (essential for file paths)
    title = metadata['title']
    cleaned_title = re.sub(r'[^\w\s-]', '', title).strip()
    cleaned_title = re.sub(r'\s+', '_', cleaned_title).lower()
    
    # Remove characters that are unsafe or illegal in file names (e.g., /, :, ?, <, >, ")
    final_filename = f"{date_str}_{cleaned_title}.mp4"
    
    # Replace spaces with underscores and convert to lowercase for a clean filename
    base_dir = os.path.dirname(raw_output_path)

    # --- STEP 3: CONSTRUCT THE FINAL PATH ---
    final_file_path = os.path.join(base_dir, final_filename)

    print(f"VOD Title: '{title}'")
    print(f"Target RAW file: {raw_output_path}")
    print(f"Target FINAL name: {final_file_path}")

    # --- STEP 4: EXECUTE DOWNLOAD ---
    # The list of command arguments (assuming 1080p60 is the desired quality)
    command = [
        'twitch-dl', 'download', vod_id,
        '-q', '1080p60',
        '-o', raw_output_path,
    ]
    
    print(f"Starting download of {metadata['channel']}'s VOD...")
    subprocess.run(command, check=True)

    print(f"Download complete: {raw_output_path}")

    # 5. Return the calculated final path to main.py for renaming/tracking
    return final_file_path 