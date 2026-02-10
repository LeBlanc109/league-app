import pandas as pd
import logging
from pipeline_utils import has_cols, safe_merge, col_or_zero

log = logging.getLogger(__name__)

# ============================================================================
# Damage Exploding (used by add_kill_features)
# ============================================================================

def _explode_damage_list(kills_df, column_name):
    """
    Takes a kills DataFrame and a column containing lists of damage dicts
    (like "victimDamageReceived"). Explodes them into one row per damage instance.
    Returns an empty DataFrame if the column is missing or all NaN.
    """
    if column_name not in kills_df.columns:
        return pd.DataFrame()

    base = kills_df[["kill_id", "match_id", "frame", "killerId", "victimId", column_name]].copy()
    base = base.dropna(subset=[column_name])
    if base.empty:
        return pd.DataFrame()

    base = base.explode(column_name)

    # Each element is a dict like {"name": "Turret", "magicDamage": 0, ...}
    try:
        details = pd.json_normalize(base[column_name])
    except Exception as e:
        log.warning("json_normalize failed for '%s': %s", column_name, e)
        return pd.DataFrame()
    details.index = base.index

    result = base[["kill_id", "match_id", "frame", "killerId", "victimId"]].copy()
    result["dmg_source_name"]        = details.get("name", "")
    result["dmg_source_participant"] = details.get("participantId")
    result["dmg_spell_name"]         = details.get("spellName", "")
    result["dmg_magic"]              = details.get("magicDamage", 0)
    result["dmg_physical"]           = details.get("physicalDamage", 0)
    result["dmg_true"]               = details.get("trueDamage", 0)
    return result


def _get_kills_and_damage(events_df):
    """
    Returns (kills, damage_recv, damage_dealt).
    Any of these can be an empty DataFrame if data is missing.
    """
    kills = events_df[events_df["type"] == "CHAMPION_KILL"].copy()

    if not has_cols(kills, "killerId", "victimId"):
        empty = pd.DataFrame()
        return empty, empty, empty

    kills["kill_id"] = range(len(kills))
    damage_recv = _explode_damage_list(kills, "victimDamageReceived")
    damage_dealt = _explode_damage_list(kills, "victimDamageDealt")

    return kills, damage_recv, damage_dealt


# ============================================================================
# Kill Features: tower deaths, free kills, zero-damage deaths
# ============================================================================

def add_kill_features(stats_df, events_df):
    new_cols = ["tower_deaths", "free_kills", "zero_dmg_deaths"]
    merge_on = ["match_id", "frame", "participant_id"]

    if not has_cols(events_df, "type"):
        for col in new_cols:
            stats_df[col] = 0
        return stats_df

    kills, damage_recv, damage_dealt = _get_kills_and_damage(events_df)

    # --- Tower deaths: did you die with turret damage involved? ---
    tower_deaths_df = None
    if not damage_recv.empty and "dmg_source_name" in damage_recv.columns:
        tower_dmg = damage_recv[
            damage_recv["dmg_source_name"].str.contains("Turret|Tower", case=False, na=False)
        ]
        if not tower_dmg.empty:
            # One tower-death per kill event, not per turret shot
            tower_kills = tower_dmg.drop_duplicates(subset=["kill_id"])
            tower_deaths_df = (
                tower_kills
                .groupby(["match_id", "frame", "victimId"]).size()
                .reset_index(name="tower_deaths")
                .rename(columns={"victimId": "participant_id"})
            )
    stats_df = safe_merge(stats_df, tower_deaths_df, merge_on, ["tower_deaths"])

    # --- Free kills: victim dealt < 100 total damage back ---
    free_kills_df = None
    if not kills.empty and not damage_dealt.empty:
        victim_dmg_back = damage_dealt.groupby("kill_id").agg(
            magic_back=("dmg_magic", "sum"),
            phys_back=("dmg_physical", "sum"),
            true_back=("dmg_true", "sum"),
        ).reset_index()
        victim_dmg_back["total_dmg_back"] = (
            victim_dmg_back["magic_back"]
            + victim_dmg_back["phys_back"]
            + victim_dmg_back["true_back"]
        )

        kills = kills.merge(victim_dmg_back[["kill_id", "total_dmg_back"]], on="kill_id", how="left")
        kills["total_dmg_back"] = kills["total_dmg_back"].fillna(0)
        kills["is_free_kill"] = (kills["total_dmg_back"] < 100).astype(int)

        free_kills_df = (
            kills.groupby(["match_id", "frame", "killerId"])["is_free_kill"]
            .sum().reset_index(name="free_kills")
            .rename(columns={"killerId": "participant_id"})
        )
    stats_df = safe_merge(stats_df, free_kills_df, merge_on, ["free_kills"])

    # --- Zero-damage deaths: victim dealt literally nothing ---
    zero_deaths_df = None
    if not kills.empty and not damage_dealt.empty:
        kills_with_dealt = set(damage_dealt["kill_id"].unique())
        kills["victim_did_zero"] = (~kills["kill_id"].isin(kills_with_dealt)).astype(int)

        zero_deaths_df = (
            kills.groupby(["match_id", "frame", "victimId"])["victim_did_zero"]
            .sum().reset_index(name="zero_dmg_deaths")
            .rename(columns={"victimId": "participant_id"})
        )
    stats_df = safe_merge(stats_df, zero_deaths_df, merge_on, ["zero_dmg_deaths"])

    return stats_df


