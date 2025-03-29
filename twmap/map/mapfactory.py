import logging

from twmap.datamodel.dataloader import DataLoader
from twmap.map.map import Map

import os
from typing import List
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

import pandas as pd
import io
import datetime
import concurrent.futures
import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MapFactory:
    
    def __init__(self, s3_data_path: str, custom_color_map: dict = None, s3_map_path: str = "s3://tw-timelapse", local: bool = False, max_coords: int = 730):
        
        self.local = local
        self.s3_data_path = s3_data_path
        self.s3_data_bucket = s3_data_path.split('/')[2]
        self.s3_map_path = s3_map_path
        self.s3_map_bucket = s3_map_path.split('/')[2]
        
        self.s3_client = boto3.client('s3')
        
        self.worlds = self.get_worlds()
            
        self.custom_color_map = custom_color_map
        self.max_coords = max_coords
    
    def create_top_10_map(self, village_model: pd.DataFrame, player_model: pd.DataFrame, tribe_model: pd.DataFrame,  conquer_model: pd.DataFrame, world_id: str):
        # Convert the timestamp string from YYYYMMDD_HHMMSS format to datetime
        map_time = pd.to_datetime(village_model["datetime"][0], format="%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        world_id = village_model.iloc[0]["world_id"]
        
        logging.info(f"Creating maps for world {world_id} at time {map_time}")
        
        map = Map(village_model, player_model, tribe_model, conquer_model, map_time, world_id, custom_color_map=self.custom_color_map, max_coords=self.max_coords)
        
        logging.info(f"Creating top player map for world {world_id} at time {map_time}")
        image_top_players = map.draw_top_players(center_text=True).copy()  # Create the map with top players
        image_top_tribes = map.draw_top_tribes(center_text=True, zones_of_control=False).copy()  # Create the map with top tribes

        
        image_top_players_with_legend = map.draw_legend("players", image_top_players)  # Create the map with top players and legend
        image_top_tribes_with_legend = map.draw_legend("tribes", image_top_tribes)  # Create the map with top tribes and legend
        
        logging.info(f"Creating top tribe map with zones of control for world {world_id} at time {map_time}")
        # Create zone of control map
        image_top_tribes_zoc = map.draw_top_tribes(center_text=True, zones_of_control=True).copy()
        image_top_tribes_with_legend_zoc = map.draw_legend("tribes", image_top_tribes_zoc)
        
        return {
            "top_players": image_top_players_with_legend,
            "top_tribes_no_zoc": image_top_tribes_with_legend,
            "top_tribes_zoc": image_top_tribes_with_legend_zoc
        }
    
    def generate_specific_maps(self, world_id: str, specific_tribes: List[str], regenerate_all: bool = False, max_coords: int = 730, custom_folder: str = None) -> None:
        """Generate maps highlighting specific tribes for a given world_id
        
        Parameters:
        -----------
        world_id: ID of the world to generate maps for
        specific_tribes: List of tribe tags/names to highlight
        regenerate_all: Whether to regenerate all maps or only missing ones
        max_coords: Maximum coordinates for the map
        custom_folder: Optional custom folder name in S3 to store maps
        """
        
        self.max_coords = max_coords
        print(f"Generating specific tribe maps for world {world_id} with tribes {specific_tribes}")
        logging.info(f"Generating specific tribe maps for {len(specific_tribes)} tribes in world {world_id}")
        
        # Get all available data timestamps for this world
        s3_data = self._get_data_timestamps(world_id)
        
        logging.info(f"Found {len(s3_data)} data timestamps for world {world_id}")
        logging.info(f"Example, {len(s3_data)}: {s3_data.iloc[0]}")
        
        if s3_data.empty:
            logging.info(f"No data found for world {world_id}")
            return
        
        # Skip filtering and proceed to generate maps for all timestamps
        logging.info(f"Generating {len(s3_data)} specific tribe maps for world {world_id}")
        # Process each timestamp with ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            with tqdm.tqdm(total=len(s3_data), desc="Generating specific tribe maps") as pbar:
                for _, row in s3_data.iterrows():
                    ally_file = row['ally']
                    player_file = row['player']
                    village_file = row['village']
                    conquer_file = row['conquer']
                    datetimestamp = row['datetimestamp']
                    
                    # Submit the map generation task to the executor
                    future = executor.submit(
                        self._generate_specific_map, 
                        world_id, 
                        ally_file, 
                        player_file, 
                        village_file, 
                        conquer_file, 
                        datetimestamp, 
                        specific_tribes,
                        custom_folder
                    )
                    future.add_done_callback(lambda p: pbar.update())
                    futures.append(future)
                
                # Wait for all futures to complete
                for future in concurrent.futures.as_completed(futures):
                    future.result()
        
        logging.info(f"Completed generating specific tribe maps for world {world_id}")

    def _generate_specific_map(self, world_id: str, ally_file: str, player_file: str, village_file: str, 
                            conquer_file: str, datetimestamp: str, specific_tribes: List[str], custom_folder: str = None):
        """Helper function to generate a single specific tribe map"""
        logging.info(f"Generating specific tribe map for world {world_id} at time {datetimestamp}")
        
        # Load data
        data_loader = DataLoader(self.s3_data_path, world_id)
        tribe_df, player_df, village_df, conquer_df = data_loader.load_specific_files(ally_file, player_file, village_file, conquer_file)
        
        # Create specific tribe maps
        maps = self.create_specific_map(village_df, player_df, tribe_df, conquer_df, world_id, specific_tribes)
        
        # Define S3 folder structure
        folder_prefix = "specific_tribes"
        if custom_folder:
            folder_prefix = custom_folder
        
        # Upload each map to S3
        for map_name, image in maps.items():
            image_bytes = io.BytesIO()
            image.save(image_bytes, format='PNG')
            image_bytes.seek(0)
            
            s3_path = f"{world_id}/{folder_prefix}/{map_name}/{world_id}_{map_name}_{datetimestamp}.png"
            
            logging.info(f"Uploading {s3_path} to S3.")
            self.s3_client.upload_fileobj(image_bytes, self.s3_map_bucket, s3_path)
            logging.info(f"Uploaded {s3_path} to S3.")
    
    def create_specific_map(self, village_model: pd.DataFrame, player_model: pd.DataFrame, tribe_model: pd.DataFrame, conquer_model: pd.DataFrame, world_id: str, specific_tribes: List[int]):
        """
        Create maps highlighting specific tribes with custom colors
        
        Parameters:
        -----------
        village_model: DataFrame containing village data
        player_model: DataFrame containing player data
        tribe_model: DataFrame containing tribe data
        conquer_model: DataFrame containing conquer data
        world_id: ID of the world
        specific_tribes: List of tribe tags/names to highlight
        
        Returns:
        --------
        Dict containing the generated images
        """
        # Convert the timestamp string from YYYYMMDD_HHMMSS format to datetime
        map_time = pd.to_datetime(village_model["datetime"][0], format="%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        world_id = village_model.iloc[0]["world_id"]
        
        logging.info(f"Creating specific tribe maps for world {world_id} at time {map_time}")
                
        # Create Map instance with custom color map
        map = Map(village_model, player_model, tribe_model, conquer_model, map_time, world_id, 
                custom_color_map=self.custom_color_map, max_coords=self.max_coords, tribe_list=specific_tribes)
        
        # Create maps with specific tribes
        logging.info(f"Creating map highlighting specific tribes for world {world_id}")
        
        # Draw tribes map with only specific tribes highlighted
        image_specific_tribes = map.draw_specific_tribes(center_text=True, zones_of_control=False).copy()
        image_specific_tribes_with_legend = map.draw_legend("tribes", image_specific_tribes, specific=True)
        
        # Create zone of control map for specific tribes
        image_specific_tribes_zoc = map.draw_specific_tribes(center_text=True, zones_of_control=True).copy()
        image_specific_tribes_with_legend_zoc = map.draw_legend("tribes", image_specific_tribes_zoc, specific=True)
        

        return {
            "specific_tribes_no_zoc": image_specific_tribes_with_legend,
            "specific_tribes_zoc": image_specific_tribes_with_legend_zoc,
        }
    
    def generate_missing_maps(self, world_id: str, regenerate_all: bool = False, max_coords: int = 730) -> None:
        """Generate missing maps for a given world_id
        """
        
        self.max_coords = max_coords
        
        logging.info(f"Generating missing maps for world {world_id}")
        
        missing_maps = self.get_missing_maps(world_id, regenerate_all)
        
        if missing_maps.empty:
            logging.info(f"No missing maps found for world {world_id}")
            return
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            with tqdm.tqdm(total=len(missing_maps), desc="Generating maps") as pbar:
                for _, row in missing_maps.iterrows():
                    ally_file = row['ally']
                    player_file = row['player']
                    village_file = row['village']
                    conquer_file = row['conquer']
                    
                    datetimestamp = row['datetimestamp']
                    
                    # Submit the map generation task to the executor
                    future = executor.submit(self._generate_map, world_id, ally_file, player_file, village_file, conquer_file, datetimestamp)
                    future.add_done_callback(lambda p: pbar.update())
                    futures.append(future)
                
                # Wait for all futures to complete
                for future in concurrent.futures.as_completed(futures):
                    future.result()
    
    def _generate_map(self, world_id: str, ally_file: str, player_file: str, village_file: str, conquer_file: str, datetimestamp: str, custom_s3_path: str = None):
        """Helper function to generate a single map"""
        logging.info(f"Generating map for world {world_id} at time {datetimestamp}")
        
        # Load data
        data_loader = DataLoader(self.s3_data_path, world_id)
        tribe_df, player_df, village_df, conquer_df = data_loader.load_specific_files(ally_file, player_file, village_file, conquer_file)
        
        # Create map
        maps = self.create_top_10_map(village_df, player_df, tribe_df, conquer_df, world_id)
        
        for map_name, image in maps.items():
            image_bytes = io.BytesIO()
            image.save(image_bytes, format='PNG')
            image_bytes.seek(0)
            
            folder = map_name
            s3_path = f"{world_id}/{folder}/{world_id}_{map_name}_{datetimestamp}.png"
            if custom_s3_path:
                s3_path = f"{custom_s3_path}/{world_id}_{map_name}_{datetimestamp}.png"
            
            logging.info(f"Uploading {s3_path} to S3.")
            self.s3_client.upload_fileobj(image_bytes, self.s3_map_bucket, s3_path)
            logging.info(f"Uploaded {s3_path} to S3.")

    def get_missing_maps(self, world_id: str, regenerate_all: bool = False) -> pd.DataFrame:
        """Get all files of twdata in s3 bucket that don't have corresponding maps
        Returns DataFrame with ally, player, village and conquer file paths for missing maps
        """
        
        logging.info(f"Getting missing maps for world {world_id}")
        s3_data = self._get_data_timestamps(world_id)
        map_timestamps = self._get_map_timestamps(world_id)
        
        if s3_data.empty:
            logging.info(f"No data found for world {world_id}")
            return pd.DataFrame()
            
        if regenerate_all:
            logging.info(f"Regenerate all maps for world {world_id}")
            return s3_data
        
        # Convert map timestamps to set for faster lookup
        map_timestamps_set = set(map_timestamps)
        
        # Filter s3_data to only include rows where datetimestamp is not in map_timestamps
        missing_maps_df = s3_data[~s3_data['datetimestamp'].isin(map_timestamps_set)]
        
        logging.info(f"Found {len(missing_maps_df)} missing maps for world {world_id}")
        
        return missing_maps_df
    
    def _get_data_timestamps(self, world_id: str = None):
        """Get all timestamps of twdata in s3 bucket, optionally filtered by world_id
        """
        
        s3_data = self._list_s3_data(world_id)
        if s3_data.empty:
            return []
            
        logging.info(f"Found {len(s3_data)} files in s3 bucket")

        # Extract timestamps from file names and add as new column
        s3_data['datetimestamp'] = s3_data['ally'].apply(
            lambda x: x.split('/')[-1].split('_')[2] + '_' + x.split('/')[-1].split('_')[3].replace('.txt','') if x is not None else None
        )
        
        return s3_data
    
    def _get_map_timestamps(self, world_id: str = None):
        """Get all timestamps of twmap in s3 bucket, optionally filtered by world_id
        """
        
        s3_maps = self._list_s3_maps(world_id)
            
        datetimestamps = []
        
        for file in s3_maps:
            if file.endswith(".png"):
                filename = file.split("/")[-1]
                datetimestamp = filename.split("_")[-2] + "_" + filename.split("_")[-1].replace(".png", "")
                datetimestamps.append(datetimestamp)
        
        # Convert back to sorted list for consistent return format
        datetimestamps = sorted(list(datetimestamps))
        
        return datetimestamps
    
    def _list_s3_data(self, world_id: str):
        """Find all files of twdata in s3 bucket, optionally filtered by world_id
        """
        
        prefix = self.s3_data_path.split('/')[3]
        if world_id:
            prefix = os.path.join(prefix, world_id)

        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.s3_data_bucket, Prefix=prefix)
            
            # Initialize dictionaries to store file paths by type
            file_categories = {
                'ally': [],
                'player': [],
                'village': [],
                'conquer': []
            }
            
            for page in page_iterator:
                if 'Contents' not in page:
                    continue
                
                # Categorize files based on prefix
                for item in page['Contents']:
                    file_path = item['Key']
                    file_name = file_path.split('/')[-1]
                    
                    if file_name.startswith("ally_"):
                        file_categories['ally'].append(file_path)
                    elif file_name.startswith("player_"):
                        file_categories['player'].append(file_path)
                    elif file_name.startswith("village_"):
                        file_categories['village'].append(file_path)
                    elif file_name.startswith("conquer_"):
                        file_categories['conquer'].append(file_path)
                    else:
                        # this will contain other file types in the future
                        continue
                
            if not any(file_categories.values()):
                return pd.DataFrame()
            
            # Find the maximum length of any file type list
            max_length = max(len(files) for files in file_categories.values())
            
            # Pad shorter lists with None values
            for category in file_categories:
                file_categories[category].extend([None] * (max_length - len(file_categories[category])))
            
            # Create the DataFrame
            result_df = pd.DataFrame(file_categories)
            
            return result_df
        
        except (NoCredentialsError, PartialCredentialsError):
            logging.error("Credentials not available")
            return []
        
    def _list_s3_maps(self, world_id: str):
        """
        Find all maps in s3 bucket, optionally filtered by world_id
        """
        prefix = world_id
        
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.s3_map_bucket, Prefix=prefix)
            if 'Contents' in response:
                files = [item['Key'] for item in response['Contents']]
                # Sort the files before returning
                files.sort()
                return files
            else:
                return []
        except (NoCredentialsError, PartialCredentialsError):
            logging.error("Credentials not available")
            return []
    
    def get_worlds(self):
        """
        Get all worlds in s3 bucket
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.s3_data_bucket, Delimiter='/')
            if 'CommonPrefixes' in response:
                return [prefix['Prefix'].split('/')[0] for prefix in response['CommonPrefixes']]
            else:
                return []
        except (NoCredentialsError, PartialCredentialsError):
            logging.error("Credentials not available")
            return []

if __name__ == "__main__":
    factory = MapFactory("s3://tribalwars-scraped/", max_coords=730)
    factory.generate_missing_maps("en142", regenerate_all=False, max_coords=730)
    factory.generate_missing_maps("en143", regenerate_all=False, max_coords=700)
    factory.generate_missing_maps("en144", regenerate_all=False, max_coords=680)
    factory.generate_missing_maps("en145", regenerate_all=False, max_coords=650)
    factory.generate_missing_maps("en146", regenerate_all=False, max_coords=650) 
    factory.generate_missing_maps("enc1", regenerate_all=False, max_coords=650)
    factory.generate_missing_maps("enc2", regenerate_all=False, max_coords=650)
    