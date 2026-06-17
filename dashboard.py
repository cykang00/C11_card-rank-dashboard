import streamlit as st
import plotly.express as px
from core.data_source import load_sample
from core.charts import latest_snapshot, keyword_timeseries

st.set_page_config(page_title="네이버 키워드 트래커", layout="wide")
st.title("📊 네이버 신용카드 키워드 트래커")
st.caption("샘플 데이터 모드 — 수집기 연결 전 미리보기")

df = load_sample()
snap = latest_snapshot(df)

# 1) 비교 표 + 검색량 막대
st.subheader("키워드 비교 (최신 수집일)")
st.dataframe(snap, use_container_width=True, hide_index=True)
st.plotly_chart(
    px.bar(
        snap.sort_values("search_total", ascending=False),
        x="keyword", y="search_total", color="comp_idx",
        title="키워드별 월 검색량", text_auto=True,
    ),
    use_container_width=True,
)

# 2) 검색량 vs 1위 입찰가 산점도 (기회 탐색)
st.subheader("기회 탐색: 검색량 vs 1위 입찰가")
st.plotly_chart(
    px.scatter(
        snap, x="search_total", y="bid_pos1", color="comp_idx",
        size="search_total", text="keyword",
        labels={"search_total": "월 검색량", "bid_pos1": "1위 예상입찰가(원)"},
        title="검색량 대비 1위 입찰가 (왼쪽 위 = 저비용·고검색 기회)",
    ),
    use_container_width=True,
)

# 3) 선택 키워드 추이
st.subheader("키워드 추이")
kw = st.selectbox("키워드 선택", sorted(df["keyword"].unique()))
ts = keyword_timeseries(df, kw)
st.plotly_chart(
    px.line(
        ts, x="collected_date", y=["search_total", "bid_pos1", "bid_pos2", "bid_pos3"],
        markers=True, title=f"'{kw}' 날짜별 검색량·입찰가 추이",
    ),
    use_container_width=True,
)
