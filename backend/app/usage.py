"""Per-turn token tracking. Trackers are looked up by a string id carried in the LangGraph config."""
import threading


class Tracker:
    def __init__(self):
        self.tin = 0
        self.tout = 0
        self.calls = 0
        self._lock = threading.Lock()

    def add(self, tin: int, tout: int) -> None:
        with self._lock:
            self.tin += int(tin or 0)
            self.tout += int(tout or 0)
            self.calls += 1


_trackers: dict[str, Tracker] = {}
_lock = threading.Lock()


def register(usage_id: str) -> Tracker:
    t = Tracker()
    with _lock:
        _trackers[usage_id] = t
    return t


def release(usage_id: str) -> None:
    with _lock:
        _trackers.pop(usage_id, None)


def record(config, response) -> None:
    """Add the token usage of an AIMessage to the current turn's tracker."""
    try:
        uid = (config or {}).get("configurable", {}).get("usage_id")
        t = _trackers.get(uid)
        um = getattr(response, "usage_metadata", None)
        if t and um:
            t.add(um.get("input_tokens", 0), um.get("output_tokens", 0))
    except Exception:
        pass
