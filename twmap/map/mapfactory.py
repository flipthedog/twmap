import logging

from twmap.datamodel.dataloader import DataLoader
from twmap.map.map import Map

import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MapFactory:
    
    def __init__(self, s3_path: str, save_location: str = "images", refresh: bool = False):
        self.s3_path = s3_path
        self.loader = DataLoader(s3_path, "data/", refresh=refresh)
        
        self.village_models, self.player_models, self.tribe_models, self.conquer_models = self.loader.load()
        
        self.world_id = self.loader.world_id
        self.image_save_location = save_location + f"/{self.world_id}"
    
    def create_maps(self, max_images: int = None):
        
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
            
            map = Map(self.village_models[i], self.player_models[i], self.tribe_models[i], self.conquer_models[i], map_time, world_id)
            
            if not os.path.exists(self.image_save_location):
                os.makedirs(self.image_save_location)
            
            map.image_top_tribes_with_legend.save(self.image_save_location + f"/top_tribes_{world_id}_{map_save_time}.png")
            map.image_top_players_with_legend.save(self.image_save_location + f"/top_players_{world_id}_{map_save_time}.png")

if __name__ == "__main__":
    factory = MapFactory("s3://tribalwars-scraped/en144/")
    factory.create_maps()
