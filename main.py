import os
import time
import datetime
import sys

# Imports from internal modules
from .state_manager import StateManager
from .twitch_api import get_access_token, get_channel_info, get_latest_vod_info
from .processing import download_vod, transcode_vod, generate_safe_filename
# from .youtube_api import upload_video # Keep commented until implemented

# --- CONFIGURATION (Paths must match Docker/TrueNAS mounts) ---
CONFIG_DIR = "/app/config"
STAGING_DIR = "/vods"
TRACKER_FILE = os.path.join(CONFIG_DIR, "last_vod_id.txt")

# --- MAIN CONTROL FLOW ---

def check_environment():
    """Validates required environment variables."""
    required_vars = [
        "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "TWITCH_CHANNEL_NAME",
        # Uncomment these when you implement the YouTube API part:
        # "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"
    ]
    for var in required_vars:
        if not os.environ.get(var):
            raise EnvironmentError(f"Missing required environment variable: {var}")

def main():
    """Coordinates the entire check, download, transcode, and upload process."""

if __name__ == "__main__":
    main()