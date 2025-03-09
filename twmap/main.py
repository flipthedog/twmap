import logging 

from twmap.map.mapfactory import MapFactory

# This generates all missing maps for all worlds, using default colors and parameters
factory = MapFactory("s3://tribalwars-scraped/", max_coords=730)
factory.generate_missing_maps("en142", regenerate_all=False, max_coords=730)
factory.generate_missing_maps("en143", regenerate_all=False, max_coords=700)
factory.generate_missing_maps("en144", regenerate_all=False, max_coords=680)
factory.generate_missing_maps("en145", regenerate_all=False, max_coords=650)
factory.generate_missing_maps("en146", regenerate_all=False, max_coords=650) 
factory.generate_missing_maps("enc1", regenerate_all=False, max_coords=650)
factory.generate_missing_maps("enc2", regenerate_all=False, max_coords=650)
