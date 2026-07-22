"""Build a daily *broadcast* news digest as a styled HTML page.

Organized by broadcaster (SBS·KBS·MBC·YTN) as an ordered "방송 다시보기"-style
rundown: per-broadcaster header, numbered rows with headline (clickable) and,
where available, a section chip + air time.

Ordering source:
- SBS 8뉴스 / KBS 뉴스9 / MBC 뉴스데스크 → scraped from each broadcaster's page in
  actual on-air order (see scrape.py).
- YTN (and any scraper failure) → Google News RSS per domain, newest-first.

Writes digests/broadcast-YYYY-MM-DD.html + digests/broadcast-latest.html.
Run:  python -m news_digest.broadcast
"""

from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if __package__:
    from . import scrape, sources
    from .fetch import Article, fetch_articles
    from .main import _format_time
else:  # pragma: no cover
    import scrape  # type: ignore
    import sources  # type: ignore
    from fetch import Article, fetch_articles  # type: ignore
    from main import _format_time  # type: ignore

KST = ZoneInfo("Asia/Seoul")

BROADCASTERS = {
    "SBS": "news.sbs.co.kr",
    "KBS": "news.kbs.co.kr",
    "MBC": "imnews.imbc.com",
    "YTN": "ytn.co.kr",
}
PROGRAM = {"SBS": "8뉴스", "KBS": "뉴스9", "MBC": "뉴스데스크", "YTN": "최신 뉴스"}
BROADCASTER_COLORS = {
    "SBS": "#00a0e0",
    "KBS": "#e60012",
    "MBC": "#003da5",
    "YTN": "#e4002b",
}
BROADCAST_SECTIONS = {
    "정치": "정치", "경제": "경제", "사회": "사회",
    "국제": "국제", "문화": "문화", "스포츠": "스포츠",
}
MAX_PER_SECTION = 5
MAX_PER_BROADCASTER = 22


def _pub_key(article: Article) -> datetime:
    try:
        return parsedate_to_datetime(article.published)
    except Exception:  # noqa: BLE001
        return datetime.min.replace(tzinfo=timezone.utc)


def _google_fallback(domain: str, recency: str) -> list[Article]:
    """Newest-first per-broadcaster list from Google News (no on-air order)."""
    collected: list[Article] = []
    seen: set[str] = set()
    for section, keyword in BROADCAST_SECTIONS.items():
        for a in fetch_articles(domain, keyword, recency, MAX_PER_SECTION):
            key = a.title.lower()
            if key in seen:
                continue
            seen.add(key)
            a.section = section
            collected.append(a)
    collected.sort(key=_pub_key, reverse=True)
    return collected[:MAX_PER_BROADCASTER]


def collect_broadcast() -> dict[str, tuple[list[Article], bool]]:
    """Return {broadcaster: (items, is_rundown)}; is_rundown=True when scraped
    in real on-air order, False for the Google News fallback."""
    now = datetime.now(KST)
    year = now.strftime("%Y")
    recency = os.environ.get("RECENCY", sources.RECENCY)

    scrapers = {
        "SBS": lambda: scrape.scrape_sbs(MAX_PER_BROADCASTER),
        "KBS": lambda: scrape.scrape_kbs(MAX_PER_BROADCASTER),
        "MBC": lambda: scrape.scrape_mbc(year, MAX_PER_BROADCASTER),
    }

    result: dict[str, tuple[list[Article], bool]] = {}
    for name, domain in BROADCASTERS.items():
        items: list[Article] = []
        is_rundown = False
        if name in scrapers:
            try:
                items = scrapers[name]()
                is_rundown = True
                print(f"[{name}] scraped rundown: {len(items)}건")
            except Exception as err:  # noqa: BLE001
                print(f"[{name}] scrape failed ({err}); Google News fallback")
        if not items:
            items = _google_fallback(domain, recency)
            is_rundown = False
            print(f"[{name}] fallback: {len(items)}건")
        result[name] = (items, is_rundown)
    return result


