"""순위 스냅샷 저장 + 변동 감지.

순위는 수시로 바뀌므로 매 수집을 다 저장하지 않는다. 키워드별로 직전 저장된
순위(카드명 순서)와 새 순위를 비교해 **달라졌을 때만** 새 스냅샷을 append 한다.
"""
import os
import pandas as pd

COLUMNS = ["collected_at", "keyword", "rank", "card_name", "ad_title", "display_url"]
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "rank_history.csv")


def load_history(path: str = DEFAULT_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["collected_at"] = pd.to_datetime(df["collected_at"])
    return df


def _ranking_signature(rows: list[dict]) -> list[str]:
    """순위 비교용 시그니처: 순서대로 카드명(없으면 광고제목)."""
    return [(r.get("card_name") or r.get("ad_title") or "")[:60] for r in rows]


def latest_signature(df: pd.DataFrame, keyword: str) -> list[str]:
    sub = df[df["keyword"] == keyword]
    if sub.empty:
        return []
    last = sub[sub["collected_at"] == sub["collected_at"].max()].sort_values("rank")
    return [(c or t or "")[:60]
            for c, t in zip(last["card_name"].fillna(""), last["ad_title"].fillna(""))]


def is_changed(df: pd.DataFrame, keyword: str, rows: list[dict]) -> bool:
    return _ranking_signature(rows) != latest_signature(df, keyword)


def append_snapshot(rows: list[dict], collected_at, path: str = DEFAULT_PATH) -> None:
    """rows에 collected_at을 찍어 CSV에 append (헤더는 최초 1회)."""
    out = pd.DataFrame(rows)
    out["collected_at"] = collected_at
    out = out[COLUMNS]
    header = not os.path.exists(path)
    out.to_csv(path, mode="a", header=header, index=False, encoding="utf-8-sig")
