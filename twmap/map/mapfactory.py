import logging

from twmap.datamodel.dataloader import DataLoader
from twmap.map.map import Map

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MapFactory:
    
    def __init__(self, s3_path: str, save_location: str = "ïmages"):
        self.s3_path = s3_path
        self.loader = DataLoader(s3_path)
        
        self.village_models, self.player_models, self.tribe_models, self.conquer_models = self.loader.load_s3()
        
        self.world_id = self.loader.village_files["world_id"].iloc[0]
        
        self.times = self.loader.village_files["datetime"].dt.strftime("%Y%m%d_%H%M%S").tolist()
        
        self.save_location = save_location + f"/{self.world_id}"
    
    def create_maps(self):
        
        for i in range(len(self.times)):
            
            logging.info(f"Creating map for {self.times[i]}")
            map = Map(self.village_models[i], self.player_models[i], self.tribe_models[i], self.conquer_models[i])
            top_tribes_image = map.image_top_tribes_with_legend
            top_players_image = map.image_top_players_with_legend
            
            top_tribes_image.save(f"{self.save_location}/top_tribes_{self.times[i]}.png")
            top_players_image.save(f"{self.save_location}/top_players_{self.times[i]}.png")

if __name__ == "__main__":
    factory = MapFactory("s3://tribalwars-scraped/en144/")
    factory.create_maps()
