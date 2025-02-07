from map.map import Map
from datamodel.model_loader import ModelLoader


data = "data/w144/"
loader = ModelLoader(data)

village_models, player_models, tribe_models, conquer_models = loader.load()

map = Map()
map.draw(village_models)
