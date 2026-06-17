import pandas as pd
import pytest
from core.schema import COLUMNS, validate


def test_columns_order():
    assert COLUMNS[:4] == ["collected_date", "keyword", "search_pc", "search_mobile"]
    assert "bid_pos3" in COLUMNS


def test_validate_reorders_and_passes():
    df = pd.DataFrame({c: [0] for c in reversed(COLUMNS)})
    out = validate(df)
    assert list(out.columns) == COLUMNS


def test_validate_missing_column_raises():
    df = pd.DataFrame({"keyword": ["신용카드"]})
    with pytest.raises(ValueError):
        validate(df)
