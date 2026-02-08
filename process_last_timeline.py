import pandas as pd

def process_stats(data):
    #Very first thing is matchID
    match_id = data["metadata"]["matchId"]
    rows_data = []

    for frame_idx, frame in enumerate(data["info"]["frames"]):
        for participant_id, pstats in frame["participantFrames"].items():
        
            #Nested Dicts inside participantFrames
            pstats.update(pstats.pop('championStats'))
            pstats.update(pstats.pop('damageStats'))
            pstats.update(pstats.pop('position'))

            #Arguably most importanyl we need the FRAME, matchId, and quantifiable participant_id
            pstats["match_id"] = match_id
            pstats['frame'] = frame_idx
            pstats["participant_id"] = int(participant_id)

            #ABSOLUTELY changing NOTHING about the dataframe.
            rows_data.append(pstats)
    lastgame_df = pd.DataFrame(rows_data)
    return lastgame_df

def clean_stats(stats_df):
    stats_df["team"] = stats_df["participant_id"].map({
    1: 100, 2: 100, 3: 100, 4: 100, 5: 100,
    6: 200, 7: 200, 8: 200, 9: 200, 10: 200
    })
    
    lane_mapping = {1: "TOP", 2: "JG", 3: "MID", 4: "BOT", 5: "SUP",
                6: "TOP", 7: "JG", 8: "MID", 9: "BOT", 10: "SUP"}
    
    stats_df["lane"] = stats_df["participant_id"].map(lane_mapping)
    
    stats_df["creep_score"] = stats_df["minionsKilled"] + stats_df["jungleMinionsKilled"]
    
    return stats_df


def process_events(data):
    match_id = data["metadata"]["matchId"]
    event_rows = []
    for frame_idx, frame in enumerate(data["info"]["frames"]):
        for event in frame.get("events", []):
            
            #EXPLODE mwahahaha
            if "position" in event:
                event.update(event.pop("position"))
            
            #track
            event["match_id"] = match_id
            event["frame"] = frame_idx
            
            event_rows.append(event)

    events_df = pd.DataFrame(event_rows)
    return events_df


