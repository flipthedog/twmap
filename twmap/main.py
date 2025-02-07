from map.map import Map
from datamodel.model_loader import ModelLoader

from datamodel.datafilter import DataFilter

from copy import deepcopy

from twmap.api.twapi import TWAPI
from datetime import datetime

import os

LOAD_NEW = False

worlds = [144, 145]

data_path = "data/"

if LOAD_NEW:
    api = TWAPI(worlds, "en")
    api.get_files(data_path)

for world in worlds:
    print(f"Processing world {world}...")
    loader = ModelLoader(data_path=data_path, world=world)

    village_models, player_models, tribe_models, conquer_models = loader.load()

    filter = DataFilter(village_models, player_models, tribe_models, conquer_models)

    t10_players_v = filter.get_t10_player_villages()
    t10_tribes_v = filter.get_t10_tribe_villages()

    t10_players = filter.get_t10_players()
    t10_tribes = filter.get_t10_tribes()

    map = Map()
    map.initial_draw(village_models)

    top_player_map = deepcopy(map)
    top_tribe_map = deepcopy(map)

    print("""Drawing top players and tribes...""")
    print(f"Found {len(t10_players)} top players and {len(t10_tribes)} top tribes")
    print(f"Drawing {len(t10_players_v)} villages of top 10 players")
    print(f"Drawing {len(t10_tribes_v)} villages of top 10 tribes")

    top_player_map.draw(t10_players_v, field="playerid")
    top_tribe_map.draw(t10_tribes_v, field="tribeid")

    top_player_map.draw_legend(ids=t10_players["playerid"], names=t10_players["name"])
    top_tribe_map.draw_legend(ids=t10_tribes["tribeid"], names=t10_tribes["name"])
    world_folder = os.path.join("images", f"world_{world}")
    os.makedirs(world_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    top_player_map.save(os.path.join(world_folder, f"top_players_world_{world}_{timestamp}.png"))
    top_tribe_map.save(os.path.join(world_folder, f"top_tribes_world_{world}_{timestamp}.png"))
