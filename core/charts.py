import pandas as pd


def latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    latest = df["collected_date"].max()
    return df[df["collected_date"] == latest].copy()


def keyword_timeseries(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    out = df[df["keyword"] == keyword].copy()
    return out.sort_values("collected_date")
