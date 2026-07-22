"""Fetching + parsing helpers.

Everything here is best-effort and fails soft: a feed or article that cannot be
retrieved is skipped (and logged) rather than aborting the whole run, so one
flaky publisher never takes down the digest.
"""

from __future__ import annotations

import concurrent.futures
import html
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"

# A browser-like UA — Google News and most publisher sites reject empty/curl UAs.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass
class Article:
    title: str
    link: str
    source: str = ""
    published: str = ""
    summary: str = ""
    paper: str = ""
    section: str = ""


def build_google_news_url(domain: str, keyword: str, recency: str) -> str:
    """Build a Google News RSS search URL for one publisher + optional keyword."""
    query = f"site:{domain} when:{recency}"
    if keyword:
        query += f" {keyword}"
    params = {"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}
    return f"{GOOGLE_NEWS_RSS}?{urllib.parse.urlencode(params)}"


def _get(url: str, timeout: int = 20, retries: int = 3) -> requests.Response:
    """GET with a browser UA and exponential backoff on network errors."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/xml;q=0.9, text/html;q=0.8, */*;q=0.5",
        "Accept-Language": "ko,en;q=0.8",
    }
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            resp.raise_for_status()
            return resp
        except Exception as err:  # noqa: BLE001 - best effort, report and retry
            last_err = err
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    assert last_err is not None
    raise last_err


def _clean_text(raw: str) -> str:
    """Strip HTML tags/entities and collapse whitespace."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(" ")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _split_title_source(title: str) -> tuple[str, str]:
    """Google News titles look like 'Headline - Publisher'. Split the two."""
    if " - " in title:
        head, _, tail = title.rpartition(" - ")
        if head:
            return head.strip(), tail.strip()
    return title.strip(), ""


def fetch_articles(domain: str, keyword: str, recency: str, limit: int) -> list[Article]:
    """Fetch and parse one (publisher, section) Google News feed."""
    url = build_google_news_url(domain, keyword, recency)
    try:
        resp = _get(url)
    except Exception as err:  # noqa: BLE001
        print(f"  [warn] feed fetch failed ({domain} / '{keyword}'): {err}")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as err:
        print(f"  [warn] feed parse failed ({domain} / '{keyword}'): {err}")
        return []

    articles: list[Article] = []
    seen_titles: set[str] = set()

    for item in root.iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        title, source = _split_title_source(raw_title)
        if not title:
            continue
        key = title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)

        # The RSS <source> element is the most reliable publisher name.
        source_el = item.find("source")
        if source_el is not None and (source_el.text or "").strip():
            source = source_el.text.strip()

        articles.append(
            Article(
                title=title,
                link=(item.findtext("link") or "").strip(),
                source=source,
                published=(item.findtext("pubDate") or "").strip(),
                summary=_clean_text(item.findtext("description") or ""),
            )
        )
        if len(articles) >= limit:
            break

    return articles


def _fetch_og_description(url: str) -> str:
    """Best-effort: resolve a Google News link and read its og:description."""
    try:
        resp = _get(url, timeout=12, retries=1)
    except Exception:  # noqa: BLE001 - enrichment is optional
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    for selector in (
        ("meta", {"property": "og:description"}),
        ("meta", {"name": "description"}),
        ("meta", {"name": "twitter:description"}),
    ):
        tag = soup.find(*selector)
        if tag and tag.get("content"):
            return _clean_text(tag["content"])
    # Fall back to the first substantial paragraph.
    for p in soup.find_all("p"):
        text = _clean_text(p.get_text())
        if len(text) > 40:
            return text
    return ""


def enrich_summaries(articles: list[Article], max_workers: int = 8) -> None:
    """Fill in real 1-2 sentence summaries from each article's meta description.

    Runs concurrently and mutates ``articles`` in place. Any failure just leaves
    the existing RSS summary (or nothing) untouched.
    """
    targets = [a for a in articles if a.link]
    if not targets:
        return

    def work(article: Article) -> None:
        desc = _fetch_og_description(article.link)
        if desc and len(desc) > len(article.summary):
            # Trim to roughly 1-2 sentences.
            article.summary = desc[:280].rstrip()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(work, targets))
