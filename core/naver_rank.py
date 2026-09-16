"""네이버 검색 파워링크 광고 순위 추출.

파워링크 광고는 검색결과 HTML에 서버 렌더된다. 광고 단위는 `ad_mark`(광고 표식)
스팬으로 구분되며, 각 단위에서 광고 제목·표시URL·카드 상품명을 추출한다.
"""
import re
import json
import os
import html as _html
import urllib.request
import urllib.parse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
# 모바일은 별도 UA로 m.search.naver.com 에 요청해야 모바일 파워링크 마크업을 받는다.
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
             "Mobile/15E148 Safari/604.1")


def _fetch(url: str, ua: str, timeout: float) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def fetch_search_html(keyword: str, timeout: float = 20.0) -> str:
    url = "https://search.naver.com/search.naver?query=" + urllib.parse.quote(keyword)
    return _fetch(url, UA, timeout)


def fetch_search_html_mobile(keyword: str, timeout: float = 20.0) -> str:
    url = "https://m.search.naver.com/search.naver?query=" + urllib.parse.quote(keyword)
    return _fetch(url, MOBILE_UA, timeout)


def _strip(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", _html.unescape(t))).strip()


# 표시 URL (도메인) 패턴
_URL_RE = re.compile(r"\b([a-z0-9][a-z0-9.-]+\.(?:com|co\.kr|kr|net|io)(?:/[A-Za-z0-9_/-]*)?)\b")
# 카드 상품명: '…카드'로 끝나는 토큰 (한글/영문/숫자 연속)
_CARD_RE = re.compile(r"([0-9A-Za-z가-힣+]*카드)")


def load_dictionary(path: str = None) -> dict:
    """카드 사전 로드. {keyword: [{card_name, match:[aliases]}]}"""
    path = path or os.path.join(os.path.dirname(__file__), "..", "cards.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {k: v for k, v in d.items() if not k.startswith("_")}


def extract_card_name(title: str, keyword: str, dictionary: dict = None) -> str:
    """사전 매칭으로 카드 상품명 식별. 사전에 없으면 best-effort 토큰."""
    if dictionary and keyword in dictionary:
        for entry in dictionary[keyword]:
            if any(alias in title for alias in entry["match"]):
                return entry["card_name"]
    # 사전 미스: '…카드' 토큰 best-effort
    cands = [c for c in _CARD_RE.findall(title) if len(c) > 2]
    return max(cands, key=len) if cands else ""


_ADER_ANCHOR = re.compile(r'<a\b[^>]*href="(https?://[^"]*ader\.naver[^"]*)"[^>]*>(.*?)</a>', re.S)
# PC 파워링크의 표시 도메인은 `lnk_url` 요소에 텍스트로 노출된다.
_PC_URL_RE = re.compile(r'class="lnk_url[^"]*"[^>]*>(.*?)<', re.S)
# 노이즈 도메인(광고 추적·정적리소스): 표시 URL 후보에서 제외
_NOISE_DOMS = ("ader.naver", "pstatic", "nstatic", "gstatic", "naver.net")


def _display_url_pc(unit: str) -> str:
    """PC 광고 단위에서 실제 표시 도메인 추출 (추적 URL 제외)."""
    for raw in _PC_URL_RE.findall(unit):
        txt = _strip(raw)
        if txt and not any(n in txt for n in _NOISE_DOMS):
            return txt
    # 폴백: 단위 내 도메인형 텍스트 중 노이즈 아닌 첫 번째
    for u in _URL_RE.findall(unit):
        if not any(n in u for n in _NOISE_DOMS):
            return u
    return ""


def parse_ads(page_html: str, keyword: str, top_n: int) -> list[dict]:
    """파워링크 광고를 순서대로 추출하여 상위 top_n개 반환.

    광고 단위는 `ad_mark` 경계로 나눈다. 단, ader.naver 광고 링크가 있는 단위만
    진짜 파워링크 광고로 인정한다(로그인·페이 위젯 노이즈 제외). 광고 제목은
    단위 내 가장 긴 ader 앵커 텍스트(설명형 헤드라인)로 잡는다.
    """
    start = page_html.lower().find("powerlink")
    seg = page_html[start:] if start != -1 else page_html
    marks = [m.start() for m in re.finditer(r'class="ad_mark"', seg)]
    dictionary = _DICT_CACHE if _DICT_CACHE is not None else {}
    rows: list[dict] = []
    for idx, pos in enumerate(marks):
        end = marks[idx + 1] if idx + 1 < len(marks) else pos + 4000
        unit = seg[pos:end]
        anchors = [(u, _strip(t)) for u, t in _ADER_ANCHOR.findall(unit)]
        anchors = [(u, t) for u, t in anchors if t]
        if not anchors:
            continue  # ader 광고 링크 없는 단위 = 광고 아님
        # 제목: 가장 긴 앵커 텍스트(설명형 헤드라인)
        title = max((t for _, t in anchors), key=len)
        # 카드 매칭은 단위 전체 텍스트 기준(설명에만 발행사가 있는 경우 포착)
        unit_text = " ".join(t for _, t in anchors)
        # 표시 URL: lnk_url 요소의 도메인 (추적 URL 제외)
        display_url = _display_url_pc(unit)
        rows.append({
            "rank": len(rows) + 1,
            "keyword": keyword,
            "card_name": extract_card_name(unit_text, keyword, dictionary),
            "ad_title": title,
            "display_url": display_url,
        })
        if len(rows) >= top_n:
            break
    return rows


# 모바일 파워링크 광고 단위: <ul id="power_link_body"> 안의 <li class="bx ...">,
# 각 광고는 광고표식 `icon_nad` 와 표시도메인 `class="url"` 를 가진다.
_MOBILE_URL_RE = re.compile(r'class="url"[^>]*>(.*?)<', re.S)


def parse_ads_mobile(page_html: str, keyword: str, top_n: int) -> list[dict]:
    """모바일 검색결과의 파워링크 광고를 순서대로 상위 top_n개 반환.

    광고 리스트는 `power_link_body` 컨테이너(없으면 `mobilePowerLink`)에서 시작하며,
    각 광고는 `<li class="bx ...">` 단위다. 진짜 광고만 세기 위해 광고표식
    `icon_nad` 가 있는 단위만 인정하고, 표식 없는 단위를 만나면 광고 블록이 끝난
    것으로 보고 중단한다.
    """
    anchor = page_html.find('id="power_link_body"')
    if anchor == -1:
        anchor = page_html.lower().find("mobilepowerlink")
    if anchor == -1:
        return []
    seg = page_html[anchor:anchor + 120000]
    dictionary = _DICT_CACHE if _DICT_CACHE is not None else {}
    marks = [m.start() for m in re.finditer(r'<li class="bx ', seg)]
    rows: list[dict] = []
    for idx, pos in enumerate(marks):
        end = marks[idx + 1] if idx + 1 < len(marks) else pos + 9000
        unit = seg[pos:end]
        if "icon_nad" not in unit:
            if rows:
                break  # 광고 블록 종료
            continue
        anchors = [_strip(t) for _, t in _ADER_ANCHOR.findall(unit)]
        anchors = [t for t in anchors if t]
        urlm = _MOBILE_URL_RE.search(unit)
        display_url = _strip(urlm.group(1)) if urlm else ""
        title = max(anchors, key=len) if anchors else display_url
        if not title:
            continue
        unit_text = " ".join(anchors) + " " + display_url
        rows.append({
            "rank": len(rows) + 1,
            "keyword": keyword,
            "card_name": extract_card_name(unit_text, keyword, dictionary),
            "ad_title": title,
            "display_url": display_url,
        })
        if len(rows) >= top_n:
            break
    return rows


# 추적 키워드 및 상위 노출 깊이 (한눈 대시보드 대상)
KEYWORDS = ["케이패스카드", "기후동행카드", "국민행복카드", "삼성카드"]
KEYWORD_DEPTH = {
    "케이패스카드": 5,
    "기후동행카드": 5,
    "국민행복카드": 5,
    "삼성카드": 5,
    "프리미엄카드": 10,
}


try:
    _DICT_CACHE = load_dictionary()
except Exception:
    _DICT_CACHE = {}


def collect_keyword(keyword: str, top_n: int) -> list[dict]:
    return parse_ads(fetch_search_html(keyword), keyword, top_n)


def collect(keyword: str, device: str, top_n: int = 5) -> list[dict]:
    """(파워링크) 단일 진입점. device: 'pc' | 'mobile'. 광고 순위 행 리스트 반환."""
    if device == "mobile":
        return parse_ads_mobile(fetch_search_html_mobile(keyword), keyword, top_n)
    return parse_ads(fetch_search_html(keyword), keyword, top_n)


# ─────────────────────────────────────────────────────────────
# 신용카드 비교 위젯 (검색결과 '신용카드' 영역, 관련광고순)
#
# 위젯 카드 목록은 검색결과 HTML 안에 GraphQL(JSON)로 서버렌더된다.
# 각 항목은 {"cardName": "...", "companyCode": "SS", ...} 이며 배열 순서가
# 화면 노출 순서(관련광고순, sortMethod="ri")다.
# ─────────────────────────────────────────────────────────────
COMPANY = {
    "SS": "삼성", "SH": "신한", "HD": "현대", "KB": "KB국민",
    "LO": "롯데", "WR": "우리", "HN": "하나", "BC": "BC",
    "IB": "IBK기업", "NH": "NH농협", "CT": "씨티", "SC": "SC제일",
    "KJ": "광주", "JB": "전북", "SU": "수협", "JJ": "제주",
}

_CARDAD_RE = re.compile(r'"cardName":"((?:[^"\\]|\\.)*)","companyCode":"([^"]*)"')


def _unescape_json_str(s: str) -> str:
    return s.replace('\\/', '/').replace('\\"', '"').replace('\\\\', '\\')


def parse_card_ads(page_html: str, top_n: int | None = None) -> list[dict]:
    """'신용카드' 비교 위젯의 카드 목록을 노출 순서대로 반환.

    반환 행: {rank, card_name, company_code, company}. 동일 카드명이 문서에 중복
    임베드되어도 첫 등장 순서를 유지하며 한 번만 센다.
    """
    seen: set[str] = set()
    rows: list[dict] = []
    for name, code in _CARDAD_RE.findall(page_html):
        name = _unescape_json_str(name)
        if name in seen:
            continue
        seen.add(name)
        rows.append({
            "rank": len(rows) + 1,
            "card_name": name,
            "company_code": code,
            "company": COMPANY.get(code, code),
        })
        if top_n and len(rows) >= top_n:
            break
    return rows


def collect_cards(keyword: str, device: str, top_n: int = 6) -> list[dict]:
    """'신용카드' 비교 위젯 단일 진입점. device: 'pc' | 'mobile'."""
    html = (fetch_search_html_mobile(keyword) if device == "mobile"
            else fetch_search_html(keyword))
    return parse_card_ads(html, top_n)


# ─────────────────────────────────────────────────────────────
# 전체 카드 목록 (검색결과 '더보기' → m-card-search GraphQL)
#
# 검색 위젯은 상위 6개만 노출한다. '더보기'가 여는 목록 페이지는 필터(카드사
# companyCode 또는 혜택 카테고리 benefitCategoryIds)로 좁힌 전체 카드를
# 관련광고순(sortMethod="ri")으로 보여주며, 그 데이터는 smartSearch GraphQL로
# 받는다. 지정 카드가 그 목록에서 '몇 번째'인지 알 때 쓴다.
# ─────────────────────────────────────────────────────────────
_GRAPHQL_URL = "https://m-card-search.naver.com/graphql"
_SMART_QUERY = (
    "query smartSearch($companyCode:[String],$benefitCategoryIds:[Int],"
    "$subBenefitCategoryIds:[Int],$pageNo:Int,$pageSize:Int,$sortMethod:SortMethod,"
    "$bizType:BizType,$device:AdDeviceType){"
    "cardAdList(companyCode:$companyCode,benefitCategoryIds:$benefitCategoryIds,"
    "subBenefitCategoryIds:$subBenefitCategoryIds,pageNo:$pageNo,pageSize:$pageSize,"
    "sortMethod:$sortMethod,bizType:$bizType,device:$device){"
    "cardAds{cardAdId cardName companyCode}}}"
)


def _fetch_card_page(device, variables, timeout):
    payload = json.dumps({
        "operationName": "smartSearch", "query": _SMART_QUERY, "variables": variables,
    }).encode("utf-8")
    ua = MOBILE_UA if device == "mobile" else UA
    req = urllib.request.Request(_GRAPHQL_URL, data=payload, headers={
        "User-Agent": ua, "Content-Type": "application/json", "Accept": "application/json",
        "Origin": "https://m-card-search.naver.com",
        "Referer": "https://m-card-search.naver.com/list",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", "ignore"))
    return data["data"]["cardAdList"]["cardAds"]


def fetch_card_list(device: str, *, company_code: str | None = None,
                    benefit_category_ids: list[int] | None = None,
                    sub_benefit_category_ids: list[int] | None = None,
                    page_size: int = 50, max_pages: int = 8,
                    timeout: float = 20.0) -> list[dict]:
    """필터(카드사·혜택 카테고리, 없으면 '신용카드' 전체)로 좁힌 카드를 관련광고순으로 반환.

    API가 한 번에 최대 50건만 주므로 pageNo로 끝까지 페이지네이션한다.
    반환 행: {rank, card_name, company_code}. device: 'pc' | 'mobile'.
    """
    base = {"pageSize": page_size, "sortMethod": "ri", "bizType": "CPC", "device": device}
    if company_code:
        base["companyCode"] = [company_code]
    if benefit_category_ids:
        base["benefitCategoryIds"] = benefit_category_ids
    if sub_benefit_category_ids:
        base["subBenefitCategoryIds"] = sub_benefit_category_ids
    seen: set[str] = set()
    rows: list[dict] = []
    for pno in range(1, max_pages + 1):
        cards = _fetch_card_page(device, {**base, "pageNo": pno}, timeout)
        if not cards:
            break
        for c in cards:
            name = c["cardName"]
            if name in seen:
                continue
            seen.add(name)
            rows.append({"rank": len(rows) + 1, "card_name": name,
                         "company_code": c.get("companyCode", "")})
        if len(cards) < page_size:
            break
    return rows


def fetch_company_cards(company_code: str, device: str, **kw) -> list[dict]:
    """카드사(companyCode) 전체 카드를 관련광고순으로 반환 (하위호환 래퍼)."""
    return fetch_card_list(device, company_code=company_code, **kw)


def positions_of(card_names: list[str], target_names: list[str]) -> dict:
    """순서 리스트에서 지정 카드명의 순위(1-base)를 찾는다. 없으면 None. (순수 함수)"""
    return {t: (card_names.index(t) + 1 if t in card_names else None)
            for t in target_names}


def find_card_positions(target_names: list[str], device: str, *,
                        company_code: str | None = None,
                        benefit_category_ids: list[int] | None = None,
                        sub_benefit_category_ids: list[int] | None = None) -> dict:
    """필터로 좁힌 전체 목록에서 지정 카드명들의 순위를 반환. {card_name: rank | None}"""
    rows = fetch_card_list(device, company_code=company_code,
                           benefit_category_ids=benefit_category_ids,
                           sub_benefit_category_ids=sub_benefit_category_ids)
    return positions_of([r["card_name"] for r in rows], target_names)
