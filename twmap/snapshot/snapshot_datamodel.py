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

class KillAllModel(BaseModel):
    """Represents a list of players and their number of units defeated in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    rank: int
    playerid: int
    units_defeated: int

class KillAttModel(BaseModel):
    """Represents a list of players and their number of units defeated as attacker in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    rank: int
    playerid: int
    ops_defeated_as_attacker: int

class KillDefModel(BaseModel):
    """Represents a list of players and their number of units defeated as defender in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    rank: int
    playerid: int
    ops_defeated_as_defender: int

class KillTribeModel(BaseModel):
    """Represents a list of tribes and their number of units defeated in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    rank: int
    tribeid: int
    units_defeated: int

class KillTribeAttModel(BaseModel):
    """Represents a list of tribes and their number of units defeated as attacker in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    rank: int
    tribeid: int
    ops_defeated_as_attacker: int

class KillTribeDefModel(BaseModel):
    """Represents a list of tribes and their number of units defeated as defender in a snapshot.

    Args:
        BaseModel (pydantic.BaseModel): The base model class from Pydantic.
    """
    rank: int
    tribeid: int
    ops_defeated_as_defender: int
