import re
import unicodedata

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").translate(_ZERO_WIDTH).lower()
    return re.sub(r"\s+", " ", t).strip()


_PATTERNS = [
    r"ignore (all |any |the |your |every )?(previous |prior |above |earlier |system |past )?(instructions?|prompts?|rules?|guidelines?)",
    r"disregard (all |any |the |your )?(previous|prior|above|earlier|system)",
    r"forget (all |everything|your |the |previous |prior |above )+(instructions?|rules?|prompts?|you were told)?",
    r"(reveal|show|print|display|repeat|output|leak|tell me|give me|share) (me )?(your|the|ur) (full |entire |hidden |initial |original |secret )?(system |developer )?(prompt|instructions?|rules|guidelines)",
    r"system prompt",
    r"(developer|debug|admin|god|sudo|dan) mode",
    r"jailbreak|do anything now",
    r"you are now\b",
    r"(act|behave|pretend|roleplay) (as|like) (an? |the )?(admin|administrator|developer|system|unrestricted|different|evil|hacker|dan)",
    r"\b(admin|system|developer|root) (override|command|instruction|message|access)\b",
    r"^\s*(system|assistant|developer)\s*:",
    r"new instructions?\s*:",
    r"</?\s*(system|assistant|instructions?|prompt)\s*>",
    r"(set|change|update|override|edit) (the |its |my )?(price|cost|stock|discount)",
    r"(without|skip|no need) (asking|for|the)? ?(me )?(to )?confirm",
    r"[a-z0-9+/]{120,}={0,2}",  # long base64-like blob
]
_COMPILED = [re.compile(p) for p in _PATTERNS]


def looks_like_injection(text: str) -> bool:
    t = normalise(text)
    return any(p.search(t) for p in _COMPILED)
