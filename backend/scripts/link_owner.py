"""Link the demo store to a Supabase Auth user so they can use the dashboard (RLS).
Create the user first in Supabase -> Authentication -> Users (or sign up on the dashboard login page).
Usage (from backend/):  python scripts/link_owner.py you@example.com
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/link_owner.py <email>")
    email = sys.argv[1]
    db.init_pool()
    row = db.fetchone("select id from auth.users where lower(email) = lower(%s)", (email,))
    if not row:
        sys.exit(f"no Supabase auth user with email {email}")
    db.execute("update stores set owner_id = %s where slug = %s", (row["id"], config.DEFAULT_STORE_SLUG))
    print(f"store '{config.DEFAULT_STORE_SLUG}' now owned by {email}")


if __name__ == "__main__":
    main()
