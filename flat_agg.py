import pandas as pd
import logging
from pipeline_utils import has_cols

log = logging.getLogger(__name__)

def get_flat_events_aggregation(events_df):

    if events_df.empty or "type" not in events_df.columns:
        log.info("get_flat_events_aggregation: empty or ISNT 'type' column, returning None")
        return None
    # This list will hold all our little dataframes (kills, wards, etc.)
    partial_dfs = []


    def count_events(df, user_col, feature_name):
        if not has_cols(df, user_col):
            return
        
        # Filter: ID must exist and not be 0 (Neutral/Minion)
        valid = df[df[user_col].notna() & (df[user_col] != 0)]
        if valid.empty:
            return
        
        if not valid.empty:
            # Group by Match -> Frame -> Player
            agg = valid.groupby(["match_id", "frame", user_col]).size()
            agg.name = feature_name
            agg.index.names = ["match_id", "frame", "participant_id"]
            partial_dfs.append(agg)

    # --- 1. Simple Counts ---
    metrics = [
        ("CHAMPION_KILL",           "killerId",  "kills_in_frame"),
        ("CHAMPION_KILL",           "victimId",  "deaths_in_frame"),
        ("WARD_PLACED",             "creatorId", "wards_placed"),
        ("WARD_KILL",               "killerId",  "wards_destroyed"),
        ("BUILDING_KILL",           "killerId",  "turrets_killed"),
        ("TURRET_PLATE_DESTROYED",  "killerId",  "plates_taken"),
    ]
    for evt_type, col, name in metrics:
        subset = events_df[events_df["type"] == evt_type]
        count_events(subset, col, name)

    # --- 2. Assists ---
    kills = events_df[events_df["type"] == "CHAMPION_KILL"]
    if has_cols(kills, "assistingParticipantIds"):
        assists = kills.explode("assistingParticipantIds")
        count_events(assists, "assistingParticipantIds", "assists_in_frame")

    # --- 3. Monsters ---
    monsters = events_df[events_df["type"] == "ELITE_MONSTER_KILL"]
    if has_cols(monsters, "monsterType", "killerId"):
        monster_map = {
            "DRAGON":       "dragons_killed",
            "BARON_NASHOR": "barons_killed",
            "RIFTHERALD":   "heralds_killed",
            "HORDE":        "grubs_killed",
        }
        for m_type, name in monster_map.items():
            count_events(monsters[monsters["monsterType"] == m_type], "killerId", name)

    # --- 4. Bounty Gold ---
    if has_cols(kills, "shutdownBounty", "killerId"):
        valid_bounty = kills[kills["shutdownBounty"] > 0]
        if not valid_bounty.empty:
            agg = valid_bounty.groupby(["match_id", "frame", "killerId"])["shutdownBounty"].sum()
            agg.name = "bounty_gold_earned"
            agg.index.names = ["match_id", "frame", "participant_id"]
            partial_dfs.append(agg)

    # --- 5. Combine ---
    if not partial_dfs:
        log.info("get_flat_events_aggregation: zero events matched any metric")
        return None

    result = pd.concat(partial_dfs, axis=1).fillna(0).reset_index()
    return result