# ============================================================================
# Ganked Deaths: 3+ enemies involved in your death
# ============================================================================

def _count_people_involved(assist_list):
    """Killer + assisters. If no assist list, just the killer (1)."""
    if isinstance(assist_list, list):
        return len(assist_list) + 1
    return 1


def add_ganked_deaths(stats_df, events_df):
    if not has_cols(events_df, "type"):
        stats_df["ganked_deaths"] = 0
        return stats_df

    kills = events_df[events_df["type"] == "CHAMPION_KILL"].copy()
    if kills.empty or not has_cols(kills, "assistingParticipantIds", "victimId"):
        stats_df["ganked_deaths"] = 0
        return stats_df

    kills["num_involved"] = kills["assistingParticipantIds"].apply(_count_people_involved)
    kills["was_ganked"] = (kills["num_involved"] >= 3).astype(int)

    ganked = (
        kills.groupby(["match_id", "frame", "victimId"])["was_ganked"]
        .sum().reset_index(name="ganked_deaths")
        .rename(columns={"victimId": "participant_id"})
    )
    return safe_merge(stats_df, ganked, ["match_id", "frame", "participant_id"], ["ganked_deaths"])


# ============================================================================
# Objective Streaks
# ============================================================================

def add_objective_streaks(stats_df, events_df):
    if not has_cols(events_df, "type"):
        stats_df["obj_streak"] = 0
        return stats_df

    objectives = events_df[events_df["type"].isin(["ELITE_MONSTER_KILL", "BUILDING_KILL"])].copy()
    if objectives.empty:
        stats_df["obj_streak"] = 0
        return stats_df

    objectives = objectives.sort_values(["match_id", "frame", "timestamp"])

    # Figure out which team gets credit
    if "killerTeamId" in objectives.columns:
        objectives["obj_team"] = objectives["killerTeamId"].fillna(0)
    else:
        objectives["obj_team"] = 0

    # For building kills, the killing team is the OPPOSITE of teamId
    building_mask = objectives["type"] == "BUILDING_KILL"
    if "teamId" in objectives.columns:
        objectives.loc[building_mask, "obj_team"] = (
            objectives.loc[building_mask, "teamId"].map({100: 200, 200: 100})
        )

    # Streak tracking: reset when the team changes
    objectives["team_changed"] = (objectives["obj_team"] != objectives["obj_team"].shift()).astype(int)
    objectives["streak_group"] = objectives.groupby("match_id")["team_changed"].cumsum()
    objectives["obj_streak"] = objectives.groupby(["match_id", "streak_group"]).cumcount() + 1

    # Get the max streak per frame per team
    obj_streak = (
        objectives[["match_id", "frame", "obj_team", "obj_streak"]]
        .rename(columns={"obj_team": "team"})
        .groupby(["match_id", "frame", "team"])["obj_streak"].max()
        .reset_index()
    )

    if "team" not in stats_df.columns:
        stats_df["obj_streak"] = 0
        return stats_df

    stats_df = stats_df.merge(obj_streak, on=["match_id", "frame", "team"], how="left")
    stats_df["obj_streak"] = (
        stats_df.groupby(["match_id", "participant_id"])["obj_streak"]
        .ffill().fillna(0).astype(int)
    )
    return stats_df


# ============================================================================
# Helper: Build a "window" DataFrame for post-objective tracking
# ============================================================================

