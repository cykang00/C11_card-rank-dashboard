"""3~5분 랜덤 간격으로 collect.run_once 를 반복 실행하는 폴링 루프.

네이버 ToS·차단 위험을 줄이려 고정 주기 대신 랜덤 지터를 둔다. 변동이 있을 때만
저장되므로 rank_history.csv 는 깔끔하게 쌓인다. Ctrl+C 로 종료.

실행: uv run python collect_loop.py
"""
import random
import time
import datetime as _dt
from collect import run_once

MIN_SEC, MAX_SEC = 180, 300  # 3~5분

if __name__ == "__main__":
    print("폴링 루프 시작 (3~5분 랜덤 간격, Ctrl+C 종료)")
    while True:
        ts = _dt.datetime.now().strftime("%H:%M:%S")
        try:
            result = run_once()
            changes = sum(1 for v in result.values() if "변동 감지" in v)
            print(f"[{ts}] 수집 — 변동 {changes}건")
        except Exception as e:
            print(f"[{ts}] 오류: {e}")
        wait = random.uniform(MIN_SEC, MAX_SEC)
        print(f"  다음 수집까지 {wait/60:.1f}분 대기")
        time.sleep(wait)
