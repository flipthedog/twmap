import logging
import os
from datetime import datetime
from typing import List, Dict
import pandas as pd
import numpy as np

from twmap.world.world_loader import WorldLoader
from twmap.snapshot.dataloader import DataLoader
from twmap.snapshot.datafilter import DataFilter
from twmap.snapshot.snapshot_datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel
from twmap.map.colors import ColorManager

# Set up matplotlib for animations
try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib not available. Please install with: pip install matplotlib")

color_manager = ColorManager()

def extract_s3_key(s3_path: str) -> str:
    if s3_path.startswith('s3://'):
        # Remove s3://bucket-name/ prefix
        parts = s3_path.split('/', 3)
        return parts[3] if len(parts) > 3 else s3_path
    return s3_path

def compute_world_statistics(world: str, server: str = "en", interval: int = 1):
    """Compute statistics for a given world
    
    Args:
        world: World number (e.g., "143")
        server: Server name (e.g., "en")
        interval: Process every nth frame (default: 1, meaning all frames)
    Returns:
        Dictionary with statistics
    """
    # Load world
    world_loader = WorldLoader(world=world, server=server)
    world_model = world_loader.load_world()

    if not world_model:
        raise ValueError(f"World {server}{world} not found")
    
    # Load snapshot data
    data_loader = DataLoader(world_loader)

    tribe_models, player_models, village_models, conquer_models, killall_models, killall_tribe_models = data_loader.load_all_files()
    
    # I want to prepare the following statistics:
    # - Total number of villages of the top 10 players 
    # - Total number of points of the top 10 players
    # - Total OD of the top 10 players
    # - Total number of villages of the top 10 tribes
    # - Total number of points of the top 10 tribes
    # - Total OD of the top 10 tribes

    stats = [

    ]

    for i in range(0, len(tribe_models), interval):
                
        villages = village_models[i]
        players = player_models[i]
        tribes = tribe_models[i]
        conquers = conquer_models[i]
        killalls = killall_models[i]
        killall_tribes = killall_tribe_models[i]

        # Skip if any dataframes are empty
        if (villages.empty or players.empty or tribes.empty):
            continue

        print(f"Processing snapshot {i+1}/{len(world_model.snapshots)} with {len(villages)} villages, {len(players)} players, {len(tribes)} tribes, {len(conquers)} conquers, {len(killalls)} killalls, {len(killall_tribes)} killall tribes")
        print(f"  Sample villages: {villages[:3]}")

        data_filter = DataFilter(
            village_df=villages,
            player_df=players,
            tribe_df=tribes,
            conquer_df=conquers,
            killall_df=killalls,
            killall_df_tribe=killall_tribes
        )

        t10_players = data_filter.get_t10_players()
        t10_players_od = data_filter.get_killall_t10_players()
        t10_villages = data_filter.get_t10_player_villages()
        t10_players_past_conquers = data_filter.get_past_day_t10_conquers_players()
        
        t10_tribes = data_filter.get_t10_tribes()
        t10_tribes_od = data_filter.get_killall_t10_tribes()
        t10_tribe_villages = data_filter.get_t10_tribe_villages()
        t10_tribes_past_conquers = data_filter.get_past_day_t10_conquers_tribes()

        stats.append({
            "timestamp": data_filter.printed_timestamp,
            "t10_players": t10_players,
            "t10_players_od": t10_players_od,
            "t10_player_villages": t10_villages,
            "t10_players_past_conquers": t10_players_past_conquers,
            "t10_tribes": t10_tribes,
            "t10_tribes_od": t10_tribes_od,
            "t10_tribe_villages": t10_tribe_villages,
            "t10_tribes_past_conquers": t10_tribes_past_conquers,
        })

    return stats


