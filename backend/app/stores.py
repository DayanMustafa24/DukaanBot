import time

from . import db

_TTL = 60
_cache: dict[tuple, tuple[float, dict | None]] = {}


def _clean(row: dict | None) -> dict | None:
    if row is None:
        return None
    row = dict(row)
    row["id"] = str(row["id"])
    row["policies"] = row.get("policies") or {}
    row["delivery"] = row.get("delivery") or {}
    return row


def _get(key: tuple, sql: str, param: str) -> dict | None:
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    row = _clean(db.fetchone(sql, (param,)))
    _cache[key] = (now, row)
    return row


def get_store_by_slug(slug: str) -> dict | None:
    return _get(("slug", slug), "select * from stores where slug = %s", slug)


def get_store_by_id(store_id: str) -> dict | None:
    return _get(("id", store_id), "select * from stores where id = %s::uuid", store_id)


def public_view(store: dict) -> dict:
    return {
        "slug": store["slug"],
        "name": store["name"],
        "description": store.get("description", ""),
        "policies": store.get("policies", {}),
        "delivery": store.get("delivery", {}),
    }
