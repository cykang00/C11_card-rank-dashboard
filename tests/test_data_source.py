import pandas as pd
from core.data_source import load_sample
from core.schema import COLUMNS


def test_load_sample_has_schema(tmp_path):
    csv = tmp_path / "s.csv"
    pd.DataFrame([{
        "collected_date": "2026-06-17", "keyword": "신용카드",
        "search_pc": 12000, "search_mobile": 88000, "search_total": 100000,
        "comp_idx": "높음", "avg_depth": 15, "avg_ctr_pc": 0.8, "avg_ctr_mobile": 1.2,
        "bid_pos1": 5400, "bid_pos2": 3900, "bid_pos3": 2800,
    }]).to_csv(csv, index=False, encoding="utf-8-sig")
    df = load_sample(str(csv))
    assert list(df.columns) == COLUMNS
    assert str(df["collected_date"].dtype).startswith("datetime")


def test_load_bundled_sample():
    df = load_sample("sample_data.csv")
    assert len(df) == 15
    assert df["keyword"].nunique() == 5
