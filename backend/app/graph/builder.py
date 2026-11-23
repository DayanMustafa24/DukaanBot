from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import AgentState


def _after_agent(state: AgentState) -> str:
    last = state["messages"][-1]
    return "tools" if isinstance(last, AIMessage) and getattr(last, "tool_calls", None) else "done"


def _after_tools(state: AgentState) -> str:
    if state.get("propose_summary"):
        return "proposal"
    return state.get("active_agent", "sales")


def build_graph(checkpointer):
    g = StateGraph(AgentState)
    g.add_node("load_context", nodes.load_context)
    g.add_node("guard_router", nodes.guard_router)
    g.add_node("refusal", nodes.refusal)
    g.add_node("sales_agent", nodes.sales_agent)
    g.add_node("order_agent", nodes.order_agent)
    g.add_node("run_tools", nodes.run_tools)
    g.add_node("proposal", nodes.proposal)
    g.add_node("place_order", nodes.place_order)
    g.add_node("cancel_order", nodes.cancel_order)
    g.add_node("memory_curator", nodes.memory_curator)

    g.add_edge(START, "load_context")
    g.add_edge("load_context", "guard_router")
    g.add_conditional_edges(
        "guard_router",
        lambda s: s["route"],
        {"refuse": "refusal", "sales": "sales_agent", "order": "order_agent", "place": "place_order", "cancel": "cancel_order"},
    )
    g.add_edge("refusal", END)
    g.add_conditional_edges("sales_agent", _after_agent, {"tools": "run_tools", "done": "memory_curator"})
    g.add_conditional_edges("order_agent", _after_agent, {"tools": "run_tools", "done": "memory_curator"})
    g.add_conditional_edges("run_tools", _after_tools, {"sales": "sales_agent", "order": "order_agent", "proposal": "proposal"})
    g.add_edge("proposal", "memory_curator")
    g.add_edge("place_order", "memory_curator")
    g.add_edge("cancel_order", END)
    g.add_edge("memory_curator", END)
    return g.compile(checkpointer=checkpointer)
