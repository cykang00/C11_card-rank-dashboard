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

# 경쟁 키워드 (관련광고순 TOP6 + 삼성 강조)
COMP_KWS = ["케이패스카드", "기후동행카드", "국민행복카드"]

# 프리미엄 지정 카드 (여러 패널에서 공용)
PREMIUM_TRACK = [
    "THE iD. TITANIUM (포인트)",
    "THE iD. PLATINUM (포인트)",
    "THE iD. 1st",
    "THE 1(스카이패스)",
]

# 삼성카드: 삼성 전체목록(companyCode=SS)에서 지정 카드가 몇 번째인지
SAMSUNG_KW = "삼성카드"
SAMSUNG_CODE = "SS"
SAMSUNG_TRACK = [
    "K-패스 삼성카드",
    "기후동행 삼성카드",
    "국민행복 삼성카드 V2",
    "MY S-OIL 삼성카드",
] + PREMIUM_TRACK

# 프리미엄카드: '프리미엄카드' 검색 더보기 목록(혜택 카테고리 6, 130건) 기준 지정 카드 순위
PREMIUM_KW = "프리미엄카드"
PREMIUM_BENEFIT_IDS = [6]
PREMIUM_SUB_BENEFIT_IDS = []   # 하위(33) 넣으면 다른 29건 목록이 되어 화면과 어긋남

# 삼성카드 추가 추적: 삼성 전체목록(SS)에서 아래 카드들의 순위 (하단 섹션)
# ※ 카탈로그 표기와 정확히 일치해야 매칭됨 (STATION 카드는 '… 카드 (…)' 형태)
EXTRA_KW = "삼성 카드 추가 순위"
EXTRA_TRACK = [
    "네이버페이 taptap",
    "삼성 iD PLUG-IN 카드",
    "신세계이마트 삼성카드 7",
    "taptap DRIVE",
    "삼성 iD SELECT ON 카드",
    "삼성 iD 해외 3.5 카드",
    "모니모카드",
    "삼성카드 & MILEAGE PLATINUM(스카이패스)",
    "삼성 iD ALL 카드",
    "삼성 iD VITA 카드",
    "KTX 삼성카드",
    "삼성 iD PET 카드",
    "삼성 iD ENERGY 카드",
    "모니모페이카드",
    "삼성 iD STATION 카드 (HD현대오일뱅크)",
    "taptap DIGITAL",
    "모니모A 카드",
    "아메리칸 엑스프레스 블루",
    "아메리칸 엑스프레스 리저브",
    "삼성 iD STATION 카드 (SK에너지)",
    "다이소 삼성카드",
    "삼성 iD ONE 카드",
    "삼성페이 삼성카드 taptap",
    "삼성 iD STATION 카드 (GS칼텍스)",
    "삼성 iD NOMAD 카드",
    "taptap SHOPPING",
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
/* 헤더 우측(마지막 열)의 버튼+수집시각을 가로 중앙 정렬 */
div[data-testid="stHorizontalBlock"] > div:last-child div[data-testid="stVerticalBlock"] { align-items:center; }
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
.err { background:#FDECEC; color:#B42318; border:1px solid #F5C2C0; border-radius:10px;
       padding:9px 12px; font-size:.82rem; font-weight:600; margin:2px 0 12px; }

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
            return ("comp", job), ("ok", nr.collect_cards(kw, dev, TOP_N))
        except Exception as e:
            return ("comp", job), ("err", str(e))

    def samsung(dev):
        # 삼성 전체목록(SS)을 한 번만 받아 삼성 패널 + 추가 추적 패널 순위를 함께 계산
        try:
            rows = nr.fetch_card_list(dev, company_code=SAMSUNG_CODE, page_size=120)
            names = [r["card_name"] for r in rows]
            return ("sam", dev), ("ok", (nr.positions_of(names, SAMSUNG_TRACK),
                                         nr.positions_of(names, EXTRA_TRACK)))
        except Exception as e:
            return ("sam", dev), ("err", str(e))

    def premium(dev):
        try:
            return ("prem", dev), ("ok", nr.find_card_positions(
                PREMIUM_TRACK, dev, benefit_category_ids=PREMIUM_BENEFIT_IDS,
                sub_benefit_category_ids=PREMIUM_SUB_BENEFIT_IDS))
        except Exception as e:
            return ("prem", dev), ("err", str(e))

    comp_jobs = [(kw, dev) for kw in COMP_KWS for dev, _ in DEVICES]
    with _cf.ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(comp, j) for j in comp_jobs]
        futs += [ex.submit(samsung, dev) for dev, _ in DEVICES]
        futs += [ex.submit(premium, dev) for dev, _ in DEVICES]
        results = [f.result() for f in futs]

    sam, prem, extra = {}, {}, {}
    for (kind, sub), res in results:
        if kind == "comp":
            out[sub] = res           # sub = (kw, dev)
        elif kind == "sam":
            status, payload = res
            if status == "ok":
                sam_pos, extra_pos = payload
                sam[sub] = ("ok", sam_pos)
                extra[sub] = ("ok", extra_pos)
            else:
                sam[sub] = res
                extra[sub] = res
        else:
            prem[sub] = res
    out[SAMSUNG_KW] = sam
    out[PREMIUM_KW] = prem
    out[EXTRA_KW] = extra
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


