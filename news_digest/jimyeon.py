"""Newspaper *지면*(print edition) digest, rendered as a 면 × 신문사 table.

Scrapes each paper's Naver 지면보기 (media.naver.com/press/{oid}/newspaper),
which lists articles grouped by page (A1면, A2면, …) in the print edition's own
order. Output is a table: columns = newspapers, rows = 1면~6면 + 사설, so you can
compare at a glance what each newsroom put on its front pages.

Writes digests/YYYY-MM-DD.html + digests/latest.html.
Run:  python -m news_digest.jimyeon
"""

from __future__ import annotations

import html
import os
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

if __package__:
    from .fetch import Article, USER_AGENT, fetch_articles
else:  # pragma: no cover
    from fetch import Article, USER_AGENT, fetch_articles  # type: ignore

KST = ZoneInfo("Asia/Seoul")

OFFICES = OrderedDict([
    ("조선일보", "023"),
    ("동아일보", "020"),
    ("중앙일보", "025"),
    ("한국일보", "469"),
    ("한겨레", "028"),
])
PAPER_COLORS = {
    "조선일보": "#1a4b8c", "동아일보": "#0b6b3a", "중앙일보": "#c8102e",
    "한국일보": "#005bac", "한겨레": "#d7192d",
}
FALLBACK_DOMAIN = {
    "조선일보": "chosun.com", "동아일보": "donga.com", "중앙일보": "joongang.co.kr",
    "한국일보": "hankookilbo.com", "한겨레": "hani.co.kr",
}

# Rows of the table (front pages 1~6 plus editorials).
PAGE_ROWS = ["1면", "2면", "3면", "4면", "5면", "6면"]
EDITORIAL_ROW = "사설"
ROWS = PAGE_ROWS + [EDITORIAL_ROW]

MAX_PER_CELL = 5
# Capture the section prefix so we can keep only the main section (A면 / no prefix)
# and drop B·C·S 별지 sections (경제·스포츠 등).
_MYEON_RE = re.compile(r"([A-Z]?)(\d{1,2})\s*면")
_MAIN_PREFIXES = {"", "A"}


def _get(url: str, timeout: int = 20) -> requests.Response:
    r = requests.get(
        url, headers={"User-Agent": USER_AGENT, "Accept-Language": "ko"}, timeout=timeout
    )
    r.raise_for_status()
    return r


def scrape_jimyeon(paper: str, oid: str, ymd: str) -> list[tuple[int, Article]]:
    """Return [(면번호, Article), ...] across the whole print edition, in order."""
    url = f"https://media.naver.com/press/{oid}/newspaper?date={ymd}"
    soup = BeautifulSoup(_get(url).text, "html.parser")

    out: list[tuple[int, Article]] = []
    current = 0
    seen: set[str] = set()
    for el in soup.find_all(["h3", "a"]):
        if el.name == "h3":
            m = _MYEON_RE.match(el.get_text(" ", strip=True))
            if m:
                # Main section (A면 / no prefix) -> page number; 별지(B·C…) -> -1.
                current = int(m.group(2)) if m.group(1) in _MAIN_PREFIXES else -1
            continue
        href = el.get("href", "")
        if "/article/newspaper/" not in href:
            continue
        title = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        link = href.split("?")[0]
        if len(title) < 4 or link in seen:
            continue
        seen.add(link)
        art = Article(title=title, link=link, source=paper)
        out.append((current, art))
    if not out:
        raise RuntimeError(f"{paper}: no 지면 articles parsed")
    return out


def _is_editorial(title: str) -> bool:
    t = title.strip()
    return t.startswith("[사설]") or t.startswith("<사설>") or t.startswith("[社說]")


def collect(ymd: str):
    """Return (matrix, failed) where matrix[row][paper] = [Article,...]."""
    recency = os.environ.get("RECENCY", "1d")
    matrix: dict[str, dict[str, list[Article]]] = {r: {p: [] for p in OFFICES} for r in ROWS}
    failed: dict[str, bool] = {}

    for paper, oid in OFFICES.items():
        try:
            items = scrape_jimyeon(paper, oid, ymd)
            failed[paper] = False
            for myeon, art in items:
                if _is_editorial(art.title):
                    matrix[EDITORIAL_ROW][paper].append(art)
                elif 1 <= myeon <= len(PAGE_ROWS):
                    matrix[f"{myeon}면"][paper].append(art)
            counts = {r: len(matrix[r][paper]) for r in ROWS if matrix[r][paper]}
            print(f"[{paper}] 지면 OK · {counts}")
        except Exception as err:  # noqa: BLE001
            failed[paper] = True
            print(f"[{paper}] 지면 실패 ({err}); Google News fallback")
            arts = fetch_articles(FALLBACK_DOMAIN.get(paper, ""), "", recency, MAX_PER_CELL)
            for a in arts:
                a.source = paper
            matrix["1면"][paper] = arts
    return matrix, failed


