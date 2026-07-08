import datetime as dt
import pandas as pd
from core import rank_store as store


def _rows(order):
    return [{"rank": i + 1, "keyword": "기후동행카드", "card_name": c,
             "ad_title": f"{c} 광고", "display_url": "x.com"} for i, c in enumerate(order)]


def test_append_and_load(tmp_path):
    p = str(tmp_path / "h.csv")
    store.append_snapshot(_rows(["A", "B"]), dt.datetime(2026, 6, 17, 9, 0), path=p)
    df = store.load_history(p)
    assert list(df.columns) == store.COLUMNS
    assert len(df) == 2


def test_is_changed_detects_reorder(tmp_path):
    p = str(tmp_path / "h.csv")
    store.append_snapshot(_rows(["A", "B"]), dt.datetime(2026, 6, 17, 9, 0), path=p)
    df = store.load_history(p)
    assert store.is_changed(df, "기후동행카드", _rows(["B", "A"])) is True
    assert store.is_changed(df, "기후동행카드", _rows(["A", "B"])) is False


def test_is_changed_true_when_empty():
    df = pd.DataFrame(columns=store.COLUMNS)
    assert store.is_changed(df, "기후동행카드", _rows(["A"])) is True
