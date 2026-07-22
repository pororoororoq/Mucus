"""Probe #4: run all three scrapers + confirm KBS broadName/broadOrder."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

if __package__:
    from . import scrape
    from .fetch import USER_AGENT
else:  # pragma: no cover
    import scrape  # type: ignore
    from fetch import USER_AGENT  # type: ignore

KST = ZoneInfo("Asia/Seoul")
YEAR = datetime.now(KST).strftime("%Y")


def show(name, fn):
    print(f"\n==================== {name} ====================")
    try:
        items = fn()
        print(f"  parsed {len(items)} items")
        for i, a in enumerate(items[:14], 1):
            sec = f"[{a.section}] " if getattr(a, "section", "") else ""
            print(f"   {i:2d}. {sec}{a.title[:52]!r}  {a.link[-45:]}")
    except Exception as e:  # noqa: BLE001
        print(f"  FAILED: {e!r}")


def kbs_fields():
    print("\n----- KBS broadName values present -----")
    url = "https://news.kbs.co.kr/api/getNewsList?currentPageNo=1&rowsPerPage=100&exceptPhotoYn=N"
    data = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20).json().get("data", [])
    from collections import Counter
    print("  broadName counts:", dict(Counter((d.get("broadName") or "∅") for d in data)))
    print("  뉴스9 items (broadOrder / localCode / title):")
    for d in data:
        if re.search(r"뉴스\s*9", d.get("broadName") or ""):
            print(f"    order={d.get('broadOrder')} local={d.get('localCode')!r} "
                  f"{(d.get('newsTitle') or '')[:40]!r}")


def main() -> int:
    show("SBS 8뉴스", lambda: scrape.scrape_sbs())
    show("KBS 뉴스9", lambda: scrape.scrape_kbs())
    show("MBC 뉴스데스크", lambda: scrape.scrape_mbc(YEAR))
    kbs_fields()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
