import json
import logging
import re
import time

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from .. import budget, stores
from .. import config as settings
from ..llm import get_llm, llm_call
from ..memory.longterm import load_memory, save_memory
from ..safety.injection import looks_like_injection, normalise
from ..safety.output_guard import SAFE_REFUSAL, guard_reply
from ..tools import ALLOWED, ORDER_TOOLS, SALES_TOOLS, TOOLS_BY_NAME
from ..tools.notify import notify_seller
from ..tools.orders import PAY_LABEL, OrderError, create_order
from .prompts import CURATOR_PROMPT, ROUTER_PROMPT, SUMMARY_PROMPT, build_prompt
from .state import AgentState

log = logging.getLogger("graph")

# ---------------------------------------------------------------- helpers


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    out = []
    if isinstance(content, list):
        for b in content:
            if isinstance(b, str):
                out.append(b)
            elif isinstance(b, dict) and b.get("type") == "text":
                out.append(b.get("text", ""))
    return "".join(out)


def last_user_text(state: dict) -> str:
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            return text_of(m.content)
    return ""


def last_ai_text(state: dict) -> str:
    for m in reversed(state.get("messages", [])):
        if isinstance(m, AIMessage) and text_of(m.content).strip():
            return text_of(m.content)
    return ""


def parse_json(s: str) -> dict:
    m = re.search(r"\{.*\}", s or "", re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


_YES_STRONG = {"yes", "y", "yeah", "yep", "yup", "confirm", "confirmed", "ok", "okay", "sure", "haan", "han", "ji", "jee",
               "theek", "thik", "kardo", "bilkul", "done", "go"}
_YES_ALL = _YES_STRONG | {"please", "it", "the", "order", "ahead", "kar", "do", "hai", "place", "correct", "right", "pls", "plz"}
_NO_STRONG = {"no", "n", "nope", "cancel", "nahi", "nahin", "na", "abort", "mat"}
_NO_ALL = _NO_STRONG | {"thanks", "thank", "you", "please", "order", "the", "it", "my", "i", "dont", "don't", "want", "to", "anymore", "now", "karo", "kar", "do"}


def yes_no(msg: str):
    """Deterministic read of the customer's own words. Only used when an order is pending."""
    toks = re.findall(r"[a-z']+", normalise(msg))
    if not toks or len(toks) > 6:
        return None
    if all(t in _YES_ALL for t in toks) and any(t in _YES_STRONG for t in toks):
        return "yes"
    if all(t in _NO_ALL for t in toks) and any(t in _NO_STRONG for t in toks):
        return "no"
    return None


def history_for_llm(messages: list, limit: int) -> list:
    """Past turns -> plain Human/AI text only (no stale tool blocks); current turn -> full (incl. tool calls/results)."""
    idx = 0
    for i, m in enumerate(messages):
        if isinstance(m, HumanMessage):
            idx = i
    past, cur = messages[:idx], messages[idx:]
    compact: list = []
    for m in past:
        if isinstance(m, HumanMessage):
            t = text_of(m.content).strip()
            if t:
                compact.append(HumanMessage(content=t))
        elif isinstance(m, AIMessage):
            t = text_of(m.content).strip()
            if t:
                compact.append(AIMessage(content=t))
    compact = compact[-limit:]
    while compact and not isinstance(compact[0], HumanMessage):
        compact.pop(0)
    merged: list = []
    for m in compact:
        if merged and type(merged[-1]) is type(m):
            merged[-1] = type(m)(content=merged[-1].content + "\n" + m.content)
        else:
            merged.append(m)
    if merged and cur and isinstance(merged[-1], HumanMessage) and isinstance(cur[0], HumanMessage):
        cur = [HumanMessage(content=merged[-1].content + "\n" + text_of(cur[0].content))] + cur[1:]
        merged = merged[:-1]
    return merged + cur


# ---------------------------------------------------------------- nodes


def load_context(state: AgentState, config: RunnableConfig):
    c = config["configurable"]
    sid, uid = str(c["store_id"]), c["user_id"]
    store = stores.get_store_by_id(sid) or {}
    try:
        mem = load_memory(sid, uid)
    except Exception:
        log.exception("load_memory failed")
        mem = {}
    return {
        "store_id": sid,
        "user_id": uid,
        "store": {"name": store.get("name", "the shop"), "description": store.get("description", ""), "policies": store.get("policies", {})},
        "memory": mem,
        "budget_mode": budget.mode(),
        "tool_log": [],
        "tool_rounds": 0,
        "propose_summary": "",
        "order_placed": False,
        "save_memory": False,
        "route": "",
        "intent": "",
    }


def guard_router(state: AgentState, config: RunnableConfig):
    msg = last_user_text(state)

    # 1) deterministic injection screen (no LLM)
    if looks_like_injection(msg):
        return {"route": "refuse", "intent": "injection"}

    # 2) pending order: the customer's own YES/NO is read deterministically
    pending = state.get("pending_order")
    patch: dict = {}
    if pending and time.time() - pending.get("proposed_at", 0) > settings.PENDING_TTL_SECONDS:
        pending = None
        patch["pending_order"] = None
    if pending:
        d = yes_no(msg)
        if d == "yes":
            return {**patch, "route": "place", "intent": "confirm"}
        if d == "no":
            return {**patch, "route": "cancel", "intent": "cancel"}
        return {**patch, "route": "order", "intent": "order", "active_agent": "order"}

    # 3) LLM intent classification (small, JSON only)
    prompt = ROUTER_PROMPT.format(
        mode=state.get("active_agent") or "sales",
        last_ai=last_ai_text(state)[:200].replace("\n", " "),
        msg=msg[:500],
    )
    try:
        resp = llm_call(get_llm("router"), [HumanMessage(content=prompt)], config)
        data = parse_json(text_of(resp.content))
    except Exception:
        log.exception("router failed; defaulting to sales")
        data = {}
    intent = str(data.get("intent", "browse")).lower()
    save = bool(data.get("save_memory", False))
    if intent in ("off_topic", "injection"):
        return {**patch, "route": "refuse", "intent": intent}
    if intent == "order":
        return {**patch, "route": "order", "intent": intent, "active_agent": "order", "save_memory": save}
    return {**patch, "route": "sales", "intent": intent, "active_agent": "sales", "save_memory": save}


def refusal(state: AgentState, config: RunnableConfig):
    name = (state.get("store") or {}).get("name", "the shop")
    text = f"Sorry, I can only help with shopping at {name}: products, sizes, prices, delivery and orders. What are you looking for today?"
    out = []
    # Replace the blocked message in history so it cannot influence later turns.
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            out.append(HumanMessage(content="[blocked message]", id=m.id))
            break
    out.append(AIMessage(content=text))
    return {"messages": out}


def _agent(state: AgentState, config: RunnableConfig, kind: str):
    tools = SALES_TOOLS if kind == "sales" else ORDER_TOOLS
    msgs = [SystemMessage(content=build_prompt(kind, state))] + history_for_llm(state["messages"], settings.MAX_HISTORY_MSGS)
    resp = llm_call(get_llm("agent", tools), msgs, config)
    if getattr(resp, "tool_calls", None):
        if state.get("tool_rounds", 0) >= settings.MAX_TOOL_ROUNDS:
            resp = AIMessage(content="Sorry, I couldn't finish that. Could you rephrase what you need?")
    else:
        text, flagged = guard_reply(text_of(resp.content))
        if flagged or not text.strip():
            resp = AIMessage(content=text if flagged else "Sorry, could you say that again?")
    return {"messages": [resp], "active_agent": kind}


def sales_agent(state: AgentState, config: RunnableConfig):
    return _agent(state, config, "sales")


def order_agent(state: AgentState, config: RunnableConfig):
    return _agent(state, config, "order")


def run_tools(state: AgentState, config: RunnableConfig):
    last = state["messages"][-1]
    kind = state.get("active_agent", "sales")
    allowed = ALLOWED.get(kind, set())
    out, log_entries, update = [], list(state.get("tool_log", [])), {}
    for tc in last.tool_calls:
        name = tc["name"]
        tool = TOOLS_BY_NAME.get(name)
        if tool is None or name not in allowed:
            content = json.dumps({"ok": False, "error": f"tool {name} not available"})
        else:
            try:
                res = tool.invoke({"name": name, "args": tc["args"], "id": tc["id"], "type": "tool_call"}, config)
                content = res.content if hasattr(res, "content") else str(res)
            except Exception as e:  # validation errors etc. go back to the model, never crash the turn
                content = json.dumps({"ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"})
        out.append(ToolMessage(content=content, tool_call_id=tc["id"], name=name))
        log_entries.append({"name": name, "args": tc["args"], "result": content[:300]})
        if name == "propose_order":
            data = parse_json(content)
            if data.get("ok"):
                update["pending_order"] = data["pending_order"]
                update["propose_summary"] = data["summary"]
    update.update({"messages": out, "tool_log": log_entries, "tool_rounds": state.get("tool_rounds", 0) + 1})
    return update


def proposal(state: AgentState, config: RunnableConfig):
    """Deterministic confirmation prompt: the summary comes straight from the tool, not from the LLM."""
    return {"messages": [AIMessage(content=state["propose_summary"])]}


def place_order(state: AgentState, config: RunnableConfig):
    """Runs only after the customer's own YES (deterministic). create_order is never exposed to the LLM."""
    c = config["configurable"]
    pending = state["pending_order"]
    log_entries = list(state.get("tool_log", []))
    try:
        order = create_order(pending, str(c["store_id"]), c["user_id"], c.get("raw_thread_id", ""))
    except OrderError as e:
        return {
            "messages": [AIMessage(content=f"Sorry, {e}. Please pick another size or item and I'll update your order.")],
            "pending_order": None,
            "active_agent": "order",
        }
    store = stores.get_store_by_id(str(c["store_id"])) or {}
    status = notify_seller(store, order, pending)
    log_entries.append({"name": "create_order", "args": {"pending_id": pending["id"], "items": len(pending["items"])}, "result": f"order DK-{order['order_no']} total {order['total']}"})
    log_entries.append({"name": "notify_seller", "args": {"order_no": order["order_no"]}, "result": status})
    pay = PAY_LABEL.get(pending.get("payment_method"), "Cash on delivery")
    reply = (
        f"Order placed! Your order number is DK-{order['order_no']}. Total: Rs {order['total']:,} ({pay}). "
        f"The seller will contact you on {pending['phone']} to arrange delivery. Thank you for shopping with {store.get('name', 'us')}!"
    )
    summary = ", ".join(f"{l['qty']}x {l['name']} ({l['size']})" for l in order["lines"])
    return {
        "messages": [AIMessage(content=reply)],
        "pending_order": None,
        "order_placed": True,
        "last_order": {"name": pending["customer_name"], "city": pending["city"], "summary": summary},
        "tool_log": log_entries,
    }


def cancel_order(state: AgentState, config: RunnableConfig):
    return {"messages": [AIMessage(content="No problem, I've cancelled that order. Anything else I can help you with?")], "pending_order": None}


def _maybe_summarise(state: AgentState, config: RunnableConfig) -> dict:
    msgs = state.get("messages", [])
    if len(msgs) <= settings.SUMMARISE_AT:
        return {}
    cut = settings.SUMMARISE_COUNT
    while cut < len(msgs) and not isinstance(msgs[cut], HumanMessage):
        cut += 1
    if cut >= len(msgs) - 2:
        return {}
    old = msgs[:cut]
    lines = []
    for m in old:
        t = text_of(m.content).strip()
        if t and isinstance(m, (HumanMessage, AIMessage)):
            lines.append(f"{'Customer' if isinstance(m, HumanMessage) else 'Assistant'}: {t[:300]}")
    prompt = SUMMARY_PROMPT.format(prev=state.get("summary") or "none", lines="\n".join(lines))
    resp = llm_call(get_llm("summary"), [HumanMessage(content=prompt)], config)
    return {"summary": text_of(resp.content).strip(), "messages": [RemoveMessage(id=m.id) for m in old if getattr(m, "id", None)]}


def memory_curator(state: AgentState, config: RunnableConfig):
    out: dict = {}
    sid, uid = state["store_id"], state["user_id"]
    try:
        mem = dict(state.get("memory") or {})
        if state.get("order_placed") and state.get("last_order"):
            o = state["last_order"]
            mem.update(save_memory(sid, uid, {"name": o["name"], "city": o["city"], "last_order_summary": o["summary"]}))
        elif state.get("save_memory") and state.get("budget_mode") == "normal":
            resp = llm_call(get_llm("curator"), [HumanMessage(content=CURATOR_PROMPT.format(msg=last_user_text(state)[:400]))], config)
            data = parse_json(text_of(resp.content))
            if data:
                mem.update(save_memory(sid, uid, data))
        out["memory"] = mem
    except Exception:
        log.exception("memory curation failed (non-fatal)")
    try:
        if state.get("budget_mode") == "normal":
            out.update(_maybe_summarise(state, config))
    except Exception:
        log.exception("summarise failed (non-fatal)")
    return out
