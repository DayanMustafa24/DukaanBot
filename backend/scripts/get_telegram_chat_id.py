"""Print Telegram chat ids that messaged your bot. Message the bot once first.
Usage (from backend/):  python scripts/get_telegram_chat_id.py
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        sys.exit("TELEGRAM_BOT_TOKEN is empty in .env")
    r = httpx.get(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates", timeout=15)
    data = r.json()
    seen = {}
    for u in data.get("result", []):
        chat = (u.get("message") or u.get("channel_post") or {}).get("chat")
        if chat:
            seen[chat["id"]] = chat.get("first_name") or chat.get("title") or ""
    if not seen:
        sys.exit("no messages found: open your bot in Telegram, press Start, send 'hi', then run this again")
    for cid, name in seen.items():
        print(f"chat id: {cid}  ({name})")
    print("Put it in .env as SEED_TELEGRAM_CHAT_ID=<id>, then run: python scripts/init_db.py")


if __name__ == "__main__":
    main()
