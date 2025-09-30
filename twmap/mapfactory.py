import logging

from twmap.snapshot.dataloader import DataLoader
from twmap.snapshot.datafilter import DataFilter
from twmap.map.map import Map
from twmap.world.world_loader import WorldLoader
from twmap.map.colors import ColorManager

import os
from typing import List
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

import pandas as pd
import io
import concurrent.futures
import tqdm

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
        # Remove the sync() call as it doesn't exist
        self.data_loader = DataLoader(world_loader)
        
        self.s3_data_bucket = world_loader.s3_snapshot_bucket
        self.s3_map_bucket = world_loader.s3_image_bucket
        
        self.s3_client = boto3.client('s3')
            
        self.custom_color_map = ColorManager().sunset_gradient
        self.max_coords = max_coords
    
    def create_top_10_map(self, data_filter: DataFilter):
        # Convert the timestamp string from YYYYMMDD_HHMMSS format to datetime

        logging.info(f"Creating maps for world {data_filter.world_id} at time {data_filter.printed_timestamp}")
        
        map = Map(data_filter, custom_color_map=self.custom_color_map, max_coords=self.max_coords)
        
        logging.info(f"Creating top player map for world {data_filter.world_id} at time {data_filter.printed_timestamp}")
        
        image_top_players = map.draw_top_players(center_text=True).copy()  # Create the map with top players
        image_top_tribes = map.draw_top_tribes(center_text=True, zones_of_control=False).copy()  # Create the map with top tribes

        image_top_players_with_legend = map.draw_legend("players", image_top_players)  # Create the map with top players and legend
        image_top_tribes_with_legend = map.draw_legend("tribes", image_top_tribes)  # Create the map with top tribes and legend
        
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
        players_image_bytes = pil_to_bytes(image_top_players_with_legend)
        tribes_image_bytes = pil_to_bytes(image_top_tribes_with_legend)

        self.s3_client.put_object(Bucket=self.s3_map_bucket, Key=self.world_loader.top_players_image_prefix + timestamp_str + ".png", Body=players_image_bytes)
        self.s3_client.put_object(Bucket=self.s3_map_bucket, Key=self.world_loader.top_tribes_image_prefix + timestamp_str + ".png", Body=tribes_image_bytes)
    
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
            conquer_key = extract_s3_key(timelapse_image.conquer_data_path) if timelapse_image.conquer_data_path else None
            
            # Load data files using the data loader
            tribe_df, player_df, village_df, conquer_df = self.data_loader.load_specific_files(
                ally_key, player_key, village_key, conquer_key
            )
            
            # Create data filter
            data_filter = DataFilter(village_df, player_df, tribe_df, conquer_df)
            
            # Generate maps
            self.create_top_10_map(data_filter)
            
            logging.info(f"Successfully generated maps for timestamp {timelapse_image.timestamp}")
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing timestamp {timelapse_image.timestamp}: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def generate_missing_maps(self, max_workers: int = 4):
        """Generate maps for all snapshots in the world loader that are missing in the S3 map bucket.
        
        Args:
            max_workers (int): Maximum number of parallel workers for processing
        """
        
        # Get all timelapse images that need processing (not yet generated)
        missing_timelapse_images = [
            img for img in self.world_loader.timelapse_images 
            if not img.image_generated
        ]
        
        if not missing_timelapse_images:
            logging.info("No missing timelapse images to process.")
            return
        
        logging.info(f"Found {len(missing_timelapse_images)} missing timelapse images to process")
        
        # Process in parallel
        successful_count = 0
        failed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_image = {
                executor.submit(self._process_single_timelapse_image, img): img 
                for img in missing_timelapse_images
            }
            
            # Process results with progress bar
            with tqdm.tqdm(total=len(missing_timelapse_images), desc="Processing timelapse images") as pbar:
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
