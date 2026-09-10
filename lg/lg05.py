"""看清楚：工位每次【收到】什么、【交出】什么、笔记本【变成】什么。

跑法：  python3 lg05.py     （不联网、不花钱）
"""
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def fmt(m):
    """把一条消息压成一行，方便肉眼看。"""
    kind = type(m).__name__.replace("Message", "")
    tag = ""
    if getattr(m, "tool_calls", None):
        tag = " 🔧" + m.tool_calls[0]["name"]
    if getattr(m, "tool_call_id", None):
        tag = " ↩" + m.tool_call_id
    return f"{kind:<7}{tag:<10} {str(m.content)[:30]!r}"


SCRIPT = [
    ("我先看看目录。", "ls"),
    ("干完了。", "echo TASK_DONE"),
]
_i = [0]


def call_model(state: AgentState) -> dict:
    print("\n" + "─" * 68)
    print("进入工位 call_model")
    print(f"  【收到】state['messages'] 里有 {len(state['messages'])} 条：")
    for k, m in enumerate(state["messages"]):
        print(f"        [{k}] {fmt(m)}")

    text, cmd = SCRIPT[_i[0]]
    _i[0] += 1
    message = AIMessage(content=text,
                        tool_calls=[{"name": "bash", "args": {"command": cmd},
                                     "id": f"call_{_i[0]}"}])

    print(f"  【交出】return {{'messages': [ {fmt(message)} ]}}")
    return {"messages": [message]}


def run_tools(state: AgentState) -> dict:
    print("\n" + "─" * 68)
    print("进入工位 run_tools")
    print(f"  【收到】state['messages'] 里有 {len(state['messages'])} 条，最后一条是：")
    last = state["messages"][-1]
    print(f"        {fmt(last)}")
    out = [ToolMessage(content=f"<假的输出：{tc['args']['command']}>",
                       tool_call_id=tc["id"]) for tc in last.tool_calls]
    print(f"  【交出】return {{'messages': [ {fmt(out[0])} ]}}")
    return {"messages": out}


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, ToolMessage):
        return "done" if "TASK_DONE" in last.content else "call_model"
    return "run_tools"


builder = StateGraph(AgentState)
builder.add_node("call_model", call_model)
builder.add_node("run_tools", run_tools)
builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", should_continue,
                              {"run_tools": "run_tools", "done": END})
builder.add_conditional_edges("run_tools", should_continue,
                              {"call_model": "call_model", "done": END})
app = builder.compile()

print("=" * 68)
print("开工。invoke 传进去的笔记本初始内容 = 2 条消息")
print("=" * 68)
final = app.invoke({"messages": [
    SystemMessage(content="你是一个助手。"),
    HumanMessage(content="随便干点啥"),
]})

print("\n" + "=" * 68)
print(f"跑完，笔记本里一共 {len(final['messages'])} 条：")
print("=" * 68)
for k, m in enumerate(final["messages"]):
    print(f"  [{k}] {fmt(m)}")
