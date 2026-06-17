import pandas as pd
from core.schema import validate


def load_sample(path: str = "sample_data.csv") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = validate(df)
    df["collected_date"] = pd.to_datetime(df["collected_date"])
    return df
