from PIL import Image, ImageDraw, ImageFont

from pandas import DataFrame 

from twmap.datamodel.datafilter import DataFilter
from twmap.datamodel.datamodel import VillageModel
from twmap.map.colors import ColorManager

from typing import List

from datetime import timezone, datetime

import urllib.parse

import logging
from copy import deepcopy


class Map:

    def __init__(self, village_df: DataFrame, player_df: DataFrame, tribe_df: DataFrame, conquer_df: DataFrame, printed_datetime: str = None):
        """Load it with TW data and create a map

        Args:
            village_df (DataFrame): DataFrame containing village data
            player_df (DataFrame): DataFrame containing player data
            tribe_df (DataFrame): DataFrame containing tribe data
            conquer_df (DataFrame): DataFrame containing conquer data
        """

        self.village_df = village_df
        self.player_df = player_df
        self.tribe_df = tribe_df
        self.conquer_df = conquer_df
        
        self.printed_datetime = printed_datetime

        if self.printed_datetime is None:
            self.printed_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            # TODO: read this from the file

        self.data_filter = DataFilter(village_df, player_df, tribe_df, conquer_df)

        self.t10_players_v = self.data_filter.get_t10_player_villages()
        self.t10_tribes_v = self.data_filter.get_t10_tribe_villages()
        self.t10_players = self.data_filter.get_t10_players()
        self.t10_tribes = self.data_filter.get_t10_tribes()

        self.past_day_conquers_p10 = self.data_filter.get_past_day_t10_conquers_players()
        self.past_day_conquers_t10 = self.data_filter.get_past_day_t10_conquers_tribes()
        
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

        self.initial_map()

        self.initial_image = deepcopy(self.image)
        
        self.image_top_players = self.draw_top_players().copy()  # Save the map with top players
        self.color_manager.reset_color_index()
        self.image_top_tribes = self.draw_top_tribes().copy()  # Save the map with top tribes

        self.image_top_players_with_legend = self.draw_legend("players", self.image_top_players)  # Save the map with top players and legend
        self.image_top_tribes_with_legend = self.draw_legend("tribes", self.image_top_tribes)  # Save the map with top tribes and legend

    def initial_map(self):

        # create list of villages
        villages = [VillageModel(**village) for village in self.village_df.to_dict(orient="records")]
        
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
        self.draw(self.village_df, None)

        # draw barbarian villages
        self.draw(self.village_df, "barbarian")

        if self.show_grid:
            self.draw_grid(self.image, self.grid_color, 100)
            
        if self.watermark:
            self.watermark("github.com/flipthedog/twmap")
        
        if self.add_current_date_time:
            self.add_current_date_time()

    def draw_top_players(self):
        logging.info(f"Drawing {len(self.t10_players_v)} villages of top 10 players")
        logging.info(f"Found {len(self.t10_players)} top players")
        self.image = self.initial_image
        self.draw(self.t10_players_v, "playerid")
        self.draw(self.past_day_conquers_p10, "playerid", 3)
        return self.image
    
    def draw_top_tribes(self):
        logging.info(f"Drawing {len(self.t10_tribes_v)} villages of top 10 tribes")
        logging.info(f"Found {len(self.t10_tribes)} top tribes")
        self.image = self.initial_image
        self.draw(self.t10_tribes_v, "tribeid")
        self.draw(self.past_day_conquers_t10, "tribeid", 3)
        return self.image

    def draw_legend(self, top_type: str = "players", image: Image = None):
        
        image = self.crop_image(image, 200)

        if self.watermark:  
            image = self.watermark("github.com/flipthedog/twmap")
        
        if self.add_current_date_time:
            
            image = self.add_current_date_time()
        
        draw = ImageDraw.Draw(image)

        if top_type == "players":
            ids = self.t10_players['playerid'].to_list()
            names = self.t10_players['name'].to_list()
        elif top_type == "tribes":
            ids = self.t10_tribes['tribeid'].to_list()
            names = self.t10_tribes['name'].to_list()
        else:
            raise ValueError("Invalid top_type. Expected 'players' or 'tribes'.")

        # Add background
        draw.rectangle([0, 0, 500, (len(ids) + 1) * 24], fill="#000000")

        draw.text((0, 0), f"Top {top_type.capitalize()}", fill=self.tw_color, font=self.font, anchor="lt")
        
        for i in range(0, len(ids)):
            draw.text((50, (i + 1) * 24), f"{i + 1}. {urllib.parse.unquote_plus(names[i])}", fill=self.tw_color, font=self.font, anchor="lt")
            draw.rectangle([0, (i + 1) * 24, 20, (i + 1) * 24 + 20], fill=self.color_manager.get_color(ids[i]))

        return image

    def draw(self, village_df: DataFrame, field: str, size_multiplier: float = 1.0):

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

            cell_size = self.cell_size * size_multiplier

            draw.rectangle([x, y, x + cell_size - self.spacing, y + cell_size - self.spacing], fill=color)

        return self.image
    
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
        draw.text((0, self.image.height - 10), self.printed_datetime + " UTC", fill=self.tw_color, font=self.font, anchor="lb")
        return self.image

    def watermark(self, text: str):
        draw = ImageDraw.Draw(self.image)
        draw.text((self.image.width - 10, self.image.height - 10), text, fill=self.tw_color, font=self.font, anchor="rb")
        return self.image
        
    def local_save(self, filename: str):
        self.image.save(filename, quality=95)
