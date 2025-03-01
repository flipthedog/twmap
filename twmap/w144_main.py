import logging 

from twmap.map.mapfactory import MapFactory
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

s3_paths = [
    "s3://tribalwars-scraped/en144/",
]

specific_tribes = [
    "Sock%7E2",
    "Socks%21",
    "SPS",
    "HOUNDS",
    "J%C3%A4ger",
    "DOGS",
    "Taste",
    "%3DBOW%3D",
    "TF",
    "SPS-2",
    "SPS-3",
]

custom_color_map_ids = {
    "350": "#0072ff",  # Sock%7E2
    "98": "#00aaf2",   # Socks%21
    "54": "#ff93ac",   # SPS
    "106": "#fc3468",  # SPS-2
    "65": "#ff084a",   # SPS-3
    "341": "#ff4800",  # Hounds
    "89": "#f28e41",   # DOGS
    "242": "#039438",  # J%C3%A4ger
    "404": "#8d03ff",  # Taste
    "373": "#f5e902",  # %3DBOW%3D
    "370": "#e0faaf",  # TF
}

MAX_IMAGES = None

start_time = datetime.now()

for s3_path in s3_paths:
    map_factory = MapFactory(s3_path, refresh=False)
    map_factory.create_top_10_maps(max_images=MAX_IMAGES)
    map_factory = MapFactory(s3_path, refresh=False, custom_color_map=custom_color_map_ids)
    map_factory.create_maps(max_images=MAX_IMAGES, specific_tribes=specific_tribes)

end_time = datetime.now()

logging.info(f"Time taken: {end_time - start_time}")

