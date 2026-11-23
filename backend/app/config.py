import os
from pathlib import Path

from dotenv import load_dotenv

_app_dir = Path(__file__).resolve().parent
# Load .env from backend/ and from the project root (first one found wins per variable).
for _p in (_app_dir.parent / ".env", _app_dir.parent.parent / ".env"):
    if _p.exists():
        load_dotenv(_p, override=False)


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name) or default)
    except ValueError:
        return default


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "claude-haiku-5-5")
DATABASE_URL = os.getenv("DATABASE_URL", "")
DEFAULT_STORE_SLUG = os.getenv("DEFAULT_STORE_SLUG", "nazakat-threads")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
RATE_LIMIT_PER_MIN = int(_float("RATE_LIMIT_PER_MIN", 30))
FAKE_LLM = os.getenv("FAKE_LLM", "0") == "1"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

PRICE_IN_PER_MTOK = _float("PRICE_IN_PER_MTOK", 0)
PRICE_OUT_PER_MTOK = _float("PRICE_OUT_PER_MTOK", 0)
BUDGET_SOFT_USD = _float("BUDGET_SOFT_USD", 1.40)
BUDGET_HARD_USD = _float("BUDGET_HARD_USD", 1.90)

# Agent tuning
MAX_HISTORY_MSGS = 10      # past messages shown to the LLM (current turn is always full)
SUMMARISE_AT = 24          # stored messages before summarising
SUMMARISE_COUNT = 14       # oldest messages folded into the summary
MAX_TOOL_ROUNDS = 4
PENDING_TTL_SECONDS = 1800
CANARY = "ZX-CANARY-7731"
