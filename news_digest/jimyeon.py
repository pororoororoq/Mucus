"""Newspaper *지면*(print front-page) digest.

Scrapes each paper's Naver 지면보기 (media.naver.com/press/{oid}/newspaper),
which lists articles grouped by page (A1면, A2면, …) in the print edition's own
order — i.e. what each newsroom judged most important. Grouped by 면 per paper.

Writes digests/YYYY-MM-DD.html + digests/latest.html (this IS the newspaper
digest; replaces the earlier Google-News-by-section version, which remains as a
per-paper fallback if a 지면 page can't be scraped).

Run:  python -m news_digest.jimyeon
"""

from __future__ import annotations

import os
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

if __package__:
    from . import main as newsmain
    from .fetch import Article, USER_AGENT, fetch_articles
else:  # pragma: no cover
    import main as newsmain  # type: ignore
    from fetch import Article, USER_AGENT, fetch_articles  # type: ignore

KST = ZoneInfo("Asia/Seoul")

# Display name -> Naver office id.
OFFICES = OrderedDict([
    ("조선일보", "023"),
    ("동아일보", "020"),
    ("중앙일보", "025"),
    ("한국일보", "469"),
    ("한겨레", "028"),
])

# How many 지면 articles to keep per paper (covers roughly 1~4면).
MAX_PER_PAPER = 15

_MYEON_RE = re.compile(r"([A-Z]?\d{1,2})\s*면")


def _get(url: str, timeout: int = 20) -> requests.Response:
    r = requests.get(
        url, headers={"User-Agent": USER_AGENT, "Accept-Language": "ko"}, timeout=timeout
    )
    r.raise_for_status()
    return r


def scrape_jimyeon(paper: str, oid: str, ymd: str) -> "OrderedDict[str, list[Article]]":
    """Return {면_label: [Article, ...]} in print order for one paper."""
    url = f"https://media.naver.com/press/{oid}/newspaper?date={ymd}"
    soup = BeautifulSoup(_get(url).text, "html.parser")

    groups: "OrderedDict[str, list[Article]]" = OrderedDict()
    current = None
    seen: set[str] = set()
    kept = 0
    # h3 (면 headers) and article <a> appear in document order.
    for el in soup.find_all(["h3", "a"]):
        if el.name == "h3":
            m = _MYEON_RE.match(el.get_text(" ", strip=True))
            if m:
                current = f"{m.group(1)}면"
            continue
        href = el.get("href", "")
        if "/article/newspaper/" not in href:
            continue
        title = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        link = href.split("?")[0]
        if len(title) < 4 or link in seen:
            continue
        seen.add(link)
        label = current or "지면"
        art = Article(title=title, link=link, source=paper)
        art.section = label
        groups.setdefault(label, []).append(art)
        kept += 1
        if kept >= MAX_PER_PAPER:
            break
    if not groups:
        raise RuntimeError(f"{paper}: no 지면 articles parsed")
    return groups


def _fallback(paper: str, oid_domain: str, recency: str) -> "OrderedDict[str, list[Article]]":
    """Google News fallback for a paper whose 지면 page failed."""
    arts = fetch_articles(oid_domain, "", recency, 8)
    for a in arts:
        a.source = paper
        a.section = "최신"
    return OrderedDict([("최신(지면 수집 실패)", arts)] if arts else [])


# Publisher domains for the fallback path.
FALLBACK_DOMAIN = {
    "조선일보": "chosun.com", "동아일보": "donga.com", "중앙일보": "joongang.co.kr",
    "한국일보": "hankookilbo.com", "한겨레": "hani.co.kr",
}


def collect(ymd: str) -> "OrderedDict[str, OrderedDict[str, list[Article]]]":
    recency = os.environ.get("RECENCY", "1d")
    result: "OrderedDict[str, OrderedDict[str, list[Article]]]" = OrderedDict()
    for paper, oid in OFFICES.items():
        try:
            groups = scrape_jimyeon(paper, oid, ymd)
            n = sum(len(v) for v in groups.values())
            print(f"[{paper}] 지면 {n}건 · {list(groups)}")
        except Exception as err:  # noqa: BLE001
            print(f"[{paper}] 지면 실패 ({err}); Google News fallback")
            groups = _fallback(paper, FALLBACK_DOMAIN.get(paper, ""), recency)
        result[paper] = groups
    return result


def main() -> int:
    now = datetime.now(KST)
    ymd = now.strftime("%Y%m%d")
    data = collect(ymd)

    page = newsmain.render_html(
        data, now,
        title="📰 오늘의 신문 지면 다이제스트",
        source_note="네이버 지면보기 · 각 신문 1면부터 편집 순서",
    )

    repo_root = Path(__file__).resolve().parent.parent
    out_dir = Path(os.environ.get("OUTPUT_DIR", repo_root / "digests"))
    out_dir.mkdir(parents=True, exist_ok=True)
    dated = out_dir / f"{now.strftime('%Y-%m-%d')}.html"
    latest = out_dir / "latest.html"
    dated.write_text(page, encoding="utf-8")
    latest.write_text(page, encoding="utf-8")
    print(f"[write] {dated}")
    print(f"[write] {latest}")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [f"### 📰 신문 지면 다이제스트 — {now.strftime('%Y-%m-%d %H:%M KST')}", ""]
        for paper, groups in data.items():
            n = sum(len(v) for v in groups.values())
            lines.append(f"- **{paper}** — {n}건 ({', '.join(groups)})")
        lines.append("")
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
