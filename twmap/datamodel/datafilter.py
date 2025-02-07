from twmap.datamodel.datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel

import pandas as pd

class DataFilter:

    def __init__(self, village_df: pd.DataFrame, player_df: pd.DataFrame, tribe_df: pd.DataFrame, conquer_df: pd.DataFrame):
        self.village_df = village_df
        self.player_df = player_df
        self.tribe_df = tribe_df
        self.conquer_df = conquer_df

        self.joined_player_villages = pd.merge(self.village_df, self.player_df, on="playerid")
    
    def get_t10_players(self):
        """Get top 10 players by points and return list of ids

        Returns:
            _type_: _description_
        """
        return self.player_df.nlargest(10, "points")
    
    def get_t10_tribes(self):
        """Get top 10 tribes by points.

        Returns:
            pd.DataFrame: DataFrame containing top 10 tribes by points.
        """
        return self.tribe_df.nlargest(10, "tribe_points")

    def filter_villages_player(self, player_id: int):
        """Filter villages by player id.

        Args:
            player_id (int): The ID of the player.

        Returns:
            pd.DataFrame: DataFrame containing villages of the specified player.
        """
        return self.village_df[self.village_df["playerid"] == player_id]
    
    def filter_villages_tribe(self, tribe_id: int):
        """Filter villages by tribe id, first get all players in tribe then filter villages by player ids
        """
        players_in_tribe = self.player_df[self.player_df["tribeid"] == tribe_id]
        player_ids = players_in_tribe["playerid"]
        return self.village_df[self.village_df["playerid"].isin(player_ids)]
    
    def get_t10_player_villages(self):
        """Get top 10 players by points and return a single DataFrame of villages

        Returns:
            pd.DataFrame: DataFrame containing villages of top 10 players
        """
        t10_players = self.get_t10_players()
        t10_player_villages = [self.filter_villages_player(player_id) for player_id in t10_players["playerid"]]
        return pd.concat(t10_player_villages, ignore_index=True)
    
    def get_t10_tribe_villages(self):
        """Get top 10 tribes by points and return df of villages with tribeid included

        Returns:
            pd.DataFrame: DataFrame containing villages of top 10 tribes with tribeid included
        """
        t10_tribes = self.get_t10_tribes()
        t10_tribe_villages = [self.filter_villages_tribe(tribe_id) for tribe_id in t10_tribes["tribeid"]]
        result_df = pd.concat(t10_tribe_villages, ignore_index=True)
        result_df = result_df.merge(self.player_df[['playerid', 'tribeid']], on='playerid', how='left')
        return result_df