def create_stats_animation(stats: List[Dict], world: str, server: str = "en", save_dir: str = "videos"):
    """Create racing line chart animation from computed statistics.
    
    Args:
        stats: List of statistics dictionaries from compute_world_statistics
        world: World number
        server: Server name
        save_dir: Directory to save the video
    """
    if not MATPLOTLIB_AVAILABLE:
        logging.error("matplotlib is required for animations. Install with: pip install matplotlib")
        return
    
    if not stats:
        logging.error("No statistics data provided")
        return
    
    # Create output directory
    os.makedirs(f"{save_dir}/{world}", exist_ok=True)
    
    # Initialize color manager with better color assignment
    # Use the sunset gradient for better visual distinction
    color_manager = ColorManager()
    color_manager.create_custom_color_map(color_manager.sunset_gradient)
    
    # Collect all unique player and tribe IDs and assign colors via ColorManager
    for stat in stats:
        if stat['t10_players'] is not None:
            for _, player in stat['t10_players'].iterrows():
                # This will automatically assign and cache colors
                color_manager.get_color(f"player_{player['playerid']}")
        if stat['t10_tribes'] is not None:
            for _, tribe in stat['t10_tribes'].iterrows():
                # This will automatically assign and cache colors
                color_manager.get_color(f"tribe_{tribe['tribeid']}")
    
    # Create player points animation
    _create_player_points_animation(stats, world, server, save_dir, color_manager)
    
    # Create player OD animation
    _create_player_od_animation(stats, world, server, save_dir, color_manager)
    
    # Create tribe points animation
    _create_tribe_points_animation(stats, world, server, save_dir, color_manager)
    
    # Create tribe OD animation
    _create_tribe_od_animation(stats, world, server, save_dir, color_manager)
    
    logging.info(f"All animations saved to {save_dir}/{world}/")