def _build_objective_windows(events_df, event_filter, window_size=5):
    """
    Given filtered objective events (with 'killerTeamId', 'frame', 'match_id'),
    return a DataFrame of (match_id, team, frame) marking which frames are
    inside the post-objective window.

    Example: baron at frame 10, window_size=5 → frames 11-15 are flagged.
    """
    obj_events = events_df[event_filter].copy()

    if obj_events.empty or "killerTeamId" not in obj_events.columns:
        return None

    window_rows = []
    for _, row in obj_events.iterrows():
        baron_frame = int(row["frame"])
        for f in range(baron_frame + 1, baron_frame + window_size + 1):
            window_rows.append({
                "match_id": row["match_id"],
                "team": row["killerTeamId"],
                "frame": f,
            })

    if not window_rows:
        return None

    # Drop duplicates so multiple barons don't create duplicate rows
    return pd.DataFrame(window_rows).drop_duplicates()


# ============================================================================
# Grub → Tower Plate Impact
# ============================================================================

def add_grub_tower_impact(stats_df, events_df):
    if not has_cols(events_df, "type", "monsterType") or "team" not in stats_df.columns:
        stats_df["tower_dmg_after_grubs"] = 0
        return stats_df

    grubs = events_df[
        (events_df["type"] == "ELITE_MONSTER_KILL") & (events_df["monsterType"] == "HORDE")
    ].copy()

    if grubs.empty or "killerTeamId" not in grubs.columns:
        stats_df["tower_dmg_after_grubs"] = 0
        return stats_df

    # Use first grub frame per team
    grubs["team"] = grubs["killerTeamId"]
    grub_frames = grubs.groupby(["match_id", "team"])["frame"].min().reset_index()
    grub_frames = grub_frames.rename(columns={"frame": "grub_frame"})

    stats_df = stats_df.merge(grub_frames, on=["match_id", "team"], how="left")
    stats_df["frames_since_grubs"] = stats_df["frame"] - stats_df["grub_frame"]

    in_window = (stats_df["frames_since_grubs"] >= 0) & (stats_df["frames_since_grubs"] <= 5)
    plates = col_or_zero(stats_df, "plates_taken")
    stats_df["tower_dmg_after_grubs"] = plates.where(in_window, 0)

    stats_df = stats_df.drop(columns=["grub_frame", "frames_since_grubs"], errors="ignore")
    return stats_df


# ============================================================================
# Baron → Turret Payoff (5 frames after EACH baron)
# ============================================================================

def add_baron_tower_impact(stats_df, events_df):
    if not has_cols(events_df, "type", "monsterType") or "team" not in stats_df.columns:
        stats_df["turrets_after_baron"] = 0
        return stats_df

    baron_filter = (
        (events_df["type"] == "ELITE_MONSTER_KILL")
        & (events_df["monsterType"] == "BARON_NASHOR")
    )
    windows = _build_objective_windows(events_df, baron_filter, window_size=5)

    if windows is None:
        stats_df["turrets_after_baron"] = 0
        return stats_df

    # Flag which (match, team, frame) combos are in a baron window
    windows["in_baron_window"] = True
    stats_df = stats_df.merge(windows, on=["match_id", "team", "frame"], how="left")
    stats_df["in_baron_window"] = stats_df["in_baron_window"].fillna(False)

    turrets = col_or_zero(stats_df, "turrets_killed")
    stats_df["turrets_after_baron"] = turrets.where(stats_df["in_baron_window"], 0)

    stats_df = stats_df.drop(columns=["in_baron_window"])
    return stats_df


# ============================================================================
# Elder Dragon → Damage During Buff (5 frames after each elder)
# ============================================================================

def add_elder_damage_impact(stats_df, events_df):
    needed = ["type", "monsterType", "monsterSubType"]
    if not has_cols(events_df, *needed) or "team" not in stats_df.columns:
        stats_df["dmg_during_elder"] = 0
        stats_df["had_elder"] = 0
        return stats_df

    elder_filter = (
        (events_df["type"] == "ELITE_MONSTER_KILL")
        & (events_df["monsterType"] == "DRAGON")
        & (events_df["monsterSubType"] == "ELDER_DRAGON")
    )
    windows = _build_objective_windows(events_df, elder_filter, window_size=5)

    if windows is None:
        stats_df["dmg_during_elder"] = 0
        stats_df["had_elder"] = 0
        return stats_df

    windows["in_elder_window"] = True
    stats_df = stats_df.merge(windows, on=["match_id", "team", "frame"], how="left")
    stats_df["in_elder_window"] = stats_df["in_elder_window"].fillna(False)

    dmg = col_or_zero(stats_df, "totalDamageDoneToChampions")
    stats_df["dmg_during_elder"] = dmg.where(stats_df["in_elder_window"], 0)
    stats_df["had_elder"] = stats_df["in_elder_window"].astype(int)

    stats_df = stats_df.drop(columns=["in_elder_window"])
    return stats_df