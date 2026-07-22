"""Validation probe: run the real scrapers on a CI runner and print results."""

from __future__ import annotations

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
YEAR = datetime.now(KST).strftime("%Y")


def show(name: str, fn):
    print(f"\n==================== {name} ====================")
    try:
        items = fn()
        print(f"  parsed {len(items)} items")
        for i, a in enumerate(items[:12], 1):
            sec = f"[{a.section}] " if getattr(a, "section", "") else ""
            print(f"   {i:2d}. {sec}{a.title[:55]!r}")
            print(f"       {a.link}")
    except Exception as e:  # noqa: BLE001
        print(f"  FAILED: {e!r}")


def dump_mbc_structure():
    print("\n----- MBC raw anchor structure (first 2) -----")
    try:
        url = f"https://imnews.imbc.com/replay/{YEAR}/nwdesk/index.html"
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        n = 0
        for a in soup.find_all("a", href=True):
            if "/nwdesk/article/" not in a["href"]:
                continue
            print(re.sub(r"\n\s*\n", "\n", a.prettify())[:700])
            print("   ---")
            n += 1
            if n >= 2:
                break
    except Exception as e:  # noqa: BLE001
        print(f"  dump failed: {e!r}")


def main() -> int:
    print(f"probe @ {datetime.now(KST).isoformat()}")
    show("SBS 8뉴스", lambda: scrape.scrape_sbs())
    show("KBS 뉴스9", lambda: scrape.scrape_kbs())
    show("MBC 뉴스데스크", lambda: scrape.scrape_mbc(YEAR))
    dump_mbc_structure()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
