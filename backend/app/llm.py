import json
import re
import uuid

from langchain_core.messages import AIMessage, ToolMessage

from . import config, usage

_MAX_TOKENS = {"router": 80, "agent": 350, "curator": 150, "summary": 220}
_cache: dict = {}


class FakeLLM:
    """Free offline stand-in (FAKE_LLM=1) for testing plumbing: DB, memory, checkpoints, API format. Not smart."""

    def __init__(self, role: str, tool_names: list[str]):
        self.role = role
        self.tool_names = tool_names

    @staticmethod
    def _ai(content="", tool_calls=None):
        return AIMessage(
            content=content,
            tool_calls=tool_calls or [],
            usage_metadata={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )

    def invoke(self, messages, config=None):
        raw = str(messages[-1].content)
        low = raw.lower()
        if self.role == "router":
            msg = low.split("message:", 1)[-1].split("\nreply json", 1)[0].strip()
            if any(k in msg for k in ("python", "election", "weather", "poem")):
                intent = "off_topic"
            elif any(k in msg for k in ("buy", "order", "name is", "phone", "address", "chahiye")):
                intent = "order"
            else:
                intent = "browse"
            save = any(k in msg for k in ("my name is", "i wear", "i always", "i love", "i like"))
            return self._ai(json.dumps({"intent": intent, "save_memory": save}))
        if self.role == "curator":
            m = re.search(r"my name is (\w+)", low)
            s = re.search(r"size (xs|s|m|l|xl)\b", low)
            data = {}
            if m:
                data["name"] = m.group(1).title()
            if s:
                data["size_pref"] = s.group(1).upper()
            return self._ai(json.dumps(data))
        if self.role == "summary":
            return self._ai("(fake summary)")
        last = messages[-1]
        if isinstance(last, ToolMessage):
            return self._ai("(fake) " + str(last.content)[:300])
        if "search_catalog" in self.tool_names:
            for w in ("hoodie", "kurta", "tee", "jeans", "cap", "lawn"):
                if w in low:
                    return self._ai("", [{"name": "search_catalog", "args": {"query": w}, "id": "fake_" + uuid.uuid4().hex[:8], "type": "tool_call"}])
        return self._ai("(fake) Hi! Tell me what you are looking for.")


def get_llm(role: str, tools=None):
    names = tuple(sorted(t.name for t in tools)) if tools else ()
    key = (role, names)
    if key in _cache:
        return _cache[key]
    if config.FAKE_LLM:
        llm = FakeLLM(role, list(names))
    else:
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(
            model=config.MODEL_NAME,
            api_key=config.ANTHROPIC_API_KEY,
            max_tokens=_MAX_TOKENS[role],
            timeout=25,
            max_retries=1,
        )
        if tools:
            llm = llm.bind_tools(tools)
    _cache[key] = llm
    return llm


def llm_call(llm, messages, cfg):
    """Invoke and add the token usage to this turn's tracker."""
    resp = llm.invoke(messages)
    usage.record(cfg, resp)
    return resp
