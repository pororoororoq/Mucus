"""Direct scrapers for each broadcaster's evening-news rundown (in air order).

Discovered via scrape_probe.py:
- SBS 8뉴스   : programMain.do?prog_cd=RE — clip links with "동영상 기사 {mm:ss} {섹션} {제목}"
- KBS 뉴스9   : api/getNewsList JSON, contentsCode "0001" = 뉴스9
- MBC 뉴스데스크: replay/{year}/nwdesk/index.html — /nwdesk/article/{id}.html in order
- YTN         : no clean ordered rundown endpoint → handled by Google News fallback elsewhere

Each scraper fails soft (raises), and callers fall back to Google News RSS.
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

if __package__:
    from .fetch import Article, USER_AGENT
else:  # pragma: no cover
    from fetch import Article, USER_AGENT  # type: ignore

_SECTION_RE = re.compile(r"^(정치|경제|사회|국제|문화|생활|연예|스포츠|날씨|IT|과학)\s+")


def _get(url: str, timeout: int = 20) -> requests.Response:
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ko,en;q=0.8"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r


# --------------------------------------------------------------------------- SBS
# prog_cd=R1 (8뉴스) serves the rundown in static HTML; prog_cd=RE is JS-rendered.
SBS_URL = "https://news.sbs.co.kr/news/programMain.do?prog_cd=R1"


def scrape_sbs(limit: int = 20) -> list[Article]:
    soup = BeautifulSoup(_get(SBS_URL).text, "html.parser")
    out: list[Article] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "endPage.do" not in href or "SBSNEWSPROGRAM" not in href:
            continue
        # Title/section live in <p class="desc"><strong><em class="cate">섹션</em>제목
        section = ""
        title = ""
        strong = a.find("strong")
        if strong:
            cate = strong.find("em")
            if cate:
                section = cate.get_text(strip=True)
                cate.extract()
            title = re.sub(r"\s+", " ", strong.get_text(" ", strip=True))
        if len(title) < 5:
            continue
        if title in seen:
            continue
        seen.add(title)
        link = "https://news.sbs.co.kr" + href if href.startswith("/") else href
        art = Article(title=title, link=link, source="SBS 8뉴스")
        art.section = section
        out.append(art)
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("SBS: no rundown items parsed")
    return out


# --------------------------------------------------------------------------- KBS
KBS_API = (
    "https://news.kbs.co.kr/api/getNewsList"
    "?currentPageNo=1&rowsPerPage=100&exceptPhotoYn=N"
)
_KBS_NEWS9_RE = re.compile(r"뉴스\s*9")


def _kbs_order(d: dict) -> int:
    for key in ("broadOrder", "orderSeq", "listNum"):
        v = d.get(key)
        if v not in (None, ""):
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return 9999


def scrape_kbs(limit: int = 20) -> list[Article]:
    data = _get(KBS_API).json().get("data", [])
    # broadName identifies the program (e.g. "뉴스 9"); broadOrder is the rundown slot.
    items = [d for d in data if _KBS_NEWS9_RE.search(d.get("broadName") or "")]
    # Drop regional-edition closings / duplicate closings, keep national rundown.
    items = [d for d in items if "클로징" not in (d.get("newsTitle") or "")]
    items.sort(key=_kbs_order)
    out: list[Article] = []
    seen: set[str] = set()
    for d in items:
        title = (d.get("newsTitle") or "").strip()
        ncd = d.get("newsCode")
        if not title or not ncd or title in seen:
            continue
        seen.add(title)
        link = f"https://news.kbs.co.kr/news/pc/view/view.do?ncd={ncd}"
        art = Article(title=title, link=link, source="KBS 뉴스9")
        art.published = d.get("serviceTime", "") or d.get("deskTime", "")
        out.append(art)
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("KBS: no 뉴스9 items parsed")
    return out


# --------------------------------------------------------------------------- MBC
def _mbc_title(anchor) -> str:
    for node in (
        anchor.find(class_=re.compile(r"tit", re.I)),
        anchor.find("strong"),
        anchor.find("em"),
        anchor.find(["h2", "h3", "h4"]),
    ):
        if node:
            t = re.sub(r"\s+", " ", node.get_text(" ", strip=True))
            if len(t) >= 6:
                return t
    t = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
    return t[:45]


def scrape_mbc(year: str, limit: int = 20) -> list[Article]:
    url = f"https://imnews.imbc.com/replay/{year}/nwdesk/index.html"
    soup = BeautifulSoup(_get(url).text, "html.parser")
    out: list[Article] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        if "/nwdesk/article/" not in a["href"]:
            continue
        title = _mbc_title(a)
        if len(title) < 5 or title in seen:
            continue
        seen.add(title)
        href = a["href"]
        link = href if href.startswith("http") else "https://imnews.imbc.com" + href
        out.append(Article(title=title, link=link, source="MBC 뉴스데스크"))
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("MBC: no 뉴스데스크 items parsed")
    return out
