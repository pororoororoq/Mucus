"""Build a daily Korean-newspaper news digest as a styled HTML page.

Groups recent articles by newspaper and section (using Google News RSS, no API
key required) and writes ``digests/YYYY-MM-DD.html`` plus a rolling
``digests/latest.html``. The same HTML is used as the email body.

Env toggles:
  ENRICH=0        Disable per-article summary enrichment (faster, headlines only).
  RECENCY=2d      Override the recency window (default from sources.py).
  OUTPUT_DIR=...  Override the output directory (default: <repo>/digests).

Run locally:  python -m news_digest.main   (or:  cd news_digest && python main.py)
"""

from __future__ import annotations

import html
import os
import re
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Support both "python -m news_digest.main" and "python main.py".
if __package__:
    from . import sources
    from .fetch import Article, enrich_summaries, fetch_articles
else:  # pragma: no cover - direct-run convenience
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import sources  # type: ignore
    from fetch import Article, enrich_summaries, fetch_articles  # type: ignore

KST = ZoneInfo("Asia/Seoul")

# Accent color per newspaper (used for the section header bar).
PAPER_COLORS = {
    "조선일보": "#1a4b8c",
    "동아일보": "#0b6b3a",
    "중앙일보": "#c8102e",
    "한국일보": "#005bac",
    "한겨레": "#d7192d",
}
DEFAULT_COLOR = "#334155"


def collect() -> dict[str, dict[str, list[Article]]]:
    """Return {paper: {section: [Article, ...]}}."""
    recency = os.environ.get("RECENCY", sources.RECENCY)
    result: dict[str, dict[str, list[Article]]] = {}

    for paper, domain in sources.PAPERS.items():
        print(f"[{paper}] fetching…")
        per_section: dict[str, list[Article]] = {}
        for section, keyword in sources.SECTIONS.items():
            articles = fetch_articles(
                domain, keyword, recency, sources.MAX_ITEMS_PER_SECTION
            )
            for a in articles:
                a.paper = paper
                a.section = section
            if articles:
                per_section[section] = articles
                print(f"    {section}: {len(articles)}건")
        result[paper] = per_section
    return result


def deduplicate(data: dict[str, dict[str, list[Article]]]) -> None:
    """Drop a headline from later sections if it already appeared earlier
    within the same paper (Google News keyword filters overlap)."""
    for per_section in data.values():
        seen: set[str] = set()
        for section in list(per_section.keys()):
            kept: list[Article] = []
            for a in per_section[section]:
                key = a.title.lower()
                if key in seen:
                    continue
                seen.add(key)
                kept.append(a)
            if kept:
                per_section[section] = kept
            else:
                del per_section[section]


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _format_time(pubdate: str) -> str:
    """Convert an RSS pubDate to a short KST 'MM/DD HH:MM' string."""
    if not pubdate:
        return ""
    try:
        dt = parsedate_to_datetime(pubdate).astimezone(KST)
        return dt.strftime("%m/%d %H:%M")
    except Exception:  # noqa: BLE001
        return pubdate


def _meaningful_summary(article: Article) -> str:
    """Return a summary only if it adds information beyond the headline.

    Google News feed descriptions are frequently just the headline echoed with
    the source appended, so we suppress those to keep the digest clean.
    """
    summary = article.summary.strip()
    if not summary:
        return ""
    if _norm(article.title) in _norm(summary) and len(summary) < len(article.title) + 25:
        return ""
    return summary


