import requests
import os

class TWAPI: 

    def __init__(self, world: int, language: str):
        
        self.world = world
        self.url = f"https://en{self.world}.tribalwars.net/game.php"

        self.map_files = {
            "village": "/map/village.txt",
            "player": "/map/player.txt",
            "ally": "/map/ally.txt",
            "conquer": "/map/conquer.txt"
        }

    def get_files(self, save_location: str = "data/"):
        for key, value in self.map_files.items():
            url_get = self.url + value
            response = requests.get(url_get)

            save_location = save_location + f"en{self.world}/"

            if not os.path.exists(save_location):
                os.makedirs(save_location)
            
            with open(save_location + f"{key}.txt", "w") as f:
                f.write(response.text)
            
            print(f"Saved {key}.txt to {save_location}")


        

if __name__ == "__main__":

    tw_api = TWAPI(144, "en")

    tw_api.get_files()
    