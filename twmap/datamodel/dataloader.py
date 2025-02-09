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

    def list_files(self):
        
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

    def load_s3(self):
        """Load data from the data path and validate the data against the models.
        """

        village_files, player_files, tribe_files, conquer_files = self.list_files()
        
        for file_path in village_files["file_path"].values:
            data = self.retrieve_from_s3(file_path)
            village_df = pd.read_csv(StringIO(data), sep=",", header=None, names=VillageModel.model_fields.keys(), index_col=False)
            village_df["datetime"] = village_files[village_files["file_path"] == file_path]["datetime"].values[0]
            village_df["world_id"] = village_files[village_files["file_path"] == file_path]["world_id"].values[0]
            village_schema = Pandantic(VillageModel)

            village_model = village_schema.validate(village_df)
            
            self.village_models.append(village_model)
        
        for file_path in player_files["file_path"].values:
            data = self.retrieve_from_s3(file_path)
            player_df = pd.read_csv(StringIO(data), sep=",", header=None, names=PlayerModel.model_fields.keys(), index_col=False)
            player_df["datetime"] = player_files[player_files["file_path"] == file_path]["datetime"].values[0]
            player_df["world_id"] = player_files[player_files["file_path"] == file_path]["world_id"].values[0]
            player_schema = Pandantic(PlayerModel)

            player_model = player_schema.validate(player_df)
            
            self.player_models.append(player_model)
        
        for file_path in tribe_files["file_path"].values:
            data = self.retrieve_from_s3(file_path)
            tribe_df = pd.read_csv(StringIO(data), sep=",", header=None, names=TribeModel.model_fields.keys(), index_col=False)
            tribe_df["datetime"] = tribe_files[tribe_files["file_path"] == file_path]["datetime"].values[0]
            tribe_df["world_id"] = tribe_files[tribe_files["file_path"] == file_path]["world_id"].values[0]
            tribe_schema = Pandantic(TribeModel)

            tribe_model = tribe_schema.validate(tribe_df)
            
            self.tribe_models.append(tribe_model)
        
        for file_path in conquer_files["file_path"].values:
            data = self.retrieve_from_s3(file_path)
            conquer_df = pd.read_csv(StringIO(data), sep=",", header=None, names=ConquerModel.model_fields.keys(), index_col=False)
            conquer_df["datetime"] = conquer_files[conquer_files["file_path"] == file_path]["datetime"].values[0]
            conquer_df["world_id"] = conquer_files[conquer_files["file_path"] == file_path]["world_id"].values[0]
            conquer_schema = Pandantic(ConquerModel)

            conquer_model = conquer_schema.validate(conquer_df)
            
            self.conquer_models.append(conquer_model)
        
        return self.village_models, self.player_models, self.tribe_models, self.conquer_models

    def load_local(self):
        """Load data from local path and validate the data against the models.
        """
        village_files, player_files, tribe_files, conquer_files = self.list_files()
        
        for file_path in village_files["file_path"].values:
            data = pd.read_csv(os.path.join(self.local_path, file_path.split("/")[-1]), sep=",", header=None, names=VillageModel.model_fields.keys(), index_col=False)
            village_schema = Pandantic(VillageModel)

            village_model = village_schema.validate(data)
            
            self.village_models.append(village_model)
        
        for file_path in player_files["file_path"].values:
            data = pd.read_csv(os.path.join(self.local_path, file_path.split("/")[-1]), sep=",", header=None, names=PlayerModel.model_fields.keys(), index_col=False)
            player_schema = Pandantic(PlayerModel)

            player_model = player_schema.validate(data)
            
            self.player_models.append(player_model)
        
        for file_path in tribe_files["file_path"].values:
            data = pd.read_csv(os.path.join(self.local_path, file_path.split("/")[-1]), sep=",", header=None, names=TribeModel.model_fields.keys(), index_col=False)
            tribe_schema = Pandantic(TribeModel)

            tribe_model = tribe_schema.validate(data)
            
            self.tribe_models.append(tribe_model)
        
        for file_path in conquer_files["file_path"].values:
            data = pd.read_csv(os.path.join(self.local_path, file_path.split("/")[-1]), sep=",", header=None, names=ConquerModel.model_fields.keys(), index_col=False)
            conquer_schema = Pandantic(ConquerModel)

            conquer_model = conquer_schema.validate(data)
            
            self.conquer_models.append(conquer_model)
        
        return self.village_models, self.player_models, self.tribe_models, self.conquer_models

    def load(self):
        """Load data based on the refresh flag."""
        if self.refresh:
            logging.info("Loading data from s3 at " + self.s3_path)
            models = self.load_s3()
            logging.info("Saving models locally")
            # Save models locally
            self.save_local(models)
            return models
        else:
            return self.load_local()

    def save_local(self, models):
        """Save models locally."""
        village_models, player_models, tribe_models, conquer_models = models

        for model, file_name in zip([village_models, player_models, tribe_models, conquer_models],
                                    ["village_models.csv", "player_models.csv", "tribe_models.csv", "conquer_models.csv"]):
            df = pd.DataFrame([m.__dict__ for m in model])
            df.to_csv(os.path.join(self.local_path, file_name), index=False)

if __name__ == "__main__":
    loader = DataLoader("s3://tribalwars-scraped/en144/", "data/", refresh=True)
    village_models, player_models, tribe_models, conquer_models = loader.load()
    print(village_models)
    print(player_models)
    print(tribe_models)
    print(conquer_models)