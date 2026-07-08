import os
from core import naver_rank as nr

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "naver_climate.html")
MOBILE_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "naver_mobile_kpass.html")
CARD_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "naver_pc_samsung.html")


def _card_html():
    with open(CARD_FIXTURE, encoding="utf-8") as f:
        return f.read()


def _html():
    with open(FIXTURE, encoding="utf-8") as f:
        return f.read()


def _mobile_html():
    with open(MOBILE_FIXTURE, encoding="utf-8") as f:
        return f.read()


def test_parse_ads_returns_ranked_rows():
    rows = nr.parse_ads(_html(), "기후동행카드", 5)
    assert 1 <= len(rows) <= 5
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    assert all(r["ad_title"] for r in rows)


def test_parse_ads_respects_top_n():
    rows = nr.parse_ads(_html(), "기후동행카드", 3)
    assert len(rows) <= 3


def test_extract_card_name_uses_dictionary():
    d = {"기후동행카드": [{"card_name": "신한 기후동행카드", "match": ["신한"]}]}
    assert nr.extract_card_name("신한 후불 기후동행 신용카드", "기후동행카드", d) == "신한 기후동행카드"


def test_extract_card_name_falls_back_to_token():
    assert nr.extract_card_name("무엇 프리미엄카드 혜택", "프리미엄카드", {}) == "프리미엄카드"


def test_extract_card_name_empty_when_no_card():
    assert nr.extract_card_name("그냥 광고 문구", "기후동행카드", {}) == ""


def test_parse_ads_mobile_returns_ranked_rows():
    rows = nr.parse_ads_mobile(_mobile_html(), "케이패스카드", 5)
    assert 1 <= len(rows) <= 5
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    assert all(r["ad_title"] for r in rows)


def test_parse_ads_mobile_extracts_display_url_and_card():
    rows = nr.parse_ads_mobile(_mobile_html(), "케이패스카드", 5)
    urls = [r["display_url"] for r in rows]
    assert any("shinhancard.com" in u for u in urls)
    # 사전 매칭으로 발행사 상품명이 채워진다
    assert any(r["card_name"] for r in rows)


def test_parse_ads_mobile_respects_top_n():
    rows = nr.parse_ads_mobile(_mobile_html(), "케이패스카드", 2)
    assert len(rows) <= 2


def test_parse_ads_mobile_empty_when_no_powerlink():
    assert nr.parse_ads_mobile("<html>광고 없음</html>", "케이패스카드", 5) == []


def test_parse_card_ads_returns_ordered_cards():
    rows = nr.parse_card_ads(_card_html(), 6)
    assert len(rows) == 6
    assert [r["rank"] for r in rows] == [1, 2, 3, 4, 5, 6]
    # 관련광고순 노출 순서: 첫 카드는 삼성카드 taptap O
    assert rows[0]["card_name"] == "삼성카드 taptap O"
    assert rows[0]["company"] == "삼성"


def test_parse_card_ads_dedupes_and_maps_company():
    rows = nr.parse_card_ads(_card_html())
    names = [r["card_name"] for r in rows]
    assert len(names) == len(set(names))  # 중복 없음
    assert all(r["company"] for r in rows)


def test_parse_card_ads_empty_when_no_widget():
    assert nr.parse_card_ads("<html>위젯 없음</html>") == []


def test_positions_of_finds_ranks_and_missing():
    order = ["A카드", "B카드", "C카드"]
    got = nr.positions_of(order, ["C카드", "A카드", "없는카드"])
    assert got == {"C카드": 3, "A카드": 1, "없는카드": None}
