import logging

from twmap.datamodel.dataloader import DataLoader
from twmap.map.map import Map

import os
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MapFactory:
    
    def __init__(self, s3_path: str, save_location: str = "images", refresh: bool = False):
        self.s3_path = s3_path
        self.loader = DataLoader(s3_path, "data/", refresh=refresh)
        
        self.village_models, self.player_models, self.tribe_models, self.conquer_models = self.loader.load()
        
        self.world_id = self.loader.world_id
        self.image_save_location = save_location + f"/{self.world_id}"
    
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
            
            map = Map(self.village_models[i], self.player_models[i], self.tribe_models[i], self.conquer_models[i], map_time, world_id)
            
            if not os.path.exists(self.image_save_location):
                os.makedirs(self.image_save_location)
            
            image_top_players = map.draw_top_players(center_text=True).copy()  # Save the map with top players
        
            image_top_tribes = map.draw_top_tribes(center_text=True, zones_of_control=True).copy()  # Save the map with top tribes

            image_top_players_with_legend = map.draw_legend("players", image_top_players)  # Save the map with top players and legend
            image_top_tribes_with_legend = map.draw_legend("tribes", image_top_tribes)  # Save the map with top tribes and legend
            
            image_top_tribes_with_legend.save(self.image_save_location + f"/top_tribes_{world_id}_{map_save_time}.png")
            image_top_players_with_legend.save(self.image_save_location + f"/top_players_{world_id}_{map_save_time}.png")
        
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
            
            map = Map(self.village_models[i], self.player_models[i], self.tribe_models[i], self.conquer_models[i], map_time, world_id, player_list=specific_players, tribe_list=specific_tribes)
            
            if not os.path.exists(self.image_save_location):
                os.makedirs(self.image_save_location)
            
            if specific_players:
                image_specific_players = map.draw_specific_players().copy()  # Save the map with specific players
                image_specific_players_with_legend = map.draw_legend("players", image_specific_players, True)  # Save the map with specific players and legend
                image_specific_players_with_legend.save(self.image_save_location + f"/custom_players_{world_id}_{map_save_time}.png")
            
            if specific_tribes:
                image_specific_tribes = map.draw_specific_tribes(center_text=True).copy()  # Save the map with specific tribes
                image_specific_tribes_with_legend = map.draw_legend("tribes",image_specific_tribes, True)  # Save the map with specific tribes and legend
                image_specific_tribes_with_legend.save(self.image_save_location + f"/custom_tribes_{world_id}_{map_save_time}.png")

if __name__ == "__main__":
    factory = MapFactory("s3://tribalwars-scraped/en144/")
    factory.create_maps()
