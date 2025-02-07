from PIL import Image, ImageDraw

from twmap.datamodel.datamodel import VillageModel
from pandas import DataFrame 

from typing import List


class Map:

    def __init__(self):
        
        self.cell_color = "#58761b"
        self.background_color = "#436213"
        
        self.dull_cell_color = "#0c2909"
        self.dull_background_color = "#395436"
        self.dull_colors = True

        self.tw_color = "#edd8ad"

        self.village_color = "#823c0a"
        self.barbarian_color = "#969696"

        self.grid_color = "#000000"

        self.world_origin = 500
        self.world_height = 1000
        self.world_width = 1000

        self.show_grid = True
        self.show_center_lines = True

        self.show_barbarians = True

        self.max_x = 0
        self.max_y = 0

        self.zoom = 3

        self.cell_size = 4
        self.spacing = 1

        self.image_height = self.world_height * (self.cell_size + self.spacing)
        self.image_width = self.world_width * (self.cell_size + self.spacing)

    def draw(self, villages: List[VillageModel]):

        # draw a grid pattern with each box representing a village

        
        if self.dull_colors:
            cell_color = self.dull_cell_color
            background_color = self.dull_background_color
        else:
            cell_color = self.cell_color
            background_color = self.background_color
        
        image = Image.new("RGB", (self.image_height, self.image_width), background_color)
        
        draw = ImageDraw.Draw(image)

        for i in range(0, self.world_height):

            for j in range(0, self.world_width):

                # print(f"Drawing cell at {i}, {j}")

                x = i * (self.cell_size + self.spacing)
                y = j * (self.cell_size + self.spacing)

                # print(f"Drawing cell at {x}, {y}")

                draw.rectangle([x, y, x+self.cell_size - self.spacing, y+self.cell_size - self.spacing], fill=cell_color)
        

        for village in villages:

            x = village.x_coord * (self.cell_size + self.spacing)
            y = village.y_coord * (self.cell_size + self.spacing)

            if village.playerid == 0 and self.show_barbarians:
                color = self.barbarian_color
            else: 
                color = self.village_color

            draw.rectangle([x, y, x+self.cell_size - self.spacing, y+self.cell_size - self.spacing], fill=color)

        if self.show_grid:
            self.draw_grid(image, self.grid_color, 100)
        
        # crop around the center
        image = self.crop_image(image, 200)

        image.show()

    def crop_image(self, image: Image, spacing: int):

        return image.crop(((self.world_origin - spacing) * (self.cell_size + self.spacing), (self.world_origin - spacing) * (self.cell_size + self.spacing), (self.world_origin + spacing) * (self.cell_size + self.spacing), (self.world_origin + spacing) * (self.cell_size + self.spacing)))

    def draw_grid(self, image: Image, color: str, grid_spacing: int):
        
        draw = ImageDraw.Draw(image)

        for i in range(0, self.world_height, grid_spacing):
            x = i * (self.cell_size + self.spacing) - 1
            draw.line([x, 0, x, self.image_height], fill=color, width=1)
        
        for j in range(0, self.world_width, grid_spacing):
            y = j * (self.cell_size + self.spacing) - 1
            draw.line([0, y, self.image_width, y], fill=color, width=1)
