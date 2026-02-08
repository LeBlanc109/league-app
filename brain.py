import json
import pandas as pd

#API KEY
#from riot_auth import api_key
#Import the custom methods
import process_last_timeline as prod_t
import process_pgi as pgi

import flat_agg as fa
import dimensions as dim
import f_sandbox as fs
import explode_sandbox as es

def activate_brain(timeline , post_gameinfo):
    print("--- 🧠 BRAIN ACTIVATED ---")
    
    print("Processing: Stats and Events")
    stats_df = prod_t.process_stats(timeline)
    events_df = prod_t.process_events(timeline)
    print("Processing Completed")

    print("Cleaning: Stats")
    better_stats_df = prod_t.clean_stats(stats_df) 
    better_stats_df['role'] = better_stats_df['lane']
    print("Cleaning Completed")

    print("Flat Aggregation for Events")
    flat_agg_ev = fa.get_flat_events_aggregation(events_df)

    #tehn merge
    print("Merging the CleanedSt. with FlatAggEv")
    sacred_timeline = dim.three_d(better_stats_df , flat_agg_ev)
    print("Merging Completed")

    # 6. FEATURE ENGINEERING (Sandbox)
    print("Resetting the Index???")
    #reset index???
    sacred_timeline = sacred_timeline.reset_index()
    
    #Basic Feature Engineering
    print("Adding: F_Sandbox")
    sacred_timeline = fs.add_gold_diff(sacred_timeline)
    sacred_timeline = fs.add_team_gold_diff(sacred_timeline)
    sacred_timeline = fs.add_vision_falloff(sacred_timeline)
    sacred_timeline = fs.add_cs_rate_change(sacred_timeline)
    sacred_timeline = fs.add_kp(sacred_timeline)
    sacred_timeline = fs.add_team_kill_diff(sacred_timeline)
    #fs.add_kill_streak_tracking(sacred_timeline , events_df)
    print("Added f_sandbox")

    ##EXPLODING -> the Deep Analysis, or "time analysis"
    print("EXPLODING")
    sacred_timeline = es.add_kill_features(sacred_timeline , events_df)
    sacred_timeline = es.add_ganked_deaths(sacred_timeline , events_df)
    sacred_timeline = es.add_objective_streaks(sacred_timeline , events_df)
    sacred_timeline = es.add_baron_tower_impact(sacred_timeline , events_df)
    sacred_timeline = es.add_elder_damage_impact(sacred_timeline , events_df)
    print("Deep Analysis Completed")

    print("Parsing the pgi")
    static_df = pgi.parse_match_results(post_gameinfo)
    print("Parsing: Complete. Now -> Merging")

    sacred_timeline = sacred_timeline.merge(static_df, on=['match_id', 'participant_id'], how='left')
    print("Merging Complete")

    #finish...
    print("All done!")
    return sacred_timeline
