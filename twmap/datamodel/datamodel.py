from pydantic import BaseModel


class VillageModel(BaseModel):
    villageid: int
    name: str
    x_coord: int
    y_coord: int
    playerid: int
    points: int
    unknown1: int


class PlayerModel(BaseModel):
    playerid: int
    name: str
    tribeid: int
    village_count: int
    points: int
    unknown1: int


class TribeModel(BaseModel):
    tribeid: int
    name: str
    tag: str
    num_members: int
    max_members: int
    tribe_points: int
    tribe_max_points: int
    rank: int


class ConquerModel(BaseModel):
    conquer_id: int
    village_id: int
    new_owner_id: int
    old_owner_id: int
