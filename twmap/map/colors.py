import random


class ColorManager:

    def __init__(self):
        
        self.color_map = {}

        self.colors =  [
'#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990'
        ]

        self.cell_color = "#58761b"
        self.background_color = "#436213"

        self.dull_cell_color = "#0c2909"
        self.dull_background_color = "#395436"
        self.dull_colors = True

        self.tw_color = "#edd8ad"

        self.village_color = "#823c0a"
        self.barbarian_color = "#969696"

        self.grid_color = "#000000"
        
    def get_unique_color(self):

        return self.colors.pop(0)
    
    def get_color(self, key: str):
        if key in self.color_map:
            return self.color_map[key]
        else:
            color = self.get_unique_color()
            self.color_map[key] = color
            return color
