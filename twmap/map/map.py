from PIL import Image, ImageDraw, ImageFont

from twmap.datamodel.datamodel import VillageModel
from pandas import DataFrame 

from twmap.map.colors import ColorManager

from typing import List

from datetime import datetime

import urllib.parse


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

        self.add_date_time = True
        self.add_watermark = True

        self.color_manager = ColorManager()

    def draw_legend(self, ids: DataFrame, names: DataFrame):

        draw = ImageDraw.Draw(self.image)

        ids = ids.to_list()
        names = names.to_list()

        font = ImageFont.truetype("arial.ttf", 24)  # Specify the font size here

        # Add background
        draw.rectangle([0, 0, 500, len(ids) * 24], fill="#000000")

        for i in range(0, len(ids)):
            draw.text((50, i * 24), f"{i}. {urllib.parse.unquote_plus(names[i])}", fill=self.tw_color, font=font, anchor="lt")
            draw.rectangle([0, i * 24, 20, i * 24 + 20], fill=self.color_manager.get_color(ids[i]))

        return self.image

    def draw(self, village_df: DataFrame, id: int):

        villages = [VillageModel(**village) for village in village_df.to_dict(orient="records")]

        draw = ImageDraw.Draw(self.image)

        color = self.color_manager.get_color(id)

        for village in villages:

            x = village.x_coord * (self.cell_size + self.spacing)
            y = village.y_coord * (self.cell_size + self.spacing)

            draw.rectangle([x, y, x+self.cell_size - self.spacing, y+self.cell_size - self.spacing], fill=color)
        

        return self.image

    
    def initial_draw(self, village_df: DataFrame):
        
        # create list of villages
        villages = [VillageModel(**village) for village in village_df.to_dict(orient="records")]
        
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
        # image = self.crop_image(image, 200)

        if self.add_date_time:
            image = self.add_current_date_time(image)
        
        if self.add_watermark:
            image = self.watermark(image, "github.com/flipthedog/twmap")

        self.image = image

    def crop_image(self, image: Image, spacing: int):
        
        self.image =  image.crop(((self.world_origin - spacing) * (self.cell_size + self.spacing), (self.world_origin - spacing) * (self.cell_size + self.spacing), (self.world_origin + spacing) * (self.cell_size + self.spacing), (self.world_origin + spacing) * (self.cell_size + self.spacing)))
        return self.image

    def draw_grid(self, image: Image, color: str, grid_spacing: int):
        
        draw = ImageDraw.Draw(image)

        for i in range(0, self.world_height, grid_spacing):
            x = i * (self.cell_size + self.spacing) - 1
            draw.line([x, 0, x, self.image_height], fill=color, width=1)
        
        for j in range(0, self.world_width, grid_spacing):
            y = j * (self.cell_size + self.spacing) - 1
            draw.line([0, y, self.image_width, y], fill=color, width=1)
    
    def add_current_date_time(self, image: Image):
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("arial.ttf", 24)  # Specify the font size here
        draw.text((0, 0), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fill=self.tw_color, font=font, anchor="lt")
        return image

    def watermark(self, image: Image, text: str):
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("arial.ttf", 24)  # Specify the font size here
        width, height = image.size
        draw.text((width - 10, height - 10), text, fill=self.tw_color, font=font, anchor="rb")
        return image