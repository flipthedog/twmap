import logging 

from twmap.map.mapfactory import MapFactory
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

s3_paths = [
    "s3://tribalwars-scraped/en142/",
    "s3://tribalwars-scraped/en143/",
    "s3://tribalwars-scraped/en144/",
    "s3://tribalwars-scraped/en145/",
    "s3://tribalwars-scraped/enc1/",
    "s3://tribalwars-scraped/enc2/",
]

MAX_IMAGES = None
start_time = datetime.now()

for s3_path in s3_paths:
    map_factory = MapFactory(s3_path, refresh=True)
    map_factory.create_top_10_maps(max_images=MAX_IMAGES)

end_time = datetime.now()

logging.info(f"Time taken: {end_time - start_time}")

