from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Data model for a particular world in Tribal Wars
# Including the current timelapse images that have already been generated
# Including the files present in S3 for this world

# Every single world model has many image files associated with it
# Every single s3 file model has one world associated with it, but many files for a snapshot

class BaseWorldModel(BaseModel):
    """Base model with common fields.

    Args:
        BaseModel (_type_): The base model class.
    """
    world: str
    server: str


class WorldSettingsModel(BaseWorldModel):
    """World configuration and timelapse settings.

    Args:
        BaseWorldModel (_type_): The base world model class.
    """
    max_coords: int = Field(..., description="The maximum coordinates for this world, e.g., 750 for a 1500x1500 map.")
    has_barbarians: bool = Field(..., description="Indicates if the world has barbarian villages.")

    timelapse_interval: int = Field(..., description="The interval in hours for generating timelapse images.")

class SnapshotFileModel(BaseWorldModel):
    """Represents the files associated with a snapshot.

    Args:
        BaseWorldModel (_type_): The base world model class.
    """
    timestamp: int
    village_data_path: str
    player_data_path: str
    tribe_data_path: str
    conquer_data_path: Optional[str] = None
    killall_data_path: Optional[str] = None
    killall_tribe_data_path: Optional[str] = None

class TimelapseImageModel(SnapshotFileModel):
    """Represents a timelapse image for a world.

    Args:
        SnapshotFileModel (_type_): The snapshot file model class.
    """
    top_players_image_path: Optional[str] = None  # T10 Players
    top_tribes_image_path: Optional[str] = None  # T10 Tribes

    image_generated: bool = Field(..., description="Indicates if the timelapse image has been generated.")
    generation_timestamp: Optional[int] = None
    generation_error: Optional[str] = None


class WorldModel(WorldSettingsModel):
    """Represents a world with its settings, snapshots, and timelapse images.

    Args:
        WorldSettingsModel (_type_): The world settings model class.
    """
    snapshots: List[TimelapseImageModel] = Field(default_factory=list, description="List of snapshots and their associated files.")
    last_updated: Optional[int] = None
