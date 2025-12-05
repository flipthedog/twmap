from twmap.snapshot.snapshot_datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel
import pandas as pd
import logging


class DataFilter:
    """Class to filter villages, players, tribes, and conquers based on various criteria for a single snapshot.
    
    """

    def __init__(self, village_df: pd.DataFrame, player_df: pd.DataFrame, tribe_df: pd.DataFrame, conquer_df: pd.DataFrame,
                 killall_df: pd.DataFrame = None, killall_df_tribe: pd.DataFrame = None, killatt_df: pd.DataFrame = None, 
                 killdef_df: pd.DataFrame = None, killtribeatt_df: pd.DataFrame = None, killtribedef_df: pd.DataFrame = None):
        self.village_df = village_df
        self.player_df = player_df
        self.tribe_df = tribe_df
        self.conquer_df = conquer_df
        self.killall_df = killall_df
        self.killall_df_tribe = killall_df_tribe
        self.killatt_df = killatt_df
        self.killdef_df = killdef_df
        self.killtribeatt_df = killtribeatt_df
        self.killtribedef_df = killtribedef_df
        
        self.printed_timestamp = pd.to_datetime(village_df["datetime"][0], format="%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        self.world_id = village_df.iloc[0]["world_id"]

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
            data_pull_datetime = pd.to_datetime(data_pull_datetime, format="%Y%m%d_%H%M%S")
            data_pull_datetime = data_pull_datetime.astype(int) // 10**9
            data_pull_datetime = data_pull_datetime.iloc[0]
            past_three_days = data_pull_datetime - (86400 * 3)
            past_day_conquers = self.conquer_df[
                (self.conquer_df["timestamp"] > past_three_days) & 
                (self.conquer_df["timestamp"] <= data_pull_datetime)
            ]
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
    
    def filter_villages_by_tribe_ids(self, tribe_ids: list):
        """Filter villages by list of tribe ids.

        Args:
            tribe_ids (list): List of tribe ids.

        Returns:
            pd.DataFrame: DataFrame containing villages of the specified tribe ids with tribeid included.
        """
        tribe_df = self.filter_tribes(tribe_ids)
        players_in_tribes = self.player_df[self.player_df["tribeid"].isin(tribe_df["tribeid"])]
        villages = self.village_df[self.village_df["playerid"].isin(players_in_tribes["playerid"])]
        return villages.merge(players_in_tribes[['playerid', 'tribeid']], on='playerid', how='left')
    
    def get_past_day_conquers_by_tribe_ids(self, tribe_ids: list):
        """Get conquers from the past day of tribes specified by ids. Uses the epoch timestamp to filter. Return filter on village df

        Args:
            tribe_ids (list): List of tribe ids.

        Returns:
            pd.DataFrame: DataFrame containing conquers from the past day of tribes specified by ids.
        """
        past_day_conquers = self.get_past_day_conquers()
        if past_day_conquers.empty:
            logging.info("No conquers found in the past day for the specified tribe ids.")
            return pd.DataFrame()
        tribe_villages = self.filter_villages_by_tribe_ids(tribe_ids)
        result = tribe_villages[tribe_villages["villageid"].isin(past_day_conquers["villageid"])]
        if result.empty:
            logging.info("No conquers found in the past day for villages of the specified tribe ids.")
        return result
    
    def get_past_day_conquers_by_tribe_tags(self, tribe_tags: list):
        """Get conquers from the past day of tribes specified by tags. Uses the epoch timestamp to filter. Return filter on village df

        Args:
            tribe_tags (list): List of tribe tags.

        Returns:
            pd.DataFrame: DataFrame containing conquers from the past day of tribes specified by tags.
        """
        past_day_conquers = self.get_past_day_conquers()
        if past_day_conquers.empty:
            logging.info("No conquers found in the past day for the specified tribe tags.")
            return pd.DataFrame()
        tribe_villages = self.filter_villages_by_tribe_tags(tribe_tags)
        result = tribe_villages[tribe_villages["villageid"].isin(past_day_conquers["villageid"])]
        if result.empty:
            logging.info("No conquers found in the past day for villages of the specified tribe tags.")
        return result
    
    def get_past_day_conquers_by_player_names(self, player_names: list):
        """Get conquers from the past day of players specified by names. Uses the epoch timestamp to filter. Return filter on village df

        Args:
            player_names (list): List of player names.

        Returns:
            pd.DataFrame: DataFrame containing conquers from the past day of players specified by names.
        """
        player_villages = self.filter_villages_by_player_names(player_names)
        past_day_conquers = self.get_past_day_conquers()
        if past_day_conquers.empty:
            logging.info("No conquers found in the past day for the specified player names.")
            return pd.DataFrame()
        return player_villages[player_villages["villageid"].isin(past_day_conquers["villageid"])]
    
    def get_top_10_killall_players(self):
        """Get top 10 killall players.

        Returns:
            pd.DataFrame: DataFrame containing top 10 killall players.
        """
        if self.killall_df is None:
            logging.info("No killall data available.")
            return pd.DataFrame()
        
        killall_df_numeric = self.killall_df.copy()
        killall_df_numeric["units_defeated"] = pd.to_numeric(killall_df_numeric["units_defeated"], errors='coerce')
        top_10_killall_player_ids = killall_df_numeric.nlargest(10, "units_defeated")["playerid"].tolist()
        filtered_players = self.filter_players(top_10_killall_player_ids)
        result = filtered_players.merge(self.killall_df[['playerid', 'units_defeated']], on='playerid', how='left')
        return result.sort_values('units_defeated', ascending=False)
    
    def get_top_10_killall_tribes(self):
        """Get top 10 killall tribes.

        Returns:
            pd.DataFrame: DataFrame containing top 10 killall tribes.
        """
        if self.killall_df_tribe is None:
            logging.info("No killall tribe data available.")
            return pd.DataFrame()
        
        killall_df_tribe_numeric = self.killall_df_tribe.copy()
        killall_df_tribe_numeric["units_defeated"] = pd.to_numeric(killall_df_tribe_numeric["units_defeated"], errors='coerce')
        top_10_killall_tribe_ids = killall_df_tribe_numeric.nlargest(10, "units_defeated")["tribeid"].tolist()
        filtered_tribes = self.filter_tribes(top_10_killall_tribe_ids)
        result = filtered_tribes.merge(killall_df_tribe_numeric[['tribeid', 'units_defeated']], on='tribeid', how='left')
        return result.sort_values('units_defeated', ascending=False)
    
    def get_killall_t10_players(self):
        """Get killall of top 10 players
        """
        t10_players = self.get_t10_players()
        if self.killall_df is None:
            logging.info("No killall data available.")
            return pd.DataFrame()
        
        killall_data = self.killall_df[self.killall_df["playerid"].isin(t10_players["playerid"])]
        return killall_data.merge(self.player_df[['playerid', 'name']], on='playerid', how='left')
    
    def get_killall_t10_tribes(self):
        """Get killall of top 10 tribes
        """
        t10_tribes = self.get_t10_tribes()
        if self.killall_df_tribe is None:
            logging.info("No killall tribe data available.")
            return pd.DataFrame()
        
        killall_data = self.killall_df_tribe[self.killall_df_tribe["tribeid"].isin(t10_tribes["tribeid"])]
        return killall_data.merge(self.tribe_df[['tribeid', 'tag']], on='tribeid', how='left')
    
    def get_tribe_war_overview(self, window_days: int = 3, tribe_ids: list = None):
        """Summarize recent village transfers between tribes to highlight war outcomes.

        Args:
            window_days: Time window (in days) to inspect. Minimum enforced is 1 day.
            tribe_ids: Optional list of tribe IDs to focus on. If provided, only
                transfers where either tribe participates will be returned.

        Returns:
            dict: "pairwise" DataFrame showing per tribe-pair gains and "totals"
                  DataFrame showing aggregate gains/losses per tribe.
        """
        if self.conquer_df.empty:
            logging.info("No conquer data available to summarize wars.")
            return {"pairwise": pd.DataFrame(), "totals": pd.DataFrame()}

        data_pull_datetime = self.conquer_df["datetime"]
        if data_pull_datetime.empty:
            logging.info("No conquer timestamps available.")
            return {"pairwise": pd.DataFrame(), "totals": pd.DataFrame()}

        data_pull_datetime = pd.to_datetime(data_pull_datetime, format="%Y%m%d_%H%M%S")
        data_pull_datetime = data_pull_datetime.astype(int) // 10**9
        window_end = data_pull_datetime.iloc[0]
        window_seconds = max(window_days, 1) * 86400
        window_start = window_end - window_seconds

        recent_conquers = self.conquer_df[
            (self.conquer_df["timestamp"] > window_start) &
            (self.conquer_df["timestamp"] <= window_end)
        ].copy()

        if recent_conquers.empty:
            logging.info("No conquers found in the requested window for war overview.")
            return {"pairwise": pd.DataFrame(), "totals": pd.DataFrame()}

        required_owner_cols = {"new_owner_id", "old_owner_id"}
        if not required_owner_cols.issubset(recent_conquers.columns):
            logging.error("Conquer dataframe missing owner columns required for war overview: %s", required_owner_cols)
            return {"pairwise": pd.DataFrame(), "totals": pd.DataFrame()}

        recent_conquers = recent_conquers.rename(columns={
            "new_owner_id": "new_playerid",
            "old_owner_id": "old_playerid"
        })

        player_subset = self.player_df[["playerid", "tribeid", "name"]]
        tribe_subset = self.tribe_df[["tribeid", "tag"]]

        recent_conquers = recent_conquers.merge(
            player_subset.rename(columns={"playerid": "old_playerid", "tribeid": "old_tribeid", "name": "old_player_name"}),
            on="old_playerid",
            how="left"
        )
        recent_conquers = recent_conquers.merge(
            player_subset.rename(columns={"playerid": "new_playerid", "tribeid": "new_tribeid", "name": "new_player_name"}),
            on="new_playerid",
            how="left"
        )

        recent_conquers = recent_conquers.merge(
            tribe_subset.rename(columns={"tribeid": "old_tribeid", "tag": "old_tribe_tag"}),
            on="old_tribeid",
            how="left"
        )
        recent_conquers = recent_conquers.merge(
            tribe_subset.rename(columns={"tribeid": "new_tribeid", "tag": "new_tribe_tag"}),
            on="new_tribeid",
            how="left"
        )

        if tribe_ids is not None:
            tribe_id_set = set(tribe_ids)
            recent_conquers = recent_conquers[
                recent_conquers["old_tribeid"].isin(tribe_id_set) |
                recent_conquers["new_tribeid"].isin(tribe_id_set)
            ]

        recent_conquers = recent_conquers.dropna(subset=["old_tribeid", "new_tribeid"])
        recent_conquers = recent_conquers[recent_conquers["old_tribeid"] != recent_conquers["new_tribeid"]]

        if recent_conquers.empty:
            logging.info("No tribe-versus-tribe conquers to report in the selected window.")
            return {"pairwise": pd.DataFrame(), "totals": pd.DataFrame()}

        pairwise = recent_conquers.groupby(
            ["new_tribeid", "new_tribe_tag", "old_tribeid", "old_tribe_tag"],
            dropna=False
        ).agg(
            villages_taken=("villageid", "count"),
            latest_timestamp=("timestamp", "max")
        ).reset_index()

        pairwise = pairwise.sort_values("villages_taken", ascending=False)

        gains = pairwise.groupby(["new_tribeid", "new_tribe_tag"], dropna=False)["villages_taken"].sum().reset_index()
        gains = gains.rename(columns={
            "new_tribeid": "tribeid",
            "new_tribe_tag": "tribe_tag",
            "villages_taken": "villages_gained"
        })

        losses = pairwise.groupby(["old_tribeid", "old_tribe_tag"], dropna=False)["villages_taken"].sum().reset_index()
        losses = losses.rename(columns={
            "old_tribeid": "tribeid",
            "old_tribe_tag": "tribe_tag",
            "villages_taken": "villages_lost"
        })

        tribe_totals = gains.merge(losses, on=["tribeid", "tribe_tag"], how="outer").fillna(0)
        tribe_totals["net_villages"] = tribe_totals["villages_gained"] - tribe_totals["villages_lost"]
        tribe_totals = tribe_totals.sort_values("net_villages", ascending=False).reset_index(drop=True)

        return {"pairwise": pairwise, "totals": tribe_totals}
    
    def get_past_month_conquers(self):
        """Get conquers from the past month. Uses the epoch timestamp to filter. Return filter on village df

        Returns:
            pd.DataFrame: DataFrame containing conquers from the past month.
        """
        data_pull_datetime = self.conquer_df["datetime"]
        if data_pull_datetime.empty:
            logging.info("No conquers found in the dataset.")
            return pd.DataFrame()
        data_pull_datetime = pd.to_datetime(data_pull_datetime, format="%Y%m%d_%H%M%S")
        data_pull_datetime = data_pull_datetime.astype(int) // 10**9
        data_pull_datetime = data_pull_datetime.iloc[0]
        past_month = data_pull_datetime - (86400 * 30)
        past_month_conquers = self.conquer_df[
            (self.conquer_df["timestamp"] > past_month) & 
            (self.conquer_df["timestamp"] <= data_pull_datetime)
        ]
        if past_month_conquers.empty:
            logging.info("No conquers found in the past month.")
            return pd.DataFrame()
        return self.village_df[self.village_df["villageid"].isin(past_month_conquers["villageid"])]
    
    def get_biggest_conquerors(self, top_n: int = 10):
        """Get biggest conquerors in the past month.

        Args:
            top_n (int): Number of top conquerors to return.
        Returns:
            pd.DataFrame: DataFrame containing top N conquerors in the past month.
        """
        past_month_conquers = self.get_past_month_conquers()
        if past_month_conquers.empty:
            logging.info("No conquers found in the past month for biggest conquerors.")
            return pd.DataFrame()
        conquer_counts = past_month_conquers['conqueror_playerid'].value_counts().head(top_n).reset_index()
        conquer_counts.columns = ['playerid', 'conquer_count']
        result = conquer_counts.merge(self.player_df[['playerid', 'name']], on='playerid', how='left')
        return result
    
    