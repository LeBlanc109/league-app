def get_flat_events_aggregation(events_df):
    # All FLAT, as in NO relationships... event features go here
    flat_agg = []

    # Kills
    kills = events_df[events_df["type"] == "CHAMPION_KILL"]
    kills_event = kills.groupby(["match_id", "frame", "killerId"]).size().reset_index(name="kills_in_frame")
    kills_event = kills_event.rename(columns={"killerId": "participant_id"})
    flat_agg.append(kills_event)

    # Wards
    wards = events_df[events_df["type"] == "WARD_PLACED"]
    create_ward_event = wards.groupby(["match_id", "frame", "creatorId"]).size().reset_index(name="wards_placed")
    create_ward_event = create_ward_event.rename(columns={"creatorId": "participant_id"})
    flat_agg.append(create_ward_event)

    # Deaths
    deaths = events_df[events_df["type"] == "CHAMPION_KILL"]
    death_event = deaths.groupby(["match_id", "frame", "victimId"]).size().reset_index(name="deaths_in_frame")
    death_event = death_event.rename(columns={"victimId": "participant_id"})
    flat_agg.append(death_event)

    ########################### Assists — explode the assistingParticipantIds list first
    assist_events = events_df[events_df["type"] == "CHAMPION_KILL"].dropna(subset=["assistingParticipantIds"])
    assists_exploded = assist_events.explode("assistingParticipantIds")
    assists_feat = assists_exploded.groupby(["match_id", "frame", "assistingParticipantIds"]).size().reset_index(name="assists_in_frame")
    assists_feat = assists_feat.rename(columns={"assistingParticipantIds": "participant_id"})
    flat_agg.append(assists_feat)

    # Wards Destroyed
    ward_kills = events_df[events_df["type"] == "WARD_KILL"]
    ward_kill_event = ward_kills.groupby(["match_id", "frame", "killerId"]).size().reset_index(name="wards_destroyed")
    ward_kill_event = ward_kill_event.rename(columns={"killerId": "participant_id"})
    flat_agg.append(ward_kill_event)

    # Dragons
    dragons = events_df[(events_df["type"] == "ELITE_MONSTER_KILL") & (events_df["monsterType"] == "DRAGON")]
    drag_event = dragons.groupby(["match_id", "frame", "killerId"]).size().reset_index(name="dragons_killed")
    drag_event = drag_event.rename(columns={"killerId": "participant_id"})
    flat_agg.append(drag_event)

    # Baron
    barons = events_df[(events_df["type"] == "ELITE_MONSTER_KILL") & (events_df["monsterType"] == "BARON_NASHOR")]
    baron_event = barons.groupby(["match_id", "frame", "killerId"]).size().reset_index(name="barons_killed")
    baron_event = baron_event.rename(columns={"killerId": "participant_id"})
    flat_agg.append(baron_event)

    # Rift Herald / Void Grubs
    heralds = events_df[(events_df["type"] == "ELITE_MONSTER_KILL") & (events_df["monsterType"] == "RIFTHERALD")]
    herald_event = heralds.groupby(["match_id", "frame", "killerId"]).size().reset_index(name="heralds_killed")
    herald_event = herald_event.rename(columns={"killerId": "participant_id"})
    flat_agg.append(herald_event)

    grubs = events_df[(events_df["type"] == "ELITE_MONSTER_KILL") & (events_df["monsterType"] == "HORDE")]
    grubs_event = grubs.groupby(["match_id", "frame", "killerId"]).size().reset_index(name="grubs_killed")
    grubs_event = grubs_event.rename(columns={"killerId": "participant_id"})
    flat_agg.append(grubs_event)

    #### Turrets
    tower = events_df[events_df["type"] == "BUILDING_KILL"]
    tower_kill_event = tower.groupby(["match_id", "frame", "killerId"]).size().reset_index(name="turrets_killed")
    tower_kill_event = tower_kill_event.rename(columns={"killerId": "participant_id"})
    flat_agg.append(tower_kill_event)

    # Turret Plates
    plates = events_df[events_df["type"] == "TURRET_PLATE_DESTROYED"]
    tower_plates_taken = plates.groupby(["match_id", "frame", "killerId"]).size().reset_index(name="plates_taken")
    tower_plates_taken = tower_plates_taken.rename(columns={"killerId": "participant_id"})
    flat_agg.append(tower_plates_taken)

    # Bounty Gold Earned (sum, not count)
    bounty_kills = events_df[events_df["type"] == "CHAMPION_KILL"].dropna(subset=["shutdownBounty"])
    bounty_event = bounty_kills.groupby(["match_id", "frame", "killerId"])["shutdownBounty"].sum().reset_index(name="bounty_gold_earned")
    bounty_event = bounty_event.rename(columns={"killerId": "participant_id"})
    flat_agg.append(bounty_event)

    flat_event_features = flat_agg[0]
    for eventf in flat_agg[1:]:
        flat_event_features = flat_event_features.merge(eventf, on=["match_id", "frame", "participant_id"], how="outer")

    return flat_event_features
