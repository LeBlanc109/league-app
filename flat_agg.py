def get_flat_events_aggregation(events_df):
   flat_agg = []

   def _agg_count(df, group_col, feat_name):
       """Group by match_id/frame/group_col, count rows, rename to participant_id."""

       if df.empty:
           return None
       
       result = df.groupby(["match_id", "frame", group_col]).size().reset_index(name=feat_name)
       return result.rename(columns={group_col: "participant_id"})
   
   def _agg_sum(df, group_col, value_col, feat_name):
       """Group by match_id/frame/group_col, sum a column, rename to participant_id."""

       if df.empty:
           return None
       
       result = df.groupby(["match_id", "frame", group_col])[value_col].sum().reset_index(name=feat_name)
       return result.rename(columns={group_col: "participant_id"})
   def _add(result):
       
       if result is not None:
           flat_agg.append(result)

   # Champion kills — one filter, three features (kills, deaths, assists)
   champ_kills = events_df[events_df["type"] == "CHAMPION_KILL"]
   _add(_agg_count(champ_kills, "killerId",  "kills_in_frame"))
   _add(_agg_count(champ_kills, "victimId",  "deaths_in_frame"))
   assists = champ_kills.dropna(subset=["assistingParticipantIds"]).explode("assistingParticipantIds")
   _add(_agg_count(assists, "assistingParticipantIds", "assists_in_frame"))
   bounties = champ_kills.dropna(subset=["shutdownBounty"])
   _add(_agg_sum(bounties, "killerId", "shutdownBounty", "bounty_gold_earned"))

   # Wards
   _add(_agg_count(events_df[events_df["type"] == "WARD_PLACED"], "creatorId", "wards_placed"))
   _add(_agg_count(events_df[events_df["type"] == "WARD_KILL"],   "killerId", "wards_destroyed"))

   # Elite monsters — same pattern, different monsterType filter
   monsters = events_df[events_df["type"] == "ELITE_MONSTER_KILL"]
   for monster_type, feat_name in [
       ("DRAGON",       "dragons_killed"),
       ("BARON_NASHOR", "barons_killed"),
       ("RIFTHERALD",   "heralds_killed"),
       ("HORDE",        "grubs_killed"),
   ]:
    _add(_agg_count(monsters[monsters["monsterType"] == monster_type], "killerId", feat_name))

   # Buildings
   _add(_agg_count(events_df[events_df["type"] == "BUILDING_KILL"],          "killerId", "turrets_killed"))
   _add(_agg_count(events_df[events_df["type"] == "TURRET_PLATE_DESTROYED"], "killerId", "plates_taken"))

   # Merge all features
   if not flat_agg:
       return None
   
   result = flat_agg[0]
   for feat_df in flat_agg[1:]:
       result = result.merge(feat_df, on=["match_id", "frame", "participant_id"], how="outer")
       
   return result


