"""제휴카드 신용카드검색 순위 대시보드.

네이버 검색결과 '신용카드' 비교 위젯(관련광고순)의 카드 노출 순서를 키워드별 PC/모바일로
한 화면에 보여준다. 삼성카드는 '더보기' 전체 목록에서 지정 카드의 순위만 표시한다.
버튼을 누를 때마다 온디맨드 수집하며 누적 저장하지 않는다.
"""
import datetime as _dt
import html as _html
import concurrent.futures as _cf

import streamlit as st

from core import naver_rank as nr

DEVICES = [("pc", "💻 PC"), ("mobile", "📱 모바일")]
TOP_N = 6

# 삼성카드는 순위 목록 대신 '지정 카드가 삼성카드 전체목록에서 몇 번째인지'만 표시
SAMSUNG_KW = "삼성카드"
SAMSUNG_CODE = "SS"
SAMSUNG_TRACK = [
    "K-패스 삼성카드",
    "기후동행 삼성카드",
    "국민행복 삼성카드 V2",
    "MY S-OIL 삼성카드",
]
# 경쟁 키워드에서 강조할 카드 (정확히 이 카드명일 때만)
HIGHLIGHT_CARDS = set(SAMSUNG_TRACK)

st.set_page_config(page_title="제휴카드 신용카드검색 순위", page_icon="💳", layout="wide")

st.markdown("""
<style>
:root { --pri:#1B5FE0; --pri-soft:#E7F0FF; --navy:#0B2E73; --ink:#1B2430; --muted:#7C8698;
        --line:#EBEFF6; --card:#fff; --hl:#D6EDFF; --hl-ink:#0B4EA6; }
.stApp { background:#F3F6FC;
   font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.block-container { padding-top:0; padding-bottom:3.5rem; max-width:1340px; }
#MainMenu, header[data-testid="stHeader"], footer { visibility:hidden; }
/* 위젯 사이 세로 간격 (영역 간 여백) */
div[data-testid="stVerticalBlock"] { gap:1.5rem; }

/* 상단 브랜드 바 = 유일한 가로 블록(헤더)에 카드 스타일 */
/* 상단 바 = 전체 폭(full-bleed) 평평한 헤더 (::before로 흰 바를 화면 끝까지) */
.stApp { overflow-x:hidden; }
div[data-testid="stHorizontalBlock"] { position:relative; background:transparent;
   align-items:center; margin-top:-1.6rem; margin-bottom:1.1rem;
   padding-top:20px; padding-bottom:20px; }
div[data-testid="stHorizontalBlock"]::before { content:""; position:absolute; z-index:0;
   top:0; bottom:0; left:calc(50% - 50vw); width:100vw; background:#fff;
   border-bottom:1px solid #E9EDF4; box-shadow:0 2px 10px rgba(27,60,120,.05); }
div[data-testid="stHorizontalBlock"] > div { position:relative; z-index:1; }
.brand { display:flex; align-items:center; gap:16px; }
.logo { font-size:1.5rem; font-weight:800; letter-spacing:-.03em; color:var(--pri);
   padding-right:18px; border-right:1px solid #DFE4EE; line-height:1; }
.ttl .t1 { font-size:1.18rem; font-weight:800; color:var(--ink); letter-spacing:-.02em; }
.upd { text-align:center; color:var(--muted); font-size:.8rem; font-weight:600;
   margin-top:0; font-variant-numeric:tabular-nums; }
.upd b { color:var(--ink); }
/* 헤더 우측: 버튼 아래 수집시각, 버튼폭=텍스트폭, 서로 가운데 정렬 */
div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] { gap:9px; }
div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button {
   width:200px; margin:0 auto; display:block; padding:.5rem .6rem; }

/* 카드 */
.kw { background:var(--card); border-radius:18px; padding:18px 22px 10px;
      box-shadow:0 6px 22px rgba(27,60,120,.06); height:100%; }
.kw-head { display:flex; align-items:center; gap:9px; margin-bottom:14px; }
.kw-title { font-size:1.08rem; font-weight:800; color:var(--ink); letter-spacing:-.01em; }
.tag { font-size:.68rem; font-weight:700; color:var(--pri); background:var(--pri-soft);
       padding:3px 10px; border-radius:999px; }
/* 경쟁 키워드 3열 → 좁으면 1열 */
.comp-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:20px; }
@media (max-width:1000px){ .comp-grid { grid-template-columns:1fr; } }
.devblock { margin-bottom:16px; }
.devblock:last-child { margin-bottom:2px; }
.dev { font-size:.8rem; font-weight:700; color:var(--muted); margin-bottom:6px; }

table.rk { width:100%; border-collapse:collapse; font-size:.86rem; }
table.rk th { text-align:left; font-weight:600; color:var(--muted); font-size:.72rem;
              padding:5px 8px; border-bottom:1px solid var(--line); }
table.rk td { padding:8px 8px; border-bottom:1px solid var(--line); color:var(--ink); vertical-align:middle; }
table.rk td.rk-no { width:30px; text-align:center; font-weight:800; color:var(--pri);
           font-variant-numeric:tabular-nums; }
td.co { white-space:nowrap; width:56px; color:var(--muted); font-weight:600; font-size:.8rem; }
table.rk tr.hl td { background:var(--hl); color:var(--hl-ink); font-weight:700; }
table.rk tr.hl td.rk-no { color:var(--hl-ink); }

/* 삼성 추적 카드 (상단 피처 카드) */
table.sam { width:100%; border-collapse:collapse; font-size:.92rem; }
table.sam th { text-align:left; font-weight:600; color:var(--muted); font-size:.74rem;
               padding:8px 12px; border-bottom:1px solid var(--line); }
table.sam td { padding:12px; border-bottom:1px solid var(--line); color:var(--ink); }
td.big { text-align:center; width:110px; font-weight:800; font-size:1.15rem;
         color:var(--pri); font-variant-numeric:tabular-nums; }
td.miss { text-align:center; width:110px; color:var(--muted); font-weight:600; font-size:.85rem; }
td.cname { font-weight:700; }

.note { color:var(--muted); font-size:.76rem; margin:8px 2px 2px; }

/* 새로고침 버튼 */
div[data-testid="stButton"] > button { background:var(--pri); color:#fff; border:none;
   border-radius:12px; font-weight:700; padding:.55rem 1.1rem; box-shadow:0 4px 14px rgba(27,95,224,.28); }
div[data-testid="stButton"] > button:hover { background:#1550c4; transform:translateY(-1px); }
</style>
""", unsafe_allow_html=True)


