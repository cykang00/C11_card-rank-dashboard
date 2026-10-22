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

DEVICES = [("pc", "PC"), ("mobile", "모바일")]
TOP_N = 6

# 경쟁 키워드 (관련광고순 TOP6 + 삼성 강조)
COMP_KWS = ["케이패스카드", "국민행복카드"]

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
    "국민행복 삼성카드 V2",
    "MY S-OIL 삼성카드",
] + PREMIUM_TRACK

# 프리미엄카드: '프리미엄카드' 검색 더보기 목록(혜택 카테고리 6, 130건) 기준 지정 카드 순위
PREMIUM_KW = "프리미엄카드"
PREMIUM_BENEFIT_IDS = [6]
PREMIUM_SUB_BENEFIT_IDS = []   # 하위(33) 넣으면 다른 29건 목록이 되어 화면과 어긋남

# 삼성카드 추가 추적: 삼성 전체목록(SS)에서 아래 카드들의 순위 (하단 섹션)
# ※ 카탈로그 표기와 정확히 일치해야 매칭됨 (STATION 카드는 '… 카드 (…)' 형태)
EXTRA_KW = "삼성카드 추가 순위"
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
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
:root{ --bg:#EDF0F8; --card:#fff; --ink:#202A44; --muted:#8A92A8; --faint:#AEB6C8;
  --line:#EFF1F7; --line2:#F4F6FB;
  --acc:#4E6EF5; --acc-ink:#3A57D8; --acc-soft:#EBF0FE; --acc-soft2:#F3F6FE;
  --grad1:#5A78FA; --grad2:#6E8CFF; --hl:#EAF0FF; --miss-bg:#F0F2F7;
  --sh:0 14px 34px -18px rgba(60,80,170,.22); --sh-sm:0 8px 20px -14px rgba(60,80,170,.18); --r:24px; }
