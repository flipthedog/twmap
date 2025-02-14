import logging

from twmap.datamodel.dataloader import DataLoader
from twmap.map.map import Map

import os
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MapFactory:
    
    def __init__(self, s3_path: str, save_location: str = "images", refresh: bool = False, custom_color_map: dict = None):
        self.s3_path = s3_path
        self.loader = DataLoader(s3_path, "data/", refresh=refresh)
        
        self.village_models, self.player_models, self.tribe_models, self.conquer_models = self.loader.load()
        
        self.world_id = self.loader.world_id
        self.image_save_location = save_location + f"/{self.world_id}"
        
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
            
            map = Map(self.village_models[i], self.player_models[i], self.tribe_models[i], self.conquer_models[i], map_time, world_id, custom_color_map=self.custom_color_map)
            
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
            
            # image_top_tribes_with_legend.save(os.path.join(tribe_save_location, f"top_tribes_{world_id}_{map_save_time}.png"))
            # image_top_players_with_legend.save(os.path.join(player_save_location, f"top_players_{world_id}_{map_save_time}.png"))
            
            image_top_tribes_with_legend.save(os.path.join(tribe_save_location, f"{i}.png"))
            image_top_players_with_legend.save(os.path.join(player_save_location, f"{i}.png"))
        
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
            
            map = Map(self.village_models[i], self.player_models[i], self.tribe_models[i], self.conquer_models[i], map_time, world_id, player_list=specific_players, tribe_list=specific_tribes, custom_color_map=self.custom_color_map)
            
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

if __name__ == "__main__":
    factory = MapFactory("s3://tribalwars-scraped/en144/")
    factory.create_maps()
