import logging 

from twmap.mapfactory import MapFactory
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

s3_paths = [
    "s3://tribalwars-scraped/en145/",
]

specific_tribes = [
    "Chess",
    "Dark",
    "Final1",
    "Anime",
    "LEGEND",
    "SPAG",
    "AVALON",
    "Rusty",
    "%7ECSM%7E",
    "Chesss",
    "Shadow",
    "Magnus",
    "PStar",
    "SPAGH",
    "Why%3F"
]

def generate_unique_hex_colors(n):
    colors = set()
    while len(colors) < n:
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        colors.add(color)
    return list(colors)

tribe_ids = [
    "83", "133", "44", "413", "102", "17", "77", "69", "351", 
    "169", "649", "242", "626", "175", "5"
]

unique_colors = generate_unique_hex_colors(len(tribe_ids))

custom_color_map_ids = dict(zip(tribe_ids, unique_colors))

MAX_IMAGES = None

start_time = datetime.now()

for s3_path in s3_paths:
    map_factory = MapFactory(s3_path, refresh=False)
    map_factory.create_top_10_maps(max_images=MAX_IMAGES)
    map_factory = MapFactory(s3_path, refresh=False, custom_color_map=custom_color_map_ids)
    map_factory.create_maps(max_images=MAX_IMAGES, specific_tribes=specific_tribes)

end_time = datetime.now()

logging.info(f"Time taken: {end_time - start_time}")

