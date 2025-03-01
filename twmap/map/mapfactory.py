import logging

from twmap.datamodel.dataloader import DataLoader
from twmap.map.map import Map

import os
from typing import List
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

import pandas as pd
import io


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MapFactory:
    
    def __init__(self, s3_data_path: str, save_location: str = "images", refresh: bool = False, custom_color_map: dict = None, s3_upload_path: str = "s3://tw-timelapse", local: bool = False):
        
        self.local = local
        self.s3_data_path = s3_data_path
        self.s3_upload_path = s3_upload_path
        self.loader = DataLoader(s3_data_path, "data/", refresh=refresh)
        
        self.village_models, self.player_models, self.tribe_models, self.conquer_models = self.loader.load()
        
        self.world_id = self.loader.world_id
        self.max_coords = self.loader.get_max_village_coordinates()
        self.t10_tribes_list = self.loader.get_top_10_tribes()
        self.t10_players_list = self.loader.get_top_10_players()
        
        logging.info(f"Completed loading data for world {self.world_id}")
        logging.info(f"Max coords: {self.max_coords}")
        logging.info(f"Top 10 tribes: {self.t10_tribes_list}")
        logging.info(f"Top 10 players: {self.t10_players_list}")
        
        if self.local:
            self.image_save_location = save_location + f"/{self.world_id}"
        else:
            self.s3_save_location = s3_upload_path + f"/{self.world_id}"
            
        self.custom_color_map = custom_color_map
        
        self.s3_client = boto3.client('s3')
        self.s3_bucket = self.s3_upload_path.split('/')[2]
    
    def create_top_10_map(self, village_model: pd.DataFrame, player_model: pd.DataFrame, tribe_model: pd.DataFrame,  conquer_model: pd.DataFrame, map_time: str, world_id: str):
    
        map_time = village_model.iloc[0]["datetime"].strftime("%Y-%m-%d %H:%M:%S")
        map_save_time = village_model.iloc[0]["datetime"].strftime("%Y%m%d_%H%M%S")
        world_id = village_model.iloc[0]["world_id"]
        
        logging.info(f"Creating maps for world {world_id} at time {map_time}")
        
        map = Map(village_model, player_model, tribe_model, conquer_model, map_time, world_id, custom_color_map=self.custom_color_map, max_coords=self.max_coords)
        
        image_top_players = map.draw_top_players(center_text=True).copy()  # Create the map with top players
        image_top_tribes = map.draw_top_tribes(center_text=True, zones_of_control=False).copy()  # Create the map with top tribes

        image_top_players_with_legend = map.draw_legend("players", image_top_players)  # Create the map with top players and legend
        image_top_tribes_with_legend = map.draw_legend("tribes", image_top_tribes)  # Create the map with top tribes and legend
        
        # Create zone of control map
        image_top_tribes_zoc = map.draw_top_tribes(center_text=True, zones_of_control=True).copy()
        image_top_tribes_with_legend_zoc = map.draw_legend("tribes", image_top_tribes_zoc)
        
        return {
            "top_players": image_top_players_with_legend,
            "top_tribes_no_zoc": image_top_tribes_with_legend,
            "top_tribes_zoc": image_top_tribes_with_legend_zoc
        }
    
    def generate_missing_maps(self):
        logging.info("Starting to generate missing maps.")
        existing_maps = self._list_s3_maps()
        missing_maps = self._identify_missing_maps(existing_maps)
        
        logging.info(f"Found {len(missing_maps)} missing maps.")
        
        # get the missing timestamps
        missing_timestamps = [map.split("_top_players_")[1].split(".png")[0] for map in missing_maps]
        
        for missing_timestamp in missing_timestamps:
            # find the index of the missing timestamp in the village_models
            index = next(i for i, village_model in enumerate(self.village_models) if village_model.iloc[0]["datetime"].strftime("%Y%m%d_%H%M%S") == missing_timestamp)
            
            village_model = self.village_models[index]
            map_time = village_model.iloc[0]["datetime"].strftime("%Y-%m-%d %H:%M:%S")
            world_id = village_model.iloc[0]["world_id"]
            logging.info(f"Creating maps for world {world_id} at time {map_time}")
            maps = self.create_top_10_map(village_model, self.player_models[index], self.tribe_models[index], self.conquer_models[index], map_time, world_id)
            
            for map_name, image in maps.items():
                image_bytes = io.BytesIO()
                image.save(image_bytes, format='PNG')
                image_bytes.seek(0)
                
                folder = map_name
                s3_path = f"{self.world_id}/{folder}/{self.world_id}_{map_name}_{missing_timestamp}.png"
                logging.info(f"Uploading {s3_path} to S3.")
                self.s3_client.upload_fileobj(image_bytes, self.s3_bucket, s3_path)
        
        logging.info("Finished generating missing maps.")

    def _list_s3_maps(self) -> List[str]:
        """
        List maps that have already been created in the S3 bucket.
        """

        existing_maps = []
        try:
            s3 = boto3.client('s3')
            bucket_name = self.s3_upload_path.split('/')[2]
            prefix = '/'.join(self.s3_upload_path.split('/')[3:])

            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            for obj in response.get('Contents', []):
                if obj['Key'].endswith(".png"):
                    existing_maps.append(f"s3://{bucket_name}/{obj['Key']}")
        except (NoCredentialsError, PartialCredentialsError) as e:
            logging.error(f"Error accessing S3: {e}")
        
        return existing_maps
    
    def _identify_missing_maps(self, existing_maps: List[str]) -> List[str]:
        """
        Identify maps that have not been created based on the DataLoader.
        """
        missing_maps = []
        for i, village_model in enumerate(self.village_models):
            map_time = village_model.iloc[0]["datetime"].strftime("%Y%m%d_%H%M%S")
            player_map_path = f"{self.s3_save_location}/top_players/{self.world_id}_top_players_{map_time}.png"

            if player_map_path not in existing_maps:
                missing_maps.append(player_map_path)

        return missing_maps

if __name__ == "__main__":
    factory = MapFactory("s3://tribalwars-scraped/en144/", refresh=False)
    print(factory._list_s3_maps())
    print(factory._identify_missing_maps(factory._list_s3_maps()))
    factory.generate_missing_maps()