# ── 수집 ────────────────────────────────────────────────
def collect_all() -> dict:
    out = {}

    def comp(job):
        kw, dev = job
        try:
            return job, ("ok", nr.collect_cards(kw, dev, TOP_N))
        except Exception as e:
            return job, ("err", str(e))

    def samsung(dev):
        try:
            return dev, ("ok", nr.find_card_positions(SAMSUNG_TRACK, SAMSUNG_CODE, dev))
        except Exception as e:
            return dev, ("err", str(e))

    comp_jobs = [(kw, dev) for kw in nr.KEYWORDS if kw != SAMSUNG_KW for dev, _ in DEVICES]
    with _cf.ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(comp, j) for j in comp_jobs]
        futs += [ex.submit(samsung, dev) for dev, _ in DEVICES]
        results = [f.result() for f in futs]

    sam = {}
    for key, res in results:
        if isinstance(key, tuple):
            out[key] = res
        else:
            sam[key] = res
    out[SAMSUNG_KW] = sam
    return out


# ── 렌더 ────────────────────────────────────────────────
def _rank_table(rows) -> str:
    trs = []
    for r in rows:
        cls = ' class="hl"' if r.get("card_name") in HIGHLIGHT_CARDS else ""
        co = _html.escape(r.get("company") or "—")
        name = _html.escape(r.get("card_name") or "")
        trs.append(f'<tr{cls}><td class="rk-no">{r["rank"]}</td>'
                   f'<td class="co">{co}</td><td>{name}</td></tr>')
    return ('<table class="rk"><thead><tr><th>순위</th><th>카드사</th><th>카드명</th></tr>'
            '</thead><tbody>' + "".join(trs) + "</tbody></table>")


