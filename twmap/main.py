import logging 

from twmap.map.mapfactory import MapFactory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

s3_paths = [
    "s3://tribalwars-scraped/en144/",
    "s3://tribalwars-scraped/en145/",
]

MAX_IMAGES = 1

for s3_path in s3_paths:
    map_factory = MapFactory(s3_path, refresh=False)
    map_factory.create_maps(MAX_IMAGES)
    