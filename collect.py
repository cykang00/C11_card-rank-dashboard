"""1회 수집: 모든 키워드의 파워링크 순위를 가져와 변동 시에만 저장.

스케줄러/루프가 이 스크립트를 반복 호출한다.
"""
import datetime as _dt
from core import naver_rank as nr
from core import rank_store as store


def run_once() -> dict:
    now = _dt.datetime.now().replace(microsecond=0)
    df = store.load_history()
    summary = {}
    for keyword, depth in nr.KEYWORD_DEPTH.items():
        try:
            rows = nr.collect_keyword(keyword, depth)
        except Exception as e:
            summary[keyword] = f"수집실패: {e}"
            continue
        if not rows:
            summary[keyword] = "광고 없음"
            continue
        if store.is_changed(df, keyword, rows):
            store.append_snapshot(rows, now)
            summary[keyword] = f"변동 감지 → {len(rows)}건 저장"
        else:
            summary[keyword] = "변동 없음"
    return summary


if __name__ == "__main__":
    ts = _dt.datetime.now().strftime("%H:%M:%S")
    result = run_once()
    print(f"[{ts}] 수집 완료")
    for k, v in result.items():
        print(f"  - {k}: {v}")
