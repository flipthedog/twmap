import logging

from twmap.datamodel.dataloader import DataLoader
from twmap.map.map import Map

import os
from typing import List
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MapFactory:
    
    def __init__(self, s3_data_path: str, save_location: str = "images", refresh: bool = False, custom_color_map: dict = None, s3_upload_path: str = "s3://tw-timelapse/", local: bool = False):
        
        self.s3_data_path = s3_data_path
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
            self.s3_save_location = s3_upload_path + f"{self.world_id}/"
            
        self.custom_color_map = custom_color_map
    
    def create_top_10_maps(self, max_images: int = None):
        
        if max_images is not None:
            self.village_models = self.village_models[:max_images]
            self.player_models = self.player_models[:max_images]
            self.tribe_models = self.tribe_models[:max_images]
            self.conquer_models = self.conquer_models[:max_images]
        
        for i in range(len(self.village_models)):
            village_model = self.village_models[i]
            
            map_time = village_model.iloc[0]["datetime"].strftime("%Y-%m-%d %H:%M:%S")
            map_save_time = village_model.iloc[0]["datetime"].strftime("%Y%m%d_%H%M%S")
            world_id = village_model.iloc[0]["world_id"]
            
            logging.info(f"Creating maps for world {world_id} at time {map_time}")
            
            map = Map(self.village_models[i], self.player_models[i], self.tribe_models[i], self.conquer_models[i], map_time, world_id, custom_color_map=self.custom_color_map, max_coords=self.max_coords)
            
            player_save_location = os.path.join(self.image_save_location, "players")
            tribe_save_location = os.path.join(self.image_save_location, "tribes")
            
            if not os.path.exists(player_save_location):
                os.makedirs(player_save_location)
            
            if not os.path.exists(tribe_save_location):
                os.makedirs(tribe_save_location)
            
            image_top_players = map.draw_top_players(center_text=True).copy()  # Save the map with top players
        
            image_top_tribes = map.draw_top_tribes(center_text=True, zones_of_control=False).copy()  # Save the map with top tribes

            image_top_players_with_legend = map.draw_legend("players", image_top_players)  # Save the map with top players and legend
            image_top_tribes_with_legend = map.draw_legend("tribes", image_top_tribes)  # Save the map with top tribes and legend
            
            image_top_players_with_legend.save(os.path.join(player_save_location, f"{i}.png"))

            # Create zone of control map
            image_top_tribes_zoc = map.draw_top_tribes(center_text=True, zones_of_control=True).copy()
            image_top_tribes_with_legend_zoc = map.draw_legend("tribes", image_top_tribes_zoc)
            
            zoc_save_location = os.path.join(tribe_save_location, "zoc")
            if not os.path.exists(zoc_save_location):
                os.makedirs(zoc_save_location)
            
            image_top_tribes_with_legend_zoc.save(os.path.join(zoc_save_location, f"{i}.png"))

            no_zoc_save_location = os.path.join(tribe_save_location, "no_zoc")
            if not os.path.exists(no_zoc_save_location):
                os.makedirs(no_zoc_save_location)
            
            image_top_tribes_with_legend.save(os.path.join(no_zoc_save_location, f"{i}.png"))
            
    def create_maps(self, max_images: int = None, specific_tribes: List[str] = None, specific_players: List[str] = None):
        
        if max_images is not None:
            self.village_models = self.village_models[:max_images]
            self.player_models = self.player_models[:max_images]
            self.tribe_models = self.tribe_models[:max_images]
            self.conquer_models = self.conquer_models[:max_images]
            
        for i in range(len(self.village_models)):
            village_model = self.village_models[i]
            
            map_time = village_model.iloc[0]["datetime"].strftime("%Y-%m-%d %H:%M:%S")
            map_save_time = village_model.iloc[0]["datetime"].strftime("%Y%m%d_%H%M%S")
            world_id = village_model.iloc[0]["world_id"]
            
            logging.info(f"Creating maps for world {world_id} at time {map_time}")
            
            map = Map(self.village_models[i], self.player_models[i], self.tribe_models[i], self.conquer_models[i], map_time, world_id, player_list=specific_players, tribe_list=specific_tribes, custom_color_map=self.custom_color_map, max_coords=self.max_coords)
            
            if not os.path.exists(self.image_save_location):
                os.makedirs(self.image_save_location)
            
            custom_players_save_location = os.path.join(self.image_save_location, "custom_players")
            custom_tribes_save_location = os.path.join(self.image_save_location, "custom_tribes")
            
            if not os.path.exists(custom_players_save_location):
                os.makedirs(custom_players_save_location)
            
            if not os.path.exists(custom_tribes_save_location):
                os.makedirs(custom_tribes_save_location)
            
            if specific_players:
                image_specific_players = map.draw_specific_players().copy()  # Save the map with specific players
                image_specific_players_with_legend = map.draw_legend("players", image_specific_players, True)  # Save the map with specific players and legend
                image_specific_players_with_legend.save(self.image_save_location + f"/custom_players/{i}.png")
            
            if specific_tribes:
                # Run without zones of control
                image_specific_tribes = map.draw_specific_tribes(center_text=True, zones_of_control=False).copy()
                image_specific_tribes_with_legend = map.draw_legend("tribes", image_specific_tribes, True)
                
                no_zoc_save_location = os.path.join(custom_tribes_save_location, "no_zoc")
                if not os.path.exists(no_zoc_save_location):
                    os.makedirs(no_zoc_save_location)
                
                image_specific_tribes_with_legend.save(os.path.join(no_zoc_save_location, f"{i}.png"))
                
                # Run with zones of control
                image_specific_tribes_zoc = map.draw_specific_tribes(center_text=True, zones_of_control=True).copy()
                image_specific_tribes_with_legend_zoc = map.draw_legend("tribes", image_specific_tribes_zoc, True)
                
                zoc_save_location = os.path.join(custom_tribes_save_location, "zoc")
                if not os.path.exists(zoc_save_location):
                    os.makedirs(zoc_save_location)
                
                image_specific_tribes_with_legend_zoc.save(os.path.join(zoc_save_location, f"{i}.png"))

    def generate_missing_maps(self, path: str, max_images: int = None, specific_tribes: List[str] = None, specific_players: List[str] = None):
        """
        Generate missing maps based on the provided path (S3 bucket).
        """
        # Determine if the path is an S3 bucket or local directory
        if path.startswith("s3://"):
            # Handle S3 bucket path
            existing_maps = self._list_s3_maps(path)
        else:
            # Handle local directory path
            existing_maps = self._list_local_maps(path)
        
        # Identify maps that have not been created
        missing_maps = self._identify_missing_maps(existing_maps)
        
        # Create the missing maps
        self.create_maps(max_images=max_images, specific_tribes=specific_tribes, specific_players=specific_players)
    
    def _list_s3_maps(self, s3_path: str) -> List[str]:
        """
        List maps that have already been created in the S3 bucket.
        """

        existing_maps = []
        try:
            s3 = boto3.client('s3')
            bucket_name = s3_path.split('/')[2]
            prefix = '/'.join(s3_path.split('/')[3:])

            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            for obj in response.get('Contents', []):
                if obj['Key'].endswith(".png"):
                    existing_maps.append(f"s3://{bucket_name}/{obj['Key']}")
        except (NoCredentialsError, PartialCredentialsError) as e:
            logging.error(f"Error accessing S3: {e}")
        
        return existing_maps
    
    def _list_local_maps(self, local_path: str) -> List[str]:
        """
        List maps that have already been created in the local directory.
        """
        existing_maps = []
        for root, dirs, files in os.walk(local_path):
            for file in files:
                if file.endswith(".png"):
                    existing_maps.append(os.path.join(root, file))
        return existing_maps
    
    def _identify_missing_maps(self, existing_maps: List[str]) -> List[str]:
        """
        Identify maps that have not been created based on the DataLoader.
        """
        missing_maps = []
        for i, village_model in enumerate(self.village_models):
            map_time = village_model.iloc[0]["datetime"].strftime("%Y%m%d_%H%M%S")
            player_map_path = os.path.join(self.image_save_location, "players", f"{i}.png")
            tribe_map_path = os.path.join(self.image_save_location, "tribes", "no_zoc", f"{i}.png")
            tribe_zoc_map_path = os.path.join(self.image_save_location, "tribes", "zoc", f"{i}.png")

            if player_map_path not in existing_maps:
                missing_maps.append(player_map_path)
            if tribe_map_path not in existing_maps:
                missing_maps.append(tribe_map_path)
            if tribe_zoc_map_path not in existing_maps:
                missing_maps.append(tribe_zoc_map_path)

        return missing_maps

if __name__ == "__main__":
    factory = MapFactory("s3://tribalwars-scraped/en144/")
    factory.create_maps()
