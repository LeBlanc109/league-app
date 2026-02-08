#gold diff: vs lane opponent
def add_gold_diff(stats_df):
    def calc_diffs(g):
        blue = g.loc[g["team"] == 100, "totalGold"].values[0]
        red = g.loc[g["team"] == 200, "totalGold"].values[0]
        g["blue_lane_gold_diff"] = blue - red
        g["red_lane_gold_diff"] = red - blue
        return g
    
    result = stats_df.groupby(["match_id", "frame", "role"]).apply(calc_diffs , include_groups=False).reset_index()
    return result

#  Team Gold Diff
def add_team_gold_diff(stats_df):
    team_gold = stats_df.groupby(["match_id", "frame", "team"])["totalGold"].transform("sum")
    team_sum = stats_df.groupby(["match_id", "frame"])["totalGold"].transform("sum")
    stats_df["team_total_gold"] = team_gold
    stats_df["opp_team_total_gold"] = team_sum - team_gold
    stats_df["team_gold_diff"] = team_gold - (team_sum - team_gold)
    return stats_df

# Team Kill Diff
def add_team_kill_diff(stats_df):
    team_kills = stats_df.groupby(["match_id", "frame", "team"])["kills_in_frame"].transform("sum")
    team_sum = stats_df.groupby(["match_id", "frame"])["kills_in_frame"].transform("sum")
    stats_df["team_kills"] = team_kills
    stats_df["opp_team_kills"] = team_sum - team_kills
    stats_df["team_kill_diff"] = team_kills - (team_sum - team_kills)
    return stats_df

#  Kill Participation %
def add_kp(stats_df):
    if "kills_in_frame" not in stats_df.columns:
        stats_df["kills_in_frame"] = 0

    team_kills = stats_df.groupby(["match_id", "frame", "team"])["kills_in_frame"].transform("sum")
    stats_df["team_total_kills"] = team_kills

    assists = stats_df["assists_in_frame"] if "assists_in_frame" in stats_df.columns else 0
    stats_df["kp_percent"] = ((stats_df["kills_in_frame"] + assists) / team_kills).fillna(0)
    return stats_df

# CS Farming Rate Change (detecting farming falloff or moves back into gamer position)
def add_cs_rate_change(stats_df):
    stats_df = stats_df.sort_values(["match_id", "participant_id", "frame"])
    stats_df["cs_per_min_delta"] = stats_df.groupby(["match_id", "participant_id"])["creep_score"].diff().fillna(0)
    return stats_df

def add_vision_falloff(stats_df):
    stats_df = stats_df.sort_values(["match_id", "participant_id", "frame"])

    # Early game baseline (frames 2-8)
    early_mask = (stats_df["frame"] >= 2) & (stats_df["frame"] <= 8)
    early_avg = stats_df[early_mask].groupby(["match_id", "participant_id"])["wards_placed"].transform("mean")
    stats_df["early_ward_avg"] = None
    stats_df.loc[early_mask, "early_ward_avg"] = early_avg
    stats_df["early_ward_avg"] = stats_df.groupby(["match_id", "participant_id"])["early_ward_avg"].transform("first")

    # Rolling 5-frame ward average
    stats_df["ward_rate_5"] = stats_df.groupby(["match_id", "participant_id"])["wards_placed"].rolling(5, min_periods=1).mean().reset_index(level=[0, 1], drop=True)

    stats_df["vision_falloff"] = stats_df["ward_rate_5"] - stats_df["early_ward_avg"]
    return stats_df

# 9. Kill Streak / Bounty Window Tracking
#def add_kill_streak_tracking(stats_df, events_df):
#    # Filter for kills
#    kills = events_df[events_df["type"] == "CHAMPION_KILL"].copy()
#    
#    if kills.empty:
#        stats_df["kill_streak"] = 0
#        return stats_df
#
#    # Get streaks
#    # Note: ensure columns exist in events_df
#    if "killStreakLength" in kills.columns:
#        streak = kills.groupby(["match_id", "frame", "killerId"])["killStreakLength"].max().reset_index()
#        streak = streak.rename(columns={"killerId": "participant_id", "killStreakLength": "kill_streak"})
#        
#        stats_df = stats_df.merge(streak, on=["match_id", "frame", "participant_id"], how="left")
#        stats_df["kill_streak"] = stats_df["kill_streak"].fillna(0)
#    else:
#        stats_df["kill_streak"] = 0
#        
#    return stats_df

