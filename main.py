import os
import time
import datetime
import sys

# Imports from internal modules
from state_manager import StateManager
from twitch_api import get_access_token, get_channel_info, get_all_new_vods
from processing import download_vod, generate_safe_filename, generate_final_filename
from youtube_api import upload_video # Use the new upload function

# --- CONFIGURATION (must update in docker setting in truenas custom app) ---
#CONFIG_DIR = "/app/config"
#STAGING_DIR = "/vods"
#TRACKER_FILE = os.path.join(CONFIG_DIR, "last_vod_id.txt")

# --- CONFIGURATION for testing in windows local environment ---
CONFIG_DIR = "test_config"
STAGING_DIR = "test_vods"
TRACKER_FILE = os.path.join(CONFIG_DIR, "last_vod_id.txt")

# --- MAIN CONTROL FLOW ---
def check_environment():
    """Validates required environment variables."""
    required_vars = [
        "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "TWITCH_CHANNEL_NAME",
        "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"
    ]
    for var in required_vars:
        if not os.environ.get(var):
            raise EnvironmentError(f"Missing required environment variable: {var}")

def main():
    try:
        check_environment()
        state_manager = StateManager(TRACKER_FILE)
        os.makedirs(STAGING_DIR, exist_ok=True)

    except Exception as e:
        print(f"FATAL SETUP ERROR: {e}")
        sys.exit(1)

    try:
        # 1. AUTHENTICATION & CHANNEL STATUS
        twitch_token = get_access_token()
        user_id, is_live = get_channel_info(twitch_token)

        if is_live:
            print(f"[{time.ctime()}] Streamer is currently LIVE. Postponing download.")
        #    return

        # 2. GET ALL NEW VODS AND STATE CHECK
        last_vod_id = state_manager.get_last_vod_id()
        
        # Call the new function to fetch a list of VODs until the last processed ID
        vods_to_process = get_all_new_vods(user_id, twitch_token, last_vod_id)

        if not vods_to_process:
            print("No new VODs found since last run. Exiting.")
            return

        print("-" * 50)
        print(f"--- Found {len(vods_to_process)} new VODs to process ---")

        # --- ITERATE AND PROCESS EACH VOD ---   
        for vod in vods_to_process:
            vod_id = vod['id']
            vod_title = vod['title']
            
            print(f"\nSTARTING VOD: {vod_title} ({vod_id})")

            # 1. GENERATE CONSISTENT FILENAME AND PATH
            # We call this once here so download and upload use the SAME string
            final_filename = generate_final_filename(vod)
            final_file_path = os.path.join(STAGING_DIR, final_filename) 

            # 1. Setup file paths
            #date_prefix = datetime.datetime.fromisoformat(vod['created_at'].replace('Z', '+00:00')).strftime("%Y-%m-%d")
            
            #raw_file_name = f"{vod_id}_raw.mp4"
            #final_file_name = generate_safe_filename(vod, date_prefix)
            
            #raw_file_path = os.path.join(STAGING_DIR, raw_file_name)
            #final_file_path = os.path.join(STAGING_DIR, final_file_name)

            # 2. DOWNLOAD, UPLOAD, etc.
            try:
                download_vod(vod_id, final_file_path)
                
                # UPLOAD (Placeholder
                #upload_video(final_file_path, vod) # <--- CALL THE NEW FUNCTION
                
                # 3. CRUCIAL: UPDATE STATE AFTER SUCCESS
                state_manager.update_last_vod_id(vod_id)
                print(f"VOD {vod_id} successfully processed and marked.")
                
            except Exception as pipeline_e:
                print(f"FATAL ERROR processing VOD {vod_id}: {pipeline_e}. Stopping batch.")
                # If one VOD fails, we stop the whole batch and rely on the next
                # scheduled run to retry from the last *successfully saved* VOD ID.
                return 

        print("\n--- BATCH PROCESSING COMPLETE ---")

    except Exception as e:
        print(f"FATAL AUTOMATION ERROR during pipeline execution: {e}")
        # Add robust cleanup logic here to remove any partially created files
        sys.exit(1)

if __name__ == "__main__":
    main()