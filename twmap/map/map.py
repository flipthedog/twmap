from PIL import Image, ImageDraw

from twmap.datamodel.datamodel import VillageModel
from pandas import DataFrame 

from typing import List


class Map:

    def __init__(self):
        
        self.background_color = "#58761b"
        self.tw_color = "#edd8ad"

        self.village_color = "#823c0a"
        self.barbarian_color = "#969696"

        self.grid_color = "#000000"

        self.center_x = 500
        self.center_y = 500

        self.world_origin = 500

        self.show_grid = True
        self.show_center_lines = True

        self.show_barbarians = True

        self.max_x = 0
        self.max_y = 0

        self.image_height = 1000
        self.image_width = 1000

        self.zoom = 3

    def calculate_zoom(self, villages: List[VillageModel]):

        self.max_x = max(village.x_coord for village in villages)
        self.max_y = max(village.y_coord for village in villages)

        self.zoom = self.image_height / max(self.max_x, self.max_y)
        print(f"Zoom: {self.zoom}")
    
    def draw_grid(self, image: Image, color: str):
        
        draw = ImageDraw.Draw(image)
        
        for i in range(self.world_origin, self.image_height, 100):

            j = i - self.world_origin

            print(f"Drawing line at {j}")

            draw.line([0, j, self.image_height, j], fill=color, width=1)
            draw.line([j, 0, j, self.image_height], fill=color, width=1)
        
    def draw_center_lines(self, image: Image, color: str):
        
        draw = ImageDraw.Draw(image)
        
        # draw center lines along center x and y
        draw.line([self.image_height/2, 0, self.image_height/2, self.image_height], fill=color, width=2)
        draw.line([0, self.image_height/2, self.image_width, self.image_height/2], fill=color,  width=2)


    def draw(self, villages: List[VillageModel]):
        

        # Change image size to 1000x1000
        image = Image.new("RGB", (self.image_height, self.image_width), self.background_color)        
        
        # draw villages 
        draw = ImageDraw.Draw(image)

        for village in villages:
            x = (village.x_coord - self.center_x) * self.zoom + self.center_x
            y = (village.y_coord - self.center_y) * self.zoom + self.center_y

            color = self.village_color
            if village.playerid == 0 and self.show_barbarians:
                color = self.barbarian_color
            village_size = self.zoom 
            
            draw.rectangle([x, y, x+village_size, y+village_size], fill=color)

        if self.show_grid:
            self.draw_grid(image, self.grid_color)
        
        if self.show_center_lines:
            self.draw_center_lines(image, self.grid_color)

        image.show()

