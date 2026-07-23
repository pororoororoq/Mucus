"""Probe #5: (a) full SBS/KBS rundown counts, (b) Naver 지면(front-page) discovery."""

from __future__ import annotations

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

if __package__:
    from . import scrape
    from .fetch import USER_AGENT
else:  # pragma: no cover
    import scrape  # type: ignore
    from fetch import USER_AGENT  # type: ignore

KST = ZoneInfo("Asia/Seoul")
YMD = datetime.now(KST).strftime("%Y%m%d")
H = {"User-Agent": USER_AGENT, "Accept-Language": "ko"}


def full_rundowns():
    for name, fn in (("SBS 8뉴스", lambda: scrape.scrape_sbs(100)),
                     ("KBS 뉴스9", lambda: scrape.scrape_kbs(100))):
        print(f"\n==================== {name} (uncapped) ====================")
        try:
            items = fn()
            print(f"  TOTAL parsed: {len(items)}")
            for i, a in enumerate(items, 1):
                sec = f"[{a.section}] " if getattr(a, "section", "") else ""
                print(f"   {i:2d}. {sec}{a.title[:56]}")
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e!r}")


def naver_jimyeon():
    print("\n==================== NAVER 지면 (조선 023) ====================")
    candidates = [
        f"https://media.naver.com/press/023/newspaper?date={YMD}",
        "https://media.naver.com/press/023/newspaper",
        f"https://newspaper.naver.com/main/main.naver?officeId=023&date={YMD}",
        f"https://apis.naver.com/newspaper/newspaper/list?officeId=023&date={YMD}",
    ]
    for url in candidates:
        print(f"\n  --- {url}")
        try:
            r = requests.get(url, headers=H, timeout=20)
        except Exception as e:  # noqa: BLE001
            print(f"      ERROR: {e!r}")
            continue
        ct = r.headers.get("content-type", "")
        print(f"      status={r.status_code} final={r.url[:80]} ct={ct} bytes={len(r.content)}")
        body = r.text
        if "json" in ct or body.lstrip()[:1] in "{[":
            try:
                print(f"      JSON sample: {str(json.loads(body))[:500]}")
            except Exception:  # noqa: BLE001
                pass
            continue
        soup = BeautifulSoup(body, "html.parser")
        t = soup.find("title")
        print(f"      <title>={t.get_text(strip=True) if t else None}")
        # look for page(면) markers and article links in document order
        for marker in soup.find_all(string=re.compile(r"\d+\s*면")):
            m = marker.strip()
            if m:
                print(f"      면marker: {m[:30]!r}")
        arts = []
        for a in soup.find_all("a", href=True):
            txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
            if len(txt) >= 10 and sum(1 for c in txt if "가" <= c <= "힣") > 4 \
               and re.search(r"(article|/read|newspaper|/mnews)", a["href"], re.I):
                arts.append((txt[:50], a["href"][:70]))
        print(f"      article-like links: {len(arts)}")
        for txt, href in arts[:12]:
            print(f"        {txt!r}  <- {href}")


def main() -> int:
    full_rundowns()
    naver_jimyeon()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
