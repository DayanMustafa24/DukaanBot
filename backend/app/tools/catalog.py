import json
import re
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from .. import db

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
STOP = {
    "the", "a", "an", "for", "me", "my", "i", "want", "need", "show", "find", "have", "any", "some", "with", "and",
    "or", "in", "of", "to", "do", "you", "is", "are", "size", "under", "below", "less", "than", "rs", "pkr",
}


def size_key(s: str):
    s = str(s).upper()
    if s in SIZE_ORDER:
        return (SIZE_ORDER.index(s), 0)
    if s.isdigit():
        return (50, int(s))
    return (99, 0)


def _sid(config: RunnableConfig) -> str:
    return str(config["configurable"]["store_id"])


@tool
def search_catalog(
    query: str,
    max_price: Optional[int] = None,
    category: Optional[str] = None,
    size: Optional[str] = None,
    config: RunnableConfig = None,
) -> str:
    """Search this shop's products. query = 1-3 short English keywords like 'black hoodie'. Returns up to 5 items with price and sizes in stock."""
    sid = _sid(config)
    tokens = [t for t in re.findall(r"[a-z0-9]+", (query or "").lower()) if t not in STOP and len(t) > 1][:5]
    tokens = [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in tokens]
    hay = "lower(p.name || ' ' || p.category || ' ' || p.color || ' ' || p.tags || ' ' || p.description)"

    score_sql = "0"
    score_params: list = []
    if tokens:
        score_sql = " + ".join(f"(case when {hay} like %s then 1 else 0 end)" for _ in tokens)
        score_params = [f"%{t}%" for t in tokens]

    where = ["p.store_id = %s::uuid", "p.active"]
    where_params: list = [sid]
    if max_price:
        where.append("p.price_pkr <= %s")
        where_params.append(int(max_price))
    if category:
        cat = re.sub(r"[^a-z0-9 ]", "", category.lower()).strip()
        cat = cat[:-1] if len(cat) > 3 and cat.endswith("s") else cat
        if cat:
            where.append("lower(p.category) like %s")
            where_params.append(f"%{cat}%")
    if size:
        where.append("exists (select 1 from variants v where v.product_id = p.id and v.stock > 0 and upper(v.size) = %s)")
        where_params.append(str(size).strip().upper())

    sql = f"""
        select * from (
          select p.sku, p.name, p.price_pkr, ({score_sql}) as score,
                 (select string_agg(v.size, ',') from variants v where v.product_id = p.id and v.stock > 0) as sizes
          from products p
          where {' and '.join(where)}
        ) t
        where score >= %s
        order by score desc, price_pkr asc
        limit 5
    """
    min_score = 1 if tokens else 0
    rows = db.fetchall(sql, score_params + where_params + [min_score])
    results = []
    for r in rows:
        sizes = sorted((r["sizes"] or "").split(",") if r["sizes"] else [], key=size_key)
        results.append({"sku": r["sku"], "name": r["name"], "price": r["price_pkr"], "sizes": sizes})
    if not results:
        return json.dumps({"results": [], "note": "no match; try broader keywords or drop filters"})
    return json.dumps({"results": results}, separators=(",", ":"))


@tool
def get_product(sku: str, config: RunnableConfig = None) -> str:
    """Get one product's price and exact stock per size. Use before promising availability."""
    sid = _sid(config)
    rows = db.fetchall(
        "select p.sku, p.name, p.price_pkr, p.description, v.size, v.stock "
        "from products p left join variants v on v.product_id = p.id "
        "where p.store_id = %s::uuid and p.active and upper(p.sku) = upper(%s)",
        (sid, str(sku).strip()),
    )
    if not rows:
        return json.dumps({"ok": False, "error": "sku not found; use search_catalog to find the right sku"})
    first = rows[0]
    stock = {r["size"]: r["stock"] for r in sorted(rows, key=lambda r: size_key(r["size"] or "")) if r["size"]}
    return json.dumps(
        {"sku": first["sku"], "name": first["name"], "price": first["price_pkr"], "desc": (first["description"] or "")[:160], "stock": stock},
        separators=(",", ":"),
    )
