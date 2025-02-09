import logging

from twmap.datamodel.dataloader import DataLoader
from twmap.map.map import Map

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_data = DataLoader("data/", 144)

village_models, player_models, tribe_models, conquer_models = load_data.load()

map = Map(village_models, player_models, tribe_models, conquer_models)

map.image_top_tribes_with_legend.show()
map.image_top_players_with_legend.show()