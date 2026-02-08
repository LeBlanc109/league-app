import pandas as pd
# ═══════════════════════════════════════════
# DEEP ANALYSIS — exploding nested lists
# ═══════════════════════════════════════════

def _explode_kill_damage(events_df):
    """
    Helper: explode victimDamageReceived and victimDamageDealt
    into their own flat DataFrames. Called once, results passed to features.
    """
    kills = events_df[events_df["type"] == "CHAMPION_KILL"].copy()
    kills["kill_id"] = range(len(kills))

    def _explode_damage_list(kills_df, column_name):
        base = kills_df[["kill_id", "match_id", "frame", "killerId", "victimId", column_name]].copy()
        base = base.dropna(subset=[column_name])
        base = base.explode(column_name)

        # Normalize the dicts into columns
        damage_details = pd.json_normalize(base[column_name])
        damage_details.index = base.index

        # Combine with kill metadata
        result = base[["kill_id", "match_id", "frame", "killerId", "victimId"]].copy()
        result["dmg_source_name"] = damage_details.get("name", "")
        result["dmg_source_participant"] = damage_details.get("participantId")
        result["dmg_spell_name"] = damage_details.get("spellName", "")
        result["dmg_magic"] = damage_details.get("magicDamage", 0)
        result["dmg_physical"] = damage_details.get("physicalDamage", 0)
        result["dmg_true"] = damage_details.get("trueDamage", 0)
        return result

    damage_recv = _explode_damage_list(kills, "victimDamageReceived")
    damage_dealt = _explode_damage_list(kills, "victimDamageDealt")

    return kills, damage_recv, damage_dealt


# 5. Tower Shots Taken (died to tower dive)
def add_kill_features(stats_df, events_df):
    """
    Adds tower_deaths, free_kills, and zero_dmg_deaths
    from a single call to _explode_kill_damage.
    """
    kills, damage_recv, damage_dealt = _explode_kill_damage(events_df)

    # --- Tower Deaths ---
    tower_dmg = damage_recv[damage_recv["dmg_source_name"].str.contains("Turret|Tower", case=False, na=False)]
    tower_kills = tower_dmg[["kill_id", "match_id", "frame", "victimId"]].drop_duplicates(subset=["kill_id"])
    tower_deaths = tower_kills.groupby(["match_id", "frame", "victimId"]).size().reset_index(name="tower_deaths")
    tower_deaths = tower_deaths.rename(columns={"victimId": "participant_id"})

    stats_df = stats_df.merge(tower_deaths, on=["match_id", "frame", "participant_id"], how="left")
    stats_df["tower_deaths"] = stats_df["tower_deaths"].fillna(0).astype(int)

    # --- Free Kills ---
    victim_dmg_back = damage_dealt.groupby("kill_id").agg(
        magic_back=("dmg_magic", "sum"),
        phys_back=("dmg_physical", "sum"),
        true_back=("dmg_true", "sum"),
    ).reset_index()
    victim_dmg_back["total_dmg_back"] = victim_dmg_back["magic_back"] + victim_dmg_back["phys_back"] + victim_dmg_back["true_back"]

    kills = kills.merge(victim_dmg_back[["kill_id", "total_dmg_back"]], on="kill_id", how="left")
    kills["total_dmg_back"] = kills["total_dmg_back"].fillna(0)
    kills["is_free_kill"] = (kills["total_dmg_back"] < 100).astype(int)

    free_kills = kills.groupby(["match_id", "frame", "killerId"])["is_free_kill"].sum().reset_index(name="free_kills")
    free_kills = free_kills.rename(columns={"killerId": "participant_id"})

    stats_df = stats_df.merge(free_kills, on=["match_id", "frame", "participant_id"], how="left")
    stats_df["free_kills"] = stats_df["free_kills"].fillna(0).astype(int)

    # --- Zero Damage Deaths ---
    kills_with_dealt = damage_dealt["kill_id"].unique()
    kills["victim_did_zero"] = (~kills["kill_id"].isin(kills_with_dealt)).astype(int)

    zero_deaths = kills.groupby(["match_id", "frame", "victimId"])["victim_did_zero"].sum().reset_index(name="zero_dmg_deaths")
    zero_deaths = zero_deaths.rename(columns={"victimId": "participant_id"})

    stats_df = stats_df.merge(zero_deaths, on=["match_id", "frame", "participant_id"], how="left")
    stats_df["zero_dmg_deaths"] = stats_df["zero_dmg_deaths"].fillna(0).astype(int)

    return stats_df


def _count_assists(assist_list):
    """Helper to count assists without lambda."""
    if isinstance(assist_list, list):
        return len(assist_list) + 1
    return 1

def add_ganked_deaths(stats_df, events_df):
    kills = events_df[events_df["type"] == "CHAMPION_KILL"].copy()

    kills["num_involved"] = kills["assistingParticipantIds"].apply(_count_assists)
    kills["was_ganked"] = (kills["num_involved"] >= 3).astype(int)

    ganked = kills.groupby(["match_id", "frame", "victimId"])["was_ganked"].sum().reset_index(name="ganked_deaths")
    ganked = ganked.rename(columns={"victimId": "participant_id"})

    stats_df = stats_df.merge(ganked, on=["match_id", "frame", "participant_id"], how="left")
    stats_df["ganked_deaths"] = stats_df["ganked_deaths"].fillna(0).astype(int)
    return stats_df


