"""
Schedule / rest / B2B helpers shared by train_model and aggregate_picks.
B2B: previous team game was ≤1 calendar day before the current game (gap in days ≤ 1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_b2b_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Append integer column `b2b` (0/1). Expects `prev_game_date` and sorted team-game rows.
    First game of a segment has no previous date → b2b = 0.
    """
    out = df.copy()
    raw_gap_days = (out["gameDateTimeEst"] - out["prev_game_date"]).dt.days
    out["b2b"] = np.where(raw_gap_days.notna(), (raw_gap_days <= 1).astype(np.int8), 0)
    return out


def b2b_before_game(
    sched_df: pd.DataFrame, team_id: int, game_time: pd.Timestamp
) -> int:
    """
    Inference: using historical rows in sched_df (teamId, gameDateTimeEst), return 1 if the
    team's last game before `game_time` was a back-to-back (gap ≤ 1 day), else 0.
    """
    sub = sched_df.loc[sched_df["teamId"] == int(team_id), "gameDateTimeEst"]
    if sub.empty:
        return 0
    sub = pd.to_datetime(sub, utc=True, errors="coerce").dropna().sort_values()
    past = sub[sub < game_time]
    if past.empty:
        return 0
    last = past.iloc[-1]
    gap_days = (game_time - last).total_seconds() / 86400.0
    return 1 if gap_days <= 1.0 else 0


def load_schedule_for_b2b(csv_path: str = "data/TeamStatistics.csv") -> pd.DataFrame:
    """Minimal columns for B2B inference."""
    df = pd.read_csv(
        csv_path, usecols=lambda c: c in ("teamId", "gameDateTimeEst"), low_memory=False
    )
    df["gameDateTimeEst"] = df["gameDateTimeEst"].astype(str).str.slice(0, 10)
    df["gameDateTimeEst"] = pd.to_datetime(df["gameDateTimeEst"], utc=True, errors="coerce")
    return df.dropna(subset=["gameDateTimeEst"])
