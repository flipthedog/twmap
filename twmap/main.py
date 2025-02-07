import logging
from map.map import Map
from datamodel.model_loader import ModelLoader
from datamodel.datafilter import DataFilter
from copy import deepcopy
from twmap.api.twapi import TWAPI
from datetime import datetime
import os
import boto3
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TWMap:

    def __init__(self, data_refresh=False, worlds=[144, 145], storage_path="data/", save_to_s3=False, s3_bucket="tw-timelapse", s3_path="data/"):
        self.LOAD_NEW = data_refresh
        self.worlds = worlds
        self.data_path = storage_path
        self.save_to_s3 = save_to_s3

        if self.LOAD_NEW:
            logging.info("Refreshing data from TWAPI")
            api = TWAPI(worlds, "en")
            api.get_files(self.data_path)

        if save_to_s3:
            logging.info("Setting up S3 client")
            self.session = boto3.Session(region_name="us-east-2")
            self.s3 = self.session.client("s3")
            self.s3_bucket = s3_bucket
            self.s3_path = s3_path

    def generate_maps(self):
        for world in self.worlds:
            logging.info(f"Processing world {world}...")
            loader = ModelLoader(data_path=self.data_path, world=world)
            village_models, player_models, tribe_models, conquer_models = loader.load()

            filter = DataFilter(village_models, player_models, tribe_models, conquer_models)
            t10_players_v = filter.get_t10_player_villages()
            t10_tribes_v = filter.get_t10_tribe_villages()
            t10_players = filter.get_t10_players()
            t10_tribes = filter.get_t10_tribes()

            map = Map()
            map.initial_draw(village_models)

            top_player_map = deepcopy(map)
            top_tribe_map = deepcopy(map)

            logging.info("Drawing top players and tribes...")
            logging.info(f"Found {len(t10_players)} top players and {len(t10_tribes)} top tribes")
            logging.info(f"Drawing {len(t10_players_v)} villages of top 10 players")
            logging.info(f"Drawing {len(t10_tribes_v)} villages of top 10 tribes")

            top_player_map.draw(t10_players_v, field="playerid")
            top_tribe_map.draw(t10_tribes_v, field="tribeid")

            top_player_map.draw_legend(ids=t10_players["playerid"], names=t10_players["name"])
            top_tribe_map.draw_legend(ids=t10_tribes["tribeid"], names=t10_tribes["name"])
            world_folder = os.path.join("images", f"world_{world}").replace("\\", "/")
            os.makedirs(world_folder, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            top_player_map.save(os.path.join(world_folder, f"top_players_world_{world}_{timestamp}.png"))
            top_tribe_map.save(os.path.join(world_folder, f"top_tribes_world_{world}_{timestamp}.png"))

            if self.save_to_s3:
                self.upload_to_s3(top_player_map.image, world_folder, f"top_players_world_{world}_{timestamp}.png")
                self.upload_to_s3(top_tribe_map.image, world_folder, f"top_tribes_world_{world}_{timestamp}.png")

    def upload_to_s3(self, image, folder, filename):
        logging.info(f"Uploading {filename} to S3 bucket {self.s3_bucket}")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        self.s3.put_object(Bucket=self.s3_bucket, Key=self.s3_path + folder + "/" + filename, Body=buffer, ContentType='image/png')

if __name__ == "__main__":
    logging.info("Starting TWMap")
    twmap = TWMap(data_refresh=True, save_to_s3=True)
    twmap.generate_maps()
    logging.info("Finished generating maps")
