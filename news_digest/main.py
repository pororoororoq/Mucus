"""Build a daily Korean-newspaper news digest.

Groups recent articles by newspaper and section (using Google News RSS, no API
key required) and writes a Markdown digest to ``digests/YYYY-MM-DD.md`` plus a
rolling ``digests/latest.md``.

Env toggles:
  ENRICH=0        Disable per-article summary enrichment (faster, headlines only).
  RECENCY=2d      Override the recency window (default from sources.py).
  OUTPUT_DIR=...  Override the output directory (default: <repo>/digests).

Run locally:  python -m news_digest.main   (or:  cd news_digest && python main.py)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
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


def render_markdown(data: dict[str, dict[str, list[Article]]], now: datetime) -> str:
    date_str = now.strftime("%Y-%m-%d (%a) %H:%M KST")
    lines: list[str] = []
    lines.append(f"# 📰 오늘의 한국 뉴스 다이제스트 — {date_str}")
    lines.append("")
    lines.append(
        "> 자동 생성 (Google 뉴스 RSS, 최근 24시간 기준). "
        "언론사·섹션별로 정리했습니다."
    )
    lines.append("")

    total = 0
    for paper, per_section in data.items():
        section_count = sum(len(v) for v in per_section.values())
        total += section_count
        lines.append(f"## {paper}")
        if not per_section:
            lines.append("")
            lines.append("_최근 24시간 내 수집된 기사가 없습니다._")
            lines.append("")
            continue
        for section, articles in per_section.items():
            lines.append("")
            lines.append(f"### {section}")
            for a in articles:
                headline = a.title
                lines.append(f"- **{headline}**")
                meta_bits = [b for b in (a.source, a.published) if b]
                if meta_bits:
                    lines.append(f"  - _{' · '.join(meta_bits)}_")
                if a.summary:
                    lines.append(f"  - {a.summary}")
                if a.link:
                    lines.append(f"  - [기사 링크]({a.link})")
        lines.append("")

    if total == 0:
        lines.append("")
        lines.append(
            "⚠️ 수집된 기사가 없습니다. 피드 URL 또는 네트워크 상태를 확인하세요."
        )

    lines.append("")
    lines.append("---")
    lines.append(f"_총 {total}건 · 생성 시각 {date_str}_")
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

    markdown = render_markdown(data, now)

    repo_root = Path(__file__).resolve().parent.parent
    out_dir = Path(os.environ.get("OUTPUT_DIR", repo_root / "digests"))
    out_dir.mkdir(parents=True, exist_ok=True)

    dated = out_dir / f"{now.strftime('%Y-%m-%d')}.md"
    latest = out_dir / "latest.md"
    dated.write_text(markdown, encoding="utf-8")
    latest.write_text(markdown, encoding="utf-8")
    print(f"[write] {dated}")
    print(f"[write] {latest}")

    # Surface the digest in the GitHub Actions job summary when available.
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
