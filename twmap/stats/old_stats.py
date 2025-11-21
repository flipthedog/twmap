# stats.py  
import logging 
import sys
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pandas as pd
import numpy as np

# Add the project root to Python path so we can import twmap modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from twmap.world.world_loader import WorldLoader
from twmap.snapshot.dataloader import DataLoader
from twmap.map.colors import ColorManager
from twmap.snapshot.snapshot_datamodel import VillageModel, PlayerModel, TribeModel

# Set up matplotlib for animations
try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from matplotlib.dates import DateFormatter
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib not available. Please install with: pip install matplotlib")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class WorldStatsLoader:
    """Loads all historical snapshot data for a world to enable time-series analysis."""
    
    def __init__(self, world_id: str, server: str = "en"):
        self.world_id = world_id
        self.server = server
        
        # Create WorldLoader to get snapshots
        self.world_loader = WorldLoader(world_id, server, init_load=True)
        self.loader = DataLoader(self.world_loader)
        
        self.village_snapshots: List[pd.DataFrame] = []
        self.player_snapshots: List[pd.DataFrame] = []
        self.tribe_snapshots: List[pd.DataFrame] = []
        self.timestamps: List[datetime] = []
        
    def load_all_snapshots(self):
        """Load all available snapshots for the world."""
        logging.info(f"Loading all snapshots for world {self.server}{self.world_id}")
        
        # Use the timelapse_images directly from the WorldLoader (like mapfactory does)
        timelapse_images = self.world_loader.timelapse_images
        if not timelapse_images:
            logging.error(f"No timelapse images found for world {self.server}{self.world_id}")
            return self
            
        logging.info(f"Found {len(timelapse_images)} timelapse images available")
        
        # Load more snapshots for smoother animation
        # Take every nth snapshot to create a reasonable animation timeline
        max_snapshots = 50  # Increased for smoother animation
        step = max(1, len(timelapse_images) // max_snapshots)
        selected_images = timelapse_images[::step]
        
        logging.info(f"Processing {len(selected_images)} timelapse images for animation")
        
        # Helper function to extract S3 key from full path (like in mapfactory)
        def extract_s3_key(s3_path: str) -> str:
            if s3_path.startswith('s3://'):
                # Remove s3://bucket-name/ prefix
                parts = s3_path.split('/', 3)
                return parts[3] if len(parts) > 3 else s3_path
            return s3_path
        
        # Load each snapshot's data
        for i, timelapse_image in enumerate(selected_images):
            try:
                # Extract S3 keys from full paths (following mapfactory pattern)
                ally_key = extract_s3_key(timelapse_image.tribe_data_path)
                player_key = extract_s3_key(timelapse_image.player_data_path)
                village_key = extract_s3_key(timelapse_image.village_data_path)
                conquer_key = extract_s3_key(timelapse_image.conquer_data_path) if timelapse_image.conquer_data_path else None
                
                # Load the specific files for this snapshot
                tribe_df, player_df, village_df, conquer_df, killall_df, killall_tribe_df = self.loader.load_specific_files(
                    ally_key,
                    player_key, 
                    village_key,
                    conquer_key
                )
                
                self.tribe_snapshots.append(tribe_df)
                self.player_snapshots.append(player_df)
                self.village_snapshots.append(village_df)
                
                # Convert timestamp to datetime
                snapshot_time = datetime.fromtimestamp(timelapse_image.timestamp)
                self.timestamps.append(snapshot_time)
                
                if (i + 1) % 5 == 0 or i == 0:
                    logging.info(f"Loaded {i + 1}/{len(selected_images)} snapshots - latest: {snapshot_time}")
                    
            except Exception as e:
                logging.warning(f"Failed to load snapshot {i}: {e}")
                continue
                
        logging.info(f"Successfully loaded {len(self.village_snapshots)} snapshots")
        return self
        
    def get_all_players_timeline(self) -> pd.DataFrame:
        """Get timeline data for ALL players across all snapshots."""
        if not self.player_snapshots:
            raise ValueError("No player snapshots loaded")
            
        # Create timeline DataFrame with ALL players from each snapshot
        timeline_data = []
        for i, (player_df, timestamp) in enumerate(zip(self.player_snapshots, self.timestamps)):
            for _, player_info in player_df.iterrows():
                timeline_data.append({
                    'timestamp': timestamp,
                    'playerid': player_info['playerid'],
                    'name': player_info['name'],
                    'points': player_info['points'],
                    'village_count': player_info['village_count'],
                    'snapshot_index': i
                })
                    
        return pd.DataFrame(timeline_data)
        
    def get_all_tribes_timeline(self) -> pd.DataFrame:
        """Get timeline data for ALL tribes across all snapshots."""
        if not self.tribe_snapshots:
            raise ValueError("No tribe snapshots loaded")
            
        # Create timeline DataFrame with ALL tribes from each snapshot
        timeline_data = []
        for i, (tribe_df, timestamp) in enumerate(zip(self.tribe_snapshots, self.timestamps)):
            for _, tribe_info in tribe_df.iterrows():
                timeline_data.append({
                    'timestamp': timestamp,
                    'tribeid': tribe_info['tribeid'],
                    'name': tribe_info['name'],
                    'tag': tribe_info['tag'],
                    'tribe_points': tribe_info['tribe_points'],
                    'num_members': tribe_info['num_members'],
                    'snapshot_index': i
                })
                    
        return pd.DataFrame(timeline_data)


class AnimatedStatsPlotter:
    """Creates animated plots showing player/tribe growth over time using TW color scheme."""
    
    def __init__(self, world_stats_loader: WorldStatsLoader):
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for animated plots")
            
        self.stats_loader = world_stats_loader
        self.color_manager = ColorManager()
        
        # Set up plot style to match TW aesthetic
        plt.style.use('dark_background')
        
    def create_player_points_animation(self, save_path: str = None, window_days: int = 30) -> animation.FuncAnimation:
        """Create racing line chart showing dynamic top 10 player points with sliding time window."""
        timeline_df = self.stats_loader.get_all_players_timeline()
        
        fig, ax = plt.subplots(figsize=(20, 12))
        
        # TW-style dark theme
        bg_color = '#0D1B2A'  # Dark blue background
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        
        # Get max values for consistent scaling
        max_points = timeline_df['points'].max()
        
        # Animation function
        def animate(frame):
            ax.clear()
            ax.set_facecolor(bg_color)
            
            # Get current frame timestamp
            if frame >= len(self.stats_loader.timestamps):
                return
                
            current_time = self.stats_loader.timestamps[frame]
            
            # Define sliding window (past month from current frame)
            window_start = current_time - pd.Timedelta(days=window_days)
            
            # Get current snapshot to determine top 10
            current_snapshot = timeline_df[timeline_df['snapshot_index'] == frame]
            if len(current_snapshot) == 0:
                return
                
            # Get top 10 players for this frame
            top_10_current = current_snapshot.nlargest(10, 'points')
            top_10_ids = top_10_current['playerid'].tolist()
            
            # Get windowed historical data for these top 10 players
            windowed_data = timeline_df[
                (timeline_df['playerid'].isin(top_10_ids)) & 
                (timeline_df['timestamp'] >= window_start) &
                (timeline_df['timestamp'] <= current_time)
            ]
            
            # Collect all current points for dynamic y-axis scaling
            current_window_points = windowed_data['points'].tolist()
            
            # Plot lines for each player in current top 10
            for i, (_, player_current) in enumerate(top_10_current.iterrows()):
                player_id = player_current['playerid']
                player_data = windowed_data[windowed_data['playerid'] == player_id].sort_values('timestamp')
                
                if len(player_data) > 0:
                    # Assign consistent color based on current ranking
                    color = self.color_manager.gradient_colors_10[i % len(self.color_manager.gradient_colors_10)]
                    
                    # Smooth the line if we have enough data points
                    if len(player_data) > 2:
                        try:
                            from scipy.interpolate import interp1d
                            import numpy as np
                            
                            # Convert timestamps to numeric for interpolation
                            time_nums = np.array([t.timestamp() for t in player_data['timestamp']])
                            points = player_data['points'].values
                            
                            # Create smooth interpolation
                            f = interp1d(time_nums, points, kind='cubic', bounds_error=False, fill_value='extrapolate')
                            
                            # Generate many more points for ultra-smooth curve
                            smooth_time_nums = np.linspace(time_nums[0], time_nums[-1], len(time_nums) * 10)
                            smooth_timestamps = pd.to_datetime(smooth_time_nums, unit='s', utc=True).tz_convert(player_data['timestamp'].iloc[0].tz)
                            smooth_points = f(smooth_time_nums)
                            
                            # Plot smooth line with enhanced glow effect for smoother appearance
                            ax.plot(smooth_timestamps, smooth_points, 
                                   color=color, linewidth=4, alpha=0.9, zorder=20-i, label=f"{i+1}. {player_current['name'][:12]}")
                            
                            # Add multiple glow layers for smoother appearance
                            ax.plot(smooth_timestamps, smooth_points, 
                                   color=color, linewidth=8, alpha=0.3, zorder=20-i)
                            ax.plot(smooth_timestamps, smooth_points, 
                                   color=color, linewidth=12, alpha=0.1, zorder=20-i)
                            
                        except Exception:
                            # Fall back to regular line if smoothing fails
                            ax.plot(player_data['timestamp'], player_data['points'], 
                                   color=color, linewidth=4, alpha=0.9, zorder=20-i, label=f"{i+1}. {player_current['name'][:12]}")
                            
                            ax.plot(player_data['timestamp'], player_data['points'], 
                                   color=color, linewidth=8, alpha=0.2, zorder=20-i)
                    else:
                        # Not enough points for smoothing
                        ax.plot(player_data['timestamp'], player_data['points'], 
                               color=color, linewidth=4, alpha=0.9, zorder=20-i, label=f"{i+1}. {player_current['name'][:12]}")
                        
                        ax.plot(player_data['timestamp'], player_data['points'], 
                               color=color, linewidth=8, alpha=0.2, zorder=20-i)
                    
                    # Plot markers for better visibility
                    ax.scatter(player_data['timestamp'], player_data['points'], 
                             color=color, s=40, alpha=0.8, zorder=25-i, edgecolors='white', linewidth=1.5)
                    
                    # Add player name at the current point
                    if len(player_data) > 0:
                        current_point = player_data.iloc[-1]
                        ax.annotate(f"{i+1}. {player_current['name'][:12]}", 
                                  xy=(current_point['timestamp'], current_point['points']),
                                  xytext=(10, 0), textcoords='offset points',
                                  color=color, fontweight='bold', fontsize=11,
                                  bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7, edgecolor='white'),
                                  ha='left', va='center')
            
            # Styling with TW theme  
            ax.set_xlabel('Date', color='#E0E6ED', fontsize=16, fontweight='bold')
            ax.set_ylabel('Points (Millions)', color='#E0E6ED', fontsize=16, fontweight='bold')
            ax.set_title(f'🏆 Top 10 Player Points (Past {window_days} Days) - World {self.stats_loader.server}{self.stats_loader.world_id}', 
                        color='#FFF8DC', fontsize=20, fontweight='bold', pad=30)
            
            # Grid for better readability
            ax.grid(True, alpha=0.4, color='#415A77', linestyle='-', linewidth=0.8)
            ax.set_axisbelow(True)
            
            # Formatting
            ax.tick_params(colors='#E0E6ED', labelsize=12)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000000:.1f}M'))
            
            # Set time window limits
            ax.set_xlim(window_start, current_time)
            
            # Dynamic y-axis scaling based on current window data
            if current_window_points:
                min_points = min(current_window_points)
                max_points_window = max(current_window_points)
                
                # Add some padding and ensure we start from 0 or slightly below min
                y_padding = (max_points_window - min_points) * 0.1
                y_min = max(0, min_points - y_padding)
                y_max = max_points_window + y_padding
                
                ax.set_ylim(y_min, y_max)
            else:
                ax.set_ylim(0, max_points * 1.05)
            
            # Make spines visible with TW colors
            for spine in ax.spines.values():
                spine.set_color('#415A77')
                spine.set_linewidth(2)
            
            # Add timestamp and info
            info_text = f"📅 {current_time.strftime('%Y-%m-%d %H:%M')}\n🎬 Frame {frame + 1}/{len(self.stats_loader.timestamps)}\n⏰ Window: {window_days} days"
            ax.text(0.02, 0.98, info_text, 
                   transform=ax.transAxes, color='#FFF8DC', fontsize=13, 
                   verticalalignment='top', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.8', facecolor=bg_color, alpha=0.9, edgecolor='#415A77', linewidth=2))
            
            # Add ranking summary in top right
            ranking_text = "🏅 Current Top 5:\n"
            for i, (_, player) in enumerate(top_10_current.head(5).iterrows()):
                ranking_text += f"{i+1}. {player['name'][:10]} ({player['points']/1000000:.1f}M)\n"
            
            ax.text(0.98, 0.98, ranking_text, 
                   transform=ax.transAxes, color='#FFF8DC', fontsize=11, 
                   verticalalignment='top', horizontalalignment='right', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.6', facecolor=bg_color, alpha=0.9, edgecolor='#415A77', linewidth=2))
        
        # Create animation with smoother parameters
        frames = len(self.stats_loader.timestamps)
        anim = animation.FuncAnimation(fig, animate, frames=frames, interval=300, repeat=True, blit=False)
        
        if save_path:
            logging.info(f"Saving player points racing animation to {save_path}")
            writer = animation.FFMpegWriter(fps=4, metadata=dict(artist='TWMap'), bitrate=4000)
            anim.save(save_path, writer=writer)
            
        return anim
    
    def create_tribe_points_animation(self, save_path: str = None, window_days: int = 30) -> animation.FuncAnimation:
        """Create racing line chart showing dynamic top 10 tribe points with sliding time window."""
        timeline_df = self.stats_loader.get_all_tribes_timeline()
        
        fig, ax = plt.subplots(figsize=(18, 12))
        
        # TW-style dark theme
        bg_color = '#0D1B2A'  # Dark blue background
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        
        # Get max values for consistent scaling
        max_points = timeline_df['tribe_points'].max()
        
        # Animation function
        def animate(frame):
            ax.clear()
            ax.set_facecolor(bg_color)
            
            # Get current frame timestamp
            if frame >= len(self.stats_loader.timestamps):
                return
                
            current_time = self.stats_loader.timestamps[frame]
            
            # Define sliding window (past month from current frame)
            window_start = current_time - pd.Timedelta(days=window_days)
            
            # Get current snapshot to determine top 10
            current_snapshot = timeline_df[timeline_df['snapshot_index'] == frame]
            if len(current_snapshot) == 0:
                return
                
            # Get top 10 tribes for this frame
            top_10_current = current_snapshot.nlargest(10, 'tribe_points')
            top_10_ids = top_10_current['tribeid'].tolist()
            
            # Get windowed historical data for these top 10 tribes
            windowed_data = timeline_df[
                (timeline_df['tribeid'].isin(top_10_ids)) & 
                (timeline_df['timestamp'] >= window_start) &
                (timeline_df['timestamp'] <= current_time)
            ]
            
            # Collect all current points for dynamic y-axis scaling
            current_window_points = windowed_data['tribe_points'].tolist()
            
            # Plot lines for each tribe in current top 10
            tribe_colors = {}
            for i, (_, tribe_current) in enumerate(top_10_current.iterrows()):
                tribe_id = tribe_current['tribeid']
                tribe_data = windowed_data[windowed_data['tribeid'] == tribe_id].sort_values('timestamp')
                
                if len(tribe_data) > 0:
                    # Assign consistent color based on current ranking
                    color = self.color_manager.gradient_colors_10[i % len(self.color_manager.gradient_colors_10)]
                    tribe_colors[tribe_id] = color
                    
                    # Smooth the line if we have enough data points
                    if len(tribe_data) > 2:
                        try:
                            from scipy.interpolate import interp1d
                            import numpy as np
                            
                            # Convert timestamps to numeric for interpolation
                            time_nums = np.array([t.timestamp() for t in tribe_data['timestamp']])
                            points = tribe_data['tribe_points'].values
                            
                            # Create smooth interpolation
                            f = interp1d(time_nums, points, kind='cubic', bounds_error=False, fill_value='extrapolate')
                            
                            # Generate many more points for ultra-smooth curve  
                            smooth_time_nums = np.linspace(time_nums[0], time_nums[-1], len(time_nums) * 10)
                            smooth_timestamps = pd.to_datetime(smooth_time_nums, unit='s', utc=True).tz_convert(tribe_data['timestamp'].iloc[0].tz)
                            smooth_points = f(smooth_time_nums)
                            
                            # Plot smooth line with enhanced glow effect for smoother appearance
                            ax.plot(smooth_timestamps, smooth_points, 
                                   color=color, linewidth=4, alpha=0.9, zorder=20-i)
                            
                            # Add multiple glow layers for smoother appearance
                            ax.plot(smooth_timestamps, smooth_points, 
                                   color=color, linewidth=8, alpha=0.3, zorder=20-i)
                            ax.plot(smooth_timestamps, smooth_points, 
                                   color=color, linewidth=12, alpha=0.1, zorder=20-i)
                            
                        except Exception:
                            # Fall back to regular line if smoothing fails
                            ax.plot(tribe_data['timestamp'], tribe_data['tribe_points'], 
                                   color=color, linewidth=4, alpha=0.9, zorder=20-i)
                            
                            ax.plot(tribe_data['timestamp'], tribe_data['tribe_points'], 
                                   color=color, linewidth=8, alpha=0.2, zorder=20-i)
                    else:
                        # Not enough points for smoothing
                        ax.plot(tribe_data['timestamp'], tribe_data['tribe_points'], 
                               color=color, linewidth=4, alpha=0.9, zorder=20-i)
                        
                        ax.plot(tribe_data['timestamp'], tribe_data['tribe_points'], 
                               color=color, linewidth=8, alpha=0.2, zorder=20-i)
                    
                    # Plot markers for better visibility
                    ax.scatter(tribe_data['timestamp'], tribe_data['tribe_points'], 
                             color=color, s=30, alpha=0.8, zorder=25-i, edgecolors='white', linewidth=1)
            
            # Create ranking panel on the right
            ax_main = plt.axes([0.1, 0.1, 0.65, 0.8])  # Main plot area
            ax_rank = plt.axes([0.77, 0.1, 0.2, 0.8])   # Ranking panel
            
            # Clear and setup main plot
            ax_main.clear()
            ax_main.set_facecolor(bg_color)
            
            # Re-plot on main axes
            for i, (_, tribe_current) in enumerate(top_10_current.iterrows()):
                tribe_id = tribe_current['tribeid']
                tribe_data = windowed_data[windowed_data['tribeid'] == tribe_id].sort_values('timestamp')
                
                if len(tribe_data) > 0:
                    color = self.color_manager.gradient_colors_10[i % len(self.color_manager.gradient_colors_10)]
                    
                    ax_main.plot(tribe_data['timestamp'], tribe_data['tribe_points'], 
                               color=color, linewidth=4, alpha=0.9, zorder=20-i)
                    ax_main.plot(tribe_data['timestamp'], tribe_data['tribe_points'], 
                               color=color, linewidth=8, alpha=0.2, zorder=20-i)
                    ax_main.scatter(tribe_data['timestamp'], tribe_data['tribe_points'], 
                                  color=color, s=30, alpha=0.8, zorder=25-i, edgecolors='white', linewidth=1)
            
            # Setup ranking panel
            ax_rank.clear()
            ax_rank.set_facecolor(bg_color)
            ax_rank.set_xlim(0, 1)
            ax_rank.set_ylim(0, 11)
            
            # Display current rankings
            for i, (_, tribe_current) in enumerate(top_10_current.iterrows()):
                rank = i + 1
                tag = tribe_current['tag'][:10]
                name = tribe_current['name'][:15] if 'name' in tribe_current and tribe_current['name'] else tag
                points = tribe_current['tribe_points']
                members = int(tribe_current['num_members']) if 'num_members' in tribe_current else 0
                color = self.color_manager.gradient_colors_10[i % len(self.color_manager.gradient_colors_10)]
                
                # Rank number with colored background
                ax_rank.text(0.05, 10.5-i, f"{rank}", fontsize=16, fontweight='bold', 
                           color='white', ha='center', va='center',
                           bbox=dict(boxstyle='circle', facecolor=color, alpha=0.8))
                
                # Tribe tag and name
                ax_rank.text(0.2, 10.7-i, f"[{tag}]", fontsize=11, fontweight='bold', 
                           color=color, va='center')
                ax_rank.text(0.2, 10.3-i, name, fontsize=9, 
                           color='#E0E6ED', va='center', style='italic')
                
                # Points and members
                ax_rank.text(0.95, 10.6-i, f"{points/1000000:.1f}M", fontsize=10, fontweight='bold',
                           color='#E0E6ED', va='center', ha='right')
                ax_rank.text(0.95, 10.4-i, f"({members} members)", fontsize=8, 
                           color='#A0A6AD', va='center', ha='right')
            
            # Styling for main plot
            ax_main.set_xlabel('Date', color='#E0E6ED', fontsize=14, fontweight='bold')
            ax_main.set_ylabel('Tribe Points (Millions)', color='#E0E6ED', fontsize=14, fontweight='bold')
            ax_main.set_title(f'Top 10 Tribe Points (Past {window_days} Days) - World {self.stats_loader.server}{self.stats_loader.world_id}', 
                            color='#FFF8DC', fontsize=16, fontweight='bold', pad=20)
            
            # Grid and formatting
            ax_main.grid(True, alpha=0.3, color='#415A77', linestyle='-', linewidth=0.5)
            ax_main.set_axisbelow(True)
            ax_main.tick_params(colors='#E0E6ED', labelsize=10)
            ax_main.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000000:.1f}M'))
            
            # Set time window limits
            ax_main.set_xlim(window_start, current_time)
            
            # Dynamic y-axis scaling based on current window data
            if current_window_points:
                min_points = min(current_window_points)
                max_points_window = max(current_window_points)
                
                # Add some padding and ensure we start from 0 or slightly below min
                y_padding = (max_points_window - min_points) * 0.1
                y_min = max(0, min_points - y_padding)
                y_max = max_points_window + y_padding
                
                ax_main.set_ylim(y_min, y_max)
            else:
                ax_main.set_ylim(0, max_points * 1.05)
            
            # Style ranking panel
            ax_rank.set_title('Current Rankings', color='#FFF8DC', fontsize=14, fontweight='bold')
            ax_rank.set_xticks([])
            ax_rank.set_yticks([])
            for spine in ax_rank.spines.values():
                spine.set_color('#415A77')
                spine.set_linewidth(1.5)
            
            # Main plot spines
            for spine in ax_main.spines.values():
                spine.set_color('#415A77')
                spine.set_linewidth(1.5)
            
            # Add timestamp
            info_text = f"Date: {current_time.strftime('%Y-%m-%d %H:%M')}\nFrame: {frame + 1}/{len(self.stats_loader.timestamps)}"
            ax_main.text(0.02, 0.98, info_text, 
                       transform=ax_main.transAxes, color='#FFF8DC', fontsize=12, 
                       verticalalignment='top', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor=bg_color, alpha=0.8, edgecolor='#415A77'))
        
        # Create animation
        frames = len(self.stats_loader.timestamps)
        anim = animation.FuncAnimation(fig, animate, frames=frames, interval=250, repeat=True, blit=False)
        
        if save_path:
            logging.info(f"Saving tribe points racing animation to {save_path}")
            writer = animation.FFMpegWriter(fps=5, metadata=dict(artist='TWMap'), bitrate=3200)
            anim.save(save_path, writer=writer)
            
        return anim
    
    def create_village_count_animation(self, save_path: str = None, window_days: int = 30) -> animation.FuncAnimation:
        """Create racing line chart showing dynamic top 10 player village counts with sliding time window."""
        timeline_df = self.stats_loader.get_all_players_timeline()
        
        fig, ax = plt.subplots(figsize=(18, 12))
        
        # TW-style dark theme
        bg_color = '#0D1B2A'  # Dark blue background
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        
        # Get max values for consistent scaling
        max_villages = timeline_df['village_count'].max()
        
        # Animation function
        def animate(frame):
            ax.clear()
            ax.set_facecolor(bg_color)
            
            # Get current frame timestamp
            if frame >= len(self.stats_loader.timestamps):
                return
                
            current_time = self.stats_loader.timestamps[frame]
            
            # Define sliding window (past month from current frame)
            window_start = current_time - pd.Timedelta(days=window_days)
            
            # Get current snapshot to determine top 10
            current_snapshot = timeline_df[timeline_df['snapshot_index'] == frame]
            if len(current_snapshot) == 0:
                return
                
            # Get top 10 players by village count for this frame
            top_10_current = current_snapshot.nlargest(10, 'village_count')
            top_10_ids = top_10_current['playerid'].tolist()
            
            # Get windowed historical data for these top 10 players
            windowed_data = timeline_df[
                (timeline_df['playerid'].isin(top_10_ids)) & 
                (timeline_df['timestamp'] >= window_start) &
                (timeline_df['timestamp'] <= current_time)
            ]
            
            # Create ranking panel on the right
            ax_main = plt.axes([0.1, 0.1, 0.65, 0.8])  # Main plot area
            ax_rank = plt.axes([0.77, 0.1, 0.2, 0.8])   # Ranking panel
            
            # Clear and setup main plot
            ax_main.clear()
            ax_main.set_facecolor(bg_color)
            
            # Collect all current village counts for dynamic y-axis scaling
            current_window_villages = windowed_data['village_count'].tolist()
            
            # Plot lines for each player in current top 10
            for i, (_, player_current) in enumerate(top_10_current.iterrows()):
                player_id = player_current['playerid']
                player_data = windowed_data[windowed_data['playerid'] == player_id].sort_values('timestamp')
                
                if len(player_data) > 0:
                    # Assign consistent color based on current ranking
                    color = self.color_manager.gradient_colors_10[i % len(self.color_manager.gradient_colors_10)]
                    
                    # Smooth the line if we have enough data points
                    if len(player_data) > 2:
                        try:
                            from scipy.interpolate import interp1d
                            import numpy as np
                            
                            # Convert timestamps to numeric for interpolation
                            time_nums = np.array([t.timestamp() for t in player_data['timestamp']])
                            villages = player_data['village_count'].values
                            
                            # Create smooth interpolation
                            f = interp1d(time_nums, villages, kind='cubic', bounds_error=False, fill_value='extrapolate')
                            
                            # Generate many more points for ultra-smooth curve
                            smooth_time_nums = np.linspace(time_nums[0], time_nums[-1], len(time_nums) * 10)
                            smooth_timestamps = pd.to_datetime(smooth_time_nums, unit='s', utc=True).tz_convert(player_data['timestamp'].iloc[0].tz)
                            smooth_villages = f(smooth_time_nums)
                            
                            # Plot smooth line with enhanced glow effect for smoother appearance
                            ax_main.plot(smooth_timestamps, smooth_villages, 
                                       color=color, linewidth=4, alpha=0.9, zorder=20-i)
                            
                            # Add multiple glow layers for smoother appearance
                            ax_main.plot(smooth_timestamps, smooth_villages, 
                                       color=color, linewidth=8, alpha=0.3, zorder=20-i)
                            ax_main.plot(smooth_timestamps, smooth_villages, 
                                       color=color, linewidth=12, alpha=0.1, zorder=20-i)
                            
                        except Exception:
                            # Fall back to regular line if smoothing fails
                            ax_main.plot(player_data['timestamp'], player_data['village_count'], 
                                       color=color, linewidth=4, alpha=0.9, zorder=20-i)
                            
                            ax_main.plot(player_data['timestamp'], player_data['village_count'], 
                                       color=color, linewidth=8, alpha=0.2, zorder=20-i)
                    else:
                        # Not enough points for smoothing
                        ax_main.plot(player_data['timestamp'], player_data['village_count'], 
                                   color=color, linewidth=4, alpha=0.9, zorder=20-i)
                        
                        ax_main.plot(player_data['timestamp'], player_data['village_count'], 
                                   color=color, linewidth=8, alpha=0.2, zorder=20-i)
                    
                    # Plot markers for better visibility
                    ax_main.scatter(player_data['timestamp'], player_data['village_count'], 
                                  color=color, s=30, alpha=0.8, zorder=25-i, edgecolors='white', linewidth=1)
            
            # Setup ranking panel
            ax_rank.clear()
            ax_rank.set_facecolor(bg_color)
            ax_rank.set_xlim(0, 1)
            ax_rank.set_ylim(0, 11)
            
            # Display current rankings
            for i, (_, player_current) in enumerate(top_10_current.iterrows()):
                rank = i + 1
                name = player_current['name'][:15]
                village_count = int(player_current['village_count'])
                points = player_current['points']
                color = self.color_manager.gradient_colors_10[i % len(self.color_manager.gradient_colors_10)]
                
                # Rank number with colored background
                ax_rank.text(0.05, 10.5-i, f"{rank}", fontsize=16, fontweight='bold', 
                           color='white', ha='center', va='center',
                           bbox=dict(boxstyle='circle', facecolor=color, alpha=0.8))
                
                # Player name
                ax_rank.text(0.2, 10.7-i, name, fontsize=11, fontweight='bold', 
                           color=color, va='center')
                
                # Village count and points
                ax_rank.text(0.95, 10.6-i, f"{village_count} villages", fontsize=10, fontweight='bold',
                           color='#E0E6ED', va='center', ha='right')
                ax_rank.text(0.95, 10.4-i, f"({points/1000000:.1f}M pts)", fontsize=9, 
                           color='#A0A6AD', va='center', ha='right')
            
            # Styling for main plot
            ax_main.set_xlabel('Date', color='#E0E6ED', fontsize=14, fontweight='bold')
            ax_main.set_ylabel('Village Count', color='#E0E6ED', fontsize=14, fontweight='bold')
            ax_main.set_title(f'Top 10 Player Village Counts (Past {window_days} Days) - World {self.stats_loader.server}{self.stats_loader.world_id}', 
                            color='#FFF8DC', fontsize=16, fontweight='bold', pad=20)
            
            # Grid and formatting
            ax_main.grid(True, alpha=0.3, color='#415A77', linestyle='-', linewidth=0.5)
            ax_main.set_axisbelow(True)
            ax_main.tick_params(colors='#E0E6ED', labelsize=10)
            
            # Set time window limits
            ax_main.set_xlim(window_start, current_time)
            
            # Dynamic y-axis scaling based on current window data
            if current_window_villages:
                min_villages = min(current_window_villages)
                max_villages_window = max(current_window_villages)
                
                # Add some padding and ensure we start from 0 or slightly below min
                y_padding = (max_villages_window - min_villages) * 0.1
                y_min = max(0, min_villages - y_padding)
                y_max = max_villages_window + y_padding
                
                ax_main.set_ylim(y_min, y_max)
            else:
                ax_main.set_ylim(0, max_villages * 1.05)
            
            # Style ranking panel
            ax_rank.set_title('Current Rankings', color='#FFF8DC', fontsize=14, fontweight='bold')
            ax_rank.set_xticks([])
            ax_rank.set_yticks([])
            for spine in ax_rank.spines.values():
                spine.set_color('#415A77')
                spine.set_linewidth(1.5)
            
            # Main plot spines
            for spine in ax_main.spines.values():
                spine.set_color('#415A77')
                spine.set_linewidth(1.5)
            
            # Add timestamp
            info_text = f"Date: {current_time.strftime('%Y-%m-%d %H:%M')}\nFrame: {frame + 1}/{len(self.stats_loader.timestamps)}"
            ax_main.text(0.02, 0.98, info_text, 
                       transform=ax_main.transAxes, color='#FFF8DC', fontsize=12, 
                       verticalalignment='top', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor=bg_color, alpha=0.8, edgecolor='#415A77'))
        
        # Create animation
        frames = len(self.stats_loader.timestamps)
        anim = animation.FuncAnimation(fig, animate, frames=frames, interval=250, repeat=True, blit=False)
        
        if save_path:
            logging.info(f"Saving village count racing animation to {save_path}")
            writer = animation.FFMpegWriter(fps=5, metadata=dict(artist='TWMap'), bitrate=3200)
            anim.save(save_path, writer=writer)
            
        return anim


