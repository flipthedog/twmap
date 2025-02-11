from PIL import Image, ImageDraw, ImageFont

import pandas as pd
from pandas import DataFrame
from sklearn.cluster import KMeans 

from twmap.datamodel.datafilter import DataFilter
from twmap.datamodel.datamodel import VillageModel
from twmap.map.colors import ColorManager

from typing import List

from datetime import timezone, datetime

import urllib.parse

import logging
from copy import deepcopy
from scipy.spatial import ConvexHull


class Map:

    def __init__(self, village_df: DataFrame, player_df: DataFrame, tribe_df: DataFrame, conquer_df: DataFrame, printed_datetime: str = None, printed_world: str = None, player_list: List[str] = None, tribe_list: List[str] = None):
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
        self.printed_world = printed_world
        
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
        
        if player_list:
            logging.info(f"Player list: {player_list}")
            self.player_list = player_list
            self.player_village = self.data_filter.filter_villages_by_player_names(player_list)
        if tribe_list:
            logging.info(f"Tribe list: {tribe_list}")
            self.tribe_list = tribe_list
            self.tribe_village = self.data_filter.filter_villages_by_tribe_names(tribe_list)        
        self.world_origin = 500
        self.world_height = 1000
        self.world_width = 1000

        self.show_grid = True
        self.show_center_lines = True

        self.show_barbarians = True

        self.max_x = self.village_df['x_coord'].max() - self.world_origin + 20
        self.max_y = self.village_df['y_coord'].max() - self.world_origin + 20
        self.max_border = max(self.max_x, self.max_y)
                
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

        self.font_size = 32
        self.font = ImageFont.truetype("twmap/map/fonts/ARIAL.TTF", self.font_size)  # Load the font here

        self.initial_map()

        self.initial_image = deepcopy(self.image)

    def initial_map(self):
        """Create an initial map with all player villages and barbarians.
        """
        
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
    
    def draw_top_players(self, zones_of_control: bool = False, center_text: bool = False):
        logging.info(f"Drawing {len(self.t10_players_v)} villages of top 10 players")
        logging.info(f"Found {len(self.t10_players)} top players")
        self.image = deepcopy(self.initial_image)
        self.draw(self.t10_players_v, "playerid")
        self.draw(self.past_day_conquers_p10, "playerid", 3)
        # Call the function to draw zones of control for the top 10 player villages
        if zones_of_control:
            self.draw_zones_of_control(self.t10_players_v, 10)
        if center_text:
            self.draw_centroid_text(self.t10_players_v, 10, "playerid")
        self.color_manager.reset_color_index()
        return self.image
    
    def draw_top_tribes(self, zones_of_control: bool = False, center_text: bool = False):
        logging.info(f"Drawing {len(self.t10_tribes_v)} villages of top 10 tribes")
        logging.info(f"Found {len(self.t10_tribes)} top tribes")
        self.image = deepcopy(self.initial_image)
        self.draw(self.t10_tribes_v, "tribeid")
        self.draw(self.past_day_conquers_t10, "tribeid", 3)
        if zones_of_control:
            self.draw_zones_of_control(self.t10_tribes_v, 10, "tribeid")
        if center_text:
            self.draw_centroid_text(self.t10_tribes_v, 10, "tribeid")
        self.color_manager.reset_color_index()
        return self.image

    def draw_specific_players(self, zones_of_control: bool = False, center_text: bool = False):
        logging.info(f"Drawing {len(self.player_village)} villages of specific players")
        self.image = deepcopy(self.initial_image)
        self.draw(self.player_village, "playerid")
        if zones_of_control:
            self.draw_zones_of_control(self.player_village, len(self.player_list))
        if center_text:
            self.draw_centroid_text(self.player_village, len(self.player_list), "playerid")
        self.color_manager.reset_color_index()
        return self.image
    
    def draw_specific_tribes(self, zones_of_control: bool = False, center_text: bool = False):
        logging.info(f"Drawing {len(self.tribe_village)} villages of specific tribes")
        self.image = deepcopy(self.initial_image)
        self.draw(self.tribe_village, "tribeid")
        if zones_of_control:
            self.draw_zones_of_control(self.tribe_village, len(self.tribe_list), "tribeid")
        if center_text:
            self.draw_centroid_text(self.tribe_village, len(self.tribe_list), "tribeid")
        self.color_manager.reset_color_index()
        return self.image
    
    def draw_legend(self, top_type: str = "players", image: Image = None):
        
        image = self.crop_image(image)

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
        draw.rectangle([0, 0, 450, (len(ids) + 1) * self.font_size], fill="#000000")

        draw.text((0, 0), f"Top {top_type.capitalize()}", fill=self.tw_color, font=self.font, anchor="lt")
        
        for i in range(0, len(ids)):
            draw.text((50, (i + 1) * self.font_size), f"{i + 1}. {urllib.parse.unquote_plus(names[i])}", fill=self.tw_color, font=self.font, anchor="lt")
            draw.rectangle([0, (i + 1) * self.font_size, 20, (i + 1) * self.font_size + 20], fill=self.color_manager.get_color(ids[i]))

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
    
    def crop_image(self, image: Image):
        
        spacing = self.max_border
        
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
        if self.printed_world:
            draw.text((0, self.image.height - 10), self.printed_datetime + " UTC - " + self.printed_world, fill=self.tw_color, font=self.font, anchor="lb")
        else:
            draw.text((0, self.image.height - 10), self.printed_datetime + " UTC", fill=self.tw_color, font=self.font, anchor="lb")
        return self.image

    def watermark(self, text: str):
        draw = ImageDraw.Draw(self.image)
        draw.text((self.image.width - 10, self.image.height - 10), text, fill=self.tw_color, font=self.font, anchor="rb")
        return self.image
        
    def local_save(self, filename: str):
        self.image.save(filename, quality=95)

    def draw_zones_of_control(self, village_df: DataFrame, top_n: int = 10, filter_type: str = "playerid"):
        """
        Draw zones of control for the top N players or tribes using Convex Hull and mark the centroid.

        Args:
            village_df (DataFrame): DataFrame containing the villages to cluster (must have playerid, tribeid).
            top_n (int): Number of top players or tribes to draw zones for.
            filter_type (str): Column to filter on, e.g. 'playerid' or 'tribeid'.
        """
        if filter_type == "playerid":
            top_entities = self.t10_players.head(top_n)
        elif filter_type == "tribeid":
            top_entities = self.t10_tribes.head(top_n)
        else:
            raise ValueError("Invalid filter_type. Expected 'playerid' or 'tribeid'.")

        draw = ImageDraw.Draw(self.image, 'RGBA')

        for _, entity in top_entities.iterrows():
            entity_id = entity[filter_type]
            entity_villages = village_df[village_df[filter_type] == entity_id]
            if entity_villages.empty:
                continue

            village_coords = entity_villages[['x_coord', 'y_coord']].values
            if len(village_coords) > 2:
                hull = ConvexHull(village_coords)
                polygon = [
                    (
                        village_coords[vertex, 0] * (self.cell_size + self.spacing),
                        village_coords[vertex, 1] * (self.cell_size + self.spacing)
                    )
                    for vertex in hull.vertices
                ]
                color = self.color_manager.get_color(entity_id)
                color_rgba = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                fill_color = (color_rgba[0], color_rgba[1], color_rgba[2], 60)
                draw.polygon(polygon, outline=color, fill=fill_color)

                # # Calculate the bounding box for the ellipse
                # min_x = min(p[0] for p in polygon)
                # max_x = max(p[0] for p in polygon)
                # min_y = min(p[1] for p in polygon)
                # max_y = max(p[1] for p in polygon)

                # # Draw the ellipse
                # draw.ellipse([min_x, min_y, max_x, max_y], outline=color, fill=fill_color)
                
                # Calculate centroid
                centroid_x = village_coords[:, 0].mean() * (self.cell_size + self.spacing)
                centroid_y = village_coords[:, 1].mean() * (self.cell_size + self.spacing)

                # Draw the name at the centroid
                name = urllib.parse.unquote_plus(entity['name'])
                draw.text((centroid_x, centroid_y), name, fill=fill_color, font=self.font, anchor="mm")

        return self.image

    def draw_centroid_text(self, village_df: DataFrame, top_n: int = 10, filter_type: str = "playerid"):
        """
        Draw zones of control for the top N players or tribes and mark the centroid with text.

        Args:
            village_df (DataFrame): DataFrame containing the villages to cluster (must have playerid, tribeid).
            top_n (int): Number of top players or tribes to draw zones for.
            filter_type (str): Column to filter on, e.g. 'playerid' or 'tribeid'.
        """
        if filter_type == "playerid":
            top_entities = self.t10_players.head(top_n)
        elif filter_type == "tribeid":
            top_entities = self.t10_tribes.head(top_n)
        else:
            raise ValueError("Invalid filter_type. Expected 'playerid' or 'tribeid'.")

        draw = ImageDraw.Draw(self.image, 'RGBA')


        
        for _, entity in top_entities.iterrows():
            entity_id = entity[filter_type]
            entity_villages = village_df[village_df[filter_type] == entity_id]
            
            color = self.color_manager.get_color(entity_id)
            color_rgba = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            fill_color = (color_rgba[0], color_rgba[1], color_rgba[2], 60)
            if entity_villages.empty:
                continue

            village_coords = entity_villages[['x_coord', 'y_coord']].values
            if len(village_coords) > 2:
                # Calculate centroid
                centroid_x = village_coords[:, 0].mean() * (self.cell_size + self.spacing)
                centroid_y = village_coords[:, 1].mean() * (self.cell_size + self.spacing)
        
                # Draw the name at the centroid
                name = urllib.parse.unquote_plus(entity['name'])
                draw.text((centroid_x, centroid_y), name, fill=fill_color, font=self.font, anchor="mm")

        return self.image
