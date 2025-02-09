import pandas as pd
from pandantic import Pandantic
import boto3 

import os
from io import StringIO

from twmap.datamodel.datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataLoader:

    def __init__(self, data_path: str, local_path: str, refresh: bool = False):
        # TODO: Add future support for loading from cloud
        self.data_path = data_path
        self.local_path = local_path
        
        # get the world id from the data path
        self.world_id = self.data_path.split("/")[-2]
        
        self.refresh = refresh

        self.village_models = []
        self.player_models = []
        self.tribe_models = []
        self.conquer_models = []

        # If s3 path
        if self.data_path.startswith("s3://"):
            self.s3_path = self.data_path
            self.s3_bucket = self.data_path.split("/")[2]
            self.s3_key = "/".join(self.data_path.split("/")[3:])
            self.s3_client = boto3.client("s3")
        else:
            self.s3_path = None

    def list_s3_files(self):
        
        if self.s3_path:
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket, Prefix=self.s3_key)
            files = [f["Key"] for f in response["Contents"]]
        else:
            files = os.listdir(self.data_path)
        
        files_df = pd.DataFrame(files, columns=["file_path"])

        files_df["datetime"] = files_df["file_path"].apply(lambda x: "_".join(x.split("/")[-1].split("_")[2:4]).replace(".txt", ""))
        files_df["datetime"] = pd.to_datetime(files_df["datetime"], format="%Y%m%d_%H%M%S")

        files_df["file_type"] = files_df["file_path"].apply(lambda x: x.split("/")[-1].split("_")[0])
        files_df["world_id"] = files_df["file_path"].apply(lambda x: x.split("/")[-1].split("_")[1])

        # separate the dataframes by file type
        self.village_files = files_df[files_df["file_type"] == "village"]
        self.player_files = files_df[files_df["file_type"] == "player"]
        self.tribe_files = files_df[files_df["file_type"] == "ally"]
        self.conquer_files = files_df[files_df["file_type"] == "conquer"]

        return self.village_files, self.player_files, self.tribe_files, self.conquer_files

    def retrieve_from_s3(self, file_path: str):
        response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=file_path)
        return response["Body"].read().decode("utf-8")

    def download_and_save(self):
        """Download the files from S3 and save them locally
        """
        
        logging.info("Downloading and saving files")
        
        self.list_s3_files()
        
        for file_path in self.village_files["file_path"]:
            file_content = self.retrieve_from_s3(file_path)
            file_name = file_path.split("/")[-1]
            world_id = file_name.split("_")[1]
            world_folder = os.path.join(self.local_path, world_id)
            os.makedirs(world_folder, exist_ok=True)
            with open(f"{world_folder}/{file_name}", "w") as f:
                f.write(file_content)

        for file_path in self.player_files["file_path"]:
            file_content = self.retrieve_from_s3(file_path)
            file_name = file_path.split("/")[-1]
            world_id = file_name.split("_")[1]
            world_folder = os.path.join(self.local_path, world_id)
            os.makedirs(world_folder, exist_ok=True)
            with open(f"{world_folder}/{file_name}", "w") as f:
                f.write(file_content)
        
        for file_path in self.tribe_files["file_path"]:
            file_content = self.retrieve_from_s3(file_path)
            file_name = file_path.split("/")[-1]
            world_id = file_name.split("_")[1]
            world_folder = os.path.join(self.local_path, world_id)
            os.makedirs(world_folder, exist_ok=True)
            with open(f"{world_folder}/{file_name}", "w") as f:
                f.write(file_content)
        
        for file_path in self.conquer_files["file_path"]:
            file_content = self.retrieve_from_s3(file_path)
            file_name = file_path.split("/")[-1]
            world_id = file_name.split("_")[1]
            world_folder = os.path.join(self.local_path, world_id)
            os.makedirs(world_folder, exist_ok=True)
            with open(f"{world_folder}/{file_name}", "w") as f:
                f.write(file_content)
        
        logging.info("Total number of files downloaded: ", len(self.village_files) + len(self.player_files) + len(self.tribe_files) + len(self.conquer_files))
        logging.info("Files downloaded and saved")
    
    def list_local_files(self):
        
        files = os.listdir(self.local_path + self.world_id)
        
        files_df = pd.DataFrame(files, columns=["file_path"])

        files_df["datetime"] = files_df["file_path"].apply(lambda x: "_".join(x.split("_")[2:4]).replace(".txt", ""))
        files_df["datetime"] = pd.to_datetime(files_df["datetime"], format="%Y%m%d_%H%M%S")
 
        files_df["file_type"] = files_df["file_path"].apply(lambda x: x.split("_")[0])
        files_df["world_id"] = files_df["file_path"].apply(lambda x: x.split("_")[1])

        files_df["file_path"] = files_df["file_path"].apply(lambda x: self.local_path + self.world_id + "/" + x)
        
        # separate the dataframes by file type
        self.village_files = files_df[files_df["file_type"] == "village"]
        self.player_files = files_df[files_df["file_type"] == "player"]
        self.tribe_files = files_df[files_df["file_type"] == "ally"]
        self.conquer_files = files_df[files_df["file_type"] == "conquer"]

        return self.village_files, self.player_files, self.tribe_files, self.conquer_files
    
    def load(self):
        """Load the data from the local path, or download from S3 if refresh is True"""
        
        if self.refresh:
            self.download_and_save()
        
        self.village_files, self.player_files, self.tribe_files, self.conquer_files = self.list_local_files()
                
        for file_path in self.village_files["file_path"]:
            
            village_df = pd.read_csv(file_path, sep=",", header=None, names=VillageModel.model_fields.keys(), index_col=False)
            
            village_schema =  Pandantic(VillageModel)
            village_model = village_schema.validate(village_df)
            
            village_model["datetime"] = self.village_files[self.village_files["file_path"] == file_path]["datetime"].iloc[0]
            village_model["world_id"] = self.village_files[self.village_files["file_path"] == file_path]["world_id"].iloc[0]
            
            self.village_models.append(village_model)
        
        for file_path in self.player_files["file_path"]:
            
            player_df = pd.read_csv(file_path, sep=",", header=None, names=PlayerModel.model_fields.keys(), index_col=False)
            
            player_schema =  Pandantic(PlayerModel)
            player_model = player_schema.validate(player_df)
            
            player_model["datetime"] = self.player_files[self.player_files["file_path"] == file_path]["datetime"].iloc[0]
            player_model["world_id"] = self.player_files[self.player_files["file_path"] == file_path]["world_id"].iloc[0]
            
            self.player_models.append(player_model)
        
        for file_path in self.tribe_files["file_path"]:
            
            tribe_df = pd.read_csv(file_path, sep=",", header=None, names=TribeModel.model_fields.keys(), index_col=False)
            
            tribe_schema =  Pandantic(TribeModel)
            tribe_model = tribe_schema.validate(tribe_df)
            
            tribe_model["datetime"] = self.tribe_files[self.tribe_files["file_path"] == file_path]["datetime"].iloc[0]
            tribe_model["world_id"] = self.tribe_files[self.tribe_files["file_path"] == file_path]["world_id"].iloc[0]
            
            self.tribe_models.append(tribe_model)
        
        for file_path in self.conquer_files["file_path"]:
            
            conquer_df = pd.read_csv(file_path, sep=",", header=None, names=ConquerModel.model_fields.keys(), index_col=False)
            
            conquer_schema =  Pandantic(ConquerModel)
            conquer_model = conquer_schema.validate(conquer_df)
            
            conquer_model["datetime"] = self.conquer_files[self.conquer_files["file_path"] == file_path]["datetime"].iloc[0]
            conquer_model["world_id"] = self.conquer_files[self.conquer_files["file_path"] == file_path]["world_id"].iloc[0]
            
            self.conquer_models.append(conquer_model)
                
        logging.info("Data loaded successfully")

        logging.info(f"Number of village models: {len(self.village_models)}")
        logging.info(f"Number of player models: {len(self.player_models)}")
        logging.info(f"Number of tribe models: {len(self.tribe_models)}")
        logging.info(f"Number of conquer models: {len(self.conquer_models)}")
        
        return self.village_models, self.player_models, self.tribe_models, self.conquer_models
    
if __name__ == "__main__":
    loader = DataLoader("s3://tribalwars-scraped/en144/", "data/", refresh=False)
    village_models, player_models, tribe_models, conquer_models = loader.load()
