"""Send a digest to Telegram as an HTML document (+ short caption).

Telegram chat messages can't render a full HTML table, so we upload the digest
file as a document — tapping it opens the styled page in a browser. A short
plain-text caption carries the title/date.

Env:  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  (both required)
Usage: python -m news_digest.telegram_send <html_path> "<caption>" [filename]
"""

from __future__ import annotations

import os
import sys

import requests


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — skipping.")
        return 0

    path = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else ""
    filename = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(path)

    with open(path, "rb") as fh:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={"chat_id": chat_id, "caption": caption[:1024]},
            files={"document": (filename, fh, "text/html")},
            timeout=60,
        )
    body = resp.json()
    if not body.get("ok"):
        print(f"Telegram send failed: {body}")
        resp.raise_for_status()
        return 1
    print("Telegram sent OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