def render_table(matrix, failed, now: datetime) -> str:
    esc = html.escape
    date_str = now.strftime("%Y-%m-%d (%a) %H:%M KST")
    papers = list(OFFICES)
    total = sum(len(matrix[r][p]) for r in ROWS for p in papers)

    def cell(arts: list[Article]) -> str:
        if not arts:
            return '<span class="none">—</span>'
        bits = []
        for a in arts[:MAX_PER_CELL]:
            if a.link:
                bits.append(
                    f'<a href="{esc(a.link)}" target="_blank" rel="noopener">{esc(a.title)}</a>'
                )
            else:
                bits.append(f"<span>{esc(a.title)}</span>")
        extra = len(arts) - MAX_PER_CELL
        if extra > 0:
            bits.append(f'<span class="more">+{extra}건</span>')
        return "".join(f"<div class='a'>{b}</div>" for b in bits)

    p = []
    p.append("<!DOCTYPE html>")
    p.append('<html lang="ko"><head><meta charset="utf-8">')
    p.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    p.append(f"<title>신문 지면 다이제스트 — {esc(date_str)}</title>")
    p.append(
        "<style>"
        "body{margin:0;background:#f1f5f9;color:#0f172a;line-height:1.45;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo',"
        "'Malgun Gothic',Roboto,Arial,sans-serif;-webkit-text-size-adjust:100%;}"
        ".wrap{max-width:1200px;margin:0 auto;padding:24px 14px 48px;}"
        ".hd{text-align:center;padding:4px 0 16px;}"
        ".hd h1{font-size:22px;margin:0 0 6px;}"
        ".hd .sub{color:#64748b;font-size:13px;margin:0;}"
        ".scroll{overflow-x:auto;border:1px solid #e2e8f0;border-radius:12px;background:#fff;}"
        "table{border-collapse:collapse;width:100%;min-width:900px;}"
        "th,td{border:1px solid #e8edf3;padding:8px 10px;vertical-align:top;text-align:left;}"
        "thead th{position:sticky;top:0;color:#fff;font-size:14px;font-weight:700;"
        "text-align:center;}"
        "tbody th{background:#f8fafc;color:#334155;font-weight:700;font-size:13px;"
        "white-space:nowrap;text-align:center;width:52px;position:sticky;left:0;}"
        "tr.ed th,tr.ed td{background:#fffdf5;}"
        "tr.ed th{background:#fef9e7;}"
        "td{font-size:12.5px;width:19%;}"
        ".a{padding:3px 0;border-bottom:1px dotted #eef2f6;}"
        ".a:last-child{border-bottom:0;}"
        "td a{color:#0f172a;text-decoration:none;}"
        "td a:hover{color:#1d4ed8;text-decoration:underline;}"
        ".none{color:#cbd5e1;}"
        ".more{color:#94a3b8;font-size:11px;}"
        ".ft{text-align:center;color:#94a3b8;font-size:12px;margin-top:10px;}"
        "</style></head><body><div class='wrap'>"
    )
    p.append('<div class="hd">')
    p.append("<h1>📰 오늘의 신문 지면 다이제스트</h1>")
    p.append(
        f'<p class="sub">{esc(date_str)} · 총 {esc(str(total))}건 · '
        "네이버 지면보기 · 각 신문 1면부터 편집 순서</p>")
    p.append("</div>")

    p.append('<div class="scroll"><table>')
    # header
    p.append("<thead><tr>")
    p.append('<th style="background:#334155;">면</th>')
    for paper in papers:
        color = PAPER_COLORS.get(paper, "#334155")
        mark = " ⚠" if failed.get(paper) else ""
        p.append(f'<th style="background:{color};">{esc(paper)}{mark}</th>')
    p.append("</tr></thead>")
    # body
    p.append("<tbody>")
    for row in ROWS:
        cls = ' class="ed"' if row == EDITORIAL_ROW else ""
        p.append(f"<tr{cls}>")
        p.append(f"<th>{esc(row)}</th>")
        for paper in papers:
            p.append(f"<td>{cell(matrix[row][paper])}</td>")
        p.append("</tr>")
    p.append("</tbody></table></div>")

    if any(failed.values()):
        p.append('<div class="ft">⚠ 표시 신문은 지면 수집 실패로 최신 기사로 대체되었습니다.</div>')
    p.append(f'<div class="ft">생성 시각 {esc(date_str)}</div>')
    p.append("</div></body></html>")
    return "\n".join(p) + "\n"


def main() -> int:
    now = datetime.now(KST)
    # DIGEST_DATE=YYYYMMDD lets you (re)build a specific print edition.
    ymd = os.environ.get("DIGEST_DATE") or now.strftime("%Y%m%d")
    matrix, failed = collect(ymd)
    page = render_table(matrix, failed, now)

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
        lines = [f"### 📰 신문 지면 다이제스트(표) — {now.strftime('%Y-%m-%d %H:%M KST')}", ""]
        for paper in OFFICES:
            n = sum(len(matrix[r][paper]) for r in ROWS)
            lines.append(f"- **{paper}** — {n}건")
        lines.append("")
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