html{ scroll-behavior:smooth; }
.stApp{ background:var(--bg);
  font-family:"Pretendard","Pretendard Variable","Apple SD Gothic Neo","Malgun Gothic",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.block-container{ padding-top:1.3rem; padding-bottom:4rem; max-width:1200px; }
/* Streamlit 기본 폰트보다 우선해 Pretendard 강제 (내 마크다운 영역 + 버튼) */
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
div[data-testid="stButton"] button{
  font-family:"Pretendard","Pretendard Variable","Apple SD Gothic Neo","Malgun Gothic",-apple-system,sans-serif !important; }
#MainMenu, header[data-testid="stHeader"], footer{ visibility:hidden; }
div[data-testid="stVerticalBlock"]{ gap:1.6rem; }
/* 알약 네비 = 유일한 columns 블록을 흰 pill로, 버튼은 우측 안쪽 */
div[data-testid="stHorizontalBlock"]{ background:#fff; border-radius:999px; box-shadow:var(--sh-sm);
  align-items:center; gap:.5rem; padding:8px 14px; }
div[data-testid="stHorizontalBlock"] > div:last-child div[data-testid="stButton"]{ display:flex; justify-content:flex-end; }
.navrow{ display:flex; align-items:center; gap:10px; }
.logo{ display:flex; align-items:center; gap:10px; font-weight:800; font-size:1.12rem; letter-spacing:-.02em; padding:2px 12px 2px 4px; color:var(--ink); }
.logo .mark{ width:30px; height:30px; border-radius:9px; background:linear-gradient(135deg,var(--grad1),var(--grad2));
  display:grid; place-items:center; }
.navitems{ display:flex; gap:4px; }
.navitems a{ color:var(--muted); font-weight:600; font-size:.9rem; padding:8px 16px; border-radius:999px;
  text-decoration:none; cursor:pointer; transition:background .15s,color .15s; }
.navitems a:hover{ background:var(--acc-soft); color:var(--acc-ink); }
.navitems a.on{ background:var(--acc); color:#fff; box-shadow:0 6px 16px -6px rgba(78,110,245,.6); }
.navitems a.on:hover{ background:var(--acc); color:#fff; }
:target{ scroll-margin-top:16px; }

/* 인사 */
.greet{ margin-bottom:24px; }
.hi{ font-size:1.8rem; font-weight:800; letter-spacing:-.03em; color:var(--ink); }
.hi b{ color:var(--acc); font-weight:800; }
.sub{ color:var(--muted); font-size:.88rem; margin-top:6px; }
/* 순위 색상 범례 */
.legend{ display:flex; align-items:center; gap:8px; margin-top:12px; font-size:.74rem;
  font-weight:700; color:var(--faint); }
.legend .lg{ font-weight:800; font-variant-numeric:tabular-nums; padding:3px 10px; border-radius:999px; background:#fff; box-shadow:var(--sh-sm); }
.legend .lg.t1{ color:var(--acc); } .legend .lg.t2{ color:var(--ink); } .legend .lg.t3{ color:#9AA3B6; }

/* 요약 3카드 */
.stats{ display:grid; grid-template-columns:1fr 1.2fr 1fr; gap:18px; }
.stat{ background:#fff; border-radius:var(--r); box-shadow:var(--sh); padding:26px 28px; }
.stat .chip{ width:42px; height:42px; border-radius:13px; background:var(--acc-soft); display:grid;
  place-items:center; color:var(--acc); margin-bottom:12px; font-size:1.15rem; }
.stat .lab{ color:var(--muted); font-size:.84rem; font-weight:600; }
.stat .val{ font-size:1.9rem; font-weight:800; letter-spacing:-.02em; margin-top:6px; font-variant-numeric:tabular-nums; color:var(--ink); }
.stat .val small{ font-size:.85rem; color:var(--muted); font-weight:600; margin-left:3px; }
.stat.hero{ background:linear-gradient(135deg,var(--grad1),var(--grad2)); color:#fff;
  box-shadow:0 18px 40px -16px rgba(78,110,245,.55); position:relative; overflow:hidden; }
.stat.hero .deco{ position:absolute; right:-30px; bottom:-40px; width:160px; height:160px; border-radius:50%; background:rgba(255,255,255,.1); }
.stat.hero .chip{ background:rgba(255,255,255,.18); color:#fff; }
.stat.hero .lab{ color:#D9E2FF; } .stat.hero .val{ color:#fff; } .stat.hero .val small{ color:#EAEFFF; }
.stat.hero .up{ margin-top:10px; font-size:.8rem; color:#E4EAFF; position:relative; }

/* 패널 */
.panel{ background:#fff; border-radius:var(--r); box-shadow:var(--sh); padding:30px 34px 22px; }
.phead{ display:flex; align-items:center; gap:10px; margin:0 2px 22px; }
.ptitle{ font-size:1.14rem; font-weight:800; letter-spacing:-.01em; color:var(--ink); }
.ptag{ font-size:.7rem; font-weight:700; color:var(--acc); background:var(--acc-soft); padding:4px 11px; border-radius:999px; }
.note{ color:var(--faint); font-size:.76rem; margin:12px 2px 2px; line-height:1.5; }
.err{ background:#FEEDED; color:#C0392B; border-radius:12px; padding:10px 14px; font-size:.82rem; font-weight:600; margin:0 0 12px; }

/* 지정카드 그룹표 */
.gt{ width:100%; border-collapse:separate; border-spacing:0; font-size:.92rem; table-layout:fixed; }
.gt col{ width:17.5%; } .gt col.c-name{ width:30%; }
.gt thead th{ font-weight:700; color:var(--muted); }
.gt thead tr:first-child th{ font-size:.82rem; padding:8px 12px 10px; }
.gt thead tr:first-child th .gband{ display:inline-block; background:var(--acc-soft); color:var(--acc-ink);
  padding:6px 18px; border-radius:999px; font-size:.78rem; font-weight:700; }
.gt thead tr:first-child th.cc .gband{ background:#E6ECFA; color:var(--acc-ink); }
.gt thead tr:last-child th{ font-size:.72rem; letter-spacing:.04em; color:var(--faint); padding:4px 12px 14px; }
.gt th.cardcol{ text-align:left; vertical-align:bottom; padding-left:10px; color:var(--muted); font-size:.74rem; }
.gt td{ padding:17px 14px; border-bottom:1px solid #F1F3FA; text-align:center; vertical-align:middle; }
.gt tbody tr:hover td{ background:var(--acc-soft2); }
.gt td.name{ text-align:left; font-weight:600; color:var(--ink); padding-left:10px; font-size:.95rem;
  white-space:normal; line-height:1.35; word-break:keep-all; }
/* 두 '검색' 그룹을 선 대신 은은한 음영으로 구분 (secondary 2개 열) */
.gt thead tr:first-child th.cc,
.gt thead tr:last-child th:nth-child(3), .gt thead tr:last-child th:nth-child(4),
.gt tbody td:nth-child(4), .gt tbody td:nth-child(5){ background:#F6F8FF; }
.gt tbody tr:hover td:nth-child(4), .gt tbody tr:hover td:nth-child(5){ background:#EEF2FF; }
.rk{ font-weight:800; font-variant-numeric:tabular-nums; font-size:1.14rem; letter-spacing:-.01em; }
.rk small{ font-size:.64em; font-weight:600; color:var(--faint); margin-left:1px; }
.rk.t1{ color:var(--acc); } .rk.t2{ color:var(--ink); } .rk.t3{ color:#9AA3B6; }
.miss{ display:inline-block; font-size:.72rem; font-weight:700; color:#A2AAC0; background:var(--miss-bg); padding:4px 10px; border-radius:999px; }

/* 경쟁 키워드 */
.sectlabel{ font-size:.8rem; font-weight:800; color:var(--muted); letter-spacing:.06em; margin:14px 6px 0; }
.comp-grid{ display:grid; grid-template-columns:repeat(2,1fr); gap:18px; }
@media (max-width:820px){ .comp-grid{ grid-template-columns:1fr; } }
.kw{ background:#fff; border-radius:20px; box-shadow:var(--sh); padding:24px 24px 14px; }
.kw .ptitle{ font-size:1.02rem; }
.devblock{ margin-bottom:4px; }
.dev{ font-size:.74rem; font-weight:700; color:var(--acc); background:var(--acc-soft); display:inline-block;
  padding:4px 11px; border-radius:999px; margin:14px 0 8px; }
.rt{ width:100%; border-collapse:collapse; font-size:.86rem; }
.rt td{ padding:11px 9px; border-bottom:1px solid #F1F3FA; color:var(--ink); }
.rt td.no{ width:34px; text-align:center; }
.rt td.no span{ display:inline-grid; place-items:center; width:23px; height:23px; border-radius:8px;
  background:#F2F4FA; color:var(--muted); font-weight:800; font-size:.76rem; font-variant-numeric:tabular-nums; }
.rt td.co{ color:var(--muted); font-weight:600; font-size:.78rem; white-space:nowrap; width:48px; }
.rt tr.hl td{ background:var(--hl); }
.rt tr.hl td.no span{ background:var(--acc); color:#fff; }
.rt tr.hl td.nm{ font-weight:700; color:var(--acc-ink); }

/* 새로고침 버튼 */
div[data-testid="stButton"] > button{ background:var(--acc); color:#fff; border:none; border-radius:999px;
  font-weight:700; padding:.5rem 1.35rem; box-shadow:0 8px 18px -8px rgba(78,110,245,.6); transition:transform .12s; }
div[data-testid="stButton"] > button:hover{ background:var(--acc-ink); transform:translateY(-1px); }
div[data-testid="stButton"] > button:active{ transform:scale(.98); }
</style>
""", unsafe_allow_html=True)


# ── 수집 ────────────────────────────────────────────────
# 각 지정-카드 패널은 두 목록에서의 순위를 나란히 보여준다:
#   primary = 그 패널 고유 목록(삼성카드 SS / 프리미엄카드 cat6)
#   credit  = '신용카드' 전체 목록(필터 없음)
# 목록별로 한 번만 받아(디바이스별) 여러 패널이 공유한다.
def _fetch_list(kind, dev):
    if kind == "ss":
        return nr.fetch_card_list(dev, company_code=SAMSUNG_CODE)
    if kind == "prem":
        return nr.fetch_card_list(dev, benefit_category_ids=PREMIUM_BENEFIT_IDS,
                                  sub_benefit_category_ids=PREMIUM_SUB_BENEFIT_IDS)
    return nr.fetch_card_list(dev)  # 신용카드 전체


# 패널 정의: (키, 추적목록, primary 종류, primary 라벨, secondary 종류, secondary 라벨)
PANELS = [
    (SAMSUNG_KW, SAMSUNG_TRACK, "ss", "삼성카드", "credit", "신용카드"),
    (PREMIUM_KW, PREMIUM_TRACK, "prem", "프리미엄카드", "ss", "삼성카드"),
    (EXTRA_KW, EXTRA_TRACK, "ss", "삼성카드", "credit", "신용카드"),
]
_LIST_KINDS = {"ss", "prem", "credit"}


def collect_all() -> dict:
    out = {}

    def comp(job):
        kw, dev = job
        try:
            return ("comp", job), ("ok", nr.collect_cards(kw, dev, TOP_N))
        except Exception as e:
            return ("comp", job), ("err", str(e))

    def listjob(kind, dev):
        try:
            return ("list", (kind, dev)), ("ok", [r["card_name"] for r in _fetch_list(kind, dev)])
        except Exception as e:
            return ("list", (kind, dev)), ("err", str(e))

    comp_jobs = [(kw, dev) for kw in COMP_KWS for dev, _ in DEVICES]
    list_jobs = [(k, dev) for k in _LIST_KINDS for dev, _ in DEVICES]
    with _cf.ThreadPoolExecutor(max_workers=14) as ex:
        futs = [ex.submit(comp, j) for j in comp_jobs]
        futs += [ex.submit(listjob, k, dev) for k, dev in list_jobs]
        results = [f.result() for f in futs]

    names_by = {}  # (kind, dev) -> (status, names|err)
    for (tag, sub), res in results:
        if tag == "comp":
            out[sub] = res
        else:
            names_by[sub] = res

    # 패널별로 primary + secondary 순위를 조립
    for key, track, primary_kind, _pl, secondary_kind, _sl in PANELS:
        panel = {}
        for dev, _ in DEVICES:
            pstat, pnames = names_by.get((primary_kind, dev), ("err", "데이터 없음"))
            sstat, snames = names_by.get((secondary_kind, dev), ("err", "데이터 없음"))
            if pstat == "ok" and sstat == "ok":
                panel[dev] = ("ok", {"primary": nr.positions_of(pnames, track),
                                     "secondary": nr.positions_of(snames, track)})
            else:
                panel[dev] = ("err", pnames if pstat == "err" else snames)
        out[key] = panel
    return out


# ── 렌더 ────────────────────────────────────────────────
def _rk(v) -> str:
    """순위 숫자 → 티어 컬러 span (1~5 강조, 6~15 보통, 16+ 연함)."""
    t = "t1" if v <= 5 else "t2" if v <= 15 else "t3"
    return f'<span class="rk {t}">{v}<small>위</small></span>'


def competitive_card(kw, data) -> str:
    blocks = []
    for dev, dev_label in DEVICES:
        status, payload = data.get((kw, dev), ("err", "데이터 없음"))
        if status == "err":
            inner = f'<div class="note">수집 실패: {_html.escape(str(payload))}</div>'
        elif not payload:
            inner = '<div class="note">노출 카드 없음</div>'
        else:
            trs = []
            for r in payload:
                hl = ' class="hl"' if r.get("card_name") in HIGHLIGHT_CARDS else ""
                co = _html.escape(r.get("company") or "—")
                nm = _html.escape(r.get("card_name") or "")
                trs.append(f'<tr{hl}><td class="no"><span>{r["rank"]}</span></td>'
                           f'<td class="co">{co}</td><td class="nm">{nm}</td></tr>')
            inner = '<table class="rt"><tbody>' + "".join(trs) + "</tbody></table>"
        blocks.append(f'<div class="devblock"><span class="dev">{dev_label}</span>{inner}</div>')
    return (f'<div class="kw"><div class="phead"><span class="ptitle">{_html.escape(kw)}</span></div>'
            f'{"".join(blocks)}</div>')


def tracked_card(title, primary_label, secondary_label, track, data, note_text, anchor="") -> str:
    """지정 카드가 [primary 목록]과 [secondary 목록]에서 각각 PC/모바일 몇 위인지.

    행은 'secondary(오른쪽 그룹) 모바일 순위' 오름차순 정렬(미노출은 맨 아래).
    """
    def sets(dev):
        status, payload = data.get(dev, ("err", None))
        if status == "ok":
            return payload["primary"], payload["secondary"]
        return None, None
    pc_pri, pc_sec = sets("pc")
    mo_pri, mo_sec = sets("mobile")
    err = next((pl for dev in ("pc", "mobile")
                for st_, pl in [data.get(dev, ("err", "데이터 없음"))] if st_ == "err"), None)

    def rank(d, name):
        return d.get(name) if d else None

    order = sorted(track, key=lambda n: (
        rank(mo_sec, n) is None, rank(mo_sec, n) or 0,
        rank(mo_pri, n) is None, rank(mo_pri, n) or 0))

    def cell(d, name):
        if d is None:
            return '<td><span class="miss">—</span></td>'
        v = d.get(name)
        return f'<td>{_rk(v)}</td>' if v else '<td><span class="miss">미노출</span></td>'

    trs = []
    for n in order:
        trs.append(
            f'<tr><td class="name">{_html.escape(n)}</td>'
            f'{cell(pc_pri, n)}{cell(mo_pri, n)}'
            f'{cell(pc_sec, n)}{cell(mo_sec, n)}</tr>')
    table = (
        '<table class="gt"><colgroup><col class="c-name"><col><col><col class="c-sec"><col></colgroup><thead>'
        '<tr><th class="cardcol" rowspan="2">카드명</th>'
        f'<th colspan="2"><span class="gband">{_html.escape(primary_label)} 검색</span></th>'
        f'<th colspan="2" class="cc"><span class="gband">{_html.escape(secondary_label)} 검색</span></th></tr>'
        '<tr><th>PC</th><th>MO</th><th>PC</th><th>MO</th></tr>'
        '</thead><tbody>' + "".join(trs) + "</tbody></table>")
    note = f'<div class="note">{note_text}</div>'
    errnote = (f'<div class="err">⚠ 수집 실패 — {_html.escape(str(err))}</div>' if err else "")
    aid = f' id="{anchor}"' if anchor else ""
    return (f'<div class="panel"{aid}><div class="phead"><span class="ptitle">{_html.escape(title)}</span>'
            f'<span class="ptag">{_html.escape(secondary_label)} MO 오름차순</span></div>'
            f'{errnote}{table}{note}</div>')


# ── 알약 네비 (좌: 로고·메뉴 / 우: 새로고침) ──────────────
if "data" not in st.session_state:
    st.session_state["data"] = None

ncol1, ncol2 = st.columns([5, 1.3], vertical_alignment="center")
with ncol1:
    st.markdown(
        '<div class="navrow" id="top"><div class="logo">삼성카드</div>'
        '<div class="navitems"><a class="on" href="#top">대시보드</a>'
        '<a href="#sec-samsung">삼성카드</a><a href="#sec-premium">프리미엄</a>'
        '<a href="#sec-comp">경쟁 키워드</a></div></div>', unsafe_allow_html=True)
with ncol2:
    refresh = st.button("↻ 새로고침", use_container_width=False)

# ── 인사줄 (전체 폭) + 순위 색상 범례 ─────────────────────
st.markdown(
    '<div class="greet"><div class="hi">신용카드검색 순위 <b>모니터링</b></div>'
    '<div class="sub">네이버 검색결과 ‘신용카드’ 비교 위젯 · 관련광고순 기준 · 추정치</div>'
    '<div class="legend">순위 색상'
    '<span class="lg t1">1~5위</span><span class="lg t2">6~15위</span>'
    '<span class="lg t3">16위~</span></div></div>',
    unsafe_allow_html=True)

if refresh or st.session_state.get("data") is None:
    with st.spinner("네이버에서 최신 카드 순위 수집 중…"):
        st.session_state["data"] = collect_all()
        _kst = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))  # 서버가 UTC라 KST 고정
        st.session_state["ts"] = _kst.strftime("%m/%d %H:%M:%S")
    if refresh:
        st.toast("최신 순위로 갱신했습니다 (관련광고순은 자주 바뀌지 않아 값이 같을 수 있어요)")

ts = st.session_state.get("ts", "-")
data = st.session_state["data"]

# ── 요약 3카드 ───────────────────────────────────────────
_kw_cnt = len(COMP_KWS) + 2  # +삼성카드 +프리미엄카드
_card_cnt = len(set(SAMSUNG_TRACK) | set(EXTRA_TRACK))
st.markdown(
    '<div class="stats">'
    f'<div class="stat"><div class="chip">◎</div><div class="lab">추적 키워드</div>'
    f'<div class="val">{_kw_cnt}<small>개</small></div></div>'
    '<div class="stat hero"><div class="deco"></div><div class="chip">★</div>'
    f'<div class="lab">추적 중인 삼성카드</div><div class="val">{_card_cnt}<small>종</small></div>'
    '<div class="up">PC · 모바일 동시 추적 · 관련광고순</div></div>'
    f'<div class="stat"><div class="chip">◷</div><div class="lab">마지막 수집</div>'
    f'<div class="val" style="font-size:1.45rem">{ts}</div></div>'
    '</div>', unsafe_allow_html=True)

# ── 삼성카드 ─────────────────────────────────────────────
st.markdown(tracked_card(
    SAMSUNG_KW, "삼성카드", "신용카드", SAMSUNG_TRACK, data.get(SAMSUNG_KW, {}),
    "‘삼성카드’ 검색 목록과 ‘신용카드’ 전체 검색 목록(관련광고순) 각각에서 지정 카드의 순위 · 미노출 = 목록에 없음 · 추정",
    anchor="sec-samsung",
), unsafe_allow_html=True)

# ── 프리미엄카드 ─────────────────────────────────────────
st.markdown(tracked_card(
    PREMIUM_KW, "프리미엄카드", "삼성카드", PREMIUM_TRACK, data.get(PREMIUM_KW, {}),
    "‘프리미엄카드’ 검색 목록과 ‘삼성카드’ 검색 목록(관련광고순) 각각에서 지정 카드의 순위 · 미노출 = 목록에 없음 · 추정",
    anchor="sec-premium",
), unsafe_allow_html=True)

# ── 경쟁 키워드 (2열 → 좁으면 1열) ───────────────────────
st.markdown('<div class="sectlabel" id="sec-comp">경쟁 키워드 · 관련광고순 TOP6</div>', unsafe_allow_html=True)
cards = "".join(competitive_card(kw, data) for kw in COMP_KWS)
st.markdown(f'<div class="comp-grid">{cards}</div>', unsafe_allow_html=True)

# ── 삼성카드 추가 순위 (하단) ────────────────────────────
st.markdown(tracked_card(
    EXTRA_KW, "삼성카드", "신용카드", EXTRA_TRACK, data.get(EXTRA_KW, {}),
    "‘삼성카드’ 검색 목록과 ‘신용카드’ 전체 검색 목록(관련광고순) 각각에서 지정 카드의 순위 · 미노출 = 목록에 없음 · 추정",
), unsafe_allow_html=True)
