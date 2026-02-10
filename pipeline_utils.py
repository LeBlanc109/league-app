import pandas as pd
import logging

log = logging.getLogger(__name__)


def has_cols(df, *cols):
    """Check if a DataFrame has all the listed columns and is not empty."""
    if df.empty:
        return False
    missing = [c for c in cols if c not in df.columns]
    if missing:
        log.debug("Missing columns: %s", missing)
        return False
    return True


def safe_merge(stats_df, right_df, on, new_cols):
    """
    Left-merge right_df into stats_df, filling NaN with 0 for new_cols.
    If right_df is None or empty, just adds zero columns instead of crashing.
    """
    if right_df is None or right_df.empty:
        for col in new_cols:
            stats_df[col] = 0
        return stats_df

    stats_df = stats_df.merge(right_df, on=on, how="left")
    for col in new_cols:
        stats_df[col] = stats_df[col].fillna(0).astype(int)
    return stats_df


def col_or_zero(df, col_name):
    """
    Return df[col_name] if it exists, otherwise a Series of 0s.
    Readable alternative to df.get(col_name, pd.Series(0, ...)).
    """
    if col_name in df.columns:
        return df[col_name]
    return pd.Series(0, index=df.index)