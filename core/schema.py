import pandas as pd

COLUMNS = [
    "collected_date", "keyword", "search_pc", "search_mobile", "search_total",
    "comp_idx", "avg_depth", "avg_ctr_pc", "avg_ctr_mobile",
    "bid_pos1", "bid_pos2", "bid_pos3",
]


def validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    return df[COLUMNS].copy()