def _cell_inner(status, payload, dev_label) -> str:
    if status == "err":
        return f'<div class="dev">{dev_label}</div><div class="note">수집 실패: {_html.escape(str(payload))}</div>'
    if not payload:
        return f'<div class="dev">{dev_label}</div><div class="note">노출 카드 없음</div>'
    return f'<div class="dev">{dev_label}</div>' + _rank_table(payload)


def competitive_card(kw, data) -> str:
    blocks = []
    for dev, dev_label in DEVICES:
        status, payload = data.get((kw, dev), ("err", "데이터 없음"))
        blocks.append(f'<div class="devblock">{_cell_inner(status, payload, dev_label)}</div>')
    return (f'<div class="kw"><div class="kw-head"><span class="kw-title">{_html.escape(kw)}</span></div>'
            f'{"".join(blocks)}</div>')


def samsung_card(sam) -> str:
    def ranks(dev):
        status, payload = sam.get(dev, ("err", None))
        return payload if status == "ok" else None
    pc, mo = ranks("pc"), ranks("mobile")
    err = next((pl for dev in ("pc", "mobile")
                for st_, pl in [sam.get(dev, ("err", "데이터 없음"))] if st_ == "err"), None)

    def cell(d, name):
        if d is None:
            return '<td class="miss">—</td>'
        v = d.get(name)
        return f'<td class="big">{v}위</td>' if v else '<td class="miss">미노출</td>'

    trs = [f'<tr><td class="cname">{_html.escape(n)}</td>{cell(pc, n)}{cell(mo, n)}</tr>'
           for n in SAMSUNG_TRACK]
    table = ('<table class="sam"><thead><tr><th>카드명</th>'
             '<th style="text-align:center">PC 순위</th>'
             '<th style="text-align:center">모바일 순위</th></tr></thead><tbody>'
             + "".join(trs) + "</tbody></table>")
    note = '<div class="note">삼성카드 전체 목록(관련광고순) 중 지정 카드의 순위 · 미노출 = 목록에 없음 · 순위는 조회 시점에 따라 변동(추정)</div>'
    errnote = f'<div class="note">일부 수집 실패: {_html.escape(str(err))}</div>' if err else ""
    return (f'<div class="kw feat"><div class="kw-head"><span class="kw-title">삼성카드</span>'
            f'<span class="tag">지정 카드 순위</span></div>{table}{note}{errnote}</div>')


# ── 헤더 (좌: 로고·제목 / 우: 새로고침 버튼 + 마지막 수집) ──
if "data" not in st.session_state:
    st.session_state["data"] = None

hcol1, hcol2 = st.columns([4, 1.2], vertical_alignment="center")
with hcol1:
    st.markdown(
        '<div class="brand">'
        '<span class="logo">삼성카드</span>'
        '<div class="ttl"><div class="t1">제휴카드 신용카드검색 순위 모니터링</div></div>'
        '</div>', unsafe_allow_html=True)
with hcol2:
    refresh = st.button("🔄 새로고침", use_container_width=False)
    time_ph = st.empty()

if refresh or st.session_state.get("data") is None:
    with st.spinner("네이버에서 최신 카드 순위 수집 중…"):
        st.session_state["data"] = collect_all()
        st.session_state["ts"] = _dt.datetime.now().strftime("%m/%d %H:%M:%S")
    if refresh:
        st.toast("최신 순위로 갱신했습니다 ✅ (관련광고순은 자주 바뀌지 않아 값이 같을 수 있어요)")

ts = st.session_state.get("ts", "-")
time_ph.markdown(f'<div class="upd">마지막 수집 · <b>{ts}</b></div>', unsafe_allow_html=True)

data = st.session_state["data"]

# ── 삼성카드 (최상단, 전체 폭) ───────────────────────────
st.markdown(samsung_card(data.get(SAMSUNG_KW, {})), unsafe_allow_html=True)

# ── 경쟁 키워드 (한 줄 3열 → 좁으면 세로 1열) ─────────────
comp_kws = [k for k in nr.KEYWORDS if k != SAMSUNG_KW]
cards = "".join(competitive_card(kw, data) for kw in comp_kws)
st.markdown(f'<div class="comp-grid">{cards}</div>', unsafe_allow_html=True)
