from typing import List 

class ColorManager:

    def __init__(self):
        
        self.color_map = {}
        self.colors = []

        # Original colors
        self.default_colors =  [
            '#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990'
        ]
        
        # Option 1: Distinct rainbow colors (avoiding greens and browns)
        self.rainbow_colors = [
            '#FF0000',  # Pure Red
            '#FF6600',  # Orange Red
            '#FF9900',  # Orange
            '#FFCC00',  # Golden Yellow
            '#FFFF00',  # Pure Yellow
            '#00FFFF',  # Cyan
            '#0099FF',  # Sky Blue
            '#0033FF',  # Blue
            '#6600FF',  # Purple
            '#9900FF',  # Violet
            '#FF00FF',  # Magenta
            '#FF0080'   # Pink
        ]
        
        # Option 2: 10-step gradient colors - Bright to Dark Performance Gradient
        # Smooth gradient from bright (high ranks) to dark (low ranks)
        self.gradient_colors_10 = [
            '#FFD700',  # Bright Gold (1st - Highest rank) - Champion gold
            '#FFB347',  # Light Orange (2nd) - Bright warm tone
            '#FF8C69',  # Salmon (3rd) - Warm coral
            '#FF6B9D',  # Pink (4th) - Bright pink
            '#DA70D6',  # Orchid (5th) - Light purple
            '#9370DB',  # Medium Slate Blue (6th) - Purple
            '#6495ED',  # Cornflower Blue (7th) - Medium blue
            '#4169E1',  # Royal Blue (8th) - Darker blue
            '#191970',  # Midnight Blue (9th) - Very dark blue
            '#0F0F23'   # Very Dark Navy (10th - Lowest rank) - Almost black
        ]
        
        # Option 3: High-contrast performance gradient (Purple to Gold)
        # Best performers get warm colors (gold/orange), worst get cool colors (purple/blue)
        self.performance_gradient = [
            '#FF8F00',  # Pure Gold (top - best performance)
            '#FFB74D',  # Light Orange
            '#FFD54F',  # Golden Yellow
            '#FFF59D',  # Light Yellow
            '#E1BEE7',  # Pale Purple
            '#AB47BC',  # Bright Purple
            '#8E24AA',  # Light Purple
            '#6A1B9A',  # Medium Purple
            '#4A148C',  # Dark Purple
            '#2D1B69'   # Deep Purple (bottom - worst performance)
        ]
        
        # Option 4: Traffic light inspired (Red to Green via Yellow)
        # Intuitive: Red = bad/bottom, Yellow = middle, Green = good/top
        self.traffic_gradient = [
            '#B71C1C',  # Dark Red (bottom)
            '#D32F2F',  # Red
            '#F44336',  # Light Red
            '#FF5722',  # Red Orange
            '#FF9800',  # Orange
            '#FFC107',  # Amber/Yellow
            '#FFEB3B',  # Yellow
            '#8BC34A',  # Light Green
            '#4CAF50',  # Green
            '#2E7D32'   # Dark Green (top)
        ]
        
        # Option 5: Flipped blue intensity with high distinction
        # Top performers get intense dark blue, bottom gets pale blue
        self.blue_intensity = [
            '#E8F4FD',  # Very Pale Blue (bottom - worst performance)
            '#C3E2FC',  # Pale Blue
            '#9BCBF7',  # Light Blue
            '#6FB3F0',  # Medium Light Blue
            '#4A9AE7',  # Medium Blue
            '#2E7FDB',  # Darker Blue
            '#1E63CC',  # Dark Blue
            '#164A9B',  # Very Dark Blue
            '#0F3469',  # Deep Blue
            '#08203F'   # Intense Dark Blue (top - best performance)
        ]
        
        # Option 6: Thermal/Heat map (Black to White via Red/Orange/Yellow)
        # Like a heat signature - coldest (black) to hottest (white)
        self.thermal_gradient = [
            '#000000',  # Black (coldest/bottom)
            '#1A0033',  # Very Dark Purple
            '#4A0E4E',  # Dark Purple
            '#800026',  # Dark Red
            '#BD0026',  # Red
            '#E31A1C',  # Bright Red
            '#FC4E2A',  # Red Orange
            '#FD8D3C',  # Orange
            '#FEB24C',  # Light Orange
            '#FFFFFF'   # White (hottest/top)
        ]
        
        # Option 7: Sunset gradient (Deep blue to bright yellow)
        # Evokes progression from night (bottom) to bright day (top)
        self.sunset_gradient = [
            '#FFC107',  # Bright Yellow (day/top)
            '#FF9800',  # Orange
            '#FF5722',  # Red Orange
            '#E91E63',  # Pink
            '#9C27B0',  # Purple
            '#7986CB',  # Pale Blue
            '#5C6BC0',  # Light Blue
            '#3949AB',  # Blue
            '#283593',  # Dark Blue
            '#1A237E'   # Deep Blue (night/bottom)
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
        
        self.color_index = 0

    def create_custom_color_map(self, custom_color_map: List[str]):
        self.colors = custom_color_map
    
    def reset_color_index(self):
        self.color_index = 0

    def get_unique_color(self):
        color = self.colors[self.color_index % len(self.colors)]
        self.color_index += 1
        return color
    
    def get_color(self, key: str):
        if not self.colors:
            self.colors = self.default_colors.copy()
        
        key = str(key)
        if key in self.color_map:
            return self.color_map[key]
        else:
            color = self.get_unique_color()
            self.color_map[key] = color
            return color
