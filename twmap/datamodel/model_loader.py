import pandas as pd

from pydantic import BaseModel, ValidationError
from typing import List
from pandantic import Pandantic

from twmap.datamodel.datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel


class ModelLoader:

    def __init__(self, data_path: str, world: int):
        
        self.data_path = data_path + f"en{world}/"

        self.village_models = pd.DataFrame()
        self.player_models = pd.DataFrame()
        self.tribe_models = pd.DataFrame()
        self.conquer_models = pd.DataFrame()


    def load(self):
        """_summary_
        """

        print(f"Loading data from {self.data_path}...")
        
        village_data = pd.read_csv(self.data_path + "village.txt", sep=",", header=None, names=VillageModel.model_fields.keys(), index_col=False)
        player_data = pd.read_csv(self.data_path + "player.txt", sep=",", header=None, names=PlayerModel.model_fields.keys(), index_col=False)
        tribe_data = pd.read_csv(self.data_path + "ally.txt", sep=",", header=None, names=TribeModel.model_fields.keys(), index_col=False)
        conquer_data = pd.read_csv(self.data_path + "conquer.txt", sep=",", header=None, names=ConquerModel.model_fields.keys(), index_col=False)

        village_schema = Pandantic(VillageModel)
        player_schema = Pandantic(PlayerModel)
        tribe_schema = Pandantic(TribeModel)
        conquer_schema = Pandantic(ConquerModel)

        self.village_model = village_schema.validate(dataframe=village_data, errors="skip")
        self.player_model = player_schema.validate(dataframe=player_data, errors="skip")
        self.tribe_model = tribe_schema.validate(dataframe=tribe_data, errors="skip")
        self.conquer_model = conquer_schema.validate(dataframe=conquer_data, errors="skip")

        return self.village_model, self.player_model, self.tribe_model, self.conquer_model

if __name__ == "__main__":
    loader = ModelLoader("data/w144/")

    village_models, player_models, tribe_models, conquer_models = loader.load()
    print(village_models)
    print(player_models)
    print(tribe_models)
    print(conquer_models)