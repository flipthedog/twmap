import sys
import os
from copy import copy, deepcopy

# Add the project root to Python path so we can import twmap modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from twmap.snapshot.dataloader import DataLoader
from twmap.snapshot.datafilter import DataFilter
from twmap.map.map import Map
from twmap.world.world_loader import WorldLoader
from twmap.map.colors import ColorManager

from typing import List
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

import pandas as pd
import io
import concurrent.futures
import tqdm
import gc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MapFactory:
    
    def __init__(self, world_loader: WorldLoader, max_coords: int = 300):
        """Create maps for a given world loader

        Args:
            world_loader (WorldLoader): Contains the world configuration and S3 bucket info
            custom_color_map (dict, optional): _description_. Defaults to None.
            max_coords (int, optional): _description_. Defaults to 300.
        """

        self.world_loader = world_loader
        self.data_loader = DataLoader(world_loader)
        
        self.s3_data_bucket = world_loader.s3_snapshot_bucket
        self.s3_map_bucket = world_loader.s3_image_bucket
        
        self.s3_client = boto3.client('s3')
            
        self.custom_color_map = ColorManager().default_colors
        self.max_coords = max_coords

        self.initial_image = None  # Store the initial blank image for resetting between map generations
    
    def create_top_10_map(self, data_filter: DataFilter):
        # Convert the timestamp string from YYYYMMDD_HHMMSS format to datetime

        logging.info(f"Creating maps for world {data_filter.world_id} at time {data_filter.printed_timestamp}")
        
        logging.info(f"Creating top player map for world {data_filter.world_id} at time {data_filter.printed_timestamp}")
        
        map = Map(
                  data_filter,
                  max_coords=self.max_coords,
                  output_resolution="4K",
                  apply_aspect_ratio=True,
                  server=self.world_loader.server,
                  world=self.world_loader.world
                )
        
        top_tribe, top_player = map.draw_tribal_map()
        
        # Convert PIL Images to bytes for S3 upload
        def pil_to_bytes(pil_image):
            """Convert PIL Image to bytes"""
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            return img_buffer.getvalue()
        
        # add to s3
        timestamp_str = pd.to_datetime(data_filter.printed_timestamp).strftime("%Y%m%d_%H%M%S")

        # Convert images to bytes before uploading
        players_image_bytes = pil_to_bytes(top_player)
        tribes_image_bytes = pil_to_bytes(top_tribe)

        self.s3_client.put_object(
            Bucket=self.s3_map_bucket, 
            Key=self.world_loader.top_players_image_prefix + timestamp_str + ".png", 
            Body=players_image_bytes,
            ServerSideEncryption='AES256'
        )
        self.s3_client.put_object(
            Bucket=self.s3_map_bucket, 
            Key=self.world_loader.top_tribes_image_prefix + timestamp_str + ".png", 
            Body=tribes_image_bytes,
            ServerSideEncryption='AES256'
        )

    def _process_single_timelapse_image(self, timelapse_image):
        """Process a single timelapse image to generate maps if missing.
        
        Args:
            timelapse_image: TimelapseImageModel instance
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            # Skip if images are already generated
            if timelapse_image.image_generated:
                logging.info(f"Maps already exist for timestamp {timelapse_image.timestamp}, skipping.")
                return True, None
            
            logging.info(f"Processing timelapse image for timestamp {timelapse_image.timestamp}")
            
            # Extract S3 keys from full paths (remove s3://bucket/ prefix)
            def extract_s3_key(s3_path: str) -> str:
                if s3_path.startswith('s3://'):
                    # Remove s3://bucket-name/ prefix
                    parts = s3_path.split('/', 3)
                    return parts[3] if len(parts) > 3 else s3_path
                return s3_path
            
            ally_key = extract_s3_key(timelapse_image.tribe_data_path)
            player_key = extract_s3_key(timelapse_image.player_data_path)
            village_key = extract_s3_key(timelapse_image.village_data_path)
            conquer_key = extract_s3_key(timelapse_image.conquer_data_path)
            killall_key = extract_s3_key(timelapse_image.killall_data_path) if timelapse_image.killall_data_path else None
            killalltribes_key = extract_s3_key(timelapse_image.killall_tribe_data_path) if timelapse_image.killall_tribe_data_path else None
            killatt_key = extract_s3_key(timelapse_image.killatt_data_path) if timelapse_image.killatt_data_path else None
            killdef_key = extract_s3_key(timelapse_image.killdef_data_path) if timelapse_image.killdef_data_path else None
            killtribeatt_key = extract_s3_key(timelapse_image.killtribeatt_data_path) if timelapse_image.killtribeatt_data_path else None
            killtribedef_key = extract_s3_key(timelapse_image.killtribedef_data_path) if timelapse_image.killtribedef_data_path else None

            logging.info(f"Loading data files from S3 for timestamp {timelapse_image.timestamp}")
            logging.info(f"Tribe data path: s3://{self.s3_data_bucket}/{ally_key}")
            logging.info(f"Player data path: s3://{self.s3_data_bucket}/{player_key}")
            logging.info(f"Village data path: s3://{self.s3_data_bucket}/{village_key}")
            logging.info(f"Conquer data path: s3://{self.s3_data_bucket}/{conquer_key}" if conquer_key else "No conquer data path provided.")

            try:
                # Load data files using the data loader
                tribe_df, player_df, village_df, conquer_df, killall_df, killalltribes_df, killatt_df, killdef_df, killtribeatt_df, killtribedef_df = self.data_loader.load_specific_files(
                    ally_key, player_key, village_key, conquer_key, killall_key, killalltribes_key, killatt_key, killdef_key, killtribeatt_key, killtribedef_key
                )
                
                # Create data filter
                data_filter = DataFilter(village_df, player_df, tribe_df, conquer_df, killall_df, killalltribes_df, killatt_df, killdef_df, killtribeatt_df, killtribedef_df)
                
                # Generate maps
                self.create_top_10_map(data_filter)
                
                logging.info(f"Successfully generated maps for timestamp {timelapse_image.timestamp}")
                return True, None
            
            finally:
                # Explicitly delete large objects to free memory immediately
                try:
                    del tribe_df, player_df, village_df, conquer_df, data_filter
                except:
                    pass
                # Force garbage collection
                gc.collect()
                
        except Exception as e:
            error_msg = f"Error processing timestamp {timelapse_image.timestamp}: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return False, error_msg

    def clear_s3_map_bucket(self):
        """Clear all maps from the S3 map bucket for the current world."""
        
        logging.info(f"Clearing all maps from S3 bucket {self.s3_map_bucket} for world {self.world_loader.world}")
        
        prefixes = [
            self.world_loader.top_players_image_path,
            self.world_loader.top_tribes_image_path
        ]
        
        for prefix in prefixes:
            logging.info(f"Clearing maps with prefix {prefix}")
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.s3_map_bucket, Prefix=prefix)
            
            objects_to_delete = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects_to_delete.append({'Key': obj['Key']})
            
            # Delete objects in batches of 1000 (S3 limit)
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                response = self.s3_client.delete_objects(
                    Bucket=self.s3_map_bucket,
                    Delete={'Objects': batch}
                )
                deleted_count = len(response.get('Deleted', []))
                logging.info(f"Deleted {deleted_count} objects from S3 bucket {self.s3_map_bucket}")
        
        logging.info(f"Completed clearing maps from S3 bucket {self.s3_map_bucket} for world {self.world_loader.world}")

    def generate_missing_maps(self, max_workers: int = 4, regenerate_all: bool = False, interval: int = 1):
        """Generate maps for all snapshots in the world loader that are missing in the S3 map bucket.
        
        Args:
            max_workers (int): Maximum number of parallel workers for processing
            regenerate_all (bool): If True, regenerate ALL maps (overwriting existing ones).
                                 If False, only generate missing maps.
            interval (int): Generate every Nth image (1=all, 2=every 2nd, 3=every 3rd, etc.)
        """
        
        if regenerate_all:
            # Get all timelapse images
            all_timelapse_images = self.world_loader.timelapse_images
            progress_desc = "Regenerating all timelapse images"

            self.clear_s3_map_bucket()
            
            logging.info(f"Regenerating ALL {len(all_timelapse_images)} timelapse images (including existing ones)")
            logging.warning("This will overwrite all existing maps in the S3 bucket!")

            self.world_loader.sync_timelapse_images()  # Refresh the list after clearing
            all_timelapse_images = self.world_loader.timelapse_images
            
        else:
            # Get all timelapse images that need processing (not yet generated)
            all_timelapse_images = [
                img for img in self.world_loader.timelapse_images 
                if not img.image_generated
            ]
            progress_desc = "Processing missing timelapse images"
            logging.info(f"Found {len(all_timelapse_images)} missing timelapse images to process")
        
        # Apply interval filtering - sort by timestamp first to ensure consistent ordering
        all_timelapse_images.sort(key=lambda x: x.timestamp)
        
        if interval > 1:
            # Select every Nth image starting from the first one
            timelapse_images = [all_timelapse_images[i] for i in range(0, len(all_timelapse_images), interval)]
            logging.info(f"Interval filtering: processing every {interval} image(s) - {len(timelapse_images)} out of {len(all_timelapse_images)} total")
        else:
            timelapse_images = all_timelapse_images
        
        if not timelapse_images:
            logging.info("No timelapse images to process.")
            return
        
        # Process in parallel
        successful_count = 0
        failed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_image = {
                executor.submit(self._process_single_timelapse_image, img): img 
                for img in timelapse_images
            }
            
            # Process results with progress bar
            with tqdm.tqdm(total=len(timelapse_images), desc=progress_desc) as pbar:
                for future in concurrent.futures.as_completed(future_to_image):
                    timelapse_image = future_to_image[future]
                    try:
                        success, error_msg = future.result()
                        if success:
                            successful_count += 1
                        else:
                            failed_count += 1
                            logging.error(f"Failed to process {timelapse_image.timestamp}: {error_msg}")
                    except Exception as exc:
                        failed_count += 1
                        logging.error(f"Exception while processing {timelapse_image.timestamp}: {exc}")
                    
                    pbar.update(1)
        
        logging.info(f"Completed processing: {successful_count} successful, {failed_count} failed")
        
        # Refresh the timelapse images list to reflect the newly generated images
        logging.info("Refreshing timelapse images list...")
        self.world_loader.timelapse_images = self.world_loader.sync_timelapse_images()         

if __name__ == "__main__":

    # Example usage
    world_loader = WorldLoader(world="146", server="en")
    #world_loader.sync_timelapse_images()
    
    map_factory = MapFactory(world_loader, max_coords=720)
    # hardcode to only
    #     Tribe data path: s3://tribalwars-scraped/en146/ally_en146_20250930_221509.txt
    # Player data path: s3://tribalwars-scraped/en146/player_en146_20250930_221503.txt
    # Village data path: s3://tribalwars-scraped/en146/village_en146_20250930_221458.txt
    # Conquer data path: s3://tribalwars-scraped/en146/conquer_en146_20250930_221515.txt



    # generate one map for testing
    # map_factory.world_loader.timelapse_images = map_factory.world_loader.timelapse_images[-1:]
    
    # print(f"Generating maps for world {world_loader.world} with {len(world_loader.timelapse_images)} timelapse images")
    # # for pahts
    # print(f"Using S3 data bucket: {map_factory.s3_data_bucket}")
    # print(f"Using S3 map bucket: {map_factory.s3_map_bucket}")
    # # Load data files using the data loader
    # print("Loading data files...")
    # print(f"Tribe data path: {map_factory.world_loader.timelapse_images[0].tribe_data_path}")
    # print(f"Player data path: {map_factory.world_loader.timelapse_images[0].player_data_path}")
    # print(f"Village data path: {map_factory.world_loader.timelapse_images[0].village_data_path}")
    # print(f"Conquer data path: {map_factory.world_loader.timelapse_images[0].conquer_data_path}")

    

    def extract_s3_key(s3_path: str) -> str:
        if s3_path.startswith('s3://'):
            # Remove s3://bucket-name/ prefix
            parts = s3_path.split('/', 3)
            return parts[3] if len(parts) > 3 else s3_path
        return s3_path
    
    tribe_df, player_df, village_df, conquer_df = map_factory.data_loader.load_specific_files(
        extract_s3_key("s3://tribalwars-scraped/en146/ally_en146_20250930_221509.txt"),
        extract_s3_key("s3://tribalwars-scraped/en146/player_en146_20250930_221503.txt"),
        extract_s3_key("s3://tribalwars-scraped/en146/village_en146_20250930_221458.txt"),
        extract_s3_key("s3://tribalwars-scraped/en146/conquer_en146_20250930_221515.txt")
    )
    data_filter = DataFilter(village_df, player_df, tribe_df, conquer_df)
    
    map = Map(data_filter, custom_color_map=map_factory.custom_color_map, max_coords=720)
    image_top_players = map.draw_top_players(center_text=True).copy()  # Create the
    image_top_tribes = map.draw_top_tribes(center_text=True, zones_of_control=False).copy()  # Create the map with top tribes
    image_top_players = map.crop_image(image_top_players)
    image_top_tribes = map.crop_image(image_top_tribes)
    image_top_players_with_legend = map.draw_legend("players", image_top_players)  # Create the map with top players and legend
    image_top_tribes_with_legend = map.draw_legend("tribes", image_top_tribes)  # Create the map with top tribes and legend
    image_top_players_with_legend.show()
    image_top_tribes_with_legend.show()
