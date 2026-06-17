from core.charts import latest_snapshot, keyword_timeseries
from core.data_source import load_sample


def _df():
    return load_sample("sample_data.csv")


def test_latest_snapshot_one_row_per_keyword():
    df = _df()
    snap = latest_snapshot(df)
    assert snap["keyword"].is_unique
    assert (snap["collected_date"] == df["collected_date"].max()).all()


def test_keyword_timeseries_sorted():
    df = _df()
    ts = keyword_timeseries(df, "신용카드")
    assert (ts["keyword"] == "신용카드").all()
    assert ts["collected_date"].is_monotonic_increasing