def create_world_stats_animations(world_id: str, server: str = "en", save_dir: str = "videos"):
    """Create all animated statistics for a world as MP4 videos."""
    if not MATPLOTLIB_AVAILABLE:
        logging.error("matplotlib is required. Install with: pip install matplotlib")
        return
    
    # Load world data
    logging.info(f"Creating animated statistics videos for world {server}{world_id}")
    stats_loader = WorldStatsLoader(world_id, server)
    stats_loader.load_all_snapshots()
    
    if len(stats_loader.timestamps) == 0:
        logging.error(f"No snapshots found for world {world_id}")
        return
        
    # Create plotter
    plotter = AnimatedStatsPlotter(stats_loader)
    
    # Create output directory
    os.makedirs(f"{save_dir}/{world_id}", exist_ok=True)
    
    # Generate animations as MP4 videos
    try:
        logging.info("Creating player points animation...")
        player_anim = plotter.create_player_points_animation(f"{save_dir}/{world_id}/player_points_growth.mp4")
        
        logging.info("Creating tribe points animation...")
        tribe_anim = plotter.create_tribe_points_animation(f"{save_dir}/{world_id}/tribe_points_growth.mp4")
        
        logging.info("Creating village count animation...")
        village_anim = plotter.create_village_count_animation(f"{save_dir}/{world_id}/village_count_growth.mp4")
        
        logging.info(f"All animations saved to {save_dir}/{world_id}/")
        
    except Exception as e:
        logging.error(f"Error creating animations: {e}")
        raise


