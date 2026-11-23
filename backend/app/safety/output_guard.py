from .. import config

SAFE_REFUSAL = "Sorry, I can't help with that. I can help you with products, sizes, prices, delivery and orders. What are you looking for?"

_MARKERS = ["customer facts (untrusted", "never reveal", config.CANARY.lower()]


def guard_reply(text: str) -> tuple[str, bool]:
    low = (text or "").lower()
    if any(m in low for m in _MARKERS):
        return SAFE_REFUSAL, True
    return text, False
