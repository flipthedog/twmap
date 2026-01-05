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

    def draw_war_legend(self, window_days: int = 3, top_pairs: int = 10, top_tribes: int = 10, image: Image = None):
        """Render a styled war legend, matching the aesthetics of other legends."""
        war_stats = self.data_filter.get_tribe_war_overview(window_days=window_days)
        pairwise = war_stats.get("pairwise", pd.DataFrame())
        totals = war_stats.get("totals", pd.DataFrame())


        if image is None:
            image = self.image

        legend_width = 1000
        legend_image = Image.new("RGBA", (legend_width, image.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(legend_image)

        if (pairwise is None or pairwise.empty) and (totals is None or totals.empty):
            logging.info("No war statistics available to draw war legend.")
            # Still combine the images, just show an empty legend
            combined_width = image.width + legend_image.width
            combined_image = Image.new("RGBA", (combined_width, image.height))
            combined_image.paste(image, (0, 0))
            combined_image.paste(legend_image, (image.width, 0))
            self.image = combined_image
            return self.image

        draw.rectangle([0, 0, legend_width, image.height], fill="#000000")

        title_font_size = int(self.font_size * 1.6)
        title_font = ImageFont.truetype("twmap/map/fonts/Roboto_Condensed-Bold.ttf", title_font_size)
        subtitle_font = ImageFont.truetype("twmap/map/fonts/Roboto_Condensed-Bold.ttf", int(self.font_size * 1.1))

        draw.text((legend_width // 2, 40), f"War Overview - last {window_days} days", fill=self.tw_color, font=title_font, anchor="mt")
        draw.line([40, 100, legend_width - 40, 100], fill=self.tw_color, width=3)

        section_padding = 40
        y_offset = 120

        rank_x = section_padding
        winner_x = rank_x + 90
        gain_x = winner_x + 280
        target_x = gain_x + 175
        time_x = legend_width - section_padding - 160
        row_height = self.font_size + 18

        if pairwise is not None and not pairwise.empty:
            draw.text((section_padding, y_offset), "Top Tribe Gains", fill=self.tw_color, font=subtitle_font, anchor="lt")
            y_offset += self.font_size + 20

            header_y = y_offset
            draw.text((rank_x, header_y), "#", fill=self.tw_color, font=self.font, anchor="lt")
            draw.text((winner_x, header_y), "Winner", fill=self.tw_color, font=self.font, anchor="lt")
            draw.text((gain_x, header_y), "+Villages", fill=self.tw_color, font=self.font, anchor="lt")
            draw.text((target_x, header_y), "From", fill=self.tw_color, font=self.font, anchor="lt")
            y_offset += self.font_size + 10

            for rank, (_, row) in enumerate(pairwise.head(top_pairs).iterrows(), start=1):
                attacker_tag = urllib.parse.unquote_plus(str(row.get("new_tribe_tag", "?")))
                defender_tag = urllib.parse.unquote_plus(str(row.get("old_tribe_tag", "?")))
                gained = int(row.get("villages_taken", 0))
                color = self.color_manager.get_color_without_force(row.get("new_tribeid"))

                draw.rectangle([rank_x, y_offset + 5, rank_x + 20, y_offset + self.font_size + 5], fill=color)
                draw.text((rank_x + 30, y_offset + self.font_size / 2 + 5), f"{rank}", fill=self.tw_color, font=self.font, anchor="lm")
                draw.text((winner_x, y_offset), f"[{attacker_tag}]", fill=color, font=self.font, anchor="lt")
                draw.text((gain_x, y_offset), f"+{gained}", fill=self.tw_color, font=self.font, anchor="lt")
                draw.text((target_x, y_offset), f"[{defender_tag}]", fill=self.color_manager.get_color_without_force(row.get("old_tribeid")), font=self.font, anchor="lt")
                y_offset += row_height

            y_offset += 30

        if totals is not None and not totals.empty:
            draw.text((section_padding, y_offset), "Net Village Change", fill=self.tw_color, font=subtitle_font, anchor="lt")
            y_offset += self.font_size + 20

            header_y = y_offset
            draw.text((rank_x, header_y), "#", fill=self.tw_color, font=self.font, anchor="lt")
            draw.text((winner_x, header_y), "Tribe", fill=self.tw_color, font=self.font, anchor="lt")
            draw.text((gain_x, header_y), "Net", fill=self.tw_color, font=self.font, anchor="lt")
            draw.text((target_x, header_y), "Gained", fill=self.tw_color, font=self.font, anchor="lt")
            draw.text((time_x, header_y), "Lost", fill=self.tw_color, font=self.font, anchor="lt")
            y_offset += self.font_size + 10

            for rank, (_, row) in enumerate(totals.head(top_tribes).iterrows(), start=1):
                tribe_tag = urllib.parse.unquote_plus(str(row.get("tribe_tag", "?")))
                gained = int(row.get("villages_gained", 0))
                lost = int(row.get("villages_lost", 0))
                net = int(row.get("net_villages", 0))
                color = self.color_manager.get_color_without_force(row.get("tribeid"))

                draw.rectangle([rank_x, y_offset + 5, rank_x + 20, y_offset + self.font_size + 5], fill=color)
                draw.text((rank_x + 30, y_offset + self.font_size / 2 + 5), f"{rank}", fill=self.tw_color, font=self.font, anchor="lm")
                draw.text((winner_x, y_offset), f"[{tribe_tag}]", fill=color, font=self.font, anchor="lt")
                draw.text((gain_x, y_offset), f"{net:+}", fill=self.tw_color, font=self.font, anchor="lt")
                draw.text((target_x, y_offset), f"{gained}", fill=self.tw_color, font=self.font, anchor="lt")
                draw.text((time_x, y_offset), f"{lost}", fill=self.tw_color, font=self.font, anchor="lt")
                y_offset += row_height

        combined_width = image.width + legend_image.width
        combined_image = Image.new("RGBA", (combined_width, image.height))
        combined_image.paste(image, (0, 0))
        combined_image.paste(legend_image, (image.width, 0))

        self.image = combined_image

        return self.image

    def draw_graph(self, top_type: str = "players", graph_type: str = "points", specific: bool = False, legend_width: int = 1000):
        """Draw a graph of a specific statistic for the top players or tribes.

        Supported graphs:
        - points (top 10 by points)
        - killall (opponents defeated, colored by points ranking)
        - villages (village counts of the top 10)
        - conquers (past 72h conquers of the top 10)
        """

        # Base list of top entities by points (used for colors and labels)
        if top_type == "players":
            if specific:
                base_ids = self.player_df[self.player_df['name'].isin(self.player_list)]['playerid'].tolist()
                base_names = self.player_df[self.player_df['name'].isin(self.player_list)]['name'].tolist()
                base_points = self.player_df[self.player_df['name'].isin(self.player_list)]['points'].tolist()
                base_tags = None
            else:
                base_ids = self.t10_players['playerid'].to_list()
                base_names = self.t10_players['name'].to_list()
                base_points = self.t10_players['points'].to_list()
                base_tags = None
        elif top_type == "tribes":
            if specific:
                base_ids = self.tribe_df[self.tribe_df['tribeid'].isin(self.tribe_list)]['tribeid'].tolist()
                base_names = self.tribe_df[self.tribe_df['tribeid'].isin(base_ids)]['name'].tolist()
                base_tags = self.tribe_df[self.tribe_df['tribeid'].isin(base_ids)]['tag'].tolist()
                base_points = self.tribe_df[self.tribe_df['tribeid'].isin(base_ids)]['points'].tolist()
            else:
                base_ids = self.t10_tribes['tribeid'].to_list()
                base_names = self.t10_tribes['name'].to_list()
                base_tags = self.t10_tribes['tag'].to_list()
                base_points = self.t10_tribes['tribe_points'].to_list()
        else:
            raise ValueError("Invalid top_type. Expected 'players' or 'tribes'.")

        # Precompute point-colors so other graphs can borrow the same palette
        point_color_lookup = {pid: self.color_manager.get_color(pid) for pid in base_ids}

        graph_items = []  # list of {id, name, value, color}
        title = ""

        if graph_type == "points":
            title = f"Top {top_type.capitalize()} Points - {self.data_filter.world_id}"
            for idx, pid in enumerate(base_ids):
                if top_type == "tribes":
                    raw_name = f"{urllib.parse.unquote_plus(base_names[idx])} [{urllib.parse.unquote_plus(base_tags[idx])}]"
                else:
                    raw_name = urllib.parse.unquote_plus(base_names[idx])
                graph_items.append({
                    "id": pid,
                    "name": raw_name,
                    "value": base_points[idx],
                    "color": point_color_lookup.get(pid)
                })

        elif graph_type == "killall":
            title = f"Opponents Defeated - {self.data_filter.world_id}"
            if top_type == "players":
                kill_df = self.data_filter.get_top_10_killall_players()
                for row in kill_df.itertuples(index=False):
                    pid = getattr(row, "playerid")
                    name_val = urllib.parse.unquote_plus(getattr(row, "name"))
                    defeated = int(getattr(row, "units_defeated", 0))
                    color = point_color_lookup.get(pid, self.color_manager.get_color_without_force(pid))
                    graph_items.append({"id": pid, "name": name_val, "value": defeated, "color": color})
            else:
                kill_df = self.data_filter.get_top_10_killall_tribes()
                for row in kill_df.itertuples(index=False):
                    tid = getattr(row, "tribeid")
                    name_val = urllib.parse.unquote_plus(getattr(row, "name")) if hasattr(row, "name") else urllib.parse.unquote_plus(getattr(row, "tag"))
                    tag_val = urllib.parse.unquote_plus(getattr(row, "tag")) if hasattr(row, "tag") else ""
                    defeated = int(getattr(row, "units_defeated", 0))
                    display_name = f"{name_val} [{tag_val}]" if tag_val else name_val
                    color = point_color_lookup.get(tid, self.color_manager.get_color_without_force(tid))
                    graph_items.append({"id": tid, "name": display_name, "value": defeated, "color": color})
            graph_items.sort(key=lambda x: x["value"], reverse=True)

        elif graph_type == "villages":
            title = f"Villages - Top {top_type.capitalize()}"
            if top_type == "players":
                village_counts = self.data_filter.get_t10_player_villages()["playerid"].value_counts()
                for idx, pid in enumerate(base_ids):
                    raw_name = urllib.parse.unquote_plus(base_names[idx])
                    graph_items.append({
                        "id": pid,
                        "name": raw_name,
                        "value": int(village_counts.get(pid, 0)),
                        "color": point_color_lookup.get(pid)
                    })
            else:
                village_counts = self.data_filter.get_t10_tribe_villages()["tribeid"].value_counts()
                for idx, tid in enumerate(base_ids):
                    raw_name = f"{urllib.parse.unquote_plus(base_names[idx])} [{urllib.parse.unquote_plus(base_tags[idx])}]"
                    graph_items.append({
                        "id": tid,
                        "name": raw_name,
                        "value": int(village_counts.get(tid, 0)),
                        "color": point_color_lookup.get(tid)
                    })
            graph_items.sort(key=lambda x: x["value"], reverse=True)

        elif graph_type == "conquers":
            title = f"Conquers (72h) - Top {top_type.capitalize()}"
            if top_type == "players":
                conquers_df = self.data_filter.get_past_day_t10_conquers_players()
                counts = conquers_df["playerid"].value_counts() if not conquers_df.empty else {}
                for idx, pid in enumerate(base_ids):
                    raw_name = urllib.parse.unquote_plus(base_names[idx])
                    graph_items.append({
                        "id": pid,
                        "name": raw_name,
                        "value": int(counts.get(pid, 0)),
                        "color": point_color_lookup.get(pid)
                    })
            else:
                conquers_df = self.data_filter.get_past_day_t10_conquers_tribes()
                counts = conquers_df["tribeid"].value_counts() if not conquers_df.empty else {}
                for idx, tid in enumerate(base_ids):
                    raw_name = f"{urllib.parse.unquote_plus(base_names[idx])} [{urllib.parse.unquote_plus(base_tags[idx])}]"
                    graph_items.append({
                        "id": tid,
                        "name": raw_name,
                        "value": int(counts.get(tid, 0)),
                        "color": point_color_lookup.get(tid)
                    })
            graph_items.sort(key=lambda x: x["value"], reverse=True)

        else:
            raise ValueError("Invalid graph_type. Expected 'points', 'killall', 'villages', or 'conquers'.")

        item_count = len(graph_items)
        graph_height = max(450, (item_count + 2) * self.font_size + 75)
        graph = Image.new("RGBA", (legend_width, graph_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(graph)

        title_font_size = int(self.font_size * 1.6)
        title_font = ImageFont.truetype("twmap/map/fonts/Roboto_Condensed-Bold.ttf", title_font_size)
        title_y = 10
        draw.text((legend_width // 2, title_y), title, fill=self.tw_color, font=title_font, anchor="mt")

        line_y = title_y + title_font_size + 8
        draw.line([30, line_y, legend_width - 30, line_y], fill=self.tw_color, width=3)

        max_value = max((item["value"] for item in graph_items), default=1)

        # column layout: rank | name | value | bar
        rank_x = 40
        name_x = 100
        points_x = 520
        bar_left = 820
        bar_right = legend_width - 40
        bar_max_width = max(1, bar_right - bar_left)
        bar_height = int(self.font_size * 0.8)

        base_y = line_y + 8

        for i, item in enumerate(graph_items):
            row_y = base_y + i * self.font_size
            bar_top = row_y + int(self.font_size * 0.2)
            bar_bottom = bar_top + bar_height

            color = item.get("color", self.tw_color)
            draw.rectangle([10, row_y, 30, row_y + 40], fill=color)
            draw.text((rank_x, row_y), f"{i + 1}.", fill=self.tw_color, font=self.font, anchor="lt")

            raw_name = item["name"]
            max_name_len = 18
            name_text = raw_name if len(raw_name) <= max_name_len else raw_name[:max_name_len - 3] + "..."
            draw.text((name_x, row_y), name_text, fill=color, font=self.font, anchor="lt")

            value_label = f"{item['value']:,}"
            draw.text((points_x, row_y), value_label, fill=self.tw_color, font=self.font, anchor="lt")

            draw.rectangle([bar_left, bar_top, bar_right, bar_bottom], fill="#1f1f1f")
            bar_width = int(bar_max_width * (item["value"] / max_value)) if max_value else 0
            if bar_width > 0:
                draw.rectangle([bar_left, bar_top, bar_left + bar_width, bar_bottom], fill=color)

        if item_count > 0:
            used_height = bar_bottom + 30
        else:
            used_height = line_y + self.font_size + 40
        used_height = min(used_height, graph.height)
        graph = graph.crop((0, 0, legend_width, used_height))

        return graph
    
    def draw_legend(self, top_type: str = "players", image: Image = None, specific: bool = False ):
        """Draw a stacked legend with all bar charts for the top players or tribes."""
        legend_width = 2000

        if image is None:
            image = self.image

        if self.add_watermark:  
            image = self.watermark("SirolfR")
        
        if self.add_current_date_time:
            image = self.add_current_date_time()

        # Build all graphs we want to show in order
        graphs = []

        graphs.extend([
            self.draw_graph(top_type=top_type, specific=specific, legend_width=legend_width, graph_type="points"),
            self.draw_graph(top_type=top_type, specific=specific, legend_width=legend_width, graph_type="killall"),
            self.draw_graph(top_type=top_type, specific=specific, legend_width=legend_width, graph_type="villages"),
            self.draw_graph(top_type=top_type, specific=specific, legend_width=legend_width, graph_type="conquers"),
        ])

        if top_type == "tribes":
            graphs.append(self.draw_dominance_bar(legend_width=legend_width))

        total_graph_height = sum(g.height for g in graphs)
        legend_height = max(image.height, total_graph_height)

        legend_image = Image.new("RGBA", (legend_width, legend_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(legend_image)
        draw.rectangle([0, 0, legend_width, legend_height], fill="#000000")

        current_y = 0
        for g in graphs:
            legend_image.paste(g, (0, current_y, g.width, current_y + g.height), g)
            current_y += g.height

        combined_width = image.width + legend_image.width
        combined_height = max(image.height, legend_height)
        combined_image = Image.new("RGBA", (combined_width, combined_height))
        combined_image.paste(image, (0, 0))
        combined_image.paste(legend_image, (image.width, 0))

        self.image = combined_image

        return self.image

    def get_dominance_summary(self):
        """Compute the current dominance leader and progress toward the 65% win condition."""
        total_villages = len(self.village_df)
        if total_villages == 0:
            return None

        villages_with_tribe = self.village_df.merge(
            self.player_df[["playerid", "tribeid"]], on="playerid", how="left"
        )

        tribe_counts = villages_with_tribe.dropna(subset=["tribeid"]).groupby("tribeid")["villageid"].count()
        if tribe_counts.empty:
            return None

        top_tribe_id = int(tribe_counts.idxmax())
        top_village_count = int(tribe_counts.loc[top_tribe_id])
        dominance_pct = (top_village_count / total_villages) * 100
        threshold_pct = 65.0

        tribe_row = self.tribe_df[self.tribe_df["tribeid"] == top_tribe_id]
        tribe_tag = urllib.parse.unquote_plus(tribe_row["tag"].iloc[0]) if not tribe_row.empty else "?"
        tribe_name = urllib.parse.unquote_plus(tribe_row["name"].iloc[0]) if not tribe_row.empty else ""

        return {
            "tribeid": top_tribe_id,
            "tribe_tag": tribe_tag,
            "tribe_name": tribe_name,
            "villages": top_village_count,
            "total": total_villages,
            "dominance_pct": dominance_pct,
            "threshold_pct": threshold_pct,
        }

    def draw_dominance_bar(self, legend_width: int = 1000):
        """Draw a progress bar showing the leading tribe's dominance toward 65%."""

        summary = self.get_dominance_summary()
        bar_height = 250
        graph = Image.new("RGBA", (legend_width, bar_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(graph)
        draw.rectangle([0, 0, legend_width, bar_height], fill="#000000")

        if summary is None:
            draw.text((legend_width // 2, bar_height // 2), "No tribe data to compute dominance", fill=self.tw_color, font=self.font, anchor="mm")
            return graph

        color = self.color_manager.get_color_without_force(summary["tribeid"])

        title_font = ImageFont.truetype("twmap/map/fonts/Roboto_Condensed-Bold.ttf", int(self.font_size * 1.4))
        draw.text((legend_width // 2, 24), "World Dominance", fill=self.tw_color, font=title_font, anchor="mt")

        tribe_label = f"Leading tribe: [{summary['tribe_tag']}] {summary['tribe_name']}".strip()
        draw.text((40, 90), tribe_label, fill=color, font=self.font, anchor="lt")

        progress_text = f"{summary['villages']:,}/{summary['total']:,} villages"
        draw.text((40, 150), progress_text, fill=self.tw_color, font=self.font, anchor="lt")

        bar_left = 40
        bar_right = legend_width - 40
        bar_top = 200
        bar_bottom = bar_top + 40
        draw.rectangle([bar_left, bar_top, bar_right, bar_bottom], outline=self.tw_color, fill="#1a1a1a")

        max_width = bar_right - bar_left
        fill_ratio = min(summary["dominance_pct"] / summary["threshold_pct"], 1.0)
        fill_width = int(max_width * fill_ratio)
        if fill_width > 0:
            draw.rectangle([bar_left, bar_top, bar_left + fill_width, bar_bottom], fill=color)

        draw.text((bar_right, bar_top - 10), f"{summary['threshold_pct']:.0f}% needed", fill=self.tw_color, font=self.font, anchor="rb")

        current_pct_label = f"{summary['dominance_pct']:.1f}%"
        label_x = bar_left + fill_width
        label_x = min(max(label_x, bar_left + 10), bar_right - 10)
        draw.text((label_x, bar_bottom + 8), current_pct_label, fill=self.tw_color, font=self.font, anchor="mt")

        if summary["dominance_pct"] >= summary["threshold_pct"]:
            draw.text((legend_width - 40, 80), "Threshold reached", fill=color, font=self.font, anchor="rt")

        return graph

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
            fill_color = (color_rgba[0], color_rgba[1], color_rgba[2], 255)
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
            # print("Entity id: ", entity_id)

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

    tribe_df, player_df, village_df, conquer_df, killall_df, killall_tribe_df, killatt_df, killdef_df, killtribeatt_df, killtribedef_df = data_loader.load_specific_files(
        ally_path=extract_s3_key("s3://tribalwars-scraped/en146/ally_en146_20250930_221509.txt"),
        player_path=extract_s3_key("s3://tribalwars-scraped/en146/player_en146_20250930_221503.txt"),
        village_path=extract_s3_key("s3://tribalwars-scraped/en146/village_en146_20250930_221458.txt"),
        conquer_path=extract_s3_key("s3://tribalwars-scraped/en146/conquer_en146_20250930_221515.txt"),
        killall_path=extract_s3_key("s3://tribalwars-scraped/en146/killall_en146_20250930_221537.txt"),
        killall_tribe_path=extract_s3_key("s3://tribalwars-scraped/en146/killalltribe_en146_20250930_221553.txt"),
        killatt_path=extract_s3_key("s3://tribalwars-scraped/en146/killatt_en146_20250930_221521.txt"),
        killdef_path=extract_s3_key("s3://tribalwars-scraped/en146/killdef_en146_20250930_221526.txt"),
        killtribeatt_path=extract_s3_key("s3://tribalwars-scraped/en146/killatttribe_en146_20250930_221542.txt"),
        killtribedef_path=extract_s3_key("s3://tribalwars-scraped/en146/killdeftribe_en146_20250930_221548.txt")
    )

    data_filter = DataFilter(village_df, player_df, tribe_df, conquer_df, killall_df, killall_tribe_df, killatt_df, killdef_df, killtribeatt_df, killtribedef_df)

    map = Map(data_filter, max_coords=750)
    top_players_image = map.draw_top_players(center_text=True)
    top_players_image = map.crop_image(top_players_image)
    top_players_image_with_legend = map.draw_legend(top_type="players")
    top_players_image_with_legend.show()

    top_tribes_image = map.draw_top_tribes(zones_of_control=False, center_text=True)
    top_tribes_image = map.crop_image(top_tribes_image)
    top_tribes_image_with_legend = map.draw_legend(top_type="tribes")
    top_tribes_image_with_war = map.draw_war_legend(window_days=3, top_pairs=10, top_tribes=10, image=top_tribes_image_with_legend)
    top_tribes_image_with_war.show()
