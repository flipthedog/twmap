from PIL import Image, ImageDraw, ImageFont

import pandas as pd
from pandas import DataFrame
from sklearn.cluster import KMeans 

from twmap.snapshot.datafilter import DataFilter
from twmap.map.colors import ColorManager

from typing import List

from datetime import timezone, datetime

import urllib.parse

import logging
from copy import deepcopy
from scipy.spatial import ConvexHull


class Map:

    def __init__(self, data_filter: DataFilter, player_list: List[str] = None, tribe_list: List[str] = None, custom_color_map: dict = None, max_coords: int = 300):
        """Load it with TW data and create a map

        Args:
            village_df (DataFrame): DataFrame containing village data
            player_df (DataFrame): DataFrame containing player data
            tribe_df (DataFrame): DataFrame containing tribe data
            conquer_df (DataFrame): DataFrame containing conquer data
        """
        self.data_filter = data_filter

        self.village_df = data_filter.village_df
        self.player_df = data_filter.player_df
        self.tribe_df = data_filter.tribe_df
        self.conquer_df = data_filter.conquer_df
        
        self.printed_datetime = data_filter.printed_timestamp
        self.printed_world = data_filter.world_id
        
        if self.printed_datetime is None:
            self.printed_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            # TODO: read this from the file

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
            self.player_conquer = self.data_filter.get_past_day_conquers_by_player_names(player_list)
        if tribe_list:
            logging.info(f"Tribe list: {tribe_list}")
            self.tribe_list = tribe_list
            self.tribe_village = self.data_filter.filter_villages_by_tribe_ids(tribe_list)
            self.tribe_conquer = self.data_filter.get_past_day_conquers_by_tribe_ids(tribe_list)
               
        self.world_origin = 500
        self.world_height = 1000
        self.world_width = 1000

        self.show_grid = True
        self.show_center_lines = True

        self.show_barbarians = True

        self.max_border = max_coords - self.world_origin + 20
        
        self.zoom = 3

        self.cell_size = 4
        self.spacing = 1

        self.player_village_size_multiplier = 2.0

        self.image_height = self.world_height * (self.cell_size + self.spacing)
        self.image_width = self.world_width * (self.cell_size + self.spacing)

        self.add_date_time = True
        self.add_watermark = True

        self.color_manager = ColorManager()

        if custom_color_map:
            logging.info("Loaded custom color map")
            self.color_manager.create_custom_color_map(custom_color_map)
            
        self.cell_color = self.color_manager.cell_color
        self.background_color = self.color_manager.background_color
        
        self.dull_cell_color = self.color_manager.dull_cell_color
        self.dull_background_color = self.color_manager.dull_background_color
        self.dull_colors = True

        self.tw_color = self.color_manager.tw_color

        self.village_color = self.color_manager.village_color
        self.barbarian_color = self.color_manager.barbarian_color

        self.grid_color = self.color_manager.grid_color

        self.font_size = 48
        self.font = ImageFont.truetype("twmap/map/fonts/Roboto_Condensed-Bold.ttf", self.font_size)  # Load the font here

        self.initial_map()

        self.initial_image = deepcopy(self.image)

        self.entity_centroids = {}

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
        
        self.image = Image.new("RGBA", (self.image_height, self.image_width), background_color)
        
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
            
        if self.add_watermark:
            self.watermark("SirolfR")
        
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
            self.draw_influence_zones(self.t10_tribes_v, 10, "tribeid", "clusters")
        if center_text:
            self.draw_centroid_text(self.t10_tribes_v, 10, "tribeid")
        self.color_manager.reset_color_index()
        return self.image

    def draw_specific_players(self, zones_of_control: bool = False, center_text: bool = False):
        logging.info(f"Drawing {len(self.player_village)} villages of specific players")
        self.image = deepcopy(self.initial_image)
        self.draw(self.player_village, "playerid")
        self.draw(self.player_conquer, "playerid", 3)
        if zones_of_control:
            self.draw_zones_of_control(self.player_village, len(self.player_list))
        if center_text:
            self.draw_centroid_text(self.player_village, len(self.player_list), "specificplayer")
        return self.image
    
    def draw_specific_tribes(self, zones_of_control: bool = False, center_text: bool = False):
        logging.info(f"Drawing {len(self.tribe_village)} villages of specific tribes")
        self.image = deepcopy(self.initial_image)
        self.draw(self.tribe_village, "tribeid")
        self.draw(self.tribe_conquer, "tribeid", 3)
        if zones_of_control:
            self.draw_zones_of_control(self.tribe_village, len(self.tribe_list), "specifictribe")
        if center_text:
            self.draw_centroid_text(self.tribe_village, len(self.tribe_list), "specifictribe")
        return self.image
    
    def draw_legend(self, top_type: str = "players", image: Image = None, specific: bool = False ):
                
        legend_width = 1000
        # create separate side image for legend that will be pasted together with map
        legend_image = Image.new("RGBA", (legend_width, self.image.height), (0, 0, 0, 0))

        if self.add_watermark:  
            image = self.watermark("SirolfR")
        
        if self.add_current_date_time:
            image = self.add_current_date_time()

        draw = ImageDraw.Draw(legend_image)

        if top_type == "players":
            if specific:
                ids = self.player_df[self.player_df['name'].isin(self.player_list)]['playerid'].tolist()
                names = self.player_df[self.player_df['name'].isin(self.player_list)]['name'].tolist()
            else:
                ids = self.t10_players['playerid'].to_list()
                names = self.t10_players['name'].to_list()
        elif top_type == "tribes":
            if specific:
                ids = self.tribe_df[self.tribe_df['tribeid'].isin(self.tribe_list)]['tribeid'].tolist()
                names = self.tribe_df[self.tribe_df['tribeid'].isin(ids)]['name'].tolist()
            else:
                ids = self.t10_tribes['tribeid'].to_list()
                names = self.t10_tribes['name'].to_list()
        else:
            raise ValueError("Invalid top_type. Expected 'players' or 'tribes'.")

        # Add background
        draw.rectangle([0, 0, legend_width, image.height], fill="#000000")

        if specific:
            draw.text((0, 0), "Top Tribes", fill=self.tw_color, font=self.font, anchor="lt")
            
            for i in range(0, len(ids)):
                id = ids[i]
                draw.text((50, (i + 1) * self.font_size), f"{i + 1}. {urllib.parse.unquote_plus(names[i])}", fill=self.tw_color, font=self.font, anchor="lt")
                draw.rectangle([0, (i + 1) * self.font_size, 20, (i + 1) * self.font_size + 20], fill=self.color_manager.get_color(id))
        else:
            # Create a larger font for the title
            title_font_size = int(self.font_size * 1.5)  # 50% larger than normal font
            title_font = ImageFont.truetype("twmap/map/fonts/Roboto_Condensed-Bold.ttf", title_font_size)

            draw.text((0, 0), f"Top {top_type.capitalize()} - {self.data_filter.world_id}", fill=self.tw_color, font=title_font, anchor="lt")

            # Include horizontal line
            draw.line([0, self.font_size * 1.5 + 5, legend_width, self.font_size * 1.5 + 5], fill=self.tw_color, width=3)

            for i in range(0, len(ids)):
                draw.text((75, (i + 1) * self.font_size + 40), f"{i + 1}. {urllib.parse.unquote_plus(names[i])}", fill=self.tw_color, font=self.font, anchor="lt")
                draw.rectangle([10, (i + 1) * self.font_size + 40, 50, (i + 1) * self.font_size + 80], fill=self.color_manager.get_color(ids[i]))

        # add another horizontal line at the end
        draw.line([0, (len(ids) + 1) * self.font_size + 50, legend_width, (len(ids) + 1) * self.font_size + 50], fill=self.tw_color, width=3)

        # Combine legend with main image
        combined_width = image.width + legend_image.width
        combined_image = Image.new("RGBA", (combined_width, image.height))
        combined_image.paste(image, (0, 0))
        combined_image.paste(legend_image, (image.width, 0))

        # This is for drawing lines from legend to centroids -- but its not very good looking
        
        # draw = ImageDraw.Draw(combined_image)

        # # use the ids to draw lines to centroids
        # for i in range(0, len(ids)):
        #     entity_id = ids[i]
        #     if entity_id in self.entity_centroids:
        #         centroid_x, centroid_y = self.entity_centroids[entity_id]
        #         # draw line from legend to centroid
        #         legend_x = image.width + 15
        #         legend_y = (i + 1) * self.font_size + 50  # approximate y position in legend
        
        #         color = self.color_manager.get_color(entity_id)
        #         color_rgba = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (140,)  
        #         draw.line([legend_x, legend_y, centroid_x - image.width / 2 + 100, centroid_y - image.height / 2 + 160], fill=color_rgba, width=5)
        
        self.image = combined_image

        return self.image

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
        elif filter_type == "specifictribe":
            top_entities = self.tribe_df[self.tribe_df['tag'].isin(self.tribe_list)].head(top_n)
            filter_type = "tribeid"
        elif filter_type == "specificplayer":
            top_entities = self.player_df[self.player_df['name'].isin(self.player_list)].head(top_n)
            filter_type = "playerid"
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
                fill_color = (color_rgba[0], color_rgba[1], color_rgba[2], 40)
                draw.polygon(polygon, outline=color, fill=fill_color)

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
        elif filter_type == "specifictribe":
            top_entities = self.tribe_df[self.tribe_df['tag'].isin(self.tribe_list)].head(top_n)
            filter_type = "tribeid"
        elif filter_type == "specificplayer":
            top_entities = self.player_df[self.player_df['name'].isin(self.player_list)].head(top_n)
            filter_type = "playerid"
        else:
            raise ValueError("Invalid filter_type. Expected 'playerid' or 'tribeid'.")

        # If total villages are less than 20, skip drawing
        if len(village_df) < 20:
            return self.image
            
        draw = ImageDraw.Draw(self.image, 'RGBA')

        # Calculate village counts for all entities to determine font scaling
        village_counts = {}
        for _, entity in top_entities.iterrows():
            entity_id = entity[filter_type]
            entity_villages = village_df[village_df[filter_type] == entity_id]
            village_counts[entity_id] = len(entity_villages)
        
        # Get max and min village counts for scaling
        if village_counts:
            max_villages = max(village_counts.values())
            min_villages = min(village_counts.values())
        else:
            max_villages = min_villages = 1

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
            else:
                continue
            
            # Calculate scaled font size based on village count
            village_count = village_counts[entity_id]
            if max_villages > min_villages:
                # Scale font size from 100% to 200% of base font size (smaller tribes stay normal, bigger get larger)
                scale_factor = 1.0 + (village_count - min_villages) / (max_villages - min_villages)
            else:
                scale_factor = 1.0
            
            scaled_font_size = int(self.font_size * scale_factor)
            scaled_font = ImageFont.truetype("twmap/map/fonts/Roboto_Condensed-Bold.ttf", scaled_font_size)
            
            # Draw the name at the centroid
            name = urllib.parse.unquote_plus(entity['name'])
            # Scale outline offset based on font size
            outline_offset = max(2, int(4 * scale_factor))
            for dx in [-outline_offset, 0, outline_offset]:
                for dy in [-outline_offset, 0, outline_offset]:
                    if dx != 0 or dy != 0:
                        draw.text((centroid_x + dx, centroid_y + dy), name, fill=(0, 0, 0, 255), font=scaled_font, anchor="mm")
            
            draw.text((centroid_x, centroid_y), name, fill=fill_color, font=scaled_font, anchor="mm")

            # save the centroid coordinates
            self.entity_centroids[entity_id] = (centroid_x, centroid_y)
            print("Entity id: ", entity_id)

        return self.image

