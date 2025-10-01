import pandas as pd
from typing import Optional, List
import boto3
import logging
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


from twmap.world.world_datamodel import WorldModel, TimelapseImageModel, SnapshotFileModel
import csv


class WorldLoader:
    """Controls whether data is available for a world and whether Timelapse images have been generated.
    """

    def __init__(self, world: str, server: str, s3_image_bucket: Optional[str] = None, s3_snapshot_bucket: Optional[str] = None):
        self.world = world  # e.g. 142
        self.server = server  # e.g. en
        self.s3_image_bucket = s3_image_bucket or 'tw-timelapse'
        self.s3_snapshot_bucket = s3_snapshot_bucket or 'tribalwars-scraped'

        self.s3_client = boto3.client('s3')
        self.logger = logging.getLogger(__name__)

        self.world_model: Optional[WorldModel] = None

        self.ally_file_prefix = f"{self.server}{self.world}/ally_{self.server}{self.world}_"
        self.player_file_prefix = f"{self.server}{self.world}/player_{self.server}{self.world}_"
        self.village_file_prefix = f"{self.server}{self.world}/village_{self.server}{self.world}_"
        self.conquer_file_prefix = f"{self.server}{self.world}/conquer_{self.server}{self.world}_"

        self.top_players_image_prefix = f"{self.server}{self.world}/top_players/en{self.world}_top_players_"
        self.top_tribes_image_prefix = f"{self.server}{self.world}/top_tribes/en{self.world}_top_tribes_"

        self.settings_dir = f"settings/{self.server}{self.world}/"
        self.world_settings_file = f"{self.settings_dir}world_settings.json"

        self.snapshots: List[SnapshotFileModel] = self.scan_available_snapshots()
        self.timelapse_images: List[TimelapseImageModel] = self.sync_timelapse_images()
        
    def load_world(self) -> Optional[WorldModel]:
        """Load the world model from S3.

        Returns:
            Optional[WorldModel]: The loaded world model or None if not found.
        """
        try:
            response = self.s3_client.get_object(Bucket=self.s3_image_bucket, Key=self.world_settings_file)
            world_data = response['Body'].read().decode('utf-8')
            self.world_model = WorldModel.model_validate_json(world_data)
            return self.world_model
        except self.s3_client.exceptions.NoSuchKey:
            self.logger.warning(f"World settings file not found for {self.server}{self.world} in bucket {self.s3_image_bucket}.")
            return None
        except Exception as e:
            self.logger.error(f"Error loading world settings for {self.server}{self.world}: {e}")
            return None
    
    def save_world(self) -> None:
        """Save the world model to S3.
        """
        
        json_world_model = self.world_model.model_dump_json()
        self.s3_client.put_object(Bucket=self.s3_image_bucket, Key=self.world_settings_file, Body=json_world_model)

    def create_world(self, max_coords: int, has_barbarians: bool, timelapse_interval: int) -> WorldModel:
        """Create a new world model.

        Args:
            max_coords (int): The maximum coordinates for the world.
            has_barbarians (bool): Whether the world has barbarian villages.
            timelapse_interval (int): The interval in hours for generating timelapse images.

        Returns:
            WorldModel: The created world model.
        """
        
        self.world_model = WorldModel(
            world=self.world,
            server=self.server,
            max_coords=max_coords,
            has_barbarians=has_barbarians,
            timelapse_interval=timelapse_interval
        )
        self.save_world()
        return self.world_model
    
    def scan_available_snapshots(self) -> List[SnapshotFileModel]:
        """Scan S3 for available snapshot files for the world.

        Files are saved in the following format: 
        en148/ally_en148_20250914_214200.txt
        s3://tribalwars-scraped/en149/ally_en149_20250914_214301.txt
        s3://tribalwars-scraped/en143/ally_en143_20250207_204158.txt

        The timestamp between the files is not the same, so we need to match
        files with closest timestamps and ensure each snapshot has all four files.

        Returns:
            List[SnapshotFileModel]: A list of available snapshot file models.
        """
        
        snapshot_files = []
        try:
            prefix = f"{self.server}{self.world}/"
            self.logger.info(f"Scanning S3 bucket '{self.s3_snapshot_bucket}' with prefix '{prefix}'")
            
            # Get all files using pagination
            files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.s3_snapshot_bucket, Prefix=prefix)
            
            for page in page_iterator:
                if 'Contents' in page:
                    files.extend(page['Contents'])
            
            self.logger.info(f"Found {len(files)} total files in S3")
            
            if files:
                
                # Log the file prefixes we're looking for
                self.logger.info(f"Looking for files with prefixes:")
                self.logger.info(f"  Village: {self.village_file_prefix}")
                self.logger.info(f"  Player: {self.player_file_prefix}")
                self.logger.info(f"  Ally: {self.ally_file_prefix}")
                self.logger.info(f"  Conquer: {self.conquer_file_prefix}")
                
                # Collect files by type with their timestamps and datetime objects
                village_files = {}  # timestamp -> (datetime_obj, full_key)
                player_files = {}
                ally_files = {}
                conquer_files = {}
                
                # Log first few files to see what we're working with
                for i, file in enumerate(files[:10]):
                    self.logger.info(f"Sample file {i+1}: {file['Key']}")
                
                # Track file types for analysis
                other_files = []
                
                for file in files:
                    key = file['Key']
                    try:
                        if key.startswith(self.village_file_prefix):
                            timestamp_str = key[len(self.village_file_prefix):-4]
                            dt_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                            village_files[timestamp_str] = (dt_obj, key)
                        elif key.startswith(self.player_file_prefix):
                            timestamp_str = key[len(self.player_file_prefix):-4]
                            dt_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                            player_files[timestamp_str] = (dt_obj, key)
                        elif key.startswith(self.ally_file_prefix):
                            timestamp_str = key[len(self.ally_file_prefix):-4]
                            dt_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                            ally_files[timestamp_str] = (dt_obj, key)
                        elif key.startswith(self.conquer_file_prefix):
                            timestamp_str = key[len(self.conquer_file_prefix):-4]
                            dt_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                            conquer_files[timestamp_str] = (dt_obj, key)
                        else:
                            other_files.append(key)
                    except Exception as e:
                        self.logger.warning(f"Could not parse filename {key}: {e}")
                        continue

                self.logger.info(f"Found files by type:")
                self.logger.info(f"  Village files: {len(village_files)}")
                if village_files:
                    sample_village = list(village_files.values())[0][1]
                    self.logger.info(f"    Sample: {sample_village}")
                self.logger.info(f"  Player files: {len(player_files)}")
                if player_files:
                    sample_player = list(player_files.values())[0][1]
                    self.logger.info(f"    Sample: {sample_player}")
                self.logger.info(f"  Ally files: {len(ally_files)}")
                if ally_files:
                    sample_ally = list(ally_files.values())[0][1]
                    self.logger.info(f"    Sample: {sample_ally}")
                self.logger.info(f"  Conquer files: {len(conquer_files)}")
                if conquer_files:
                    sample_conquer = list(conquer_files.values())[0][1]
                    self.logger.info(f"    Sample: {sample_conquer}")

                def find_closest_file(target_dt: datetime, file_dict: dict, max_diff_seconds: int = 3600) -> Optional[str]:
                    """Find the closest file to the target datetime within max_diff_seconds."""
                    closest_key = None
                    min_diff = float('inf')
                    
                    for timestamp_str, (file_dt, key) in file_dict.items():
                        diff = abs((target_dt - file_dt).total_seconds())
                        if diff < min_diff and diff <= max_diff_seconds:
                            min_diff = diff
                            closest_key = key
                    
                    return closest_key

                # Create snapshots by starting with village files and finding matching files
                processed_combinations = set()
                
                for village_timestamp, (village_dt, village_key) in sorted(village_files.items(), key=lambda x: x[1][0]):
                    # Find closest matching files for this village timestamp
                    player_key = find_closest_file(village_dt, player_files)
                    ally_key = find_closest_file(village_dt, ally_files)
                    conquer_key = find_closest_file(village_dt, conquer_files)
                    
                    # Create snapshot if we have the core files (village, player, ally)
                    # Conquer files are optional
                    if player_key and ally_key:
                        # Create a unique combination identifier to avoid duplicates
                        combination_id = (village_key, player_key, ally_key, conquer_key)
                        
                        if combination_id not in processed_combinations:
                            processed_combinations.add(combination_id)
                            
                            village_data_path = f"s3://{self.s3_snapshot_bucket}/{village_key}"
                            player_data_path = f"s3://{self.s3_snapshot_bucket}/{player_key}"
                            tribe_data_path = f"s3://{self.s3_snapshot_bucket}/{ally_key}"
                            conquer_data_path = f"s3://{self.s3_snapshot_bucket}/{conquer_key}" if conquer_key else None

                            try:
                                # Use the village timestamp as the main timestamp for the snapshot
                                snapshot = SnapshotFileModel(
                                    world=self.world,
                                    server=self.server,
                                    timestamp=int(village_dt.replace(tzinfo=timezone.utc).timestamp()),
                                    village_data_path=village_data_path,
                                    player_data_path=player_data_path,
                                    tribe_data_path=tribe_data_path,
                                    conquer_data_path=conquer_data_path
                                )
                                snapshot_files.append(snapshot)
                                
                                if not conquer_key:
                                    self.logger.debug(f"Created snapshot for {village_timestamp} without conquer file")
                            except Exception as e:
                                self.logger.warning(f"Could not create snapshot for timestamp {village_timestamp}: {e}")
                    else:
                        missing_files = []
                        if not player_key: missing_files.append("player")
                        if not ally_key: missing_files.append("ally")
                        self.logger.debug(f"Skipping village timestamp {village_timestamp}, missing required files: {', '.join(missing_files)}")
            else:
                self.logger.warning(f"No files found in S3 bucket '{self.s3_snapshot_bucket}' with prefix '{prefix}'")
            
            self.logger.info(f"Completed scanning snapshots for {self.server}{self.world}.")
            self.logger.info(f"Found {len(files)} total files in S3")
            self.logger.info(f"Found {len(snapshot_files)} snapshots for {self.server}{self.world}.")

            self.snapshots = snapshot_files
            return self.snapshots
        except Exception as e:
            self.logger.error(f"Error scanning snapshots for {self.server}{self.world}: {e}")
            return []

    def sync_timelapse_images(self) -> List[TimelapseImageModel]:
        """Sync the timelapse images for the world.
        
        Scans available snapshots and checks which corresponding timelapse images exist in S3.
        The timestamp from the ally file is used to construct the expected image paths.
        Uses list_objects_v2 for efficient bulk checking instead of individual head_object calls.

        Returns:
            List[TimelapseImageModel]: A list of timelapse image models with existence flags.
        """
        # First get all available snapshots
        snapshots = self.snapshots
        timelapse_images = []
        
        if not snapshots:
            self.logger.warning(f"No snapshots found for {self.server}{self.world}")
            return timelapse_images
        
        # Get all existing timelapse images for this world using list_objects_v2
        existing_images = set()
        try:
            world_prefix = f"{self.server}{self.world}/"
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.s3_image_bucket, Prefix=world_prefix)
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        # Only include PNG images from top_players and top_tribes directories
                        if key.endswith('.png') and ('top_players/' in key or 'top_tribes/' in key):
                            existing_images.add(key)
            
            self.logger.info(f"Found {len(existing_images)} existing timelapse images for {self.server}{self.world}")
            
        except Exception as e:
            self.logger.error(f"Error listing timelapse images for {self.server}{self.world}: {e}")
            # Continue with empty set - will mark all as missing
        
        for snapshot in snapshots:
            # Extract timestamp from ally file path
            # e.g., s3://tribalwars-scraped/en143/village_en143_20250207_204158.txt -> 20250207_204158
            village_filename = snapshot.village_data_path.split('/')[-1]  # village_en143_20250207_204158.txt
            timestamp_str = village_filename.split('_')[-2] + '_' + village_filename.split('_')[-1].replace('.txt', '')
            
            # Construct expected image paths
            top_players_key = f"{self.server}{self.world}/top_players/{self.server}{self.world}_top_players_{timestamp_str}.png"
            top_tribes_key = f"{self.server}{self.world}/top_tribes/{self.server}{self.world}_top_tribes_{timestamp_str}.png"
            
            top_players_path = f"s3://{self.s3_image_bucket}/{top_players_key}"
            top_tribes_path = f"s3://{self.s3_image_bucket}/{top_tribes_key}"
            
            # Check if images exist in our pre-fetched set
            top_players_exists = top_players_key in existing_images
            top_tribes_exists = top_tribes_key in existing_images
            
            # Create TimelapseImageModel
            timelapse_image = TimelapseImageModel(
                world=snapshot.world,
                server=snapshot.server,
                timestamp=snapshot.timestamp,
                village_data_path=snapshot.village_data_path,
                player_data_path=snapshot.player_data_path,
                tribe_data_path=snapshot.tribe_data_path,
                conquer_data_path=snapshot.conquer_data_path,
                top_players_image_path=top_players_path if top_players_exists else None,
                top_tribes_image_path=top_tribes_path if top_tribes_exists else None,
                image_generated=top_players_exists and top_tribes_exists
            )
            
            timelapse_images.append(timelapse_image)
            
            # Log status
            if timelapse_image.image_generated:
                self.logger.debug(f"Timelapse images found for timestamp {timestamp_str}")
            else:
                missing = []
                if not top_players_exists:
                    missing.append("top_players")
                if not top_tribes_exists:
                    missing.append("top_tribes")
                self.logger.debug(f"Missing timelapse images for timestamp {timestamp_str}: {', '.join(missing)}")
        
        generated_count = sum(1 for img in timelapse_images if img.image_generated)
        self.logger.info(f"Synced {len(timelapse_images)} timelapse image records for {self.server}{self.world} ({generated_count} generated, {len(timelapse_images) - generated_count} pending)")
        
        return timelapse_images

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = WorldLoader(world="146", server="en")
    world = loader.load_world()
    if not world:
        world = loader.create_world(max_coords=750, has_barbarians=True, timelapse_interval=6)
    
    # Scan available snapshots
    snapshots = loader.scan_available_snapshots()
    
    # Sync timelapse images (check which ones exist)
    timelapse_images = loader.sync_timelapse_images()
    
    # Write snapshots to CSV
    with open("snapshots.csv", "w", newline="") as csvfile:
        fieldnames = ["world", "server", "timestamp", "village_data_path", "player_data_path", "tribe_data_path", "conquer_data_path"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for snapshot in snapshots:
            writer.writerow({
                "world": snapshot.world,
                "server": snapshot.server,
                "timestamp": snapshot.timestamp,
                "village_data_path": snapshot.village_data_path,
                "player_data_path": snapshot.player_data_path,
                "tribe_data_path": snapshot.tribe_data_path,
                "conquer_data_path": snapshot.conquer_data_path
            })
    
    # Write timelapse images status to CSV
    with open("timelapse_images.csv", "w", newline="") as csvfile:
        fieldnames = ["world", "server", "timestamp", "image_generated", "top_players_image_path", "top_tribes_image_path"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for image in timelapse_images:
            writer.writerow({
                "world": image.world,
                "server": image.server,
                "timestamp": image.timestamp,
                "image_generated": image.image_generated,
                "top_players_image_path": image.top_players_image_path,
                "top_tribes_image_path": image.top_tribes_image_path
            })
    
    print("Snapshots written to snapshots.csv")
    print("Timelapse images status written to timelapse_images.csv")
    
    # Summary statistics
    total_snapshots = len(timelapse_images)
    generated_count = sum(1 for img in timelapse_images if img.image_generated)
    print(f"Total snapshots: {total_snapshots}")
    print(f"Timelapse images generated: {generated_count}")
    print(f"Pending generation: {total_snapshots - generated_count}")