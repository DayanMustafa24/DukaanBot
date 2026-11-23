"""Spend ledger from chat_log token counts x configured prices. Modes: normal | soft | hard."""
import logging
import time

from . import config, db

log = logging.getLogger("budget")
_cache = {"t": 0.0, "usd": 0.0}


def spent_usd() -> float:
    now = time.time()
    if now - _cache["t"] < 20:
        return _cache["usd"]
    try:
        row = db.fetchone("select coalesce(sum(tokens_in),0) as i, coalesce(sum(tokens_out),0) as o from chat_log")
        usd = (row["i"] * config.PRICE_IN_PER_MTOK + row["o"] * config.PRICE_OUT_PER_MTOK) / 1_000_000
        _cache.update(t=now, usd=usd)
    except Exception:
        log.exception("budget ledger query failed")
    return _cache["usd"]


def mode() -> str:
    # If prices are not configured we cannot estimate spend; stay in normal mode.
    if config.PRICE_IN_PER_MTOK == 0 and config.PRICE_OUT_PER_MTOK == 0:
        return "normal"
    usd = spent_usd()
    if usd >= config.BUDGET_HARD_USD:
        return "hard"
    if usd >= config.BUDGET_SOFT_USD:
        return "soft"
    return "normal"


def bump(tokens_in: int, tokens_out: int) -> None:
    """Keep the cached ledger fresh between DB refreshes."""
    _cache["usd"] += (tokens_in * config.PRICE_IN_PER_MTOK + tokens_out * config.PRICE_OUT_PER_MTOK) / 1_000_000
