from PIL import Image, ImageDraw, ImageFont

from twmap.datamodel.datamodel import VillageModel
from pandas import DataFrame 

from twmap.map.colors import ColorManager

from typing import List

from datetime import datetime

import urllib.parse


class Map:

    def __init__(self):
        
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

        self.cell_color = self.color_manager.cell_color
        self.background_color = self.color_manager.background_color
        
        self.dull_cell_color = self.color_manager.dull_cell_color
        self.dull_background_color = self.color_manager.dull_background_color
        self.dull_colors = True

        self.tw_color = self.color_manager.tw_color

        self.village_color = self.color_manager.village_color
        self.barbarian_color = self.color_manager.barbarian_color

        self.grid_color = self.color_manager.grid_color

        self.font = ImageFont.truetype("twmap/map/fonts/ARIAL.TTF", 24)  # Load the font here

    def draw_legend(self, ids: DataFrame, names: DataFrame):
        
        self.crop_image(self.image, 200)

        draw = ImageDraw.Draw(self.image)

        ids = ids.to_list()
        names = names.to_list()

        # Add background
        draw.rectangle([0, 0, 500, len(ids) * 24], fill="#000000")

        for i in range(0, len(ids)):
            draw.text((50, i * 24), f"{i}. {urllib.parse.unquote_plus(names[i])}", fill=self.tw_color, font=self.font, anchor="lt")
            draw.rectangle([0, i * 24, 20, i * 24 + 20], fill=self.color_manager.get_color(ids[i]))

        return self.image

    def draw(self, village_df: DataFrame, field: str):

        draw = ImageDraw.Draw(self.image)

        for _, village in village_df.iterrows():

            if field == "playerid":
                color = self.color_manager.get_color(village['playerid'])
            elif field == "tribeid":
                color = self.color_manager.get_color(village['tribeid'])
            elif field == "barbarian" and village['playerid'] == 0:
                color = self.barbarian_color
            else:
                color = self.village_color            

            x = village['x_coord'] * (self.cell_size + self.spacing)
            y = village['y_coord'] * (self.cell_size + self.spacing)

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
        
        self.image = Image.new("RGB", (self.image_height, self.image_width), background_color)
        
        draw = ImageDraw.Draw(self.image)

        for i in range(0, self.world_height):

            for j in range(0, self.world_width):

                x = i * (self.cell_size + self.spacing)
                y = j * (self.cell_size + self.spacing)

                draw.rectangle([x, y, x+self.cell_size - self.spacing, y+self.cell_size - self.spacing], fill=cell_color)
        

        # draw player villages
        self.draw(village_df, None)

        # draw barbarian villages
        self.draw(village_df, "barbarian")

        if self.show_grid:
            self.draw_grid(self.image, self.grid_color, 100)

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
    
    def add_current_date_time(self):
        draw = ImageDraw.Draw(self.image)
        draw.text((0, self.image.height - 10), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fill=self.tw_color, font=self.font, anchor="lb")
        return self.image

    def watermark(self, text: str):
        draw = ImageDraw.Draw(self.image)
        draw.text((self.image.width - 10, self.image.height - 10), text, fill=self.tw_color, font=self.font, anchor="rb")
        return self.image
        
    def save(self, filename: str):
        if self.add_date_time:
            self.add_current_date_time()
        
        if self.add_watermark:
            self.watermark("github.com/flipthedog/twmap")

        # self.image.save(filename, quality=95)
