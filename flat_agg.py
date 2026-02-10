import pandas as pd

def get_flat_events_aggregation(events_df):
    if events_df.empty:
        return None

    # This list will hold all our little dataframes (kills, wards, etc.)
    partial_dfs = []

    # Helper: filters invalid IDs, counts occurrences, and sets the index for easy merging
    def count_events(df, user_col, feature_name):
        if df.empty or user_col not in df.columns:
            return
        
        # Filter: ID must exist and not be 0 (Neutral/Minion)
        valid = df[df[user_col].notna() & (df[user_col] != 0)]
        
        if not valid.empty:
            # Group by Match -> Frame -> Player
            agg = valid.groupby(["match_id", "frame", user_col]).size()
            agg.name = feature_name
            agg.index.names = ["match_id", "frame", "participant_id"]
            partial_dfs.append(agg)

    # --- 1. Simple Counts ---
    # (Event Type, Column to Count, New Column Name)
    metrics = [
        ("CHAMPION_KILL", "killerId", "kills_in_frame"),
        ("CHAMPION_KILL", "victimId", "deaths_in_frame"),
        ("WARD_PLACED",   "creatorId", "wards_placed"),
        ("WARD_KILL",     "killerId", "wards_destroyed"),
        ("BUILDING_KILL", "killerId", "turrets_killed"),
        ("TURRET_PLATE_DESTROYED", "killerId", "plates_taken")
    ]

    for evt_type, col, name in metrics:
        count_events(events_df[events_df["type"] == evt_type], col, name)

    # --- 2. Assists ---
    # We assume 'assistingParticipantIds' is already a list. If not, this won't error, but won't count correctly.
    kills = events_df[events_df["type"] == "CHAMPION_KILL"]
    if "assistingParticipantIds" in kills.columns:
        assists = kills.explode("assistingParticipantIds")
        count_events(assists, "assistingParticipantIds", "assists_in_frame")

    # --- 3. Monsters (Crash Fixed) ---
    monsters = events_df[events_df["type"] == "ELITE_MONSTER_KILL"]
    if not monsters.empty and "monsterType" in monsters.columns:
        monster_map = {
            "DRAGON": "dragons_killed",
            "BARON_NASHOR": "barons_killed",
            "RIFTHERALD": "heralds_killed",
            "HORDE": "grubs_killed"
        }
        for m_type, name in monster_map.items():
            count_events(monsters[monsters["monsterType"] == m_type], "killerId", name)

    # --- 4. Bounty Gold (Summation) ---
    if "shutdownBounty" in kills.columns:
        valid_bounty = kills[kills["shutdownBounty"] > 0]
        if not valid_bounty.empty:
            agg = valid_bounty.groupby(["match_id", "frame", "killerId"])["shutdownBounty"].sum()
            agg.name = "bounty_gold_earned"
            agg.index.names = ["match_id", "frame", "participant_id"]
            partial_dfs.append(agg)

    # --- 5. Final Merge ---
    if not partial_dfs:
        return None

    # Combine everything at once (Fastest method)
    result = pd.concat(partial_dfs, axis=1)
    
    # Fill missing values with 0 and return regular columns
    return result.fillna(0).reset_index()