import pandas as pd
from pandantic import Pandantic
from pydantic import ValidationError

import boto3 
import os

from io import StringIO

from twmap.snapshot.snapshot_datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel, KillAllModel, KillTribeModel, KillAttModel, KillDefModel, KillTribeAttModel, KillTribeDefModel
from twmap.world.world_datamodel import WorldModel
from twmap.world.world_loader import WorldLoader

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataLoader:
    """Loads a snapshot from S3 into memory as pandas dataframes
    """

    def __init__(self, world_loader: WorldLoader = None):
        
        self.world_loader = world_loader

        self.village_models = []
        self.player_models = []
        self.tribe_models = []
        self.conquer_models = []
        self.killall_models = []
        self.killall_tribe_models = []
        self.killatt_models = []
        self.killdef_models = []
        self.killtribeatt_models = []
        self.killtribedef_models = []

        self.s3_client = boto3.client("s3")
        
        self.t10_tribes_list = []
        self.t10_players_list = []
        self.max_coords = 0
        
    def retrieve_from_s3(self, file_path: str):
        # Use the snapshot bucket from world_loader for data files
        bucket = self.world_loader.s3_snapshot_bucket
        response = self.s3_client.get_object(Bucket=bucket, Key=file_path)
        return response["Body"].read().decode("utf-8")

    def extract_s3_key(self, s3_path: str) -> str:
        if s3_path is None:
            return None
        if s3_path.startswith('s3://'):
            # Remove s3://bucket-name/ prefix
            parts = s3_path.split('/', 3)
            return parts[3] if len(parts) > 3 else s3_path
        return s3_path
    
    def load_all_files(self, limit: int = None):
        """Load all files from S3 into memory as pandas dataframes
        Args:
            limit (int, optional): Maximum number of snapshots to load. If None, loads all snapshots.
        Returns:
            Tuple of (tribe_df, player_df, village_df, conquer_df)
        """
        snapshots = self.world_loader.snapshots[:limit] if limit else self.world_loader.snapshots
        
        for snapshot in snapshots:
            tribe_model, player_model, village_model, conquer_model, killall_model, killall_tribe_model, killatt_model, killdef_model, killtribeatt_model, killtribedef_model = self.load_specific_files(
                self.extract_s3_key(snapshot.tribe_data_path),
                self.extract_s3_key(snapshot.player_data_path),
                self.extract_s3_key(snapshot.village_data_path),
                self.extract_s3_key(snapshot.conquer_data_path),
                self.extract_s3_key(snapshot.killall_data_path),
                self.extract_s3_key(snapshot.killall_tribe_data_path),
                self.extract_s3_key(snapshot.killatt_data_path),
                self.extract_s3_key(snapshot.killdef_data_path),
                self.extract_s3_key(snapshot.killtribeatt_data_path),
                self.extract_s3_key(snapshot.killtribedef_data_path)
            )

            self.killall_models.append(killall_model)
            self.killall_tribe_models.append(killall_tribe_model)
            self.killatt_models.append(killatt_model)
            self.killdef_models.append(killdef_model)
            self.killtribeatt_models.append(killtribeatt_model)
            self.killtribedef_models.append(killtribedef_model)
            self.tribe_models.append(tribe_model)
            self.player_models.append(player_model)
            self.village_models.append(village_model)
            self.conquer_models.append(conquer_model)
        
        return self.tribe_models, self.player_models, self.village_models, self.conquer_models, self.killall_models, self.killall_tribe_models, self.killatt_models, self.killdef_models, self.killtribeatt_models, self.killtribedef_models

    def load_specific_files(self, ally_path: str, player_path: str, village_path: str, conquer_path: str, killall_path: str = None, 
                            killall_tribe_path: str = None, killatt_path: str = None, killdef_path: str = None, killtribeatt_path: str = None, killtribedef_path: str = None):
        """Load specific files for one snapshot

        Args:
            ally_path (str): _description_
            player_path (str): _description_
            village_path (str): _description_
            conquer_path (str): _description_
            killall_path (str, optional): _description_. Defaults to None.
            killall_tribe_path (str, optional): _description_. Defaults to None.
            killatt_path (str, optional): _description_. Defaults to None.
            killdef_path (str, optional): _description_. Defaults to None.
            killtribeatt_path (str, optional): _description_. Defaults to None.
            killtribedef_path (str, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """

        try:
            # Load tribe/ally data
            content = self.retrieve_from_s3(ally_path)
            tribe_df = pd.read_csv(StringIO(content), sep=",", header=None, names=TribeModel.model_fields.keys(), index_col=False)
            # Handle NaN values by converting them to empty strings
            tribe_df = tribe_df.fillna("")
            tribe_schema = Pandantic(TribeModel)
            tribe_model = tribe_schema.validate(tribe_df)
            tribe_model["datetime"] = "_".join(ally_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
            tribe_model["world_id"] = ally_path.split("/")[-1].split("_")[1]
            tribe_model["file_path"] = ally_path

            # Load player data
            content = self.retrieve_from_s3(player_path)
            player_df = pd.read_csv(StringIO(content), sep=",", header=None, names=PlayerModel.model_fields.keys(), index_col=False)
            # Handle NaN values by converting them to empty strings
            player_df = player_df.fillna("")
            player_schema = Pandantic(PlayerModel)
            player_model = player_schema.validate(player_df)
            player_model["datetime"] = "_".join(player_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
            player_model["world_id"] = player_path.split("/")[-1].split("_")[1]
            player_model["file_path"] = player_path

            # Load village data
            content = self.retrieve_from_s3(village_path)
            village_df = pd.read_csv(StringIO(content), sep=",", header=None, names=VillageModel.model_fields.keys(), index_col=False)
            # Handle NaN values by converting them to empty strings
            village_df = village_df.fillna("")
            village_schema = Pandantic(VillageModel)
            try:
                village_model = village_schema.validate(village_df)
            except Exception as e:
                logging.error(f"Error validating village data: {e}")
                logging.error(f"Village data content: {content}")
                logging.error(f"Village data path: {village_path}")
                raise e
            
            village_model["datetime"] = "_".join(village_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
            village_model["world_id"] = village_path.split("/")[-1].split("_")[1]
            village_model["file_path"] = village_path

            # Load conquer data
            content = self.retrieve_from_s3(conquer_path)
            if content.strip():  # Check if file has content
                conquer_df = pd.read_csv(StringIO(content), sep=",", header=None, names=ConquerModel.model_fields.keys(), index_col=False)
                # Handle NaN values by converting them to empty strings
                conquer_df = conquer_df.fillna("")
                conquer_schema = Pandantic(ConquerModel)
                conquer_model = conquer_schema.validate(conquer_df)
                # since the conquer file is always named conquer.txt, we extract datetime from village path
                conquer_model["datetime"] = "_".join(village_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
                conquer_model["world_id"] = village_path.split("/")[-1].split("_")[1]
                conquer_model["file_path"] = conquer_path
            else:
                # Return empty dataframe with correct structure
                conquer_model = pd.DataFrame(columns=ConquerModel.model_fields.keys())
                conquer_model["datetime"] = "_".join(conquer_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
                conquer_model["world_id"] = conquer_path.split("/")[-1].split("_")[1]
                conquer_model["file_path"] = conquer_path

            # Load killall data if provided
            if killall_path:
                content = self.retrieve_from_s3(killall_path)
                
                killall_df = pd.read_csv(StringIO(content), sep=",", header=None, names=KillAllModel.model_fields.keys(), index_col=False)
                # Handle NaN values by converting them to empty strings
                killall_df = killall_df.fillna("")
                killall_schema = Pandantic(KillAllModel)
                killall_model = killall_schema.validate(killall_df)
                killall_model["datetime"] = "_".join(killall_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
                killall_model["world_id"] = killall_path.split("/")[-1].split("_")[1]
                killall_model["file_path"] = killall_path
            
            if killall_tribe_path:
                content = self.retrieve_from_s3(killall_tribe_path)

                killall_tribe_df = pd.read_csv(StringIO(content), sep=",", header=None, names=KillTribeModel.model_fields.keys(), index_col=False)
                # Handle NaN values by converting them to empty strings
                killall_tribe_df = killall_tribe_df.fillna("")
                killall_tribe_schema = Pandantic(KillTribeModel)
                killall_tribe_model = killall_tribe_schema.validate(killall_tribe_df)
                killall_tribe_model["datetime"] = "_".join(killall_tribe_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
                killall_tribe_model["world_id"] = killall_tribe_path.split("/")[-1].split("_")[1]
                killall_tribe_model["file_path"] = killall_tribe_path

            if killatt_path:
                content = self.retrieve_from_s3(killatt_path)

                killatt_df = pd.read_csv(StringIO(content), sep=",", header=None, names=KillAttModel.model_fields.keys(), index_col=False)
                # Handle NaN values by converting them to empty strings
                killatt_df = killatt_df.fillna("")
                killatt_schema = Pandantic(KillAttModel)
                killatt_model = killatt_schema.validate(killatt_df)
                killatt_model["datetime"] = "_".join(killatt_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
                killatt_model["world_id"] = killatt_path.split("/")[-1].split("_")[1]
                killatt_model["file_path"] = killatt_path
            
            if killdef_path:
                content = self.retrieve_from_s3(killdef_path)

                killdef_df = pd.read_csv(StringIO(content), sep=",", header=None, names=KillDefModel.model_fields.keys(), index_col=False)
                # Handle NaN values by converting them to empty strings
                killdef_df = killdef_df.fillna("")
                killdef_schema = Pandantic(KillDefModel)
                killdef_model = killdef_schema.validate(killdef_df)
                killdef_model["datetime"] = "_".join(killdef_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
                killdef_model["world_id"] = killdef_path.split("/")[-1].split("_")[1]
                killdef_model["file_path"] = killdef_path
            
            if killtribeatt_path:
                content = self.retrieve_from_s3(killtribeatt_path)

                killtribeatt_df = pd.read_csv(StringIO(content), sep=",", header=None, names=KillTribeAttModel.model_fields.keys(), index_col=False)
                # Handle NaN values by converting them to empty strings
                killtribeatt_df = killtribeatt_df.fillna("")
                killtribeatt_schema = Pandantic(KillTribeAttModel)
                killtribeatt_model = killtribeatt_schema.validate(killtribeatt_df)
                killtribeatt_model["datetime"] = "_".join(killtribeatt_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
                killtribeatt_model["world_id"] = killtribeatt_path.split("/")[-1].split("_")[1]
                killtribeatt_model["file_path"] = killtribeatt_path
            
            if killtribedef_path:
                content = self.retrieve_from_s3(killtribedef_path)

                killtribedef_df = pd.read_csv(StringIO(content), sep=",", header=None, names=KillTribeDefModel.model_fields.keys(), index_col=False)
                # Handle NaN values by converting them to empty strings
                killtribedef_df = killtribedef_df.fillna("")
                killtribedef_schema = Pandantic(KillTribeDefModel)
                killtribedef_model = killtribedef_schema.validate(killtribedef_df)
                killtribedef_model["datetime"] = "_".join(killtribedef_path.split("/")[-1].split("_")[2:4]).replace(".txt", "")
                killtribedef_model["world_id"] = killtribedef_path.split("/")[-1].split("_")[1]
                killtribedef_model["file_path"] = killtribedef_path

        except (ValidationError, Exception) as e:
            logging.error(f"Error loading data files: {e}")
            #print stack trace
            print(conquer_path + "\n\n\n\n")
            import traceback
            traceback.print_exc()
            # exit(1)
            return None, None, None, None, None, None

        return tribe_model, player_model, village_model, conquer_model, killall_model if killall_path else None, killall_tribe_model if killall_tribe_path else None, killatt_model if killatt_path else None, killdef_model if killdef_path else None, killtribeatt_model if killtribeatt_path else None, killtribedef_model if killtribedef_path else None

if __name__ == "__main__":
    loader = DataLoader("s3://tribalwars-scraped/", "en142")

    print(loader.load_from_s3_to_memory())