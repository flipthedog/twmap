from twmap.datamodel.datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel
import pandas as pd
import logging

class DataFilter:

    def __init__(self, village_df: pd.DataFrame, player_df: pd.DataFrame, tribe_df: pd.DataFrame, conquer_df: pd.DataFrame):
        self.village_df = village_df
        self.player_df = player_df
        self.tribe_df = tribe_df
        self.conquer_df = conquer_df

        self.joined_player_villages = pd.merge(self.village_df, self.player_df, on="playerid")

        # Cache variables
        self._past_day_conquers = None
        self._t10_players = None
        self._t10_tribes = None

    def get_past_day_conquers(self):
        """Get conquers from the past day. Uses the epoch timestamp to filter. Return filter on village df

        Returns:
            pd.DataFrame: DataFrame containing conquers from the past day.
        """
        if self._past_day_conquers is None:
            data_pull_datetime = self.conquer_df["datetime"]
            if data_pull_datetime.empty:
                logging.info("No conquers found in the dataset.")
                return pd.DataFrame()
            data_pull_datetime = pd.to_datetime(data_pull_datetime, format="%Y-%m-%d %H:%M:%S")
            data_pull_datetime = data_pull_datetime.astype(int) // 10**9
            data_pull_datetime = data_pull_datetime.iloc[0]
            past_day = data_pull_datetime - 86400
            past_day_conquers = self.conquer_df[self.conquer_df["timestamp"] > past_day]
            if past_day_conquers.empty:
                logging.info("No conquers found in the past day.")
                return pd.DataFrame()
            self._past_day_conquers = self.village_df[self.village_df["villageid"].isin(past_day_conquers["villageid"])]
        return self._past_day_conquers

    def get_past_day_t10_conquers_players(self):
        """Get conquers from the past day of top 10 players. Uses the epoch timestamp to filter. Return filter on village df

        Returns:
            pd.DataFrame: DataFrame containing conquers from the past day of top 10 players.
        """
        past_day_conquers = self.get_past_day_conquers()
        if past_day_conquers.empty:
            logging.info("No conquers found in the past day for top 10 players.")
            return pd.DataFrame()
        t10_players = self.get_t10_players()
        t10_player_villages = pd.concat([self.filter_villages_player(player_id) for player_id in t10_players["playerid"]], ignore_index=True)
        result = t10_player_villages[t10_player_villages["villageid"].isin(past_day_conquers["villageid"])]
        if result.empty:
            logging.info("No conquers found in the past day for villages of top 10 players.")
        return result

    def get_past_day_t10_conquers_tribes(self):
        """Get conquers from the past day of top 10 tribes. Uses the epoch timestamp to filter. Return filter on village df

        Returns:
            pd.DataFrame: DataFrame containing conquers from the past day of top 10 tribes.
        """
        past_day_conquers = self.get_past_day_conquers()
        if past_day_conquers.empty:
            logging.info("No conquers found in the past day for top 10 tribes.")
            return pd.DataFrame()
        t10_tribes = self.get_t10_tribes()
        t10_tribe_villages = pd.concat([self.filter_villages_tribe(tribeid) for tribeid in t10_tribes["tribeid"]], ignore_index=True)
        t10_tribe_villages = t10_tribe_villages.merge(self.player_df[['playerid', 'tribeid']], on='playerid', how='left')
        result = t10_tribe_villages[t10_tribe_villages["villageid"].isin(past_day_conquers["villageid"])]
        if result.empty:
            logging.info("No conquers found in the past day for villages of top 10 tribes.")
        return result

    def get_t10_players(self):
        """Get top 10 players by points and return list of ids

        Returns:
            pd.DataFrame: DataFrame containing top 10 players by points.
        """
        if self._t10_players is None:
            self._t10_players = self.player_df.nlargest(10, "points")
        return self._t10_players
    
    def get_t10_tribes(self):
        """Get top 10 tribes by points.

        Returns:
            pd.DataFrame: DataFrame containing top 10 tribes by points.
        """
        if self._t10_tribes is None:
            self._t10_tribes = self.tribe_df.nlargest(10, "tribe_points")
        return self._t10_tribes

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

    def filter_players(self, player_ids: list):
        """Filter players by list of player ids.

        Args:
            player_ids (list): List of player ids.

        Returns:
            pd.DataFrame: DataFrame containing players of the specified player ids.
        """
        return self.player_df[self.player_df["playerid"].isin(player_ids)]
    
    def filter_tribes(self, tribe_ids: list):
        """Filter tribes by list of tribe ids.

        Args:
            tribe_ids (list): List of tribe ids.

        Returns:
            pd.DataFrame: DataFrame containing tribes of the specified tribe ids.
        """
        return self.tribe_df[self.tribe_df["tribeid"].isin(tribe_ids)]

    def filter_by_tribe_tags(self, tribe_tags: list):
        """Filter tribes by list of tribe tags.

        Args:
            tribe_tags (list): List of tribe tags.

        Returns:
            pd.DataFrame: DataFrame containing tribes of the specified tribe tags.
        """
        return self.tribe_df[self.tribe_df["tag"].isin(tribe_tags)]
    
    def filter_by_player_names(self, player_names: list):
        """Filter players by list of player names.

        Args:
            player_names (list): List of player names.

        Returns:
            pd.DataFrame: DataFrame containing players of the specified player names.
        """
        return self.player_df[self.player_df["name"].isin(player_names)]

    def filter_villages_by_player_names(self, player_names: list):
        """Filter villages by list of player names.

        Args:
            player_names (list): List of player names.

        Returns:
            pd.DataFrame: DataFrame containing villages of the specified player names.
        """
        player_df = self.filter_by_player_names(player_names)
        return self.village_df[self.village_df["playerid"].isin(player_df["playerid"])]
    
    def filter_villages_by_tribe_tags(self, tribe_tags: list):
        """Filter villages by list of tribe tags.

        Args:
            tribe_tags (list): List of tribe tags.

        Returns:
            pd.DataFrame: DataFrame containing villages of the specified tribe tags with tribeid included.
        """
        tribe_df = self.filter_by_tribe_tags(tribe_tags)
        players_in_tribes = self.player_df[self.player_df["tribeid"].isin(tribe_df["tribeid"])]
        villages = self.village_df[self.village_df["playerid"].isin(players_in_tribes["playerid"])]
        return villages.merge(players_in_tribes[['playerid', 'tribeid']], on='playerid', how='left')
    
    def get_past_day_conquers_by_tribe_tags(self, tribe_tags: list):
        """Get conquers from the past day of tribes specified by tags. Uses the epoch timestamp to filter. Return filter on village df

        Args:
            tribe_tags (list): List of tribe tags.

        Returns:
            pd.DataFrame: DataFrame containing conquers from the past day of tribes specified by tags.
        """
        tribe_villages = self.filter_villages_by_tribe_tags(tribe_tags)
        past_day_conquers = self.get_past_day_conquers()
        return tribe_villages[tribe_villages["villageid"].isin(past_day_conquers["villageid"])]
    
    def get_past_day_conquers_by_player_names(self, player_names: list):
        """Get conquers from the past day of players specified by names. Uses the epoch timestamp to filter. Return filter on village df

        Args:
            player_names (list): List of player names.

        Returns:
            pd.DataFrame: DataFrame containing conquers from the past day of players specified by names.
        """
        player_villages = self.filter_villages_by_player_names(player_names)
        past_day_conquers = self.get_past_day_conquers()
        return player_villages[player_villages["villageid"].isin(past_day_conquers["villageid"])]