from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]   # short-term memory (checkpointed per store:user:thread)
    summary: str                               # rolling summary of old messages
    store_id: str
    user_id: str
    store: dict                                # slim store profile for prompts
    memory: dict                               # long-term facts for this user (loaded each turn)
    budget_mode: str                           # normal | soft | hard
    route: str                                 # refuse | sales | order | place | cancel
    intent: str
    active_agent: str                          # sales | order (sticky across turns)
    save_memory: bool
    pending_order: Optional[dict]              # proposed order awaiting the customer's YES
    propose_summary: str
    order_placed: bool
    last_order: dict
    tool_log: list                             # tool calls made this turn (returned by /chat)
    tool_rounds: int
