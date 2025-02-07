import pandas as pd

from pydantic import BaseModel, ValidationError
from typing import List

from twmap.datamodel.datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel


class ModelLoader:

    def __init__(self, data_path: str):
        
        self.data_path = data_path

        self.village_models = pd.DataFrame()
        self.player_models = pd.DataFrame()
        self.tribe_models = pd.DataFrame()
        self.conquer_models = pd.DataFrame()

    def load(self):
        """_summary_
        """

        village_data = pd.read_csv(self.data_path + "village.txt", sep=",", header=None, names=VillageModel.model_fields.keys(), index_col=False)
        player_data = pd.read_csv(self.data_path + "player.txt", sep=",", header=None, names=PlayerModel.model_fields.keys(), index_col=False)
        tribe_data = pd.read_csv(self.data_path + "ally.txt", sep=",", header=None, names=TribeModel.model_fields.keys(), index_col=False)
        conquer_data = pd.read_csv(self.data_path + "conquer.txt", sep=",", header=None, names=ConquerModel.model_fields.keys(), index_col=False)

        self.village_models = self.load_df_to_pydantic_models(village_data, VillageModel)
        self.player_models = self.load_df_to_pydantic_models(player_data, PlayerModel)
        self.tribe_models = self.load_df_to_pydantic_models(tribe_data, TribeModel)
        self.conquer_models = self.load_df_to_pydantic_models(conquer_data, ConquerModel)

        return self.village_models, self.player_models, self.tribe_models, self.conquer_models

    def load_df_to_pydantic_models(self, df: pd.DataFrame, model: BaseModel) -> List[BaseModel]:
        """_summary_

        Args:
            df (pd.DataFrame): _description_
            model (BaseModel): _description_

        Returns:
            List[BaseModel]: _description_
        """
        data_list = df.to_dict(orient="records")
        model_instances = []
        for data in data_list:
            try:
                model_instance = model(**data)
                model_instances.append(model_instance)
            except ValidationError as e:
                print(f"Validation error: {e}")
                # Handle validation errors as needed, e.g., skip the row, log the error, etc.
        
        return model_instances
    

if __name__ == "__main__":
    loader = ModelLoader("data/w144/")

    village_models, player_models, tribe_models, conquer_models = loader.load()
    print(village_models)
    print(player_models)
    print(tribe_models)
    print(conquer_models)