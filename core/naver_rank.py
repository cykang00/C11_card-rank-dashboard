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


def fetch_search_html(keyword: str, timeout: float = 20.0) -> str:
    url = "https://search.naver.com/search.naver?query=" + urllib.parse.quote(keyword)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


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
        # 표시 URL: 단위 내 도메인형 텍스트
        urls = _URL_RE.findall(unit)
        display_url = urls[0] if urls else ""
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


# 키워드별 추적 깊이
KEYWORD_DEPTH = {
    "기후동행카드": 5,
    "국민행복카드": 5,
    "케이패스카드": 5,
    "프리미엄카드": 10,
}


try:
    _DICT_CACHE = load_dictionary()
except Exception:
    _DICT_CACHE = {}


def collect_keyword(keyword: str, top_n: int) -> list[dict]:
    return parse_ads(fetch_search_html(keyword), keyword, top_n)
