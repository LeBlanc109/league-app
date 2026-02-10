import pandas as pd
import logging

log = logging.getLogger(__name__)

def process_stats(data):
    match_id = data["metadata"]["matchId"]
    rows_data = []

    for frame_idx, frame in enumerate(data["info"]["frames"]):
        for participant_id, pstats in frame["participantFrames"].items():
        
            # Safely unpack nested dicts
            for nested_key in ("championStats", "damageStats", "position"):
                nested = pstats.pop(nested_key, None)
                if isinstance(nested, dict):
                    pstats.update(nested)

            #Arguably most importanyl we need the FRAME, matchId, and quantifiable participant_id
            pstats["match_id"] = match_id
            pstats['frame'] = frame_idx
            pstats["participant_id"] = int(participant_id)
            #ABSOLUTELY changing NOTHING about the dataframe.

            rows_data.append(pstats)

    if not rows_data:
        log.warning("process_stats: no participant frames found for %s", match_id)
        return pd.DataFrame()
    
    return pd.DataFrame(rows_data)

#CLEANING
def clean_stats(stats_df):
    if stats_df.empty:
        log.warning("clean_stats: received empty DataFrame")
        return stats_df
    
    stats_df["team"] = stats_df["participant_id"].map({
    1: 100, 2: 100, 3: 100, 4: 100, 5: 100,
    6: 200, 7: 200, 8: 200, 9: 200, 10: 200
    })
    
    lane_mapping = {1: "TOP", 2: "JG", 3: "MID", 4: "BOT", 5: "SUP",
                6: "TOP", 7: "JG", 8: "MID", 9: "BOT", 10: "SUP"}
    
    stats_df["lane"] = stats_df["participant_id"].map(lane_mapping)
    
    minions = stats_df["minionsKilled"] if "minionsKilled" in stats_df.columns else 0
    jungle = stats_df["jungleMinionsKilled"] if "jungleMinionsKilled" in stats_df.columns else 0
    stats_df["creep_score"] = minions + jungle
    
    return stats_df


def process_events(data):
    match_id = data["metadata"]["matchId"]
    event_rows = []
    for frame_idx, frame in enumerate(data["info"]["frames"]):
        for event in frame.get("events", []):

            pos = event.pop("position", None)
            if isinstance(pos, dict):
                event.update(pos)
            
            #track
            event["match_id"] = match_id
            event["frame"] = frame_idx
            event_rows.append(event)

    if not event_rows:
        log.warning("process_events: no events found for %s", match_id)
        # Minimum columns so downstream filters don't KeyError
        return pd.DataFrame(columns=["match_id", "frame", "type"])
    
    return pd.DataFrame(event_rows)