def add_objective_streaks(stats_df, events_df):
    objectives = events_df[events_df["type"].isin(["ELITE_MONSTER_KILL", "BUILDING_KILL"])].copy()
    objectives = objectives.sort_values(["match_id", "frame", "timestamp"])

    objectives["obj_team"] = objectives["killerTeamId"].fillna(0)
    building_mask = objectives["type"] == "BUILDING_KILL"
    objectives.loc[building_mask, "obj_team"] = objectives.loc[building_mask, "teamId"].map({100: 200, 200: 100})

    objectives["team_changed"] = (objectives["obj_team"] != objectives["obj_team"].shift()).astype(int)
    objectives["streak_group"] = objectives.groupby("match_id")["team_changed"].cumsum()
    objectives["obj_streak"] = objectives.groupby(["match_id", "streak_group"]).cumcount() + 1

    obj_streak = objectives[["match_id", "frame", "obj_team", "obj_streak"]].copy()
    obj_streak = obj_streak.rename(columns={"obj_team": "team"})
    obj_streak = obj_streak.groupby(["match_id", "frame", "team"])["obj_streak"].max().reset_index()

    stats_df = stats_df.merge(obj_streak, on=["match_id", "frame", "team"], how="left")
    stats_df["obj_streak"] = stats_df.groupby(["match_id", "participant_id"])["obj_streak"].ffill().fillna(0).astype(int)
    return stats_df


# ═══════════════════════════════════════════
# Grubs → Tower Damage (frame-aware)
# ═══════════════════════════════════════════

def add_grub_tower_impact(stats_df, events_df):
    """Track tower damage in the 5 frames after getting grubs."""
    grubs = events_df[(events_df["type"] == "ELITE_MONSTER_KILL") & (events_df["monsterType"] == "HORDE")].copy()

    if len(grubs) == 0:
        stats_df["tower_dmg_after_grubs"] = 0
        return stats_df

    grubs["team"] = grubs["killerTeamId"]
    grub_frames = grubs.groupby(["match_id", "team"])["frame"].min().reset_index()
    grub_frames = grub_frames.rename(columns={"frame": "grub_frame"})

    stats_df = stats_df.merge(grub_frames, on=["match_id", "team"], how="left")

    stats_df["frames_since_grubs"] = stats_df["frame"] - stats_df["grub_frame"]
    in_window = (stats_df["frames_since_grubs"] >= 0) & (stats_df["frames_since_grubs"] <= 5)
    stats_df["tower_dmg_after_grubs"] = stats_df["plates_taken"].where(in_window, 0)

    stats_df = stats_df.drop(columns=["grub_frame", "frames_since_grubs"])
    return stats_df


# ═══════════════════════════════════════════
# Baron → Tower Payoff (frame-aware, per baron)
# ═══════════════════════════════════════════

def add_baron_tower_impact(stats_df, events_df):
    """Track turrets killed in 5 frames after each baron, per frame."""
    barons = events_df[(events_df["type"] == "ELITE_MONSTER_KILL") & (events_df["monsterType"] == "BARON_NASHOR")].copy()

    if len(barons) == 0:
        stats_df["turrets_after_baron"] = 0
        return stats_df

    barons["team"] = barons["killerTeamId"]
    baron_frames = barons[["match_id", "team", "frame"]].rename(columns={"frame": "baron_frame"})

    # Cross-join baron events with stats to find frames in each baron's window
    stats_df = stats_df.merge(baron_frames, on=["match_id", "team"], how="left")

    stats_df["frames_since_baron"] = stats_df["frame"] - stats_df["baron_frame"]
    in_window = (stats_df["frames_since_baron"] > 0) & (stats_df["frames_since_baron"] <= 5)
    stats_df["turrets_after_baron"] = stats_df["turrets_killed"].where(in_window, 0)

    # If multiple barons, a row may have been duplicated — aggregate back
    group_cols = [c for c in stats_df.columns if c not in ["baron_frame", "frames_since_baron", "turrets_after_baron"]]
    stats_df = stats_df.groupby(group_cols, as_index=False)["turrets_after_baron"].sum()

    return stats_df


# ═══════════════════════════════════════════
# Elder Dragon → Damage During Buff (frame-aware)
# ═══════════════════════════════════════════

def add_elder_damage_impact(stats_df, events_df):
    """Track damage done during each elder buff window (5 frames), per frame."""
    elders = events_df[
        (events_df["type"] == "ELITE_MONSTER_KILL") &
        (events_df["monsterType"] == "DRAGON") &
        (events_df["monsterSubType"] == "ELDER_DRAGON")
    ].copy()

    if len(elders) == 0:
        stats_df["dmg_during_elder"] = 0
        stats_df["had_elder"] = 0
        return stats_df

    elders["team"] = elders["killerTeamId"]
    elder_frames = elders[["match_id", "team", "frame"]].rename(columns={"frame": "elder_frame"})

    stats_df = stats_df.merge(elder_frames, on=["match_id", "team"], how="left")

    stats_df["frames_since_elder"] = stats_df["frame"] - stats_df["elder_frame"]
    in_window = (stats_df["frames_since_elder"] > 0) & (stats_df["frames_since_elder"] <= 5)

    # Damage this frame (use diff to get per-frame damage, not cumulative)
    stats_df["dmg_during_elder"] = stats_df["totalDamageDoneToChampions"].where(in_window, 0)

    # If multiple elders, aggregate back
    group_cols = [c for c in stats_df.columns if c not in ["elder_frame", "frames_since_elder", "dmg_during_elder"]]
    stats_df = stats_df.groupby(group_cols, as_index=False)["dmg_during_elder"].sum()

    stats_df["had_elder"] = (stats_df["dmg_during_elder"] > 0).astype(int)
    return stats_df







