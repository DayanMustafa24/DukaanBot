import json

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel

from .. import db
from ..stores import get_store_by_id


class CartItem(BaseModel):
    sku: str
    size: str = "FREE"
    qty: int = 1


def as_dict(i) -> dict:
    if isinstance(i, dict):
        return i
    if hasattr(i, "model_dump"):
        return i.model_dump()
    return dict(i)


def delivery_fee(store: dict, city: str, subtotal: int) -> int:
    d = (store or {}).get("delivery") or {}
    free_over = d.get("free_over")
    if free_over is not None and subtotal >= int(free_over):
        return 0
    local = [str(x).lower() for x in d.get("local_cities", [])]
    if (city or "").strip().lower() in local:
        return int(d.get("local_fee", 200))
    return int(d.get("other_fee", 350))


_VARIANT_SQL = (
    "select p.sku, p.name, p.price_pkr, v.size, v.stock from products p join variants v on v.product_id = p.id "
    "where p.store_id = %s::uuid and p.active and upper(p.sku) = %s"
)


def _find_variant(store_id: str, sku: str, size: str):
    rows = db.fetchall(_VARIANT_SQL, (store_id, sku))
    for r in rows:
        if str(r["size"]).upper() == size:
            return r
    if len(rows) == 1:  # single-variant item (e.g. FREE size): accept any size the model passed
        return rows[0]
    return None


def price_cart(store_id: str, items: list, city: str) -> dict:
    store = get_store_by_id(store_id) or {}
    lines, issues, subtotal = [], [], 0
    if not items:
        issues.append("no items given")
    for raw in items or []:
        it = as_dict(raw)
        sku = str(it.get("sku", "")).strip().upper()
        size = (str(it.get("size") or "FREE").strip() or "FREE").upper()
        try:
            qty = int(it.get("qty") or 1)
        except (TypeError, ValueError):
            qty = 0
        if qty < 1 or qty > 5:
            issues.append(f"{sku}: quantity must be between 1 and 5")
            continue
        row = _find_variant(store_id, sku, size)
        if not row:
            issues.append(f"{sku} size {size} not found (use get_product to see valid sizes)")
            continue
        if row["stock"] < qty:
            issues.append(f"{row['name']} size {row['size']}: only {row['stock']} in stock")
            continue
        line = row["price_pkr"] * qty
        subtotal += line
        lines.append({"sku": row["sku"], "name": row["name"], "size": row["size"], "qty": qty, "unit": row["price_pkr"], "line": line})
    fee = delivery_fee(store, city, subtotal) if lines else 0
    return {
        "ok": bool(lines) and not issues,
        "lines": lines,
        "subtotal": subtotal,
        "delivery_fee": fee,
        "total": subtotal + fee,
        "issues": issues,
    }


@tool
def calculate_total(items: list[CartItem], city: str, config: RunnableConfig = None) -> str:
    """Exact cart total in PKR incl. delivery to the city. items: sku, size, qty (1-5). Always use this for totals."""
    res = price_cart(str(config["configurable"]["store_id"]), items, city)
    return json.dumps(res, separators=(",", ":"))
