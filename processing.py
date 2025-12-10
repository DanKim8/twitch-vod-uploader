import subprocess
import os
import datetime
import re
import platform
import sys

STAGING_DIR = os.environ.get("STAGING_DIR", "/vods")

# Environment variables used to signal GPU availability in Docker/Linux:
# Set these to '1' in your TrueNAS Custom App Env Vars if the corresponding GPU is passed through.
USE_INTEL_QSV = os.environ.get("USE_INTEL_QSV") # For Intel Arc
USE_NVIDIA_NVENC = os.environ.get("USE_NVIDIA_NVENC") # For NVIDIA

"""Creates the final, structured filename: [YYYY-MM-DD]_safe_title.mp4"""
def generate_safe_filename(vod_info: dict, date_prefix: str) -> str:
    
    # Sanitize title by replacing unsafe characters with underscores
    title = vod_info['title']
    safe_title = re.sub(r'[^\w\-_\. ]', '_', title).replace(' ', '_')
    
    return f"{date_prefix}_{safe_title}.mp4"

def download_vod(vod_id: str, output_path: str):

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
    Dynamically selects the best H.265 (HEVC) encoder based on the execution environment.
    Prioritizes hardware acceleration, then falls back to efficient CPU encoding.
    """
    
    system_os = platform.system()
    command = ['ffmpeg']
    
    # --- HEVC Encoding Parameters ---
    # Common settings for output quality
    QUALITY_FACTOR = '20'       # General quality factor for QSV/NVENC
    CRF_QUALITY = '23'          # CRF for software (libx265); 23 is good balance
    AUDIO_BITRATE = '192k'      # FFmpeg command structure

    # 1. Hardware Detection (Highest Priority)
    
    # TrueNAS/Docker with Intel Arc/iGPU passed through
    if USE_INTEL_QSV == '1' and system_os == 'Linux':
        
        print("Detected Intel QSV (Arc). Using hardware H.265 encoding.")
        command.extend([
            '-hwaccel', 'qsv',
            '-i', input_path,
            '-c:v', 'hevc_qsv',
            '-q:v', QUALITY_FACTOR, 
            '-preset', 'fast',
        ])

    # TrueNAS/Docker with NVIDIA GPU passed through
    elif USE_NVIDIA_NVENC == '1' and system_os == 'Linux':
        
        print("Detected NVIDIA NVENC. Using hardware H.265 encoding.")
        command.extend([
            '-i', input_path,
            '-c:v', 'hevc_nvenc',       # H.265 NVIDIA encoder
            '-cq:v', QUALITY_FACTOR,    # Quality setting for NVENC
            '-preset', 'fast',
        ])
    
    # macOS (M-series Apple Silicon)
    elif system_os == 'Darwin':
        print("Detected macOS. Using native VideoToolbox for H.265.")
        command.extend([
            '-i', input_path,
            '-c:v', 'hevc_videotoolbox',
            '-q:v', '70',     # Quality factor for VideoToolbox (higher = better quality)
            '-realtime', '1', # Maximize encoding speed
        ])
    
    # Windows (Assumes H.265 capable GPU for testing)
    # Note: True hardware detection on Windows is complex; this is a placeholder.
    elif system_os == 'Windows':
        print("Detected Windows. Falling back to libx265 for portability.")
        command.extend([
            '-i', input_path,
            '-c:v', 'libx265', 
            '-crf', CRF_QUALITY,
            '-preset', 'medium',
        ])

    # 2. Software Fallback (Lowest Priority/Generic Linux)
    else:
        # Default for any unknown Linux environment without specific passthrough confirmed
        print("No specific GPU detected. Using CPU (libx265) software encoding.")
        command.extend([
            '-i', input_path,
            '-c:v', 'libx265',
            '-crf', CRF_QUALITY,
            '-preset', 'medium', # 'medium' is better than 'fast' for H.265 quality/size
        ])

    # 3. Common Audio and Output Parameters
    command.extend([
        '-c:a', 'aac',
        '-b:a', AUDIO_BITRATE,
        output_path
    ])
    
    # --- EXECUTE ---
    print(f"Executing FFmpeg...")
    subprocess.run(command, check=True)
    print(f"Transcoding complete. File saved to: {output_path}")
