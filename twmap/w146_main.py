import logging 
from twmap.mapfactory import MapFactory
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set the correct S3 path for w146
s3_path = "s3://tribalwars-scraped/"

# List of specific tribes to highlight (update these with actual w146 tribes if needed)



# Alternatively, you can manually specify colors for better visual design:
custom_color_map_ids = {
    "380": "#0072ff",  # Bright red
    # Assign similar colors to all BEEF tribes
    "31": "#ff0000",   # Red (Medium Rare)
    "201": "#ff0000",  # Red (Medium Rare 3.0)
    "339": "#ff0000",  # Red (Medium Rare 2.0)
    # Assign similar colors to all GSK tribes
    "67": "#ff5733",   # Orange (Gusak)
    "625": "#ff5733",  # Orange (Gusak2)
    "661": "#ff5733",  # Orange (gusak4)
    "151": "#ff5733",  # Orange (-GSK3-)
    # Assign similar colors to all Storm tribes
    "423": "#6a0dad",  # Purple (STORM III)
    "353": "#6a0dad",  # Purple (storm-II)
    "525": "#6a0dad",  # Purple (Storm IV)
    # Assign similar colors to all Avalon tribes
    "50": "#8e0dad",   # Teal (Avalon)
    "132": "#8e0dad",  # Teal (Avalon-II)
    "503": "#8e0dad",  # Teal (Avalon-III)
    # Adventure time:
    "60": "#00af00",  # Green (Adventure Time)
    "540": "#00af00",  # Green (Adventure Time II)
}

# tribe ids based on keys in custom_color_map_ids
tribe_ids = [int(tribe_id) for tribe_id in custom_color_map_ids.keys()]

# Maximum number of images to process (None for all)
MAX_IMAGES = None

# Configure map generation parameters
MAX_COORDS = 700  # Adjust based on world size

def main():
    start_time = datetime.now()
    logging.info(f"Starting specific map generation for w146 at {start_time}")
    
    # Create MapFactory with custom color map
    map_factory = MapFactory(s3_path, custom_color_map=custom_color_map_ids, max_coords=700)
    
    # Generate specific tribe maps
    map_factory.generate_specific_maps(
        "en146",                 # World ID
        tribe_ids,         # List of tribes to highlight
        regenerate_all=True,     # Regenerate all maps, even if they already exist
        max_coords=650,          # Max coordinates for the world
        custom_folder="w146_special"  # Optional custom folder name
    )
    
    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"Map generation completed in {duration}")

if __name__ == "__main__":
    main()