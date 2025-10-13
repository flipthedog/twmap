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
        
        image = self.crop_image(image)

        if self.add_watermark:  
            image = self.watermark("SirolfR")
        
        if self.add_current_date_time:
            image = self.add_current_date_time()
        
        draw = ImageDraw.Draw(image)

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
        draw.rectangle([0, 0, 550, (len(ids) + 1) * self.font_size], fill="#000000")

        if specific:
            draw.text((0, 0), "Tribe Legend", fill=self.tw_color, font=self.font, anchor="lt")
            
            for i in range(0, len(ids)):
                id = ids[i]
                draw.text((50, (i + 1) * self.font_size), f"{i + 1}. {urllib.parse.unquote_plus(names[i])}", fill=self.tw_color, font=self.font, anchor="lt")
                draw.rectangle([0, (i + 1) * self.font_size, 20, (i + 1) * self.font_size + 20], fill=self.color_manager.get_color(id))
        else:
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

    def draw_influence_zones(self, village_df: DataFrame, top_n: int = 10, filter_type: str = "playerid", zone_type: str = "voronoi"):
        """
        Draw advanced zones of control with multiple visualization options.
        
        Args:
            village_df (DataFrame): DataFrame containing the villages
            top_n (int): Number of top entities to draw zones for
            filter_type (str): Column to filter on ('playerid' or 'tribeid')
            zone_type (str): Type of zone ('voronoi', 'gradient', 'clusters', 'borders')
        """
        import numpy as np
        from scipy.spatial import Voronoi, voronoi_plot_2d
        from scipy.spatial.distance import cdist
        
        if filter_type == "playerid":
            top_entities = self.t10_players.head(top_n)
        elif filter_type == "tribeid":
            top_entities = self.t10_tribes.head(top_n)
        else:
            # Handle specific cases...
            pass
        
        draw = ImageDraw.Draw(self.image, 'RGBA')
        
        if zone_type == "voronoi":
            # Voronoi diagram based on village centroids
            all_centroids = []
            entity_colors = {}
            
            for _, entity in top_entities.iterrows():
                entity_id = entity[filter_type]
                entity_villages = village_df[village_df[filter_type] == entity_id]
                if not entity_villages.empty:
                    village_coords = entity_villages[['x_coord', 'y_coord']].values
                    centroid = village_coords.mean(axis=0)
                    all_centroids.append(centroid)
                    entity_colors[len(all_centroids)-1] = self.color_manager.get_color(entity_id)
            
            if len(all_centroids) > 2:
                vor = Voronoi(all_centroids)
                self._draw_voronoi_cells(draw, vor, entity_colors)
        
        elif zone_type == "gradient":
            # Influence gradient based on distance to villages
            self._draw_influence_gradient(draw, village_df, top_entities, filter_type)
        
        elif zone_type == "clusters":
            # K-means clustering with territory marking
            self._draw_cluster_territories(draw, village_df, top_entities, filter_type)
        
        elif zone_type == "borders":
            # Animated/pulsing borders around territories
            self._draw_animated_borders(draw, village_df, top_entities, filter_type)
        
        return self.image

    def draw_heat_map_influence(self, village_df: DataFrame, top_n: int = 10, filter_type: str = "playerid"):
        """
        Create a heat map showing influence zones based on village density and proximity.

        This is cool
        """
        import numpy as np
        from scipy.ndimage import gaussian_filter
        
        # Create influence grid
        grid_size = 200
        influence_grid = np.zeros((grid_size, grid_size, 3))  # RGB channels
        
        if filter_type == "playerid":
            top_entities = self.t10_players.head(top_n)
        else:
            top_entities = self.t10_tribes.head(top_n)
        
        for _, entity in top_entities.iterrows():
            entity_id = entity[filter_type]
            entity_villages = village_df[village_df[filter_type] == entity_id]
            
            if entity_villages.empty:
                continue
                
            # Get color
            color = self.color_manager.get_color(entity_id)
            rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            # Add influence for each village
            for _, village in entity_villages.iterrows():
                # Map coordinates to grid
                grid_x = int((village['x_coord'] / self.world_width) * grid_size)
                grid_y = int((village['y_coord'] / self.world_height) * grid_size)
                
                if 0 <= grid_x < grid_size and 0 <= grid_y < grid_size:
                    # Add weighted influence (could be based on village points)
                    weight = 1.0  # Could use village points here
                    influence_grid[grid_y, grid_x] += np.array(rgb) * weight
        
        # Apply Gaussian blur for smooth influence zones
        for channel in range(3):
            influence_grid[:, :, channel] = gaussian_filter(influence_grid[:, :, channel], sigma=5)
        
        # Normalize and convert to image
        max_val = np.max(influence_grid)
        if max_val > 0:
            influence_grid = (influence_grid / max_val * 255).astype(np.uint8)
        
        # Create overlay image
        heat_map = Image.fromarray(influence_grid, 'RGB')
        heat_map = heat_map.resize((self.image_width, self.image_height))
        
        # Blend with existing image
        self.image = Image.blend(self.image, heat_map, alpha=0.5)
        
        return self.image

    def draw_territorial_networks(self, village_df: DataFrame, top_n: int = 10, filter_type: str = "playerid"):
        """
        Draw network connections between allied territories or show expansion patterns.
        """
        draw = ImageDraw.Draw(self.image, 'RGBA')
        
        if filter_type == "playerid":
            top_entities = self.t10_players.head(top_n)
        else:
            top_entities = self.t10_tribes.head(top_n)
        
        # Get recent conquers to show expansion directions
        recent_conquers = self.data_filter.get_past_day_conquers()
        
        # Check if the required column exists in the DataFrame
        conquer_column = f'new_{filter_type}'
        if conquer_column not in recent_conquers.columns:
            logging.warning(f"Column '{conquer_column}' not found in conquers DataFrame. Available columns: {list(recent_conquers.columns)}")
            return self.image
        
        for _, entity in top_entities.iterrows():
            entity_id = entity[filter_type]
            entity_villages = village_df[village_df[filter_type] == entity_id]
            entity_conquers = recent_conquers[recent_conquers[conquer_column] == entity_id]
            
            if entity_villages.empty:
                continue
                
            color = self.color_manager.get_color(entity_id)
            
            # Draw expansion arrows/lines
            for _, conquer in entity_conquers.iterrows():
                # Find nearest village to show expansion direction
                conquer_x = conquer['x_coord'] * (self.cell_size + self.spacing)
                conquer_y = conquer['y_coord'] * (self.cell_size + self.spacing)
                
                # Find closest existing village
                distances = []
                for _, village in entity_villages.iterrows():
                    village_x = village['x_coord'] * (self.cell_size + self.spacing)
                    village_y = village['y_coord'] * (self.cell_size + self.spacing)
                    dist = ((conquer_x - village_x)**2 + (conquer_y - village_y)**2)**0.5
                    distances.append((dist, village_x, village_y))
                
                if distances:
                    _, closest_x, closest_y = min(distances)
                    # Draw expansion line
                    draw.line([(closest_x, closest_y), (conquer_x, conquer_y)], 
                            fill=color, width=2)
                    # Draw arrow head
                    self._draw_arrow_head(draw, closest_x, closest_y, conquer_x, conquer_y, color)
        
        return self.image

    def _draw_arrow_head(self, draw, start_x, start_y, end_x, end_y, color):
        """Helper function to draw arrow heads for expansion lines."""
        import math
        
        # Calculate arrow direction
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return
        
        # Normalize direction
        dx /= length
        dy /= length
        
        # Arrow head size
        head_length = 10
        head_angle = 0.5
        
        # Calculate arrow head points
        head_x1 = end_x - head_length * (dx * math.cos(head_angle) + dy * math.sin(head_angle))
        head_y1 = end_y - head_length * (dy * math.cos(head_angle) - dx * math.sin(head_angle))
        head_x2 = end_x - head_length * (dx * math.cos(head_angle) - dy * math.sin(head_angle))
        head_y2 = end_y - head_length * (dy * math.cos(head_angle) + dx * math.sin(head_angle))
        
        # Draw arrow head
        draw.polygon([(end_x, end_y), (head_x1, head_y1), (head_x2, head_y2)], fill=color)

    def _draw_voronoi_cells(self, draw, voronoi, entity_colors):
        """Draw Voronoi diagram cells for territory visualization."""
        import numpy as np
        
        # Draw finite Voronoi regions
        for region_idx, region in enumerate(voronoi.regions):
            if not region or -1 in region:
                continue
                
            # Get polygon vertices
            polygon = [voronoi.vertices[i] for i in region]
            if len(polygon) < 3:
                continue
                
            # Convert to screen coordinates
            screen_polygon = []
            for vertex in polygon:
                x = vertex[0] * (self.cell_size + self.spacing)
                y = vertex[1] * (self.cell_size + self.spacing)
                screen_polygon.append((x, y))
            
            # Find which entity this region belongs to
            color = None
            for point_idx, ridge in enumerate(voronoi.point_region):
                if ridge == region_idx and point_idx in entity_colors:
                    color = entity_colors[point_idx]
                    break
            
            if color:
                color_rgba = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                fill_color = (color_rgba[0], color_rgba[1], color_rgba[2], 30)
                draw.polygon(screen_polygon, outline=color, fill=fill_color)

    def _draw_influence_gradient(self, draw, village_df, top_entities, filter_type):
        """Draw influence gradient zones based on distance to villages."""
        import numpy as np
        from scipy.spatial.distance import cdist
        
        # Create a grid for calculating influence
        grid_resolution = 100
        x_coords = np.linspace(0, self.world_width, grid_resolution)
        y_coords = np.linspace(0, self.world_height, grid_resolution)
        
        for _, entity in top_entities.iterrows():
            entity_id = entity[filter_type]
            entity_villages = village_df[village_df[filter_type] == entity_id]
            
            if entity_villages.empty:
                continue
                
            color = self.color_manager.get_color(entity_id)
            color_rgba = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            village_coords = entity_villages[['x_coord', 'y_coord']].values
            
            # Calculate influence at grid points
            for i, x in enumerate(x_coords[:-1]):
                for j, y in enumerate(y_coords[:-1]):
                    grid_point = np.array([[x, y]])
                    distances = cdist(grid_point, village_coords)
                    min_distance = np.min(distances)
                    
                    # Influence decreases with distance (max influence radius = 50)
                    if min_distance < 50:
                        influence = max(0, (50 - min_distance) / 50)
                        alpha = int(influence * 80)  # Max alpha of 80
                        
                        # Draw influence rectangle
                        x1 = x * (self.cell_size + self.spacing)
                        y1 = y * (self.cell_size + self.spacing)
                        x2 = x_coords[i+1] * (self.cell_size + self.spacing)
                        y2 = y_coords[j+1] * (self.cell_size + self.spacing)
                        
                        fill_color = (color_rgba[0], color_rgba[1], color_rgba[2], alpha)
                        draw.rectangle([x1, y1, x2, y2], fill=fill_color)

    def _draw_cluster_territories(self, draw, village_df, top_entities, filter_type):
        """Draw K-means clustering territories with advanced polygonal shapes."""
        import numpy as np
        from scipy.spatial import ConvexHull
        from scipy.spatial.distance import cdist
        
        for _, entity in top_entities.iterrows():
            entity_id = entity[filter_type]
            entity_villages = village_df[village_df[filter_type] == entity_id]
            
            if len(entity_villages) < 4:  # Need at least 4 villages for meaningful clusters
                continue
                
            color = self.color_manager.get_color(entity_id)
            color_rgba = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            village_coords = entity_villages[['x_coord', 'y_coord']].values
            
            # Determine number of clusters (max 3, min 1)
            n_clusters = min(3, max(1, len(entity_villages) // 10))
            
            if n_clusters > 1:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(village_coords)
                
                # Draw improved shapes for each cluster
                for cluster_id in range(n_clusters):
                    cluster_villages = village_coords[cluster_labels == cluster_id]
                    if len(cluster_villages) < 3:
                        continue
                    
                    try:
                        # Option 1: Convex Hull for natural territory boundaries
                        hull = ConvexHull(cluster_villages)
                        
                        # Expand hull points outward for better visual coverage
                        hull_points = cluster_villages[hull.vertices]
                        center = cluster_villages.mean(axis=0)
                        
                        # Expand each hull point away from center by 15%
                        expanded_points = []
                        for point in hull_points:
                            direction = point - center
                            expanded_point = point + direction
                            expanded_points.append(expanded_point)
                        
                        # Convert to screen coordinates
                        polygon = []
                        for point in expanded_points:
                            x = point[0] * (self.cell_size + self.spacing)
                            y = point[1] * (self.cell_size + self.spacing)
                            polygon.append((x, y))
                        
                        # Draw the cluster territory
                        fill_color = (color_rgba[0], color_rgba[1], color_rgba[2], 30)
                        draw.polygon(polygon, outline=color, fill=fill_color, width=3)
                        
                        # Add cluster center marker
                        center_x = center[0] * (self.cell_size + self.spacing)
                        center_y = center[1] * (self.cell_size + self.spacing)
                        marker_size = 6
                        draw.ellipse([center_x - marker_size, center_y - marker_size,
                                    center_x + marker_size, center_y + marker_size],
                                   fill=color, outline=(255, 255, 255, 200), width=2)
                        
                    except Exception:
                        # Fallback: Draw alpha shape or buffered points
                        center = cluster_villages.mean(axis=0)
                        
                        # Create a more organic shape by connecting outer points
                        distances = cdist([center], cluster_villages)[0]
                        outer_indices = np.where(distances > np.percentile(distances, 60))[0]
                        
                        if len(outer_indices) >= 3:
                            outer_points = cluster_villages[outer_indices]
                            
                            # Sort points by angle from center for proper polygon
                            angles = np.arctan2(outer_points[:, 1] - center[1], 
                                              outer_points[:, 0] - center[0])
                            sorted_indices = np.argsort(angles)
                            outer_points = outer_points[sorted_indices]
                            
                            # Convert to screen coordinates and draw
                            polygon = []
                            for point in outer_points:
                                x = point[0] * (self.cell_size + self.spacing)
                                y = point[1] * (self.cell_size + self.spacing)
                                polygon.append((x, y))
                            
                            fill_color = (color_rgba[0], color_rgba[1], color_rgba[2], 25)
                            draw.polygon(polygon, outline=color, fill=fill_color, width=2)

    def _draw_animated_borders(self, draw, village_df, top_entities, filter_type):
        """Draw animated/pulsing borders around territories."""
        import numpy as np
        from scipy.spatial import ConvexHull
        
        for _, entity in top_entities.iterrows():
            entity_id = entity[filter_type]
            entity_villages = village_df[village_df[filter_type] == entity_id]
            
            if len(entity_villages) < 3:
                continue
                
            color = self.color_manager.get_color(entity_id)
            
            village_coords = entity_villages[['x_coord', 'y_coord']].values
            
            try:
                hull = ConvexHull(village_coords)
                
                # Create multiple border lines for pulsing effect
                for offset in [0, 3, 6]:
                    polygon = []
                    for vertex in hull.vertices:
                        x = village_coords[vertex, 0] * (self.cell_size + self.spacing) + offset
                        y = village_coords[vertex, 1] * (self.cell_size + self.spacing) + offset
                        polygon.append((x, y))
                    
                    # Different alpha for each border line
                    alpha = max(50, 150 - offset * 15)
                    color_rgba = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                    border_color = (color_rgba[0], color_rgba[1], color_rgba[2], alpha)
                    
                    # Draw dashed border effect
                    for i in range(len(polygon)):
                        start = polygon[i]
                        end = polygon[(i + 1) % len(polygon)]
                        
                        # Draw dashed line
                        self._draw_dashed_line(draw, start, end, border_color, 3, 10)
                        
            except Exception:
                # If ConvexHull fails, skip this entity
                continue

    def _draw_dashed_line(self, draw, start, end, color, width, dash_length):
        """Helper function to draw dashed lines."""
        import math
        
        x1, y1 = start
        x2, y2 = end
        
        # Calculate line length and direction
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        
        if length == 0:
            return
            
        # Normalize direction
        dx /= length
        dy /= length
        
        # Draw dashed line
        current_pos = 0
        while current_pos < length:
            # Draw dash
            dash_start_x = x1 + dx * current_pos
            dash_start_y = y1 + dy * current_pos
            dash_end_pos = min(current_pos + dash_length, length)
            dash_end_x = x1 + dx * dash_end_pos
            dash_end_y = y1 + dy * dash_end_pos
            
            draw.line([(dash_start_x, dash_start_y), (dash_end_x, dash_end_y)], 
                     fill=color, width=width)
            
            # Move to next dash (skip gap)
            current_pos += dash_length * 2

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

        return self.image

    def draw_advanced_zones(self, village_df: DataFrame, top_n: int = 10, filter_type: str = "playerid", 
                           show_voronoi: bool = True, show_gradient: bool = False, 
                           show_clusters: bool = False, show_borders: bool = False):
        """
        Draw multiple zone visualization techniques combined.
        
        Args:
            village_df (DataFrame): DataFrame containing the villages
            top_n (int): Number of top entities to draw zones for
            filter_type (str): Column to filter on ('playerid' or 'tribeid')
            show_voronoi (bool): Show Voronoi diagram zones
            show_gradient (bool): Show influence gradient zones
            show_clusters (bool): Show cluster territories
            show_borders (bool): Show animated borders
        """
        if show_gradient:
            self.draw_influence_zones(village_df, top_n, filter_type, "gradient")
        
        if show_voronoi:
            self.draw_influence_zones(village_df, top_n, filter_type, "voronoi")
        
        if show_clusters:
            self.draw_influence_zones(village_df, top_n, filter_type, "clusters")
        
        if show_borders:
            self.draw_influence_zones(village_df, top_n, filter_type, "borders")
        
        return self.image

    def draw_battle_indicators(self, village_df: DataFrame, conquer_df: DataFrame = None):
        """
        Draw battle indicators showing recent conquers and conflicts.
        """
        draw = ImageDraw.Draw(self.image, 'RGBA')
        
        if conquer_df is None:
            conquer_df = self.data_filter.get_past_day_conquers()
        
        # Draw conquest indicators
        for _, conquer in conquer_df.iterrows():
            x = conquer['x_coord'] * (self.cell_size + self.spacing)
            y = conquer['y_coord'] * (self.cell_size + self.spacing)
            
            # Draw explosion/battle effect
            for radius in [8, 12, 16]:
                alpha = max(30, 120 - radius * 5)
                battle_color = (255, 100, 100, alpha)  # Red battle indicator
                
                draw.ellipse([x - radius, y - radius, x + radius, y + radius], 
                           fill=battle_color, outline=(255, 0, 0, 200))
        
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

    map = Map(data_filter, max_coords=700)
    top_players_image = map.draw_top_players(center_text=True)
    top_players_image.show()

    top_tribes_image = map.draw_top_tribes(zones_of_control=True, center_text=True)
    top_tribes_image.show()