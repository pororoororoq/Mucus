"""Optional: Naver Search (News) API helper.

The Naver Search API is FREE but requires an application to be registered at
https://developers.naver.com (you get a Client ID + Secret; the news endpoint
allows ~25,000 calls/day). Naver does NOT provide an official front-page
("지면") API, so this returns news *search* results, not 1~3면 layout.

This module is standalone and is NOT wired into the default digest flow (which
uses Google News RSS and needs no key). Use it if you want an extra,
Naver-sourced cross-check. Set env vars NAVER_CLIENT_ID / NAVER_CLIENT_SECRET.

Quick test:
    NAVER_CLIENT_ID=... NAVER_CLIENT_SECRET=... python news_digest/naver_api.py 조선일보
"""

from __future__ import annotations

import os
import re
import sys

import requests

NAVER_NEWS_ENDPOINT = "https://openapi.naver.com/v1/search/news.json"


def search_news(query: str, display: int = 5, sort: str = "date") -> list[dict]:
    """Search Naver News. ``sort='date'`` returns newest first.

    Raises RuntimeError if credentials are missing.
    """
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET are not set. "
            "Register an app at https://developers.naver.com (free)."
        )

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": query, "display": display, "sort": sort}
    resp = requests.get(
        NAVER_NEWS_ENDPOINT, headers=headers, params=params, timeout=15
    )
    resp.raise_for_status()

    items = resp.json().get("items", [])
    cleaned = []
    for item in items:
        cleaned.append(
            {
                "title": _strip_tags(item.get("title", "")),
                "summary": _strip_tags(item.get("description", "")),
                "link": item.get("originallink") or item.get("link", ""),
                "published": item.get("pubDate", ""),
            }
        )
    return cleaned


def _strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return (
        text.replace("&quot;", '"')
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&apos;", "'")
        .strip()
    )


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "오늘 주요 뉴스"
    for i, art in enumerate(search_news(q), 1):
        print(f"{i}. {art['title']}")
        if art["summary"]:
            print(f"   {art['summary']}")
        print(f"   {art['link']}  ({art['published']})")
