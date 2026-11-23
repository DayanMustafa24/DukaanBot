import logging

import httpx

from .. import config

log = logging.getLogger("notify")


def notify_seller(store: dict, order: dict, pending: dict) -> str:
    """Send a Telegram message to the seller. Never raises; returns sent | skipped | failed."""
    token = config.TELEGRAM_BOT_TOKEN
    chat_id = (store or {}).get("telegram_chat_id")
    if not token or not chat_id:
        return "skipped"
    items = "\n".join(f"- {l['qty']} x {l['name']} ({l['size']}) = Rs {l['line']}" for l in order["lines"])
    pay = "Bank transfer" if pending.get("payment_method") == "bank_transfer" else "Cash on delivery"
    text = (
        f"New order DK-{order['order_no']} ({store.get('name', '')})\n{items}\n"
        f"Delivery: Rs {order['delivery_fee']}\nTotal: Rs {order['total']} ({pay})\n"
        f"Customer: {pending['customer_name']} | {pending['phone']}\n{pending['address']}, {pending['city']}"
    )
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=8,
        )
        return "sent" if r.status_code == 200 else f"failed:{r.status_code}"
    except Exception:
        log.exception("telegram notify failed")
        return "failed"
