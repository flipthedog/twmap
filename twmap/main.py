from map.map import Map
from datamodel.model_loader import ModelLoader

from datamodel.datafilter import DataFilter

from copy import deepcopy

data = "data/w144/"
loader = ModelLoader(data)

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

for i in range(0, 10):
    top_player_map.draw(t10_players_v[i], id=t10_players_v[i]["playerid"].unique()[0])
    top_tribe_map.draw(t10_tribes_v[i], id=t10_tribes_v[i]["tribeid"].unique()[0])


top_player_map.crop_image(top_player_map.image, 200)
top_tribe_map.crop_image(top_tribe_map.image, 200)



top_player_map.draw_legend(ids=t10_players["playerid"], names=t10_players["name"])
top_tribe_map.draw_legend(ids=t10_tribes["tribeid"], names=t10_tribes["name"])

top_player_map.image.show()
top_tribe_map.image.show()