if __name__ == "__main__":
    from twmap.snapshot.datafilter import DataFilter
    from twmap.snapshot.dataloader import DataLoader
    from twmap.world.world_loader import WorldLoader
    
    world_loader = WorldLoader(world="146", server="en", init_load=False)

    def extract_s3_key(s3_path: str) -> str:
        if s3_path.startswith('s3://'):
            # Remove s3://bucket-name/ prefix
            parts = s3_path.split('/', 3)
            return parts[3] if len(parts) > 3 else s3_path
        return s3_path

    data_loader = DataLoader(world_loader=world_loader)

    tribe_df, player_df, village_df, conquer_df = data_loader.load_specific_files(
        ally_path=extract_s3_key("s3://tribalwars-scraped/en146/ally_en146_20250930_221509.txt"),
        player_path=extract_s3_key("s3://tribalwars-scraped/en146/player_en146_20250930_221503.txt"),
        village_path=extract_s3_key("s3://tribalwars-scraped/en146/village_en146_20250930_221458.txt"),
        conquer_path=extract_s3_key("s3://tribalwars-scraped/en146/conquer_en146_20250930_221515.txt")
    )

    data_filter = DataFilter(village_df, player_df, tribe_df, conquer_df)

    map = Map(data_filter, max_coords=750)
    top_players_image = map.draw_top_players(center_text=True)
    top_players_image = map.crop_image(top_players_image)
    top_players_image_with_legend = map.draw_legend(top_type="players")
    top_players_image_with_legend.show()

    top_tribes_image = map.draw_top_tribes(zones_of_control=False, center_text=True)
    top_tribes_image = map.crop_image(top_tribes_image)
    top_tribes_image_with_legend = map.draw_legend(top_type="tribes")
    top_tribes_image_with_legend.show()
