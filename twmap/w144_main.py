import logging 

from twmap.map.mapfactory import MapFactory
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

factory = MapFactory("s3://tribalwars-scraped/", max_coords=730)

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
    "380": "#0072ff",     
    "54": "#ff93ac",   
    "106": "#ff93ac",  
    "65": "#ff93ac",   
    "341": "#ff4800",  
    "89": "#ff4800",   
    "242": "#039438",  
    "404": "#8d03ff",  
    "373": "#f5e902",  
    "370": "#ff3222",  
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