def render_broadcast_html(data: dict[str, tuple[list[Article], bool]], now: datetime) -> str:
    esc = html.escape
    date_str = now.strftime("%Y-%m-%d (%a) %H:%M KST")
    total = sum(len(v[0]) for v in data.values())

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="ko"><head>')
    parts.append('<meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append(f"<title>방송 뉴스 다이제스트 — {esc(date_str)}</title>")
    parts.append(
        "<style>"
        "body{margin:0;background:#f1f5f9;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo',"
        "'Malgun Gothic',Roboto,'Helvetica Neue',Arial,sans-serif;color:#0f172a;"
        "line-height:1.5;-webkit-text-size-adjust:100%;}"
        ".wrap{max-width:760px;margin:0 auto;padding:24px 16px 48px;}"
        ".hd{text-align:center;padding:8px 0 20px;}"
        ".hd h1{font-size:24px;margin:0 0 6px;letter-spacing:-.3px;}"
        ".hd .sub{color:#64748b;font-size:13px;margin:0;}"
        ".ch{background:#fff;border:1px solid #e2e8f0;border-radius:12px;"
        "overflow:hidden;margin:0 0 20px;box-shadow:0 1px 2px rgba(15,23,42,.04);}"
        ".ch > h2{margin:0;padding:12px 18px;color:#fff;font-size:18px;font-weight:800;"
        "letter-spacing:.5px;}"
        ".ch > h2 .prog{font-size:13px;font-weight:600;opacity:.9;margin-left:8px;}"
        ".ch > h2 .tag{float:right;font-size:11px;font-weight:600;opacity:.85;"
        "background:rgba(255,255,255,.22);border-radius:10px;padding:2px 9px;}"
        ".rundown{padding:6px 8px 12px;}"
        ".row{display:flex;align-items:flex-start;gap:10px;padding:9px 10px;"
        "border-bottom:1px solid #f4f6f9;}"
        ".row:last-child{border-bottom:0;}"
        ".num{flex:0 0 auto;width:22px;height:22px;border-radius:50%;background:#f1f5f9;"
        "color:#64748b;font-size:12px;font-weight:700;text-align:center;line-height:22px;}"
        ".body{flex:1 1 auto;min-width:0;}"
        ".chip{display:inline-block;font-size:11px;font-weight:700;color:#475569;"
        "background:#eef2f6;border-radius:4px;padding:1px 6px;margin-right:6px;"
        "vertical-align:1px;}"
        ".ttl{color:#0f172a;text-decoration:none;font-weight:600;font-size:15px;}"
        ".ttl:hover{color:#1d4ed8;text-decoration:underline;}"
        ".meta{color:#94a3b8;font-size:12px;margin-top:2px;}"
        ".empty{color:#94a3b8;font-size:13px;padding:12px 18px 16px;}"
        ".ft{text-align:center;color:#94a3b8;font-size:12px;margin-top:8px;}"
        "</style>"
    )
    parts.append("</head><body>")
    parts.append('<div class="wrap">')
    parts.append('<div class="hd">')
    parts.append("<h1>📺 오늘의 방송 뉴스 다이제스트</h1>")
    parts.append(
        f'<p class="sub">{esc(date_str)} · 총 {total}건 · '
        "SBS·KBS·MBC는 방송 편성 순서, YTN은 최신순</p>"
    )
    parts.append("</div>")

    for name, (items, is_rundown) in data.items():
        color = BROADCASTER_COLORS.get(name, "#334155")
        tag = "편성 순서" if is_rundown else "최신순"
        prog = PROGRAM.get(name, "")
        parts.append('<div class="ch">')
        parts.append(
            f'<h2 style="background:{color};">{esc(name)}'
            f'<span class="prog">{esc(prog)}</span>'
            f'<span class="tag">{tag}</span></h2>'
        )
        if not items:
            parts.append('<div class="empty">최근 수집된 기사가 없습니다.</div>')
            parts.append("</div>")
            continue
        parts.append('<div class="rundown">')
        for i, a in enumerate(items, 1):
            parts.append('<div class="row">')
            parts.append(f'<div class="num">{i}</div>')
            parts.append('<div class="body">')
            chip = f'<span class="chip">{esc(a.section)}</span>' if getattr(a, "section", "") else ""
            if a.link:
                parts.append(
                    f'{chip}<a class="ttl" href="{esc(a.link)}" target="_blank" '
                    f'rel="noopener">{esc(a.title)}</a>'
                )
            else:
                parts.append(f'{chip}<span class="ttl">{esc(a.title)}</span>')
            meta_bits = [b for b in (a.source, _format_time(a.published)) if b]
            if meta_bits:
                parts.append(f'<div class="meta">{esc(" · ".join(meta_bits))}</div>')
            parts.append("</div></div>")
        parts.append("</div>")
        parts.append("</div>")

    parts.append(f'<div class="ft">생성 시각 {esc(date_str)}</div>')
    parts.append("</div></body></html>")
    return "\n".join(parts) + "\n"


def main() -> int:
    now = datetime.now(KST)
    data = collect_broadcast()
    page = render_broadcast_html(data, now)

    repo_root = Path(__file__).resolve().parent.parent
    out_dir = Path(os.environ.get("OUTPUT_DIR", repo_root / "digests"))
    out_dir.mkdir(parents=True, exist_ok=True)

    dated = out_dir / f"broadcast-{now.strftime('%Y-%m-%d')}.html"
    latest = out_dir / "broadcast-latest.html"
    dated.write_text(page, encoding="utf-8")
    latest.write_text(page, encoding="utf-8")
    print(f"[write] {dated}")
    print(f"[write] {latest}")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [f"### 📺 방송 뉴스 다이제스트 — {now.strftime('%Y-%m-%d %H:%M KST')}", ""]
        for name, (items, is_rundown) in data.items():
            kind = "편성순서" if is_rundown else "최신순"
            lines.append(f"- **{name}** ({PROGRAM.get(name,'')}, {kind}) — {len(items)}건")
        lines.append("")
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
