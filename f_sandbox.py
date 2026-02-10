import pandas as pd
import logging
from pipeline_utils import has_cols, col_or_zero

log = logging.getLogger(__name__)


# ============================================================================
# Gold Diff vs Lane Opponent
# ============================================================================

def add_gold_diff(stats_df):
    if not has_cols(stats_df, "team", "totalGold", "lane"):
        stats_df["blue_lane_gold_diff"] = 0
        stats_df["red_lane_gold_diff"] = 0
        return stats_df

    # Split blue/red gold by lane, then compute diffs
    blue = stats_df[stats_df["team"] == 100][["match_id", "frame", "lane", "totalGold"]]
    red  = stats_df[stats_df["team"] == 200][["match_id", "frame", "lane", "totalGold"]]

    lane_diff = blue.merge(red, on=["match_id", "frame", "lane"], suffixes=("_blue", "_red"))
    lane_diff["blue_lane_gold_diff"] = lane_diff["totalGold_blue"] - lane_diff["totalGold_red"]
    lane_diff["red_lane_gold_diff"]  = lane_diff["totalGold_red"] - lane_diff["totalGold_blue"]
    lane_diff = lane_diff[["match_id", "frame", "lane", "blue_lane_gold_diff", "red_lane_gold_diff"]]

    stats_df = stats_df.merge(lane_diff, on=["match_id", "frame", "lane"], how="left")
    stats_df["blue_lane_gold_diff"] = stats_df["blue_lane_gold_diff"].fillna(0)
    stats_df["red_lane_gold_diff"]  = stats_df["red_lane_gold_diff"].fillna(0)
    return stats_df


# ============================================================================
# Team Gold Diff
# ============================================================================

def add_team_gold_diff(stats_df):
    if not has_cols(stats_df, "team", "totalGold"):
        stats_df["team_total_gold"] = 0
        stats_df["opp_team_total_gold"] = 0
        stats_df["team_gold_diff"] = 0
        return stats_df

    team_gold = stats_df.groupby(["match_id", "frame", "team"])["totalGold"].transform("sum")
    total_gold = stats_df.groupby(["match_id", "frame"])["totalGold"].transform("sum")

    stats_df["team_total_gold"]     = team_gold
    stats_df["opp_team_total_gold"] = total_gold - team_gold
    stats_df["team_gold_diff"]      = team_gold - (total_gold - team_gold)
    return stats_df


# ============================================================================
# Team Kill Diff
# ============================================================================

def add_team_kill_diff(stats_df):
    if "kills_in_frame" not in stats_df.columns:
        stats_df["kills_in_frame"] = 0

    if not has_cols(stats_df, "team"):
        stats_df["team_kills"] = 0
        stats_df["opp_team_kills"] = 0
        stats_df["team_kill_diff"] = 0
        return stats_df

    team_kills = stats_df.groupby(["match_id", "frame", "team"])["kills_in_frame"].transform("sum")
    total_kills = stats_df.groupby(["match_id", "frame"])["kills_in_frame"].transform("sum")

    stats_df["team_kills"]     = team_kills
    stats_df["opp_team_kills"] = total_kills - team_kills
    stats_df["team_kill_diff"] = team_kills - (total_kills - team_kills)
    return stats_df


# ============================================================================
# Kill Participation %
# ============================================================================

def add_kp(stats_df):
    if "kills_in_frame" not in stats_df.columns:
        stats_df["kills_in_frame"] = 0

    if not has_cols(stats_df, "team"):
        stats_df["team_total_kills"] = 0
        stats_df["kp_percent"] = 0.0
        return stats_df

    team_kills = stats_df.groupby(["match_id", "frame", "team"])["kills_in_frame"].transform("sum")
    stats_df["team_total_kills"] = team_kills

    assists = col_or_zero(stats_df, "assists_in_frame")
    personal_contribution = stats_df["kills_in_frame"] + assists
    stats_df["kp_percent"] = (personal_contribution / team_kills).fillna(0)
    return stats_df


# ============================================================================
# CS Farming Rate Change
# ============================================================================

def add_cs_rate_change(stats_df):
    if "creep_score" not in stats_df.columns:
        stats_df["cs_per_min_delta"] = 0
        return stats_df

    stats_df = stats_df.sort_values(["match_id", "participant_id", "frame"])
    stats_df["cs_per_min_delta"] = (
        stats_df.groupby(["match_id", "participant_id"])["creep_score"]
        .diff()
        .fillna(0)
    )
    return stats_df


# ============================================================================
# Vision Falloff
# ============================================================================

def add_vision_falloff(stats_df):
    if "wards_placed" not in stats_df.columns:
        stats_df["early_ward_avg"] = 0
        stats_df["ward_rate_5"] = 0
        stats_df["vision_falloff"] = 0
        return stats_df

    stats_df = stats_df.sort_values(["match_id", "participant_id", "frame"])

    # Early game baseline: average wards per frame during frames 2-8
    early_mask = (stats_df["frame"] >= 2) & (stats_df["frame"] <= 8)
    early_avg = (
        stats_df[early_mask]
        .groupby(["match_id", "participant_id"])["wards_placed"]
        .transform("mean")
    )
    stats_df["early_ward_avg"] = None
    stats_df.loc[early_mask, "early_ward_avg"] = early_avg
    stats_df["early_ward_avg"] = (
        stats_df.groupby(["match_id", "participant_id"])["early_ward_avg"]
        .transform("first")
    )

    # Rolling 5-frame ward average
    stats_df["ward_rate_5"] = (
        stats_df.groupby(["match_id", "participant_id"])["wards_placed"]
        .rolling(5, min_periods=1).mean()
        .reset_index(level=[0, 1], drop=True)
    )

    stats_df["vision_falloff"] = stats_df["ward_rate_5"] - stats_df["early_ward_avg"]
    return stats_df
