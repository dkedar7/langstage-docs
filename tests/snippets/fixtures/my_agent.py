"""Keyless echo agent: the same graph as docs/getting-started/quickstart.md.

Copied into a page's snippet work dir by `needs=my_agent.py` so blocks that say
`--agent my_agent.py:graph` can run without an API key.
"""
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, MessagesState, StateGraph


def respond(state):
    last = state["messages"][-1].content
    return {"messages": [AIMessage(content=f"You said: {last}")]}


g = StateGraph(MessagesState)
g.add_node("respond", respond)
g.add_edge(START, "respond")
g.add_edge("respond", END)
graph = g.compile()
