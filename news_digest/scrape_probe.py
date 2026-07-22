"""Diagnostic probe: discover how each broadcaster's rundown page is structured.

We can't reach the broadcaster domains from the dev sandbox, so this runs on a
GitHub Actions runner (open internet) and prints, for a list of candidate URLs,
enough structure (status, title, JSON-ness, article-like links in document
order) to write real parsers in scrape.py afterwards.

Run via the probe workflow; read the job logs.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

KST = ZoneInfo("Asia/Seoul")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

now = datetime.now(KST)
YMD = now.strftime("%Y%m%d")
Y_M_D = now.strftime("%Y-%m-%d")
YEAR = now.strftime("%Y")

CANDIDATES = {
    "SBS": [
        "https://news.sbs.co.kr/news/programMain.do?prog_cd=R1",
        "https://news.sbs.co.kr/news/programMain.do?prog_cd=RE",
        "https://news.sbs.co.kr/news/newsflashList.do",
        f"https://news.sbs.co.kr/news/newsMain.do?date={YMD}",
        "https://news.sbs.co.kr/news/newsMain.do?plink=GNB&cooper=SBSNEWS",
    ],
    "KBS": [
        "https://news.kbs.co.kr/news/pc/program/program.do?bcd=0001",
        "https://news.kbs.co.kr/news/pc/program/program.do?bcd=news9",
        "https://news.kbs.co.kr/api/getNewsList?currentPageNo=1&rowsPerPage=25&exceptPhotoYn=N",
        f"https://news.kbs.co.kr/news/pc/program/program.do?bcd=0001&ref=pMenu#{Y_M_D}",
    ],
    "MBC": [
        "https://imnews.imbc.com/replay/nwdesk/index.html",
        f"https://imnews.imbc.com/replay/{YEAR}/nwdesk/index.html",
        "https://imnews.imbc.com/replay/nwdesk/",
        "https://imnews.imbc.com/news/2026/index.html",
    ],
    "YTN": [
        "https://www.ytn.co.kr/replay/",
        "https://www.ytn.co.kr/program/",
        "https://www.ytn.co.kr/news/list.php?mcd=0102",
        "https://www.ytn.co.kr/",
    ],
}


def kr_ratio(s: str) -> float:
    if not s:
        return 0.0
    kr = sum(1 for c in s if "가" <= c <= "힣")
    return kr / max(1, len(s))


def looks_like_article_href(href: str) -> bool:
    if not href:
        return False
    return bool(
        re.search(r"(article|news|replay|view|clip)", href, re.I)
        and re.search(r"\d{4,}", href)
    )


def probe(url: str) -> None:
    print(f"\n  --- {url}")
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "ko"}, timeout=20)
    except Exception as e:  # noqa: BLE001
        print(f"      ERROR: {e}")
        return
    ct = r.headers.get("content-type", "")
    print(f"      status={r.status_code} final={r.url}")
    print(f"      content-type={ct} bytes={len(r.content)}")

    body = r.text
    if "json" in ct or body.lstrip()[:1] in "{[":
        try:
            data = json.loads(body)
            print(f"      JSON keys/sample: {str(data)[:400]}")
            return
        except Exception:  # noqa: BLE001
            pass

    soup = BeautifulSoup(body, "html.parser")
    title = soup.find("title")
    print(f"      <title>={title.get_text(strip=True) if title else None}")

    anchors = soup.find_all("a")
    print(f"      total <a>={len(anchors)}")
    shown = 0
    for a in anchors:
        href = a.get("href", "")
        text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if len(text) >= 8 and kr_ratio(text) > 0.3 and looks_like_article_href(href):
            print(f"        [{shown}] {text[:60]!r}  <- {href[:90]}")
            shown += 1
        if shown >= 15:
            break
    if shown == 0:
        # fall back: show any longish korean anchor text to understand layout
        for a in anchors:
            text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
            if len(text) >= 10 and kr_ratio(text) > 0.4:
                print(f"        (kr) {text[:60]!r}  <- {a.get('href','')[:90]}")
                shown += 1
            if shown >= 12:
                break


def main() -> int:
    print(f"probe @ {now.isoformat()}  (YMD={YMD})")
    for name, urls in CANDIDATES.items():
        print(f"\n==================== {name} ====================")
        for u in urls:
            probe(u)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
