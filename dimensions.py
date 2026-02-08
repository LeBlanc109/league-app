def three_d(cleaned_stats_df , events_flat_agg):
    cleaned_stats_df = cleaned_stats_df.merge(events_flat_agg, on=["match_id", "frame", "participant_id"], how="left")
    cleaned_stats_df = cleaned_stats_df.fillna(0)
    cleaned_stats_df = cleaned_stats_df.set_index(["match_id", "frame", "participant_id"])

    return cleaned_stats_df
