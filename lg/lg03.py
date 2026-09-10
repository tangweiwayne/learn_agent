"""用 LangGraph 重写一遍你的 v3 ReAct 循环。

模型是假的（照台词念），所以不联网、不花钱。
目的：和 v3_agent.py 一行一行对照。

跑法：  python3 lg03.py
"""
import subprocess
import tempfile
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

CWD = tempfile.mkdtemp()
DONE_MARKER = "TASK_DONE"


# ================= ① State = v3 的 self.messages =================
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ================= 假模型：照台词念（= v3 的 MockModel）=================
SCRIPT = [
    ("我先看看目录里有什么。", {"command": "ls -la"}),
    ("建一个文件试试。", {"command": "echo hello > a.txt && cat a.txt"}),
    ("干完了。", {"command": f"echo {DONE_MARKER}"}),
]
_i = [0]


def fake_model(messages):
    text, args = SCRIPT[_i[0]]
    _i[0] += 1
    return AIMessage(
        content=text,
        tool_calls=[{"name": "bash", "args": args, "id": f"call_{_i[0]}"}],
    )


# ================= ② Node 1 = v3 的 query() =================
def call_model(state: AgentState) -> dict:
    message = fake_model(state["messages"])
    print(f"\n===== 模型说 =====\n{message.content}")
    for tc in message.tool_calls:
        print(f"  🔧 {tc['name']}: {tc['args']}")
    return {"messages": [message]}


# ================= ② Node 2 = v3 的 call_tool() + 拼 tool 消息 =================
def run_tools(state: AgentState) -> dict:
    last = state["messages"][-1]
    out = []
    for tc in last.tool_calls:
        r = subprocess.run(tc["args"]["command"], shell=True, cwd=CWD,
                          capture_output=True, text=True, timeout=30)
        observation = (f"<returncode>{r.returncode}</returncode>\n"
                       f"<output>\n{r.stdout}{r.stderr}</output>")
        print(f"----- 执行结果 -----\n{observation}")
        out.append(ToolMessage(content=observation, tool_call_id=tc["id"]))
    return {"messages": out}


# ================= ③ Edge = v3 step() 里那些 if =================
def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, ToolMessage):
        if any(l.strip() == DONE_MARKER for l in last.content.splitlines()):
            return "done"
        return "call_model"
    if not last.tool_calls:
        return "done"
    return "run_tools"


# ================= 画图 =================
builder = StateGraph(AgentState)
builder.add_node("call_model", call_model)
builder.add_node("run_tools", run_tools)
builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", should_continue,
                              {"run_tools": "run_tools", "done": END})
builder.add_conditional_edges("run_tools", should_continue,
                              {"call_model": "call_model", "done": END})
app = builder.compile()


if __name__ == "__main__":
    print(f"工作目录: {CWD}")
    final = app.invoke({
        "messages": [
            SystemMessage(content="你是一个能操作电脑的助手。完成后执行 echo TASK_DONE。"),
            HumanMessage(content="请完成这个任务：随便建个文件"),
        ]
    }, config={"recursion_limit": 40})

    print("\n===== 最终的 messages =====")
    for i, m in enumerate(final["messages"]):
        kind = type(m).__name__
        extra = ""
        if getattr(m, "tool_calls", None):
            extra = "  🔧" + ",".join(tc["name"] for tc in m.tool_calls)
        if getattr(m, "tool_call_id", None):
            extra = f"  ↩{m.tool_call_id}"
        print(f"  [{i}] {kind:<14}{extra}  {str(m.content)[:44]!r}")

    print("\n===== 这张图 =====")
    for line in app.get_graph().draw_mermaid().splitlines():
        if "-->" in line or "-." in line:
            print("  " + line.strip())
