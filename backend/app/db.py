from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

_pool: ConnectionPool | None = None


def init_pool() -> ConnectionPool:
    """Sync pool. autocommit + dict_row + no prepared statements (required by PostgresSaver and Supabase pooler)."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=config.DATABASE_URL,
            min_size=1,
            max_size=6,
            timeout=15,
            kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row},
            check=ConnectionPool.check_connection,
            open=True,
        )
        _pool.wait(timeout=20)
    return _pool


def pool() -> ConnectionPool:
    if _pool is None:
        return init_pool()
    return _pool


def close() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def fetchall(sql: str, params=None) -> list[dict]:
    with pool().connection() as conn:
        return conn.execute(sql, params).fetchall()


def fetchone(sql: str, params=None) -> dict | None:
    with pool().connection() as conn:
        return conn.execute(sql, params).fetchone()


def execute(sql: str, params=None) -> None:
    with pool().connection() as conn:
        conn.execute(sql, params)
