import logging 
import sys
import os

# Add the project root to Python path so we can import twmap modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from twmap.world.world_loader import WorldLoader
from twmap.mapfactory import MapFactory

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twmap.log'),
        logging.StreamHandler()
    ]
)

def generate_maps_for_world(world: str, server: str = "en", max_coords: int = 750, max_workers: int = 4, limit_images: int = None, interval: int = 1, regenerate_all: bool = False):
    """Generate missing maps for a specific world
    
    Args:
        world: World number (e.g., "143")
        server: Server name (e.g., "en")
        max_coords: Maximum coordinates for the world map
        max_workers: Number of parallel workers
        limit_images: Limit number of images to process (for testing)
        interval: Generate every Nth image (1=all, 2=every 2nd, 3=every 3rd, etc.)
    """
    
    logging.info(f"Processing world {server}{world} with interval {interval}")
    
    # Create WorldLoader instance
    world_loader = WorldLoader(world=world, server=server)
    
    # Load or create world model
    world_model = world_loader.load_world()
    if not world_model:
        world_model = world_loader.create_world(max_coords=max_coords, has_barbarians=True, timelapse_interval=6)
        logging.info(f"Created new world model for {server}{world}")
    else:
        logging.info(f"Loaded existing world model for {server}{world}")
    
    # Print statistics
    missing_count = sum(1 for img in world_loader.timelapse_images if not img.image_generated)
    logging.info(f"World {server}{world}: {len(world_loader.snapshots)} snapshots, {missing_count} missing images")
    
    if missing_count == 0:
        logging.info(f"No missing images for world {server}{world}, skipping")
        return
    
    # Limit processing if requested (for testing)
    if limit_images and missing_count > limit_images:
        missing_images = [img for img in world_loader.timelapse_images if not img.image_generated]
        world_loader.timelapse_images = missing_images[:limit_images]
        logging.info(f"Limited processing to first {limit_images} images for testing")

    # Create MapFactory and generate missing maps
    map_factory = MapFactory(world_loader, max_coords=max_coords)
    map_factory.generate_missing_maps(max_workers=max_workers, regenerate_all=regenerate_all, interval=interval)
    
    logging.info(f"Completed processing world {server}{world}")

def main():
    """Generate all missing maps for all worlds"""
    
    # Configuration
    worlds = ["133"]  # Start with just one world for testing
    interval = 2  # Generate every 50th image (every 200 hours if data is every 4 hours)
    
    logging.info(f"Starting map generation for all worlds with interval {interval}")
    
    for world in worlds:
        try:
            # Generate maps with interval setting
            generate_maps_for_world(
                world=world, 
                server="br", 
                max_coords=750, 
                max_workers=8, 
                interval=interval,
                regenerate_all=False,  # Regenerate all maps,
            )
        except Exception as e:
            logging.error(f"Error processing world {world}: {e}")
            continue
    
    logging.info("Completed map generation for all worlds")

if __name__ == "__main__":
    main()
