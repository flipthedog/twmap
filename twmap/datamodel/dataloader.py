import pandas as pd
from pandantic import Pandantic
import boto3 
import os

from io import StringIO

from twmap.datamodel.datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataLoader:

    def __init__(self, s3_data_path: str, world_id: str):
        
        self.world_id = world_id
                
        self.village_models = []
        self.player_models = []
        self.tribe_models = []
        self.conquer_models = []

        self.s3_client = boto3.client("s3")
        self.s3_bucket = s3_data_path.split("/")[2]
        self.s3_key = world_id
        self.s3_data_path = s3_data_path
        
        self.t10_tribes_list = []
        self.t10_players_list = []
        self.max_coords = 0
        
    def list_s3_files(self, limiter=5):
        
        response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket, Prefix=self.s3_key)
        files = [f["Key"] for f in response["Contents"]]
    
        files_df = pd.DataFrame(files, columns=["file_path"])

        files_df["datetime"] = files_df["file_path"].apply(lambda x: "_".join(x.split("/")[-1].split("_")[2:4]).replace(".txt", ""))

        files_df["file_type"] = files_df["file_path"].apply(lambda x: x.split("/")[-1].split("_")[0])
        files_df["world_id"] = files_df["file_path"].apply(lambda x: x.split("/")[-1].split("_")[1])

        # separate the dataframes by file type
        self.village_files = files_df[files_df["file_type"] == "village"]
        self.player_files = files_df[files_df["file_type"] == "player"]
        self.tribe_files = files_df[files_df["file_type"] == "ally"]
        self.conquer_files = files_df[files_df["file_type"] == "conquer"]
        
        # Apply limiter if provided
        if limiter is not None:
            self.village_files = self.village_files.head(limiter)
            self.player_files = self.player_files.head(limiter)
            self.tribe_files = self.tribe_files.head(limiter)
            self.conquer_files = self.conquer_files.head(limiter)

        return self.village_files, self.player_files, self.tribe_files, self.conquer_files

    def retrieve_from_s3(self, file_path: str):
        response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=file_path)
        return response["Body"].read().decode("utf-8")

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
    
    def load_from_s3_to_memory(self):
        """Load the files from S3 directly into memory as pandas dataframes
        """
        
        logging.info("Loading files from S3 into memory")
        
        start_time = pd.Timestamp.now()
         
        self.list_s3_files()
        
        # Load village files
        for file_path in self.village_files["file_path"]:
            file_content = self.retrieve_from_s3(file_path)
            village_df = pd.read_csv(StringIO(file_content), sep=",", header=None, names=VillageModel.model_fields.keys(), index_col=False)
            
            village_schema = Pandantic(VillageModel)
            village_model = village_schema.validate(village_df)
            
            datetime = self.village_files[self.village_files["file_path"] == file_path]["datetime"].iloc[0]
            world_id = self.village_files[self.village_files["file_path"] == file_path]["world_id"].iloc[0]
            
            village_model["datetime"] = datetime
            village_model["world_id"] = world_id
            village_model["file_path"] = file_path
            
            self.village_models.append(village_model)

        # Load player files
        for file_path in self.player_files["file_path"]:
            file_content = self.retrieve_from_s3(file_path)
            player_df = pd.read_csv(StringIO(file_content), sep=",", header=None, names=PlayerModel.model_fields.keys(), index_col=False)
            
            player_schema = Pandantic(PlayerModel)
            player_model = player_schema.validate(player_df)
            
            player_model["datetime"] = self.player_files[self.player_files["file_path"] == file_path]["datetime"].iloc[0]
            player_model["world_id"] = self.player_files[self.player_files["file_path"] == file_path]["world_id"].iloc[0]
            player_model["file_path"] = file_path
            
            self.player_models.append(player_model)
        
        # Load tribe files
        for file_path in self.tribe_files["file_path"]:
            file_content = self.retrieve_from_s3(file_path)
            tribe_df = pd.read_csv(StringIO(file_content), sep=",", header=None, names=TribeModel.model_fields.keys(), index_col=False)
            
            tribe_schema = Pandantic(TribeModel)
            tribe_model = tribe_schema.validate(tribe_df)
            
            tribe_model["datetime"] = self.tribe_files[self.tribe_files["file_path"] == file_path]["datetime"].iloc[0]
            tribe_model["world_id"] = self.tribe_files[self.tribe_files["file_path"] == file_path]["world_id"].iloc[0]
            tribe_model["file_path"] = file_path
            
            self.tribe_models.append(tribe_model)
        
        # Load conquer files
        for file_path in self.conquer_files["file_path"]:
            file_content = self.retrieve_from_s3(file_path)
            conquer_df = pd.read_csv(StringIO(file_content), sep=",", header=None, names=ConquerModel.model_fields.keys(), index_col=False)
            
            conquer_schema = Pandantic(ConquerModel)
            conquer_model = conquer_schema.validate(conquer_df)
            
            conquer_model["datetime"] = self.conquer_files[self.conquer_files["file_path"] == file_path]["datetime"].iloc[0]
            conquer_model["world_id"] = self.conquer_files[self.conquer_files["file_path"] == file_path]["world_id"].iloc[0]
            conquer_model["file_path"] = file_path
            
            self.conquer_models.append(conquer_model)
        
        total_files_loaded = len(self.village_files) + len(self.player_files) + len(self.tribe_files) + len(self.conquer_files)
        logging.info(f"Total number of files loaded: {total_files_loaded}")
        logging.info(f"Number of village models: {len(self.village_models)}")
        logging.info(f"Number of player models: {len(self.player_models)}")
        logging.info(f"Number of tribe models: {len(self.tribe_models)}")
        logging.info(f"Number of conquer models: {len(self.conquer_models)}")
        end_time = pd.Timestamp.now()   
        logging.info(f"Time taken to load files: {end_time - start_time}")
        logging.info("Files loaded into memory")
        
        self.t10_players_list = self.get_top_10_players()
        self.t10_tribes_list = self.get_top_10_tribes()
        self.max_coords = self.get_max_village_coordinates()
        
        return self.village_models, self.player_models, self.tribe_models, self.conquer_models
    
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