def tracked_card(title, track, data, note_text) -> str:
    """지정 카드가 전체 목록에서 몇 번째인지 PC/모바일로 보여주는 패널."""
    def ranks(dev):
        status, payload = data.get(dev, ("err", None))
        return payload if status == "ok" else None
    pc, mo = ranks("pc"), ranks("mobile")
    err = next((pl for dev in ("pc", "mobile")
                for st_, pl in [data.get(dev, ("err", "데이터 없음"))] if st_ == "err"), None)

    def cell(d, name):
        if d is None:
            return '<td class="miss">—</td>'
        v = d.get(name)
        return f'<td class="big">{v}위</td>' if v else '<td class="miss">미노출</td>'

    trs = [f'<tr><td class="cname">{_html.escape(n)}</td>{cell(pc, n)}{cell(mo, n)}</tr>'
           for n in track]
    table = ('<table class="sam"><thead><tr><th>카드명</th>'
             '<th style="text-align:center">PC 순위</th>'
             '<th style="text-align:center">모바일 순위</th></tr></thead><tbody>'
             + "".join(trs) + "</tbody></table>")
    note = f'<div class="note">{note_text}</div>'
    errnote = (f'<div class="err">⚠ 수집 실패 — {_html.escape(str(err))}</div>' if err else "")
    return (f'<div class="kw feat"><div class="kw-head"><span class="kw-title">{_html.escape(title)}</span>'
            f'<span class="tag">지정 카드 순위</span></div>{errnote}{table}{note}</div>')


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
        _kst = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))  # 서버가 UTC라 KST 고정
        st.session_state["ts"] = _kst.strftime("%m/%d %H:%M:%S")
    if refresh:
        st.toast("최신 순위로 갱신했습니다 ✅ (관련광고순은 자주 바뀌지 않아 값이 같을 수 있어요)")

ts = st.session_state.get("ts", "-")
time_ph.markdown(f'<div class="upd">마지막 수집 · <b>{ts}</b></div>', unsafe_allow_html=True)

data = st.session_state["data"]

# ── 삼성카드 (최상단, 전체 폭) ───────────────────────────
st.markdown(tracked_card(
    SAMSUNG_KW, SAMSUNG_TRACK, data.get(SAMSUNG_KW, {}),
    "삼성카드 전체 목록(관련광고순) 중 지정 카드의 순위 · 미노출 = 목록에 없음 · 순위는 조회 시점에 따라 변동(추정)",
), unsafe_allow_html=True)

# ── 프리미엄카드 (전체 폭) ───────────────────────────────
st.markdown(tracked_card(
    PREMIUM_KW, PREMIUM_TRACK, data.get(PREMIUM_KW, {}),
    "‘프리미엄카드’ 검색 더보기 목록(관련광고순) 중 지정 카드의 순위 · 미노출 = 목록에 없음 · 추정",
), unsafe_allow_html=True)

# ── 경쟁 키워드 (한 줄 3열 → 좁으면 세로 1열) ─────────────
cards = "".join(competitive_card(kw, data) for kw in COMP_KWS)
st.markdown(f'<div class="comp-grid">{cards}</div>', unsafe_allow_html=True)

# ── 삼성 카드 추가 순위 (하단, 전체 폭) ───────────────────
st.markdown(tracked_card(
    EXTRA_KW, EXTRA_TRACK, data.get(EXTRA_KW, {}),
    "삼성카드 전체 목록(관련광고순) 중 지정 카드의 순위 · 미노출 = 현재 광고 목록에 없음 · 추정",
), unsafe_allow_html=True)
