import requests
import os
import logging

from typing import List

import time

class TWAPI: 

    def __init__(self, worlds: List[int], language: str):
        
        self.worlds = worlds

        self.urls = [f"https://{language}{world}.tribalwars.net" for world in worlds]

        self.map_files = {
            "village": "/map/village.txt",
            "player": "/map/player.txt",
            "ally": "/map/ally.txt",
            "conquer": "/map/conquer.txt"
        }

        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def get_files(self, save_location: str = "data/"):
        for url in self.urls:
            world = url.split('.')[0].replace("https://", "")
            for key, value in self.map_files.items():
                url_get = url + value
                response = requests.get(url_get)

                world_save_location = os.path.join(save_location, f"{world}/")

                if not os.path.exists(world_save_location):
                    os.makedirs(world_save_location)
                
                with open(os.path.join(world_save_location, f"{key}.txt"), "w") as f:
                    f.write(response.text)
                
                logging.info(f"Saved {key}.txt to {world_save_location}")

                # delay of 10 seconds
                time.sleep(10)


if __name__ == "__main__":

    tw_api = TWAPI([144], "en")

    tw_api.get_files()