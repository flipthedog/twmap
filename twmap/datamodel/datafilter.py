from twmap.datamodel.datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel

import pandas as pd

class DataFilter:

    def __init__(self, village_df: pd.DataFrame, player_df: pd.DataFrame, tribe_df: pd.DataFrame, conquer_df: pd.DataFrame):
        self.village_df = village_df
        self.player_df = player_df
        self.tribe_df = tribe_df
        self.conquer_df = conquer_df
    
    def get_t10_players(self):
        """Get top 10 players by points and return list of ids

        Returns:
            _type_: _description_
        """
        return self.player_df.nlargest(10, "points")
    
    def get_t10_tribes(self):
        """Get top 10 tribes by points and return list of ids

        Returns:
            _type_: _description_
        """
        return self.tribe_df.nlargest(10, "tribe_points")

    def filter_villages_player(self, player_id: int):
        """Filter villages by player id

        Args:
            player_id (_type_): _description_

        Returns:
            _type_: _description_
        """
        return self.village_df[self.village_df["playerid"] == player_id]
    
    def filter_villages_tribe(self, tribe_id: int):
        """Filter villages by tribe id, first get all players in tribe then filter villages by player ids
        """
        players = self.player_df[self.player_df["tribeid"] == tribe_id]
        player_villages = [self.filter_villages_player(player_id) for player_id in players["playerid"]]
        result =  pd.concat(player_villages)
        result["tribeid"] = tribe_id
        return result        
    
    def get_t10_player_villages(self):
        """Get top 10 players by points and return df of villages

        Returns:
            _type_: _description_
        """
        t10_players = self.get_t10_players()
        return [self.filter_villages_player(player_id) for player_id in t10_players["playerid"]]
    
    def get_t10_tribe_villages(self):
        """Get top 10 tribes by points and return df of villages

        Returns:
            _type_: _description_
        """
        t10_tribes = self.get_t10_tribes()
        return [self.filter_villages_tribe(tribe_id) for tribe_id in t10_tribes["tribeid"]]
