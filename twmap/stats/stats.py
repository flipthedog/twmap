from twmap.world.world_loader import WorldLoader
from twmap.snapshot.dataloader import DataLoader
from twmap.snapshot.datafilter import DataFilter
from twmap.snapshot.snapshot_datamodel import VillageModel, PlayerModel, TribeModel, ConquerModel
from twmap.map.colors import ColorManager

def extract_s3_key(s3_path: str) -> str:
    if s3_path.startswith('s3://'):
        # Remove s3://bucket-name/ prefix
        parts = s3_path.split('/', 3)
        return parts[3] if len(parts) > 3 else s3_path
    return s3_path

def compute_world_statistics(world: str, server: str = "en"):
    """Compute statistics for a given world
    
    Args:
        world: World number (e.g., "143")
        server: Server name (e.g., "en")
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

    tribe_models, player_models, village_models, conquer_models, killall_models, killall_tribe_models = data_loader.load_all_files(limit=40)
    
    # I want to prepare the following statistics:
    # - Total number of villages of the top 10 players 
    # - Total number of points of the top 10 players
    # - Total OD of the top 10 players
    # - Total number of villages of the top 10 tribes
    # - Total number of points of the top 10 tribes
    # - Total OD of the top 10 tribes

    stats = [

    ]

    for i in range(0, len(tribe_models)):
                
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



if __name__ == "__main__":
    import logging
    import pprint

    logging.basicConfig(level=logging.INFO)
    
    world = "150"
    server = "en"
    interval = 2

    stats = compute_world_statistics(world=world, server=server)

    pprint.pprint(stats)