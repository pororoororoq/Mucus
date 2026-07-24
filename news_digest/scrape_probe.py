"""Probe #7: validate B면 exclusion on a fully-published edition (20260724)."""

from __future__ import annotations

from collections import Counter

if __package__:
    from . import jimyeon
else:  # pragma: no cover
    import jimyeon  # type: ignore

YMD = "20260724"


def main() -> int:
    print(f"date={YMD}")
    for paper, oid in jimyeon.OFFICES.items():
        print(f"\n==================== {paper} ====================")
        try:
            items = jimyeon.scrape_jimyeon(paper, oid, YMD)
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e!r}")
            continue
        # distribution of 면 numbers (main section only; B/C -> -1)
        dist = Counter(m for m, _ in items)
        kept = {m: n for m, n in sorted(dist.items()) if 1 <= m <= 6}
        dropped = {m: n for m, n in dist.items() if m == -1}
        editorials = [a.title for m, a in items if jimyeon._is_editorial(a.title)]
        print(f"  total links={len(items)}  A면 1~6 dist={kept}  별지(-1)={dropped.get(-1,0)}")
        print(f"  editorials({len(editorials)}): {editorials[:4]}")
        # show 1면 titles to confirm they are main-section front page
        front = [a.title[:40] for m, a in items if m == 1][:5]
        print(f"  1면: {front}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
