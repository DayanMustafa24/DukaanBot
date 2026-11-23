"""Long-term memory: per (store_id, user_id) facts in Postgres. Whitelisted keys only, short sanitised values."""
import re

from .. import db
from ..safety.injection import looks_like_injection

ALLOWED_KEYS = {"name", "city", "size_pref", "color_pref", "style_pref", "budget_range", "last_order_summary", "language"}
MAX_LEN = 100


def clean_value(v) -> str:
    s = re.sub(r"[\r\n\t<>{}`]", " ", str(v or ""))
    return re.sub(r"\s+", " ", s).strip()[:MAX_LEN]


def load_memory(store_id: str, user_id: str) -> dict:
    rows = db.fetchall("select key, value from user_memory where store_id = %s::uuid and user_id = %s", (store_id, user_id))
    return {r["key"]: r["value"] for r in rows}


def save_memory(store_id: str, user_id: str, updates: dict) -> dict:
    saved = {}
    for k, v in (updates or {}).items():
        k = str(k).strip().lower()
        val = clean_value(v)
        if k not in ALLOWED_KEYS or not val or looks_like_injection(val):
            continue
        db.execute(
            "insert into user_memory (store_id, user_id, key, value) values (%s::uuid, %s, %s, %s) "
            "on conflict (store_id, user_id, key) do update set value = excluded.value, updated_at = now()",
            (store_id, user_id, k, val),
        )
        saved[k] = val
    return saved


def format_memory(mem: dict) -> str:
    if not mem:
        return "none"
    return "; ".join(f"{k}={v}" for k, v in mem.items())
