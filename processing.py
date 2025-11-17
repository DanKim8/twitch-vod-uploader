import subprocess
import os
import datetime
import re

STAGING_DIR = os.environ.get("STAGING_DIR", "/vods")

def download_vod(vod_id: str, output_path: str):
    """Executes twitch-dl to download the VOD in source quality."""
    print(f"Starting download of VOD ID: {vod_id}")
    
    # Command: twitch-dl download [VOD_ID] -q source -o [output_path]
    command = [
        'twitch-dl', 'download', vod_id,
        '-q', 'source',
        '-o', output_path,
    ]
    
    subprocess.run(command, check=True)
    print(f"Download complete: {output_path}")

def transcode_vod(input_path: str, output_path: str):
    """
    Transcodes the VOD using Intel Arc (QSV) hardware acceleration to H.265.
    (Assumes Intel Arc GPU is correctly passed through to the container)
    """
    print(f"Starting hardware transcoding to H.265 (Arc QSV)...")
    
    # FFmpeg command structure
    command = [
        'ffmpeg',
        '-hwaccel', 'qsv', # Enable Intel Quick Sync Video
        '-i', input_path,
        
        # Video: H.265 (HEVC) QSV encoder, high quality, fast preset
        '-c:v', 'hevc_qsv',
        '-q:v', '20', # High quality factor (0 is best)
        '-preset', 'fast',
        
        # Audio: AAC, 192k bitrate
        '-c:a', 'aac',
        '-b:a', '192k',
        
        # Output file
        output_path
    ]
    
    subprocess.run(command, check=True)
    print(f"Transcoding complete. File saved to: {output_path}")

def generate_safe_filename(vod_info: dict, date_prefix: str) -> str:
    """Creates the final, structured filename: [YYYY-MM-DD]_safe_title.mp4"""
    # Sanitize title by replacing unsafe characters with underscores
    title = vod_info['title']
    safe_title = re.sub(r'[^\w\-_\. ]', '_', title).replace(' ', '_')
    
    return f"{date_prefix}_{safe_title}.mp4"