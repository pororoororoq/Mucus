"""Source configuration for the Korean newspaper digest.

The default data source is Google News RSS, which needs no API key and lets us
filter by publisher domain (``site:``) and recency (``when:1d``). This makes the
digest work on the very first run in CI.

If you later want richer / more authoritative data, plug in the Naver Search API
(free, but requires a Client ID/Secret) — see ``naver_api.py`` and the README.
Note: Naver does not expose an official "지면(front-page layout) API", so true
1~3면 ordering would require scraping media.naver.com separately.
"""

# Display name -> publisher domain used in the Google News `site:` filter.
PAPERS = {
    "조선일보": "chosun.com",
    "동아일보": "donga.com",
    "중앙일보": "joongang.co.kr",
    "한국일보": "hankookilbo.com",
    "한겨레": "hani.co.kr",
}

# Section label -> extra keyword appended to the `site:` query.
# An empty keyword means "general / 종합" (no keyword filter).
# Ordering here is the order sections appear in the digest.
SECTIONS = {
    "종합": "",
    "정치": "정치",
    "경제": "경제",
    "사회": "사회",
    "국제": "국제",
    "사설·칼럼": "사설",
}

# How many articles to keep per (paper, section) after de-duplication.
MAX_ITEMS_PER_SECTION = 4

# Recency window for Google News (e.g. "1d" = last 24h, "2d", "12h").
RECENCY = "1d"