# Main execution
if __name__ == "__main__":
    """
    Example usage:
    
    This script creates animated statistics showing the growth of top 10 players and tribes 
    over time for a Tribal Wars world. It generates three types of animations:
    
    1. Player Points Growth - Shows how player points evolve over time
    2. Tribe Points Growth - Shows how tribe points evolve over time  
    3. Village Count Growth - Shows how player village counts grow over time
    
    The animations use the same TW color scheme as the timelapse images and show
    the progression over the available snapshot timeline.
    
    Usage examples:
    
    # Create animations for world en146
    python -m twmap.stats.stats
    
    # Or programmatically:
    from twmap.stats.stats import create_world_stats_animations
    create_world_stats_animations("146", "en", save_dir="my_gifs")
    """
    
    # Example usage - Change these values for your desired world
    world_id = "146"  # World number (just the number)
    server = "en"     # Server (en, de, nl, etc.)
    
    try:
        create_world_stats_animations(world_id, server)
        logging.info("Animation creation completed successfully!")
        logging.info(f"Animated MP4 videos saved to: videos/{world_id}/")
        logging.info("Files created:")
        logging.info("  - player_points_growth.mp4")
        logging.info("  - tribe_points_growth.mp4") 
        logging.info("  - village_count_growth.mp4")
    except Exception as e:
        logging.error(f"Failed to create animations: {e}")
        sys.exit(1)

