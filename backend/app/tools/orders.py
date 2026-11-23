import json
import re
import time
import uuid

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from psycopg.types.json import Jsonb

from .. import db
from ..stores import get_store_by_id
from .pricing import CartItem, delivery_fee, price_cart


class OrderError(Exception):
    pass


PAY_LABEL = {"cod": "Cash on delivery", "bank_transfer": "Bank transfer"}


@tool
def propose_order(
    items: list[CartItem],
    customer_name: str,
    phone: str,
    city: str,
    address: str,
    payment_method: str = "cod",
    config: RunnableConfig = None,
) -> str:
    """Prepare the order summary once ALL details are known. Does NOT place the order; the customer must reply YES. payment_method: cod or bank_transfer."""
    name = re.sub(r"\s+", " ", str(customer_name or "")).strip()
    digits = re.sub(r"\D", "", str(phone or ""))
    city = str(city or "").strip()
    address = re.sub(r"\s+", " ", str(address or "")).strip()
    pay = "bank_transfer" if "bank" in str(payment_method).lower() else "cod"
    errors = []
    if len(name) < 2:
        errors.append("customer_name missing")
    if not 10 <= len(digits) <= 13:
        errors.append("phone must have 10-13 digits")
    if len(city) < 2:
        errors.append("city missing")
    if len(address) < 8:
        errors.append("full address missing")
    if errors:
        return json.dumps({"ok": False, "error": "; ".join(errors)})

    priced = price_cart(str(config["configurable"]["store_id"]), items, city)
    if not priced["ok"]:
        return json.dumps({"ok": False, "error": "; ".join(priced["issues"]) or "cart invalid"})

    pending = {
        "id": uuid.uuid4().hex,
        "items": priced["lines"],
        "customer_name": name,
        "phone": digits,
        "city": city,
        "address": address,
        "payment_method": pay,
        "subtotal": priced["subtotal"],
        "delivery_fee": priced["delivery_fee"],
        "total": priced["total"],
        "proposed_at": time.time(),
    }
    lines = "\n".join(f"- {l['qty']} x {l['name']} ({l['size']}) = Rs {l['line']:,}" for l in priced["lines"])
    fee = "free" if priced["delivery_fee"] == 0 else f"Rs {priced['delivery_fee']:,}"
    summary = (
        f"Please confirm your order:\n{lines}\nDelivery to {city}: {fee}\n"
        f"Total: Rs {priced['total']:,} ({PAY_LABEL[pay]})\n"
        f"Deliver to: {name}, {digits}, {address}, {city}\n"
        "Reply YES to confirm, or tell me what to change."
    )
    return json.dumps({"ok": True, "pending_order": pending, "summary": summary})


@tool
def get_order_status(order_number: str, config: RunnableConfig = None) -> str:
    """Status of the customer's own order by number (e.g. DK-1001 or 1001)."""
    cfg = config["configurable"]
    m = re.search(r"\d+", str(order_number or ""))
    if not m:
        return json.dumps({"ok": False, "error": "give an order number like DK-1001"})
    row = db.fetchone(
        "select order_no, status, total, items, created_at from orders "
        "where store_id = %s::uuid and user_id = %s and order_no = %s",
        (str(cfg["store_id"]), cfg["user_id"], int(m.group())),
    )
    if not row:
        return json.dumps({"ok": False, "error": "no order with that number found for you"})
    names = ", ".join(f"{i['qty']}x {i['name']}" for i in row["items"])
    return json.dumps(
        {"ok": True, "order": f"DK-{row['order_no']}", "status": row["status"], "total": row["total"], "items": names,
         "placed": row["created_at"].strftime("%d %b %Y")},
        separators=(",", ":"),
    )


def create_order(pending: dict, store_id: str, user_id: str, thread_id: str) -> dict:
    """GATED: only called by the place_order node after the customer's explicit YES. Not exposed to any LLM."""
    existing = db.fetchone("select order_no, total, delivery_fee, items from orders where pending_id = %s", (pending["id"],))
    if existing:
        return {"order_no": existing["order_no"], "total": existing["total"], "delivery_fee": existing["delivery_fee"],
                "lines": existing["items"], "duplicate": True}
    store = get_store_by_id(store_id) or {}
    with db.pool().connection() as conn:
        with conn.transaction():
            lines, subtotal = [], 0
            for it in pending["items"]:
                row = conn.execute(
                    "select v.id, v.stock, p.name, p.price_pkr from variants v join products p on p.id = v.product_id "
                    "where p.store_id = %s::uuid and upper(p.sku) = %s and upper(v.size) = %s for update of v",
                    (store_id, it["sku"].upper(), it["size"].upper()),
                ).fetchone()
                if not row or row["stock"] < it["qty"]:
                    raise OrderError(f"{it['name']} ({it['size']}) is no longer available in that quantity")
                conn.execute("update variants set stock = stock - %s where id = %s", (it["qty"], row["id"]))
                line = row["price_pkr"] * it["qty"]
                subtotal += line
                lines.append({"sku": it["sku"], "name": row["name"], "size": it["size"], "qty": it["qty"], "unit": row["price_pkr"], "line": line})
            fee = delivery_fee(store, pending["city"], subtotal)
            total = subtotal + fee
            r = conn.execute(
                "insert into orders (pending_id, store_id, user_id, thread_id, customer_name, phone, city, address, items, "
                "subtotal, delivery_fee, total, payment_method) values (%s, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "returning order_no",
                (pending["id"], store_id, user_id, thread_id, pending["customer_name"], pending["phone"], pending["city"],
                 pending["address"], Jsonb(lines), subtotal, fee, total, pending["payment_method"]),
            ).fetchone()
    return {"order_no": r["order_no"], "total": total, "delivery_fee": fee, "lines": lines, "duplicate": False}
