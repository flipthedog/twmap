from pydantic import BaseModel

# Data models for villages, players, tribes, and conquers in TW Snapshot
# A snapshot is a point in time representation of the game world

class VillageModel(BaseModel):
    """Represents a list of player + barbarian villages in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    villageid: int
    name: str
    x_coord: int
    y_coord: int
    playerid: int
    points: int
    unknown1: int


class PlayerModel(BaseModel):
    """Represents a list of players in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    playerid: int
    name: str
    tribeid: int
    village_count: int
    points: int
    unknown1: int


class TribeModel(BaseModel):
    """Represents a list of tribes in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    tribeid: int
    name: str
    tag: str
    num_members: int
    max_members: int
    tribe_points: int
    tribe_max_points: int
    rank: int


class ConquerModel(BaseModel):
    """Represents a list of conquers in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    villageid: int
    timestamp: int
    new_owner_id: int
    old_owner_id: int