def render_html(
    data: dict[str, dict[str, list[Article]]],
    now: datetime,
    title: str = "📰 오늘의 한국 뉴스 다이제스트",
    source_note: str = "Google 뉴스 RSS · 최근 24시간",
) -> str:
    date_str = now.strftime("%Y-%m-%d (%a) %H:%M KST")
    total = sum(len(v) for ps in data.values() for v in ps.values())
    esc = html.escape

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="ko"><head>')
    parts.append('<meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append(f"<title>한국 뉴스 다이제스트 — {esc(date_str)}</title>")
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
        ".paper{background:#fff;border:1px solid #e2e8f0;border-radius:12px;"
        "overflow:hidden;margin:0 0 20px;box-shadow:0 1px 2px rgba(15,23,42,.04);}"
        ".paper > h2{margin:0;padding:12px 18px;color:#fff;font-size:17px;font-weight:700;}"
        ".sec{padding:6px 18px 14px;}"
        ".sec h3{font-size:12px;font-weight:700;letter-spacing:.4px;color:#475569;"
        "text-transform:none;margin:14px 0 8px;padding-bottom:5px;"
        "border-bottom:1px solid #eef2f6;}"
        ".art{padding:7px 0;border-bottom:1px solid #f4f6f9;}"
        ".art:last-child{border-bottom:0;}"
        ".art a{color:#0f172a;text-decoration:none;font-weight:600;font-size:15px;}"
        ".art a:hover{color:#1d4ed8;text-decoration:underline;}"
        ".meta{color:#94a3b8;font-size:12px;margin-top:2px;}"
        ".summary{color:#475569;font-size:13.5px;margin-top:4px;}"
        ".empty{color:#94a3b8;font-size:13px;padding:12px 18px 16px;}"
        ".ft{text-align:center;color:#94a3b8;font-size:12px;margin-top:8px;}"
        ".ft a{color:#64748b;}"
        "</style>"
    )
    parts.append("</head><body>")
    parts.append('<div class="wrap">')

    parts.append('<div class="hd">')
    parts.append(f"<h1>{esc(title)}</h1>")
    parts.append(
        f'<p class="sub">{esc(date_str)} · 총 {total}건 · {esc(source_note)}</p>'
    )
    parts.append("</div>")

    for paper, per_section in data.items():
        color = PAPER_COLORS.get(paper, DEFAULT_COLOR)
        parts.append('<div class="paper">')
        parts.append(
            f'<h2 style="background:{color};">{esc(paper)}</h2>'
        )
        if not per_section:
            parts.append('<div class="empty">최근 24시간 내 수집된 기사가 없습니다.</div>')
            parts.append("</div>")
            continue
        parts.append('<div class="sec">')
        for section, articles in per_section.items():
            parts.append(f"<h3>{esc(section)}</h3>")
            for a in articles:
                parts.append('<div class="art">')
                if a.link:
                    parts.append(
                        f'<a href="{esc(a.link)}" target="_blank" '
                        f'rel="noopener">{esc(a.title)}</a>'
                    )
                else:
                    parts.append(f"<span>{esc(a.title)}</span>")
                meta_bits = [b for b in (a.source, _format_time(a.published)) if b]
                if meta_bits:
                    parts.append(f'<div class="meta">{esc(" · ".join(meta_bits))}</div>')
                summary = _meaningful_summary(a)
                if summary:
                    parts.append(f'<div class="summary">{esc(summary)}</div>')
                parts.append("</div>")
        parts.append("</div>")
        parts.append("</div>")

    if total == 0:
        parts.append(
            '<div class="empty">⚠️ 수집된 기사가 없습니다. '
            "피드 URL 또는 네트워크 상태를 확인하세요.</div>"
        )

    parts.append(f'<div class="ft">생성 시각 {esc(date_str)}</div>')
    parts.append("</div></body></html>")
    return "\n".join(parts) + "\n"


def render_summary_markdown(data: dict[str, dict[str, list[Article]]], now: datetime) -> str:
    """Compact per-paper counts for the GitHub Actions job summary page."""
    date_str = now.strftime("%Y-%m-%d (%a) %H:%M KST")
    lines = [f"### 📰 뉴스 다이제스트 — {date_str}", ""]
    total = 0
    for paper, per_section in data.items():
        count = sum(len(v) for v in per_section.values())
        total += count
        secs = ", ".join(f"{s} {len(v)}" for s, v in per_section.items()) or "없음"
        lines.append(f"- **{paper}** — {count}건 ({secs})")
    lines.append("")
    lines.append(f"_총 {total}건 · HTML: `digests/latest.html`_")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    now = datetime.now(KST)

    data = collect()
    deduplicate(data)

    if os.environ.get("ENRICH", "1") != "0":
        print("[enrich] fetching article summaries…")
        all_articles = [a for ps in data.values() for arts in ps.values() for a in arts]
        enrich_summaries(all_articles)

    page = render_html(data, now)

    repo_root = Path(__file__).resolve().parent.parent
    out_dir = Path(os.environ.get("OUTPUT_DIR", repo_root / "digests"))
    out_dir.mkdir(parents=True, exist_ok=True)

    dated = out_dir / f"{now.strftime('%Y-%m-%d')}.html"
    latest = out_dir / "latest.html"
    dated.write_text(page, encoding="utf-8")
    latest.write_text(page, encoding="utf-8")
    print(f"[write] {dated}")
    print(f"[write] {latest}")

    # Surface a compact summary in the GitHub Actions job summary when available.
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(render_summary_markdown(data, now))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
