"""Apply schema.sql and (re)seed the demo store. Safe to re-run; re-seeding resets demo stock.
Usage (from backend/):  python scripts/init_db.py [--no-seed]
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from psycopg.types.json import Jsonb  # noqa: E402

from app import config, db  # noqa: E402
from seed_data import PRODUCTS, STORE  # noqa: E402


def main() -> None:
    if not config.DATABASE_URL:
        sys.exit("DATABASE_URL is empty. Put it in .env (project root or backend/).")
    sql = (Path(__file__).resolve().parents[1] / "sql" / "schema.sql").read_text(encoding="utf-8")
    db.init_pool()
    with db.pool().connection() as conn:
        conn.execute(sql)
    print("schema applied")

    if "--no-seed" in sys.argv:
        return
    chat_id = os.getenv("SEED_TELEGRAM_CHAT_ID") or None
    with db.pool().connection() as conn:
        with conn.transaction():
            row = conn.execute(
                "insert into stores (slug, name, description, policies, delivery, telegram_chat_id) values (%s,%s,%s,%s,%s,%s) "
                "on conflict (slug) do update set name = excluded.name, description = excluded.description, "
                "policies = excluded.policies, delivery = excluded.delivery, "
                "telegram_chat_id = coalesce(excluded.telegram_chat_id, stores.telegram_chat_id) returning id",
                (STORE["slug"], STORE["name"], STORE["description"], Jsonb(STORE["policies"]), Jsonb(STORE["delivery"]), chat_id),
            ).fetchone()
            store_id = row["id"]
            conn.execute("delete from products where store_id = %s", (store_id,))
            for sku, name, cat, color, price, desc, tags, stock in PRODUCTS:
                p = conn.execute(
                    "insert into products (store_id, sku, name, category, color, description, tags, price_pkr) "
                    "values (%s,%s,%s,%s,%s,%s,%s,%s) returning id",
                    (store_id, sku, name, cat, color, desc, tags, price),
                ).fetchone()
                for size, n in stock.items():
                    conn.execute(
                        "insert into variants (product_id, store_id, size, stock) values (%s,%s,%s,%s)",
                        (p["id"], store_id, size, n),
                    )
    print(f"seeded store '{STORE['slug']}' with {len(PRODUCTS)} products (telegram chat id {'set' if chat_id else 'not set'})")


if __name__ == "__main__":
    try:
        main()
    finally:
        db.close()