def _create_player_points_animation(stats, world, server, save_dir, color_manager):
    """Create racing line chart for player points."""
    fig, ax = plt.subplots(figsize=(20, 12))
    
    # Black background
    bg_color = '#000000'
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    plt.style.use('dark_background')
    
    def animate(frame):
        ax.clear()
        ax.set_facecolor(bg_color)
        
        if frame >= len(stats):
            return
        
        current_stat = stats[frame]
        current_time = datetime.strptime(current_stat['timestamp'], '%Y-%m-%d %H:%M:%S')
        
        # Get current top 10 players
        if current_stat['t10_players'] is None or current_stat['t10_players'].empty:
            return
        
        top_10 = current_stat['t10_players'].nlargest(10, 'points')
        
        # Collect historical data for these players
        player_histories = {}
        for _, player in top_10.iterrows():
            player_id = player['playerid']
            player_histories[player_id] = {
                'timestamps': [],
                'points': [],
                'names': []
            }
            
            # Go through all previous frames to build history
            for i in range(max(0, frame - 30), frame + 1):  # Last 30 frames window
                if i >= len(stats):
                    break
                prev_stat = stats[i]
                if prev_stat['t10_players'] is not None:
                    player_row = prev_stat['t10_players'][prev_stat['t10_players']['playerid'] == player_id]
                    if not player_row.empty:
                        player_histories[player_id]['timestamps'].append(
                            datetime.strptime(prev_stat['timestamp'], '%Y-%m-%d %H:%M:%S')
                        )
                        player_histories[player_id]['points'].append(player_row.iloc[0]['points'])
                        player_histories[player_id]['names'].append(player_row.iloc[0]['name'])
        
        # Plot lines for each player
        all_points = []
        for i, (_, player) in enumerate(top_10.iterrows()):
            player_id = player['playerid']
            player_name = player['name']
            history = player_histories.get(player_id, {})
            
            if not history.get('timestamps'):
                continue
            
            # Use default colors based on ranking (1-10)
            color = color_manager.default_colors[i % len(color_manager.default_colors)]
            
            timestamps = history['timestamps']
            points = history['points']
            
            all_points.extend(points)
            
            # Interpolate for smoother animation
            if len(timestamps) > 1:
                try:
                    from scipy.interpolate import interp1d
                    
                    time_nums = np.array([t.timestamp() for t in timestamps])
                    points_array = np.array(points)
                    
                    # Create interpolation function
                    f = interp1d(time_nums, points_array, kind='linear', bounds_error=False, fill_value='extrapolate')
                    
                    # Generate more points for smoother line (5x density)
                    smooth_time_nums = np.linspace(time_nums[0], time_nums[-1], len(time_nums) * 5)
                    smooth_timestamps = [datetime.fromtimestamp(ts) for ts in smooth_time_nums]
                    smooth_points = f(smooth_time_nums)
                    
                    # Plot smooth line with glow effect
                    ax.plot(smooth_timestamps, smooth_points, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                    ax.plot(smooth_timestamps, smooth_points, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                    ax.plot(smooth_timestamps, smooth_points, color=color, linewidth=12, alpha=0.1, zorder=20-i)
                except:
                    # Fallback to direct plotting
                    ax.plot(timestamps, points, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                    ax.plot(timestamps, points, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                    ax.plot(timestamps, points, color=color, linewidth=12, alpha=0.1, zorder=20-i)
            else:
                # Plot line with glow effect
                ax.plot(timestamps, points, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                ax.plot(timestamps, points, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                ax.plot(timestamps, points, color=color, linewidth=12, alpha=0.1, zorder=20-i)
            
            # Add markers
            ax.scatter(timestamps, points, color=color, s=40, alpha=0.8, zorder=25-i, edgecolors='white', linewidth=1.5)
            
            # Add player name at current point
            if timestamps and points:
                player_name = history['names'][-1] if history.get('names') else player['name']
                ax.annotate(f"{i+1}. {player_name[:12]}", 
                          xy=(timestamps[-1], points[-1]),
                          xytext=(10, 0), textcoords='offset points',
                          color=color, fontweight='bold', fontsize=11,
                          bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7, edgecolor='white'),
                          ha='left', va='center')
        
        # Styling
        ax.set_xlabel('Date', color='#E0E6ED', fontsize=16, fontweight='bold')
        ax.set_ylabel('Points', color='#E0E6ED', fontsize=16, fontweight='bold')
        ax.set_title(f'🏆 Top 10 Player Points - World {server}{world}', 
                    color='#FFF8DC', fontsize=20, fontweight='bold', pad=30)
        
        ax.grid(True, alpha=0.4, color='#415A77', linestyle='-', linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors='#E0E6ED', labelsize=12)
        
        # Format y-axis with thousands separator
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        # Dynamic y-axis
        if all_points:
            min_p, max_p = min(all_points), max(all_points)
            padding = (max_p - min_p) * 0.1
            ax.set_ylim(max(0, min_p - padding), max_p + padding)
        
        for spine in ax.spines.values():
            spine.set_color('#415A77')
            spine.set_linewidth(2)
        
        # Info box
        info_text = f"📅 {current_time.strftime('%Y-%m-%d %H:%M')}"
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, color='#FFF8DC', fontsize=13,
               verticalalignment='top', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.8', facecolor=bg_color, alpha=0.9, edgecolor='#415A77', linewidth=2))
    
    anim = animation.FuncAnimation(fig, animate, frames=len(stats), interval=300, repeat=True, blit=False)
    
    save_path = f"{save_dir}/{world}/player_points_growth.mp4"
    logging.info(f"Saving player points animation to {save_path}")
    writer = animation.FFMpegWriter(fps=8, metadata=dict(artist='TWMap'), bitrate=4000)
    anim.save(save_path, writer=writer)
    plt.close(fig)


def _create_tribe_points_animation(stats, world, server, save_dir, color_manager):
    """Create racing line chart for tribe points."""
    fig, ax = plt.subplots(figsize=(20, 12))
    
    # Black background
    bg_color = '#000000'
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    plt.style.use('dark_background')
    
    def animate(frame):
        ax.clear()
        ax.set_facecolor(bg_color)
        
        if frame >= len(stats):
            return
        
        current_stat = stats[frame]
        current_time = datetime.strptime(current_stat['timestamp'], '%Y-%m-%d %H:%M:%S')
        
        # Get current top 10 tribes
        if current_stat['t10_tribes'] is None or current_stat['t10_tribes'].empty:
            return
        
        top_10 = current_stat['t10_tribes'].nlargest(10, 'tribe_points')
        
        # Collect historical data for these tribes
        tribe_histories = {}
        for _, tribe in top_10.iterrows():
            tribe_id = tribe['tribeid']
            tribe_histories[tribe_id] = {
                'timestamps': [],
                'points': [],
                'tags': []
            }
            
            # Go through all previous frames to build history
            for i in range(max(0, frame - 30), frame + 1):
                if i >= len(stats):
                    break
                prev_stat = stats[i]
                if prev_stat['t10_tribes'] is not None:
                    tribe_row = prev_stat['t10_tribes'][prev_stat['t10_tribes']['tribeid'] == tribe_id]
                    if not tribe_row.empty:
                        tribe_histories[tribe_id]['timestamps'].append(
                            datetime.strptime(prev_stat['timestamp'], '%Y-%m-%d %H:%M:%S')
                        )
                        tribe_histories[tribe_id]['points'].append(tribe_row.iloc[0]['tribe_points'])
                        tribe_histories[tribe_id]['tags'].append(tribe_row.iloc[0]['tag'])
        
        # Plot lines for each tribe
        all_points = []
        for i, (_, tribe) in enumerate(top_10.iterrows()):
            tribe_id = tribe['tribeid']
            tribe_tag = tribe['tag']
            history = tribe_histories.get(tribe_id, {})
            
            if not history.get('timestamps'):
                continue
            
            # Use default colors based on ranking (1-10)
            color = color_manager.default_colors[i % len(color_manager.default_colors)]
            
            timestamps = history['timestamps']
            points = history['points']
            
            all_points.extend(points)
            
            # Interpolate for smoother animation
            if len(timestamps) > 1:
                try:
                    from scipy.interpolate import interp1d
                    
                    time_nums = np.array([t.timestamp() for t in timestamps])
                    points_array = np.array(points)
                    
                    # Create interpolation function
                    f = interp1d(time_nums, points_array, kind='linear', bounds_error=False, fill_value='extrapolate')
                    
                    # Generate more points for smoother line (5x density)
                    smooth_time_nums = np.linspace(time_nums[0], time_nums[-1], len(time_nums) * 5)
                    smooth_timestamps = [datetime.fromtimestamp(ts) for ts in smooth_time_nums]
                    smooth_points = f(smooth_time_nums)
                    
                    # Plot smooth line with glow effect
                    ax.plot(smooth_timestamps, smooth_points, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                    ax.plot(smooth_timestamps, smooth_points, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                    ax.plot(smooth_timestamps, smooth_points, color=color, linewidth=12, alpha=0.1, zorder=20-i)
                except:
                    # Fallback to direct plotting
                    ax.plot(timestamps, points, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                    ax.plot(timestamps, points, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                    ax.plot(timestamps, points, color=color, linewidth=12, alpha=0.1, zorder=20-i)
            else:
                # Plot line with glow effect
                ax.plot(timestamps, points, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                ax.plot(timestamps, points, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                ax.plot(timestamps, points, color=color, linewidth=12, alpha=0.1, zorder=20-i)
            
            ax.scatter(timestamps, points, color=color, s=40, alpha=0.8, zorder=25-i, edgecolors='white', linewidth=1.5)
            
            # Add tribe tag at current point
            if timestamps and points:
                tribe_tag = history['tags'][-1] if history.get('tags') else tribe['tag']
                ax.annotate(f"{i+1}. [{tribe_tag}]", 
                          xy=(timestamps[-1], points[-1]),
                          xytext=(10, 0), textcoords='offset points',
                          color=color, fontweight='bold', fontsize=11,
                          bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7, edgecolor='white'),
                          ha='left', va='center')
        
        # Styling
        ax.set_xlabel('Date', color='#E0E6ED', fontsize=16, fontweight='bold')
        ax.set_ylabel('Points', color='#E0E6ED', fontsize=16, fontweight='bold')
        ax.set_title(f'🏆 Top 10 Tribe Points - World {server}{world}', 
                    color='#FFF8DC', fontsize=20, fontweight='bold', pad=30)
        
        ax.grid(True, alpha=0.4, color='#415A77', linestyle='-', linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors='#E0E6ED', labelsize=12)
        
        # Format y-axis with thousands separator
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        # Dynamic y-axis
        if all_points:
            min_p, max_p = min(all_points), max(all_points)
            padding = (max_p - min_p) * 0.1
            ax.set_ylim(max(0, min_p - padding), max_p + padding)
        
        for spine in ax.spines.values():
            spine.set_color('#415A77')
            spine.set_linewidth(2)
        
        # Info box
        info_text = f"📅 {current_time.strftime('%Y-%m-%d %H:%M')}"
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, color='#FFF8DC', fontsize=13,
               verticalalignment='top', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.8', facecolor=bg_color, alpha=0.9, edgecolor='#415A77', linewidth=2))
    
    anim = animation.FuncAnimation(fig, animate, frames=len(stats), interval=300, repeat=True, blit=False)
    
    save_path = f"{save_dir}/{world}/tribe_points_growth.mp4"
    logging.info(f"Saving tribe points animation to {save_path}")
    writer = animation.FFMpegWriter(fps=8, metadata=dict(artist='TWMap'), bitrate=4000)
    anim.save(save_path, writer=writer)
    plt.close(fig)


def _create_player_od_animation(stats, world, server, save_dir, color_manager):
    """Create racing line chart for player OD (Overall Defeats)."""
    fig, ax = plt.subplots(figsize=(20, 12))
    
    # Black background
    bg_color = '#000000'
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    plt.style.use('dark_background')
    
    def animate(frame):
        ax.clear()
        ax.set_facecolor(bg_color)
        
        if frame >= len(stats):
            return
        
        current_stat = stats[frame]
        current_time = datetime.strptime(current_stat['timestamp'], '%Y-%m-%d %H:%M:%S')
        
        # Get current top 10 players by OD
        if current_stat['t10_players_od'] is None or current_stat['t10_players_od'].empty:
            return
        
        top_10 = current_stat['t10_players_od'].nlargest(10, 'units_defeated')
        
        # Collect historical data for these players
        player_histories = {}
        for _, player in top_10.iterrows():
            player_id = player['playerid']
            player_histories[player_id] = {
                'timestamps': [],
                'od': [],
                'names': []
            }
            
            # Go through all previous frames to build history
            for i in range(max(0, frame - 30), frame + 1):
                if i >= len(stats):
                    break
                prev_stat = stats[i]
                if prev_stat['t10_players_od'] is not None:
                    player_row = prev_stat['t10_players_od'][prev_stat['t10_players_od']['playerid'] == player_id]
                    if not player_row.empty:
                        player_histories[player_id]['timestamps'].append(
                            datetime.strptime(prev_stat['timestamp'], '%Y-%m-%d %H:%M:%S')
                        )
                        player_histories[player_id]['od'].append(player_row.iloc[0]['units_defeated'])
                        player_histories[player_id]['names'].append(player_row.iloc[0]['name'])
        
        # Plot lines for each player
        all_od = []
        for i, (_, player) in enumerate(top_10.iterrows()):
            player_id = player['playerid']
            player_name = player['name']
            history = player_histories.get(player_id, {})
            
            if not history.get('timestamps'):
                continue
            
            # Use default colors based on ranking (1-10)
            color = color_manager.default_colors[i % len(color_manager.default_colors)]
            
            timestamps = history['timestamps']
            od = history['od']
            
            all_od.extend(od)
            
            # Interpolate for smoother animation
            if len(timestamps) > 1:
                try:
                    from scipy.interpolate import interp1d
                    
                    time_nums = np.array([t.timestamp() for t in timestamps])
                    od_array = np.array(od)
                    
                    # Create interpolation function
                    f = interp1d(time_nums, od_array, kind='linear', bounds_error=False, fill_value='extrapolate')
                    
                    # Generate more points for smoother line (5x density)
                    smooth_time_nums = np.linspace(time_nums[0], time_nums[-1], len(time_nums) * 5)
                    smooth_timestamps = [datetime.fromtimestamp(ts) for ts in smooth_time_nums]
                    smooth_od = f(smooth_time_nums)
                    
                    # Plot smooth line with glow effect
                    ax.plot(smooth_timestamps, smooth_od, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                    ax.plot(smooth_timestamps, smooth_od, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                    ax.plot(smooth_timestamps, smooth_od, color=color, linewidth=12, alpha=0.1, zorder=20-i)
                except:
                    # Fallback to direct plotting
                    ax.plot(timestamps, od, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                    ax.plot(timestamps, od, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                    ax.plot(timestamps, od, color=color, linewidth=12, alpha=0.1, zorder=20-i)
            else:
                # Plot line with glow effect
                ax.plot(timestamps, od, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                ax.plot(timestamps, od, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                ax.plot(timestamps, od, color=color, linewidth=12, alpha=0.1, zorder=20-i)
            
            # Add markers
            ax.scatter(timestamps, od, color=color, s=40, alpha=0.8, zorder=25-i, edgecolors='white', linewidth=1.5)
            
            # Add player name at current point
            if timestamps and od:
                player_name = history['names'][-1] if history.get('names') else player['name']
                ax.annotate(f"{i+1}. {player_name[:12]}", 
                          xy=(timestamps[-1], od[-1]),
                          xytext=(10, 0), textcoords='offset points',
                          color=color, fontweight='bold', fontsize=11,
                          bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7, edgecolor='white'),
                          ha='left', va='center')
        
        # Styling
        ax.set_xlabel('Date', color='#E0E6ED', fontsize=16, fontweight='bold')
        ax.set_ylabel('Overall Defeats', color='#E0E6ED', fontsize=16, fontweight='bold')
        ax.set_title(f'⚔️ Top 10 Player OD - World {server}{world}', 
                    color='#FFF8DC', fontsize=20, fontweight='bold', pad=30)
        
        ax.grid(True, alpha=0.4, color='#415A77', linestyle='-', linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors='#E0E6ED', labelsize=12)
        
        # Format y-axis with thousands separator
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        # Dynamic y-axis
        if all_od:
            min_od, max_od = min(all_od), max(all_od)
            padding = (max_od - min_od) * 0.1
            ax.set_ylim(max(0, min_od - padding), max_od + padding)
        
        for spine in ax.spines.values():
            spine.set_color('#415A77')
            spine.set_linewidth(2)
        
        # Info box
        info_text = f"📅 {current_time.strftime('%Y-%m-%d %H:%M')}"
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, color='#FFF8DC', fontsize=13,
               verticalalignment='top', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.8', facecolor=bg_color, alpha=0.9, edgecolor='#415A77', linewidth=2))
    
    anim = animation.FuncAnimation(fig, animate, frames=len(stats), interval=300, repeat=True, blit=False)
    
    save_path = f"{save_dir}/{world}/player_od_growth.mp4"
    logging.info(f"Saving player OD animation to {save_path}")
    writer = animation.FFMpegWriter(fps=8, metadata=dict(artist='TWMap'), bitrate=4000)
    anim.save(save_path, writer=writer)
    plt.close(fig)


def _create_tribe_od_animation(stats, world, server, save_dir, color_manager):
    """Create racing line chart for tribe OD (Overall Defeats)."""
    fig, ax = plt.subplots(figsize=(20, 12))
    
    # Black background
    bg_color = '#000000'
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    plt.style.use('dark_background')
    
    def animate(frame):
        ax.clear()
        ax.set_facecolor(bg_color)
        
        if frame >= len(stats):
            return
        
        current_stat = stats[frame]
        current_time = datetime.strptime(current_stat['timestamp'], '%Y-%m-%d %H:%M:%S')
        
        # Get current top 10 tribes by OD
        if current_stat['t10_tribes_od'] is None or current_stat['t10_tribes_od'].empty:
            return
        
        top_10 = current_stat['t10_tribes_od'].nlargest(10, 'units_defeated')
        
        # Collect historical data for these tribes
        tribe_histories = {}
        for _, tribe in top_10.iterrows():
            tribe_id = tribe['tribeid']
            tribe_histories[tribe_id] = {
                'timestamps': [],
                'od': [],
                'tags': []
            }
            
            # Go through all previous frames to build history
            for i in range(max(0, frame - 30), frame + 1):
                if i >= len(stats):
                    break
                prev_stat = stats[i]
                if prev_stat['t10_tribes_od'] is not None:
                    tribe_row = prev_stat['t10_tribes_od'][prev_stat['t10_tribes_od']['tribeid'] == tribe_id]
                    if not tribe_row.empty:
                        tribe_histories[tribe_id]['timestamps'].append(
                            datetime.strptime(prev_stat['timestamp'], '%Y-%m-%d %H:%M:%S')
                        )
                        tribe_histories[tribe_id]['od'].append(tribe_row.iloc[0]['units_defeated'])
                        tribe_histories[tribe_id]['tags'].append(tribe_row.iloc[0]['tag'])
        
        # Plot lines for each tribe
        all_od = []
        for i, (_, tribe) in enumerate(top_10.iterrows()):
            tribe_id = tribe['tribeid']
            tribe_tag = tribe['tag']
            history = tribe_histories.get(tribe_id, {})
            
            if not history.get('timestamps'):
                continue
            
            # Use default colors based on ranking (1-10)
            color = color_manager.default_colors[i % len(color_manager.default_colors)]
            
            timestamps = history['timestamps']
            od = history['od']
            
            all_od.extend(od)
            
            # Interpolate for smoother animation
            if len(timestamps) > 1:
                try:
                    from scipy.interpolate import interp1d
                    
                    time_nums = np.array([t.timestamp() for t in timestamps])
                    od_array = np.array(od)
                    
                    # Create interpolation function
                    f = interp1d(time_nums, od_array, kind='linear', bounds_error=False, fill_value='extrapolate')
                    
                    # Generate more points for smoother line (5x density)
                    smooth_time_nums = np.linspace(time_nums[0], time_nums[-1], len(time_nums) * 5)
                    smooth_timestamps = [datetime.fromtimestamp(ts) for ts in smooth_time_nums]
                    smooth_od = f(smooth_time_nums)
                    
                    # Plot smooth line with glow effect
                    ax.plot(smooth_timestamps, smooth_od, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                    ax.plot(smooth_timestamps, smooth_od, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                    ax.plot(smooth_timestamps, smooth_od, color=color, linewidth=12, alpha=0.1, zorder=20-i)
                except:
                    # Fallback to direct plotting
                    ax.plot(timestamps, od, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                    ax.plot(timestamps, od, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                    ax.plot(timestamps, od, color=color, linewidth=12, alpha=0.1, zorder=20-i)
            else:
                # Plot line with glow effect
                ax.plot(timestamps, od, color=color, linewidth=4, alpha=0.9, zorder=20-i)
                ax.plot(timestamps, od, color=color, linewidth=8, alpha=0.3, zorder=20-i)
                ax.plot(timestamps, od, color=color, linewidth=12, alpha=0.1, zorder=20-i)
            
            ax.scatter(timestamps, od, color=color, s=40, alpha=0.8, zorder=25-i, edgecolors='white', linewidth=1.5)
            
            # Add tribe tag at current point
            if timestamps and od:
                tribe_tag = history['tags'][-1] if history.get('tags') else tribe['tag']
                ax.annotate(f"{i+1}. [{tribe_tag}]", 
                          xy=(timestamps[-1], od[-1]),
                          xytext=(10, 0), textcoords='offset points',
                          color=color, fontweight='bold', fontsize=11,
                          bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7, edgecolor='white'),
                          ha='left', va='center')
        
        # Styling
        ax.set_xlabel('Date', color='#E0E6ED', fontsize=16, fontweight='bold')
        ax.set_ylabel('Overall Defeats', color='#E0E6ED', fontsize=16, fontweight='bold')
        ax.set_title(f'⚔️ Top 10 Tribe OD - World {server}{world}', 
                    color='#FFF8DC', fontsize=20, fontweight='bold', pad=30)
        
        ax.grid(True, alpha=0.4, color='#415A77', linestyle='-', linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors='#E0E6ED', labelsize=12)
        
        # Format y-axis with thousands separator
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        # Dynamic y-axis
        if all_od:
            min_od, max_od = min(all_od), max(all_od)
            padding = (max_od - min_od) * 0.1
            ax.set_ylim(max(0, min_od - padding), max_od + padding)
        
        for spine in ax.spines.values():
            spine.set_color('#415A77')
            spine.set_linewidth(2)
        
        # Info box
        info_text = f"📅 {current_time.strftime('%Y-%m-%d %H:%M')}"
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, color='#FFF8DC', fontsize=13,
               verticalalignment='top', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.8', facecolor=bg_color, alpha=0.9, edgecolor='#415A77', linewidth=2))
    
    anim = animation.FuncAnimation(fig, animate, frames=len(stats), interval=300, repeat=True, blit=False)
    
    save_path = f"{save_dir}/{world}/tribe_od_growth.mp4"
    logging.info(f"Saving tribe OD animation to {save_path}")
    writer = animation.FFMpegWriter(fps=8, metadata=dict(artist='TWMap'), bitrate=4000)
    anim.save(save_path, writer=writer)
    plt.close(fig)


if __name__ == "__main__":
    import pprint

    logging.basicConfig(level=logging.INFO)
    
    world = "146"
    server = "en"
    interval = 4  # meaning do one every 4 frames
    
    # Compute statistics
    stats = compute_world_statistics(world=world, server=server, interval=interval)
    
    # Create animations
    if stats:
        logging.info(f"Successfully computed {len(stats)} snapshots of statistics")
        create_stats_animation(stats, world=world, server=server)
        logging.info("Animation creation completed!")
    else:
        logging.error("No statistics computed")