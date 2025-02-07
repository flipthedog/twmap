import random


class ColorManager:

    def __init__(self):
        
        self.color_map = {}

        self.colors =  [
'#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990'
        ]
    def get_unique_color(self):

        return self.colors.pop(0)
    
    def get_color(self, key: str):
        if key in self.color_map:
            return self.color_map[key]
        else:
            color = self.get_unique_color()
            self.color_map[key] = color
            return color
