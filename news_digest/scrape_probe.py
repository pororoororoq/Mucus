"""Probe #6: Naver 지면(newspaper) DOM — find 면(page) grouping structure."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

if __package__:
    from .fetch import USER_AGENT
else:  # pragma: no cover
    from fetch import USER_AGENT  # type: ignore

KST = ZoneInfo("Asia/Seoul")
YMD = datetime.now(KST).strftime("%Y%m%d")
H = {"User-Agent": USER_AGENT, "Accept-Language": "ko"}

OFFICES = {"조선": "023", "동아": "020", "중앙": "025", "한겨레": "028", "한국": "469"}


def dump_structure(oid: str):
    url = f"https://media.naver.com/press/{oid}/newspaper?date={YMD}"
    r = requests.get(url, headers=H, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    # Find any element whose (own) text looks like a 면 label.
    print("  candidate 면 labels (tag.class -> text):")
    seen = 0
    for el in soup.find_all(["strong", "em", "span", "h3", "h4", "b", "div"]):
        txt = el.get_text(" ", strip=True)
        if re.fullmatch(r"[A-Z]?\d{1,2}\s*면", txt or ""):
            cls = ".".join(el.get("class", []))
            print(f"    {el.name}.{cls} -> {txt!r}")
            seen += 1
        if seen >= 12:
            break
    if seen == 0:
        print("    (none matched \\d면)")

    # First newspaper article link -> print ancestor chain classes.
    a = soup.find("a", href=re.compile(r"/article/newspaper/"))
    if a:
        print("\n  first article ancestor chain:")
        node = a
        for _ in range(6):
            if node is None:
                break
            cls = ".".join(node.get("class", [])) if hasattr(node, "get") else ""
            print(f"    <{getattr(node,'name','?')} class={cls}>")
            node = node.parent
        print("\n  first article container prettify (trimmed):")
        # climb to a container that holds several article links
        cont = a
        for _ in range(5):
            if cont.parent is None:
                break
            cont = cont.parent
            if len(cont.find_all("a", href=re.compile(r"/article/newspaper/"))) >= 2:
                break
        print(re.sub(r"\n\s*\n", "\n", cont.prettify())[:1400])


def main() -> int:
    print(f"date={YMD}")
    print("\n==================== 조선(023) structure ====================")
    dump_structure("023")

    print("\n==================== office availability ====================")
    for name, oid in OFFICES.items():
        try:
            r = requests.get(f"https://media.naver.com/press/{oid}/newspaper?date={YMD}",
                             headers=H, timeout=20)
            soup = BeautifulSoup(r.text, "html.parser")
            n = len(soup.find_all("a", href=re.compile(r"/article/newspaper/")))
            t = soup.find("title")
            print(f"  {name}({oid}): status={r.status_code} links={n} title={t.get_text(strip=True) if t else None}")
        except Exception as e:  # noqa: BLE001
            print(f"  {name}({oid}): ERROR {e!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
