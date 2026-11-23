import logging
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from . import budget, config, db, usage
from .stores import get_store_by_slug, public_view
from .tools.catalog import size_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")

STATE: dict = {"graph": None, "error": None}
FALLBACK = "Sorry, I'm having trouble right now. Please try again in a moment."
_sem = threading.BoundedSemaphore(8)
_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        from .graph.builder import build_graph

        pool = db.init_pool()
        saver = PostgresSaver(pool)
        saver.setup()
        STATE["graph"] = build_graph(saver)
        log.info("agent ready (model=%s, fake=%s)", config.MODEL_NAME, config.FAKE_LLM)
    except Exception as e:  # keep /health alive; /chat returns a graceful reply
        STATE["error"] = repr(e)
        log.exception("startup failed")
    yield
    db.close()


app = FastAPI(title="DukaanBot Agent API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if config.CORS_ORIGINS != ["*"] else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    thread_id: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=8000)
    store_slug: str | None = None


def _clean_id(s: str) -> str:
    return re.sub(r"[^\w.:@\-]", "_", s.strip())[:64] or "anon"


def _rate_ok(uid: str) -> bool:
    now = time.time()
    with _hits_lock:
        q = _hits[uid]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= config.RATE_LIMIT_PER_MIN:
            return False
        q.append(now)
        return True


def _resp(reply: str, tool_calls=None, tin: int = 0, tout: int = 0) -> dict:
    return {"reply": reply, "tool_calls": tool_calls or [], "tokens": {"in": tin, "out": tout}}


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text") if isinstance(content, list) else ""


def _log_turn(store_id, uid, tid, msg, reply, tool_calls, tin, tout, ms) -> None:
    try:
        db.execute(
            "insert into chat_log (store_id, user_id, thread_id, role, content) values (%s::uuid, %s, %s, 'user', %s)",
            (store_id, uid, tid, msg),
        )
        db.execute(
            "insert into chat_log (store_id, user_id, thread_id, role, content, tool_calls, tokens_in, tokens_out, latency_ms) "
            "values (%s::uuid, %s, %s, 'assistant', %s, %s, %s, %s, %s)",
            (store_id, uid, tid, reply, Jsonb(tool_calls), tin, tout, ms),
        )
        budget.bump(tin, tout)
    except Exception:
        log.exception("chat_log insert failed (non-fatal)")


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.post("/chat")
def chat(req: ChatRequest):
    t0 = time.time()
    uid, tid = _clean_id(req.user_id), _clean_id(req.thread_id)
    msg = req.message.strip()[:1000]
    if not msg:
        return _resp("Please type a message.")
    if not _rate_ok(uid):
        return _resp("You're sending messages very fast. Please wait a few seconds and try again.")
    graph = STATE["graph"]
    if graph is None:
        log.error("chat before graph ready: %s", STATE["error"])
        return _resp(FALLBACK)
    try:
        store = get_store_by_slug(req.store_slug or config.DEFAULT_STORE_SLUG)
        if not store:
            return _resp("This store was not found.")
        if budget.mode() == "hard":
            return _resp("Sorry, the assistant is temporarily unavailable. Please try again later.")
    except Exception:
        log.exception("store/budget lookup failed")
        return _resp(FALLBACK)

    store_id = store["id"]
    usage_id = uuid.uuid4().hex
    tracker = usage.register(usage_id)
    cfg = {
        "configurable": {
            "thread_id": f"{store_id}:{uid}:{tid}",  # namespaced by store AND user: same thread_id from two users never collides
            "store_id": store_id,
            "user_id": uid,
            "raw_thread_id": tid,
            "usage_id": usage_id,
        },
        "recursion_limit": 30,
    }
    reply, tool_calls = FALLBACK, []
    if not _sem.acquire(timeout=30):
        usage.release(usage_id)
        return _resp("I'm a bit busy right now. Please try again in a moment.")
    try:
        res = graph.invoke({"messages": [HumanMessage(content=msg)], "store_id": store_id, "user_id": uid}, cfg)
        for m in reversed(res.get("messages", [])):
            if isinstance(m, AIMessage) and _text(m.content).strip():
                reply = _text(m.content).strip()
                break
        tool_calls = res.get("tool_log", []) or []
    except Exception:
        log.exception("graph failed")
    finally:
        _sem.release()
        usage.release(usage_id)

    ms = int((time.time() - t0) * 1000)
    _log_turn(store_id, uid, tid, msg, reply, tool_calls, tracker.tin, tracker.tout, ms)
    return _resp(reply, tool_calls, tracker.tin, tracker.tout)


# ----------------------------------------------------------------- storefront helpers (not graded)


@app.get("/store/{slug}")
def store_view(slug: str):
    store = get_store_by_slug(slug)
    if not store:
        raise HTTPException(404, "store not found")
    rows = db.fetchall(
        "select p.sku, p.name, p.category, p.color, p.description, p.price_pkr, "
        "coalesce(json_agg(json_build_object('size', v.size, 'stock', v.stock)) filter (where v.id is not null), '[]'::json) as sizes "
        "from products p left join variants v on v.product_id = p.id "
        "where p.store_id = %s::uuid and p.active group by p.id order by p.category, p.name",
        (store["id"],),
    )
    products = []
    for r in rows:
        sizes = sorted(r["sizes"], key=lambda s: size_key(s["size"]))
        products.append({**{k: r[k] for k in ("sku", "name", "category", "color", "description", "price_pkr")}, "sizes": sizes})
    return {"store": public_view(store), "products": products}


@app.get("/store/{slug}/orders")
def my_orders(slug: str, user_id: str):
    store = get_store_by_slug(slug)
    if not store:
        raise HTTPException(404, "store not found")
    rows = db.fetchall(
        "select order_no, status, total, items, created_at from orders where store_id = %s::uuid and user_id = %s "
        "order by created_at desc limit 20",
        (store["id"], _clean_id(user_id)),
    )
    return [
        {"order": f"DK-{r['order_no']}", "status": r["status"], "total": r["total"], "items": r["items"], "created_at": r["created_at"].isoformat()}
        for r in rows
    ]
