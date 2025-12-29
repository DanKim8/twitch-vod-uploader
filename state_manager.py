import os
from typing import Optional

class StateManager:
    """Handles reading and updating the state file on the TrueNAS host."""
    
    def __init__(self, tracker_path: str):
        self.tracker_path = tracker_path
        # Ensure the parent directory for the tracker file exists
        os.makedirs(os.path.dirname(tracker_path), exist_ok=True)
    
    def get_last_vod_id(self)-> Optional[str]:
        """Reads the ID of the last VOD that was processed."""
        try:
            with open(self.tracker_path, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None 

    def update_last_vod_id(self, vod_id: str):
        """Writes the new VOD ID to the tracker file."""
        with open(self.tracker_path, 'w') as f:
            f.write(str(vod_id))