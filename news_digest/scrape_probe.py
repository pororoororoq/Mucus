"""Targeted probe #3: nail down SBS anchor structure and KBS content codes."""

from __future__ import annotations

import re
from collections import Counter

import requests
from bs4 import BeautifulSoup

if __package__:
    from .fetch import USER_AGENT
else:  # pragma: no cover
    from fetch import USER_AGENT  # type: ignore

H = {"User-Agent": USER_AGENT, "Accept-Language": "ko"}


def sbs():
    print("\n==================== SBS ====================")
    for prog in ("RE", "R1"):
        url = f"https://news.sbs.co.kr/news/programMain.do?prog_cd={prog}"
        r = requests.get(url, headers=H, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        anchors = [a for a in soup.find_all("a", href=True) if "endPage.do" in a["href"]]
        print(f"\n  prog_cd={prog}  title={title.get_text(strip=True) if title else None}"
              f"  endPage_anchors={len(anchors)}")
        for a in anchors[:6]:
            txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
            prog_mark = "PROG" if "SBSNEWSPROGRAM" in a["href"] else ""
            print(f"      {prog_mark:4} {txt[:70]!r}  <- {a['href'][:60]}")
        if anchors:
            print("      --- first anchor prettify ---")
            print(re.sub(r"\n\s*\n", "\n", anchors[0].prettify())[:600])


def kbs():
    print("\n==================== KBS ====================")
    url = "https://news.kbs.co.kr/api/getNewsList?currentPageNo=1&rowsPerPage=100&exceptPhotoYn=N"
    data = requests.get(url, headers=H, timeout=20).json().get("data", [])
    print(f"  total items: {len(data)}")
    print(f"  first item keys: {sorted(data[0].keys()) if data else None}")
    codes = Counter(d.get("contentsCode") for d in data)
    print("  contentsCode distribution + sample title:")
    for code, n in codes.most_common():
        sample = next(d for d in data if d.get("contentsCode") == code)
        print(f"    {code}: {n:2d}  e.g. {(sample.get('newsTitle') or '')[:45]!r}")
    # Try a program-specific endpoint variant for 뉴스9.
    for variant in (
        "https://news.kbs.co.kr/api/getNewsList?currentPageNo=1&rowsPerPage=30&programCode=0001",
        "https://news.kbs.co.kr/api/getNewsList?currentPageNo=1&rowsPerPage=30&contentsCode=0001&broadcastYn=Y",
    ):
        try:
            d2 = requests.get(variant, headers=H, timeout=20).json().get("data", [])
            print(f"\n  variant {variant[-40:]} -> {len(d2)} items")
            for d in d2[:5]:
                print(f"      {d.get('contentsCode')} {(d.get('newsTitle') or '')[:45]!r}")
        except Exception as e:  # noqa: BLE001
            print(f"  variant failed: {e!r}")


def main() -> int:
    sbs()
    kbs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
