import pandas as pd
from pandantic import Pandantic
import boto3 
import os

from io import StringIO

from twmap.snapshot.snapshot_datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel
from twmap.world.world_datamodel import WorldModel
from twmap.world.world_loader import WorldLoader

from typing import List, Optional

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataLoader:
    """Loads a snapshot from S3 into memory as pandas dataframes
    """

    def __init__(self, world_loader: WorldLoader):
        
        self.world_loader = world_loader

        self.village_models = []
        self.player_models = []
        self.tribe_models = []
        self.conquer_models = []

        self.s3_client = boto3.client("s3")
        
        self.t10_tribes_list = []
        self.t10_players_list = []
        self.max_coords = 0
        
    def retrieve_from_s3(self, file_path: str):
        # Use the snapshot bucket from world_loader for data files
        bucket = self.world_loader.s3_snapshot_bucket
        response = self.s3_client.get_object(Bucket=bucket, Key=file_path)
        return response["Body"].read().decode("utf-8")

    def load_all_files(self):
        """Load all files from S3 into memory as pandas dataframes
        Returns:
            Tuple of (tribe_df, player_df, village_df, conquer_df)
        """
        for snapshot in self.world_loader.world_model.snapshots:
            tribe_model, player_model, village_model, conquer_model = self.load_specific_files(
                snapshot.tribe_data_path,
                snapshot.player_data_path,
                snapshot.village_data_path,
                snapshot.conquer_data_path
            )
            self.tribe_models.append(tribe_model)
            self.player_models.append(player_model)
            self.village_models.append(village_model)
            self.conquer_models.append(conquer_model)
        
        return self.tribe_models, self.player_models, self.village_models, self.conquer_models

    def load_specific_files(self, ally_path: str, player_path: str, village_path: str, conquer_path: str):
        """Load specific files from S3 into memory as pandas dataframes
        Args:
            ally_path (str): Path to ally file in S3
            player_path (str): Path to player file in S3  
            village_path (str): Path to village file in S3
            conquer_path (str): Path to conquer file in S3
        Returns:
            Tuple of (tribe_df, player_df, village_df, conquer_df)
        """

        # Load tribe/ally data
        content = self.retrieve_from_s3(ally_path)
        tribe_df = pd.read_csv(StringIO(content), sep=",", header=None, names=TribeModel.model_fields.keys(), index_col=False)
        tribe_schema = Pandantic(TribeModel)
        tribe_model = tribe_schema.validate(tribe_df)
        tribe_model["datetime"] = "_".join(ally_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
        tribe_model["world_id"] = ally_path.split("/")[-1].split("_")[1]
        tribe_model["file_path"] = ally_path

        # Load player data
        content = self.retrieve_from_s3(player_path)
        player_df = pd.read_csv(StringIO(content), sep=",", header=None, names=PlayerModel.model_fields.keys(), index_col=False)
        player_schema = Pandantic(PlayerModel)
        player_model = player_schema.validate(player_df)
        player_model["datetime"] = "_".join(player_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
        player_model["world_id"] = player_path.split("/")[-1].split("_")[1]
        player_model["file_path"] = player_path

        # Load village data
        content = self.retrieve_from_s3(village_path)
        village_df = pd.read_csv(StringIO(content), sep=",", header=None, names=VillageModel.model_fields.keys(), index_col=False)
        village_schema = Pandantic(VillageModel)
        village_model = village_schema.validate(village_df)
        village_model["datetime"] = "_".join(village_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
        village_model["world_id"] = village_path.split("/")[-1].split("_")[1]
        village_model["file_path"] = village_path

        # Load conquer data
        content = self.retrieve_from_s3(conquer_path)
        conquer_df = pd.read_csv(StringIO(content), sep=",", header=None, names=ConquerModel.model_fields.keys(), index_col=False)
        conquer_schema = Pandantic(ConquerModel)
        conquer_model = conquer_schema.validate(conquer_df)
        conquer_model["datetime"] = "_".join(conquer_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
        conquer_model["world_id"] = conquer_path.split("/")[-1].split("_")[1]
        conquer_model["file_path"] = conquer_path

        return tribe_model, player_model, village_model, conquer_model
    
    def get_top_10_tribes(self):
        """Create a list of the top 10 tribes over multiple dataframes
        """
        
        tribe_df = pd.concat(self.tribe_models)
        
        top_10_tribes = tribe_df.groupby("name")["tribe_points"].max().sort_values(ascending=False).head(10)
        
        return top_10_tribes
    
    def get_top_10_players(self):
        """Create a list of the top 10 players over multiple dataframes
        """
        
        player_df = pd.concat(self.player_models)
        
        top_10_players = player_df.groupby("name")["points"].max().sort_values(ascending=False).head(10)
        
        return top_10_players
    
    def get_max_village_coordinates(self):
        """Get the max village coordinates over multiple dataframes
        """
        
        village_df = pd.concat(self.village_models)
        
        max_village_coordinates = max(village_df["x_coord"].max(), village_df["y_coord"].max())
        
        return max_village_coordinates
    
if __name__ == "__main__":
    loader = DataLoader("s3://tribalwars-scraped/", "en142")

    print(loader.load_from_s3_to_memory())